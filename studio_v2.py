"""
Studio v2 - 小说制作核心引擎

流水线：
  导演(Dir) → 演员(Act) → 写手(Wri) → 五道检查关卡 → (如有问题)重写

每一步都写入审计日志（Markdown + JSON），存在项目文件夹。
"""
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from config import LLMConfig

from agents.v2 import (
    DirectorAgent, ActorAgent, WriterAgent,
    WorldReviewer, CharacterReviewer, PlotReviewer,
    ForeshadowReviewer, AIFlavourDetector, QualityReviewer,
    AgentResult,
)
from project_manager import ProjectManager, AuditEntry
from character_file_manager import CharacterFileManager

logger = logging.getLogger("studio_v2")


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class SceneRecord:
    """单场戏的记录"""
    scene_idx: int
    location: str
    atmosphere: str
    goal: str
    director_decisions: list[str] = field(default_factory=list)  # 导演每轮指令
    actor_lines: list[dict] = field(default_factory=list)  # [{character, text, raw}]
    transition_text: str = ""  # 过渡语


@dataclass
class ChapterResult:
    """章节生成结果"""
    chapter_num: int
    chapter_title: str
    raw_text: str  # 写手产出
    final_text: str  # 经过检查/修改后的最终版本
    scenes: list[SceneRecord]
    dialogue_log: str  # 导演+演员对话记录（供写手参考）
    review_reports: dict  # 各关卡检查报告摘要
    issues_fixed: int  # 修复了多少问题
    issues_remaining: int  # 遗留多少问题
    audit_entries: list[dict]  # 完整审计条目


# ── Studio v2 ──────────────────────────────────────────────

class StudioV2:
    """
    小说制作工作室 v2

    核心流程：
    1. 导演拆解场景 → 每场戏指挥演员轮次
    2. 演员按指令发言（附角色记忆）
    3. 写手把对话记录扩展成网文正文
    4. 五道检查关卡批量审查
    5. 如有问题 → 针对性重写 → 再审
    6. 所有操作写入审计日志

    用法：
        studio = StudioV2(project=pm, llm_config=config.llm)
        result = studio.produce_chapter(
            chapter_num=1,
            chapter_outline="...",
            chapter_title="觉醒",
        )
        print(result.final_text)
    """

    def __init__(
        self,
        project: ProjectManager,
        llm_config: LLMConfig,
        max_turns_per_scene: int = 20,
        max_rewrite_rounds: int = 2,
    ):
        self.project = project
        self.llm = llm_config
        self.max_turns = max_turns_per_scene
        self.max_rewrite_rounds = max_rewrite_rounds

        # 审计钩子：每次Agent调用自动记录
        def audit_hook(agent_name, input_summary, raw_output, result):
            entry = AuditEntry(
                agent=agent_name,
                chapter=0,  # 暂定，后面会更新
                phase="",
                input_summary=input_summary[:200],
                raw_output=raw_output[:500],
                checks_passed=result.checks_passed,
                checks_failed=result.checks_failed,
                issues=[dict(i) for i in result.issues],
            )
            self.project.audit.add(entry)

        # 初始化各 Agent
        self.director = DirectorAgent(llm_config, audit_hook)
        self.writer = WriterAgent(llm_config, audit_hook)

        # 检查关卡（不自动写审计，每个关卡独立检查）
        self.world_reviewer = WorldReviewer(llm_config)
        self.char_reviewer = CharacterReviewer(llm_config)
        self.plot_reviewer = PlotReviewer(llm_config)
        self.foreshadow_reviewer = ForeshadowReviewer(llm_config)
        self.ai_flavour = AIFlavourDetector(llm_config)
        self.quality_reviewer = QualityReviewer(llm_config)

        # 角色文件管理器
        self.cfm = CharacterFileManager(project.project_dir)

        # 运行时状态
        self._current_chapter: int = 0
        self._actor_instances: dict = {}  # 每个角色一个ActorAgent

    # ── 角色演员管理 ──────────────────────────────────────

    def _get_actor(self, character_name: str) -> ActorAgent:
        if character_name not in self._actor_instances:
            self._actor_instances[character_name] = ActorAgent(self.llm)
        return self._actor_instances[character_name]

    def _get_character_profile(self, name: str) -> str:
        """直接读取角色 .md 文件全文（包含记忆、技能、道具、关系）"""
        import os
        # 直接读文件
        char_path = os.path.join(self.project.project_dir, "characters", f"{name}.md")
        if os.path.exists(char_path):
            with open(char_path, "r", encoding="utf-8") as f:
                return f.read()

        # Fallback: 从 characters.md 纯文本中提取
        characters = self.project.get_characters()
        if not characters:
            return f"角色：{name}（无详细资料）"
        lines = characters.split("\n")
        in_section = False
        profile_lines = []
        for line in lines:
            if name in line and any(r in line for r in ["#", "##", "**", "角色", "人物"]):
                in_section = True
            if in_section:
                profile_lines.append(line)
                if len(profile_lines) > 30:
                    break
        return "\n".join(profile_lines[:20]) or characters[:500]

    def _get_character_memory(self, name: str) -> str:
        """从角色文件获取记忆部分"""
        char = self.cfm.get_character(name)
        if char and char.memories:
            recent = char.memories[-5:]
            return "\n".join(f"第{m.chapter}章: {m.summary}" for m in recent)
        return self.project.get_character_memory(name)

    def _save_character_memory(self, name: str, memory: str):
        self.project.save_character_memory(name, memory)

    # ── 核心流程 ──────────────────────────────────────────

    def produce_chapter(
        self,
        chapter_num: int,
        chapter_outline: str,
        chapter_title: str = "",
        foreshadow_notes: str = "",
    ) -> ChapterResult:
        """
        制作一章节的完整流程。
        """
        self._current_chapter = chapter_num
        title = chapter_title or f"第{chapter_num}章"

        logger.info(f"=== Studio v2: {title} 开始 ===")
        self.project.update_status("writing", chapter=chapter_num)

        # 读取前序章节摘要（用于保持连贯性）
        prev_summary = self._load_previous_summaries(chapter_num)

        # 第1步：导演拆解场景
        logger.info("[导演] 拆解章节为场景...")
        scene_plan = self._plan_scenes(chapter_outline, chapter_num, prev_summary=prev_summary)

        scenes: list[SceneRecord] = []
        dialogue_lines: list[str] = []

        # 第2步：每场戏 → 演员轮次
        for si, plan in enumerate(scene_plan):
            scene = self._produce_scene(
                scene_idx=si,
                plan=plan,
                chapter_num=chapter_num,
                prev_dialogue="\n".join(dialogue_lines[-5:]),
            )
            scenes.append(scene)
            for dl in scene.actor_lines:
                subtext = f"  (subtext: {dl['purpose']})" if dl.get('purpose') else ""
                dialogue_lines.append(f"[{dl['character']}] {dl['text']}{subtext}")

        dialogue_log = "\n".join(dialogue_lines)

        # 第3步：写手扩展
        logger.info("[写手] 扩展对话记录为正文...")
        style_guide = self.project.get_style_guide()
        write_result = self.writer.write_from_dialogue(
            dialogue_log=dialogue_log,
            chapter_title=title,
            chapter_outline=chapter_outline,
            foreshadow_notes=foreshadow_notes,
            words_target=self.project.meta.words_per_chapter,
            style_guide=style_guide,
            prev_summary=prev_summary,
        )
        raw_text = write_result.raw

        # 第4步：五道检查关卡
        logger.info("[审查] 五道检查关卡...")
        review_reports = self._run_all_reviews(
            chapter_text=raw_text,
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
        )

        # 汇总问题
        all_issues = []
        for report in review_reports.values():
            if report.issues:
                all_issues.extend(report.issues)

        # 第5步：针对性重写（如有问题）
        final_text = raw_text
        issues_fixed = 0
        issues_remaining = 0

        if all_issues:
            logger.info(f"[重写] 发现 {len(all_issues)} 个问题，开始修复...")
            final_text, issues_fixed, issues_remaining = self._rewrite_until_clean(
                text=raw_text,
                issues=all_issues,
                chapter_title=title,
                chapter_outline=chapter_outline,
            )

        # 第6步：保存
        self._save_chapter_result(
            chapter_num=chapter_num,
            title=title,
            raw_text=raw_text,
            final_text=final_text,
            scenes=scenes,
            review_reports=review_reports,
            issues_fixed=issues_fixed,
            issues_remaining=issues_remaining,
        )

        # 第7步：更新角色记忆
        self._update_character_memories_after_chapter(chapter_num, scenes, final_text)

        # 第8步：生成章节摘要（供后续章节使用）
        self._generate_chapter_summary(chapter_num, title, final_text)

        logger.info(f"=== {title} 完成！修复{issues_fixed}个问题，剩余{issues_remaining} ===")

        return ChapterResult(
            chapter_num=chapter_num,
            chapter_title=title,
            raw_text=raw_text,
            final_text=final_text,
            scenes=scenes,
            dialogue_log=dialogue_log,
            review_reports={k: v.raw[:300] for k, v in review_reports.items()},
            issues_fixed=issues_fixed,
            issues_remaining=issues_remaining,
            audit_entries=[asdict(e) for e in self.project.audit.entries[-20:]],
        )

    # ── 第1步：导演拆解场景 ────────────────────────────────

    def _plan_scenes(self, chapter_outline: str, chapter_num: int, prev_summary: str = "") -> list[dict]:
        """
        让导演把章节大纲拆成场景计划。
        返回 [{location, atmosphere, goal, characters}] 列表。
        """
        result = self.director.plan_chapter(chapter_outline, chapter_num, prev_summary=prev_summary)
        raw = result.raw

        scenes = []
        # 简单解析导演输出，提取场景信息
        # 格式：【第1场】地点 | 氛围 | 目标
        current = None
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 检测场景开始
            m = None
            for kw in ["第1场", "第2场", "第3场", "第4场", "第5场", "第6场",
                       "【第1场】", "【第2场】", "【第3场】", "【第4场】", "【第5场】"]:
                if kw in line:
                    m = re.search(r'[\uff08【(]([^】)\uff09]*)[\uff09】]?\s*([^|\n]+)?', line)
                    break

            if m or "场" in line:
                if current:
                    scenes.append(current)
                parts = line.replace("【", "").replace("】", "").replace("(", "｜").replace(")", "")
                segs = [s.strip() for s in re.split(r'[,，|／/｜]', parts) if s.strip()]
                current = {
                    "location": segs[1] if len(segs) > 1 else "未知地点",
                    "atmosphere": segs[2] if len(segs) > 2 else "平静",
                    "goal": segs[3] if len(segs) > 3 else "推进情节",
                    "characters": [],
                }
            elif current and "角色" in line:
                chars = re.findall(r'[\u4e00-\u9fff]{2,4}', line)
                # 过滤掉"角色"这个字面量和其他非角色名词
                noise_words = {"角色", "在场", "出场", "人物", "包括", "涉及", "参与"}
                chars = [c for c in chars if c not in noise_words]
                current["characters"] = chars

        if current:
            scenes.append(current)

        # 默认保底
        if not scenes:
            scenes = [{"location": "未知地点", "atmosphere": "紧张", "goal": "推进情节", "characters": []}]

        logger.info(f"[导演] 拆解出 {len(scenes)} 场戏")
        return scenes

    # ── 第2步：真·多AI角色对话 ────────────────────────────

    def _produce_scene(
        self,
        scene_idx: int,
        plan: dict,
        chapter_num: int,
        prev_dialogue: str = "",
    ) -> SceneRecord:
        from agents.v2.base import BaseAgentV2

        scene = SceneRecord(
            scene_idx=scene_idx,
            location=plan["location"],
            atmosphere=plan["atmosphere"],
            goal=plan["goal"],
        )

        # 获取在场角色
        characters_text = self.project.get_characters()
        primary_chars = self._extract_primary_characters(characters_text)
        all_known_chars = self.cfm.list_characters() if hasattr(self, 'cfm') and self.cfm else primary_chars
        characters_present = plan.get("characters") or primary_chars[:3]
        # 过滤：只保留真正存在角色档案的名字
        if all_known_chars:
            validated = [c for c in characters_present if any(
                c in k or k in c for k in all_known_chars
            )]
            if validated:
                characters_present = validated
            else:
                characters_present = all_known_chars[:3]

        # 强制保证至少2个角色参与对话（独角戏没意义）
        if len(characters_present) < 2 and all_known_chars:
            for known in all_known_chars:
                if known not in characters_present:
                    characters_present.append(known)
                if len(characters_present) >= 3:
                    break

        # ── NPC生成：严格校验世界观合理性，最多1个龙套 ──
        npc_profiles: dict[str, str] = {}
        # 只有当主角色不足2人且场景确实需要对手时才生成NPC
        world_setting_brief = ""
        try:
            ws = self.project.get_world_setting()
            world_setting_brief = ws[:300] if ws else ""
        except Exception:
            pass

        if len(characters_present) < 2:
            npc_result = BaseAgentV2(self.llm, "").call(
                f"""这场戏主要角色不够，需要一个临时角色（龙套）。

世界观背景（必须严格遵守）：
{world_setting_brief if world_setting_brief else '玄幻修仙世界'}

场景地点：{plan['location']}
场景氛围：{plan['atmosphere']}
场景目标：{plan['goal']}
已有角色：{', '.join(characters_present)}

规则：
- 只生成1个龙套，必须是这个地点合理存在的人（如：宗门大典→长老弟子，黑市→商贩接头人，荒野→猎户旅人）
- 禁止生成与场景不符的角色（如：高端宗门大典不能出现地痞、茶馆伙计、狱卒）
- 输出格式：角色名|身份|性格关键词
- 如果现有角色已够，输出"无"

输出（只输出一行）：""",
                max_tokens=4096,
                input_summary=f"Scene {scene_idx+1}: identify NPC",
            )
            npc_raw = npc_result.raw.strip()
            # 去除思考标签
            for tag in ["<think>", "</think>"]:
                npc_raw = npc_raw.replace(tag, "")
            npc_raw = npc_raw.strip()
            # 取第一行有效内容
            first_line = ""
            for ln in npc_raw.split("\n"):
                ln = ln.strip()
                if ln and "|" in ln:
                    first_line = ln
                    break

            if first_line and "无" not in first_line[:3]:
                parts = first_line.split("|")
                if len(parts) >= 2:
                    npc_name = parts[0].strip()
                    npc_desc = "|".join(parts[1:]).strip()
                    if npc_name and npc_name not in characters_present:
                        npc_profiles[npc_name] = npc_desc
                        characters_present.append(npc_name)

        logger.info(f"[场景{scene_idx+1}] 最终角色列表: {characters_present}，临时龙套: {list(npc_profiles.keys())}")

        # ── 为每个角色创建独立AI实例 ──
        char_agents: dict[str, BaseAgentV2] = {}
        char_names_list = []  # 有序列表
        for name in characters_present:
            profile = self._get_character_profile(name)
            memory = self._get_character_memory(name)

            # 如果是临时龙套角色（无正式档案），用临时描述
            if not profile and name in npc_profiles:
                profile = f"临时角色：{npc_profiles[name]}"
            elif not profile:
                profile = f"龙套角色，在场景中短暂出现"

            system_prompt = f"""You ARE "{name}". You are not playing a role — you are this person.

## Your identity file (may be Chinese — understand it, but follow English instructions)
{profile}

## Your private memories (only you know this)
{memory if memory else '(You just arrived here. No prior memories.)'}

## Current scene
Location: {plan['location']}
Atmosphere: {plan['atmosphere']}

## How you work
Each turn, the director gives you a COMMUNICATION GOAL and a FOCUS POINT.
- Communication goal = what you should try to achieve (e.g. probe, threaten, conceal)
- Focus point = a specific detail to pay attention to (e.g. someone's hand, an object)

The director will NEVER tell you what to say or do. Your lines and actions are 100% your own decision, based on your personality, memories, and current situation.

## Right to resist
The director's instruction is merely an "impulse" in your mind. If it conflicts with your personality or memories:
- You may execute passively: achieve the goal in a more subtle or twisted way
- You may redirect: fold the goal into your own behavioral logic
- You may NOT completely ignore the goal, but HOW you express it is entirely up to you

## Pre-speech self-check (THE MOST IMPORTANT RULE)
Before opening your mouth, answer: "What concrete, practical purpose does this line serve?"
- If you cannot answer → stay silent, write【台词】（无）
- If the purpose is "express emotion" or "show attitude" → use action instead, stay silent
- You only speak when you need to: make someone do something / extract information / stop someone from doing something

Every line of dialogue MUST have a specific, utilitarian purpose. Lines without purpose are waste.

## Output format (strictly these 3 lines, no more)
【目的】What I'm trying to achieve with this action/line: (one sentence, concrete purpose)
【动作】Atomic physical verb. What you did, no adjectives, no rhetoric. e.g. 手握住剑柄, 后退一步, 把杯子推过去
【台词】What you say (in Chinese, matching your speech style). Write（无）if action alone achieves the purpose.

## Actor Protocol v2.0

### No self-certification
NEVER quote your own background lore, professional codes, skill names, or titles in dialogue. Your identity must be shown through IMPACT on others, not through recitation.
BAD: 圣朝律法第三章：自毁法器威胁钦天监使者，罪同谋逆。
GOOD: 你再动一下试试。

### Information conservation
Only say what MUST be said in the current moment. If the other person already knows it, or if an action can convey it — do NOT put it in dialogue.

### Minimal action
Actions must be atomic physical verbs. Leave all rhetoric to the Writer Agent.
BAD:【动作】眼神中闪过一丝挣扎，指尖颤抖地摸向剑柄
GOOD:【动作】手握住剑柄

## Iron laws
- You only know your own affairs. You cannot read others' minds.
- You can only perceive what happens in the current scene.
- Your speech must sound like THIS person would actually talk, not literary prose.
- NEVER repeat or imitate what someone else just said.
- Output exactly ONE turn, never multiple."""

            agent = BaseAgentV2(self.llm, system_prompt)
            char_agents[name] = agent
            char_names_list.append(name)

        # ── 导演AI：控制发言顺序 ──
        director_agent = BaseAgentV2(self.llm, "")

        # ── 开始对话循环 ──
        conversation_log: list[str] = []  # 所有角色可见的公共记录
        max_rounds = 10
        last_speaker = None
        consecutive_count = 0

        scene.director_decisions.append(f"多AI对话模式：{plan['location']}，角色：{characters_present}")

        stale_count = 0  # 连续"打嘴炮"计数
        prev_director_cmd = ""  # 导演上一轮给出的指令
        prev_actor_result = ""  # 演员上一轮的实际执行结果

        for round_num in range(max_rounds):
            # 导演决定谁发言 + 给出指令
            next_speaker, director_instruction = self._director_pick_speaker(
                director_agent=director_agent,
                plan=plan,
                characters=char_names_list,
                conversation_log=conversation_log,
                last_speaker=last_speaker,
                consecutive_count=consecutive_count,
                round_num=round_num,
                max_rounds=max_rounds,
                prev_director_cmd=prev_director_cmd,
                prev_actor_result=prev_actor_result,
            )

            if next_speaker == "END":
                logger.info(f"[场景{scene_idx+1}] 导演判定场景目标完成，结束对话")
                break

            # 严格锁定角色名单：导演只能从已确定的角色里选，禁止凭空创建
            matched = self._match_character(next_speaker, char_names_list)
            if not matched:
                logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] 导演选了不存在的角色'{next_speaker}'，强制轮转")
                matched = char_names_list[round_num % len(char_names_list)]
            next_speaker = matched
            if director_instruction:
                logger.info(f"[场景{scene_idx+1}][R{round_num+1}] 导演指令→{next_speaker}: {director_instruction[:50]}")

            # 连发限制
            if next_speaker == last_speaker:
                consecutive_count += 1
                if consecutive_count > 2:
                    others = [n for n in char_names_list if n != last_speaker]
                    next_speaker = others[round_num % len(others)] if others else char_names_list[0]
                    consecutive_count = 1
            else:
                consecutive_count = 1
            last_speaker = next_speaker

            # ── 检查是否需要注入物理事件（连续2轮嘴炮） ──
            inject_event = ""
            if stale_count >= 2:
                event_result = director_agent.call(
                    f"""对话陷入空转，你必须制造一个突发物理事件来打断僵局。

当前场景：{plan['location']}（{plan['atmosphere']}）
场景目标：{plan['goal']}
最近对话：
{chr(10).join(conversation_log[-4:])}

要求：
- 生成一个符合当前场景的突发事件（如有人闯入、物体碎裂、环境突变、暗器袭来等）
- 必须是物理层面的变化，不是心理活动
- 一句话，不超过30字
- 只输出事件本身，不加任何解释

突发事件：""",
                    max_tokens=4096,
                    input_summary=f"Scene {scene_idx+1}: inject physical event",
                )
                inject_event = event_result.raw.strip()[:60]
                if inject_event:
                    conversation_log.append(f"【环境】{inject_event}")
                    scene.actor_lines.append({
                        "character": "环境",
                        "text": inject_event,
                        "raw": f"【环境】{inject_event}",
                    })
                    logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] 检测到打嘴炮，导演注入事件：{inject_event}")
                stale_count = 0

            # 构建该角色看到的对话历史
            visible_log = "\n".join(conversation_log[-10:]) if conversation_log else "（场景刚开始，还没人说话）"
            if prev_dialogue and round_num == 0:
                visible_log = f"（前情）{prev_dialogue[-300:]}\n{visible_log}"

            event_hint = f"\n\n⚠ SUDDEN EVENT just happened: {inject_event}. You MUST react to this. You cannot ignore it." if inject_event else ""

            # Director's intent (communication goal + focus point)
            if director_instruction:
                direction_section = f"""
## The impulse rising in your mind right now (from the director)
{director_instruction}

Remember: this is only an impulse. How you express it — what you say, what you do — is entirely determined by YOUR personality and YOUR memories. The director cannot speak for you."""
            else:
                direction_section = "\n(No specific direction from the director. React freely based on the scene.)"

            actor_prompt = f"""It's your turn now.

## Scene goal
{plan['goal']}

## What you see and hear (dialogue history, may be Chinese)
{visible_log}{event_hint}
{direction_section}

Now, as {next_speaker}, what do you do?
Consider your personality, your memories, and your current situation. Give your authentic reaction.

Output exactly ONE turn (three lines):
【目的】What I'm trying to achieve: ...
【动作】(atomic physical action, in Chinese)
【台词】(in Chinese, matching your speech style. Write（无）if action alone achieves the purpose)"""

            # 调用该角色的独立AI
            agent = char_agents[next_speaker]
            result = agent.call(
                actor_prompt,
                max_tokens=4096,
                input_summary=f"Scene {scene_idx+1} R{round_num+1}: {next_speaker}",
            )

            raw_response = result.raw.strip()
            # 防御：如果AI返回空，重试一次
            if not raw_response or raw_response.startswith("[ERROR"):
                logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] {next_speaker} 返回空，重试...")
                result = agent.call(actor_prompt, max_tokens=4096, input_summary=f"Retry {next_speaker}")
                raw_response = result.raw.strip()

            # 解析角色输出（目的+动作+台词）
            purpose = ""
            action = ""
            dialogue = ""
            for line in raw_response.split("\n"):
                line = line.strip()
                m = re.match(r'【目的】\s*(.*)', line)
                if m:
                    purpose = m.group(1).strip()
                    continue
                m = re.match(r'【动作】\s*(.*)', line)
                if m:
                    action = m.group(1).strip()
                    continue
                m = re.match(r'【台词】\s*(.*)', line)
                if m:
                    dialogue = m.group(1).strip()
                    continue
            if purpose:
                logger.info(f"[{next_speaker}目的] {purpose[:40]}")

            # 组装成公共记录
            parts = []
            if action:
                parts.append(action)
            if dialogue and dialogue != "（无）":
                parts.append(dialogue)
            text = " ".join(parts) if parts else raw_response[:100]

            # ── 话题熔断：滑动窗口检测最近3轮是否原地打转 ──
            if dialogue and len(conversation_log) >= 1:
                # 检查与上一轮的相似度
                prev_text = conversation_log[-1]
                similarity = self._text_similarity(dialogue, prev_text)
                # 检查与最近3轮的平均相似度（话题是否在循环）
                topic_stuck = False
                if len(conversation_log) >= 3:
                    recent_sims = [self._text_similarity(dialogue, log) for log in conversation_log[-3:]]
                    avg_sim = sum(recent_sims) / len(recent_sims)
                    if avg_sim > 0.25:
                        topic_stuck = True
                        logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] 话题熔断！最近3轮平均相似度{avg_sim:.0%}，对话陷入死循环")

                if similarity > 0.30 or topic_stuck:
                    stale_count += 1
                    if stale_count >= 2:
                        # 熔断：强制结束场景，不再废话
                        logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] 连续{stale_count}次嘴炮，强制结束场景")
                        conversation_log.append(f"【{next_speaker}】{text}")
                        scene.actor_lines.append({"character": next_speaker, "text": text, "raw": f"【{next_speaker}】{text}"})
                        break
                    else:
                        # 第一次：要求重写，给一次机会
                        logger.warning(f"[场景{scene_idx+1}][R{round_num+1}] {next_speaker} 复读检测触发，要求重写")
                        retry_prompt = f"""Your last line was too similar to the recent dialogue. REJECTED.

Recent dialogue:
{chr(10).join(conversation_log[-2:])}

You CANNOT repeat topics or phrasing. You must use a concrete physical action to change the situation (e.g. stand up and leave, grab something, physically interrupt someone).

Ask yourself: what is my PURPOSE right now? Output three lines:
【目的】……
【动作】……
【台词】……（write（无）if action alone achieves the purpose）"""
                        result2 = agent.call(retry_prompt, max_tokens=4096, input_summary=f"Anti-repeat {next_speaker}")
                        raw2 = result2.raw.strip()
                        action2, dialogue2 = "", ""
                        for ln in raw2.split("\n"):
                            ln = ln.strip()
                            ma = re.match(r'【动作】\s*(.*)', ln)
                            if ma:
                                action2 = ma.group(1).strip()
                            md = re.match(r'【台词】\s*(.*)', ln)
                            if md:
                                dialogue2 = md.group(1).strip()
                        if action2 or dialogue2:
                            action = action2 or action
                            dialogue = dialogue2 or dialogue
                            parts = []
                            if action:
                                parts.append(action)
                            if dialogue and dialogue != "（无）":
                                parts.append(dialogue)
                            text = " ".join(parts) if parts else text
                else:
                    stale_count = 0
            else:
                stale_count = 0

            # 写入公共对话记录（所有角色下一轮都能看到）
            conversation_log.append(f"【{next_speaker}】{text}")

            # 写入场景记录（包含purpose供写手参考）
            scene.actor_lines.append({
                "character": next_speaker,
                "text": text,
                "raw": f"【{next_speaker}】{text}",
                "purpose": purpose,
            })

            logger.info(f"[场景{scene_idx+1}][R{round_num+1}] {next_speaker}: {text[:60]}...")

            # 记录本轮导演指令和演员结果，供下一轮导演参考
            prev_director_cmd = f"{next_speaker}|{director_instruction}" if director_instruction else ""
            prev_actor_result = f"{next_speaker}: {text[:80]}"

        logger.info(f"[场景{scene_idx+1}] {plan['location']} - {len(scene.actor_lines)}轮对话（多AI模式，{len(scene.actor_lines)}次API调用）")
        return scene

    @staticmethod
    def _text_similarity(text_a: str, text_b: str) -> float:
        """基于字符级 bigram 的 Jaccard 相似度（轻量、无依赖）"""
        if not text_a or not text_b:
            return 0.0
        def bigrams(s):
            s = re.sub(r'[【】\s]', '', s)
            return set(s[i:i+2] for i in range(len(s) - 1)) if len(s) >= 2 else {s}
        a, b = bigrams(text_a), bigrams(text_b)
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _director_pick_speaker(
        self,
        director_agent: "BaseAgentV2",
        plan: dict,
        characters: list[str],
        conversation_log: list[str],
        last_speaker: str | None,
        consecutive_count: int,
        round_num: int,
        max_rounds: int,
        prev_director_cmd: str = "",
        prev_actor_result: str = "",
    ) -> tuple[str, str]:
        """导演决定下一个行动的角色+给出意图指令（不是台词），返回 (角色名, 意图指令) 或 ("END", "")"""
        log_text = "\n".join(conversation_log[-8:]) if conversation_log else "（还没开始）"

        # 导演回顾：上一轮我指示了什么，演员实际做了什么
        review_section = ""
        if prev_director_cmd and prev_actor_result:
            review_section = f"""
## Your last instruction vs what actually happened
Your instruction: {prev_director_cmd}
Actor's actual response: {prev_actor_result}
(If the actor deviated from your intent, adjust your next instruction accordingly. Do NOT repeat the same instruction.)
"""

        prompt = f"""You are the DIRECTOR. Your job is to deal cards, not write scripts.

## Scene goal
{plan['goal']}

## Characters present
{', '.join(characters)}

## Dialogue so far ({len(conversation_log)} rounds, max {max_rounds})
{log_text}

## Last speaker
{last_speaker or 'none'} (consecutive: {consecutive_count})
{review_section}
## Your duties
1. Pick the next character to act (cannot be the same as last speaker more than 2 times in a row)
2. Give a COMMUNICATION GOAL: what this character should try to achieve this turn (e.g. probe, threaten, conceal, reveal, provoke)
3. Give a FOCUS POINT: a specific concrete detail to focus on (e.g. the other person's trembling hand, the map on the table, footsteps outside)

## FORBIDDEN
- Do NOT write specific dialogue (e.g. "say: the tea is cold")
- Do NOT dictate specific actions (e.g. "draw sword", "smash cup") — the actor decides actions
- Do NOT dictate specific emotions (e.g. "angry", "sad") — emotions emerge from the actor

You control the skeleton (conflict direction). Actors grow the flesh (lines and actions).

## Output format (strictly one line)
CHARACTER_NAME|COMMUNICATION_GOAL|FOCUS_POINT

Examples:
林默|observe everyone's reaction to "passage of time" through a pretext|the old woman's hand on the key
周半仙|probe whether the other person knows about the secret tunnel entrance|micro-expression when "east wall" is mentioned

If the scene goal is achieved or dialogue is sufficient, output: END

Next:"""

        result = director_agent.call(
            prompt,
            max_tokens=4096,
            input_summary=f"Director pick speaker R{round_num+1}",
        )
        raw = result.raw.strip()
        # 去除思考模型可能输出的标签
        for tag in ["<think>", "</think>"]:
            raw = raw.replace(tag, "")
        raw = raw.strip()
        # 取第一个有效行（跳过空行）
        pick = ""
        for line in raw.split("\n"):
            line = line.strip().replace("【", "").replace("】", "")
            if line:
                pick = line
                break

        # 结束判定
        if not pick or "END" in pick.upper() or "结束" in pick:
            return ("END", "")

        # 解析 "角色名|交际目标|关注点" → 合并为意图指令
        instruction = ""
        if "|" in pick:
            parts = [p.strip() for p in pick.split("|")]
            pick = parts[0]
            goal = parts[1] if len(parts) > 1 else ""
            focus = parts[2] if len(parts) > 2 else ""
            instruction = f"交际目标：{goal}" if goal else ""
            if focus:
                instruction += f"\n关注点：{focus}"
        elif "：" in pick or ":" in pick:
            parts = re.split(r'[：:]', pick, 1)
            pick = parts[0].strip()
            instruction = parts[1].strip() if len(parts) > 1 else ""

        # 匹配角色名
        for char in characters:
            if char in pick:
                return (char, instruction)

        return (pick, instruction)

    def _extract_primary_characters(self, characters_text: str) -> list[str]:
        """从角色设定中提取主要角色名"""
        if not characters_text:
            return ["主角", "配角"]
        names = re.findall(r'^#+\s*[\*\*]?([\u4e00-\u9fff]{2,4})', characters_text, re.MULTILINE)
        if not names:
            names = re.findall(r'([\u4e00-\u9fff]{2,4})[:：]', characters_text)
        return names[:5] if names else ["主角"]

    def _match_character(self, char: str, available: list[str]) -> str | None:
        """模糊匹配角色名"""
        if char in available:
            return char
        for av in available:
            if char in av or av in char:
                return av
        return None

    # ── 章节摘要（前情提要）──────────────────────────────────

    def _generate_chapter_summary(self, chapter_num: int, title: str, final_text: str):
        """用 LLM 为本章生成摘要，存到 summaries/ 目录"""
        from agents.v2.base import BaseAgentV2
        import os

        prompt = f"""请为小说的"{title}"写一段前情摘要。

正文：
{final_text[:2000]}

要求：
- 3-5句话，不超过150字
- 只写关键事件：谁做了什么、发生了什么转折、留下了什么悬念
- 不要形容词堆砌，不要评论，只陈述事实
- 用"本章"开头

输出摘要（仅一段）："""

        agent = BaseAgentV2(self.llm, "")
        result = agent.call(prompt, max_tokens=4096, input_summary=f"Chapter {chapter_num} summary")

        summary = result.raw.strip()[:200]
        if not summary:
            summary = f"第{chapter_num}章内容"

        # 保存到 summaries/chapter_NNN_summary.md
        summaries_dir = os.path.join(self.project.project_dir, "summaries")
        os.makedirs(summaries_dir, exist_ok=True)
        path = os.path.join(summaries_dir, f"chapter_{chapter_num:03d}_summary.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title} 摘要\n\n{summary}\n")

        logger.info(f"[摘要] 第{chapter_num}章摘要已保存：{summary[:50]}...")

    def _load_previous_summaries(self, chapter_num: int) -> str:
        """加载第1章到第N-1章的所有摘要，拼成前情提要"""
        import os

        if chapter_num <= 1:
            return ""

        summaries_dir = os.path.join(self.project.project_dir, "summaries")
        if not os.path.exists(summaries_dir):
            return ""

        parts = []
        for i in range(1, chapter_num):
            path = os.path.join(summaries_dir, f"chapter_{i:03d}_summary.md")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # 去掉标题行，只保留摘要内容
                    lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
                    if lines:
                        parts.append(f"第{i}章：{''.join(lines)}")

        if not parts:
            return ""

        return "【前情提要】\n" + "\n".join(parts)

    def _update_character_memories_after_chapter(self, chapter_num: int, scenes: list, final_text: str):
        """章节结束后，用 LLM 为每个出场角色生成本章记忆摘要"""
        from agents.v2.base import BaseAgentV2

        # 获取所有已知角色名
        all_known_chars = self.cfm.list_characters()
        logger.info(f"[记忆更新] 已知角色: {all_known_chars}")

        # 从 actor_lines 收集对话（严格匹配的角色）
        char_dialogue: dict[str, list[str]] = {}
        for scene in scenes:
            for actor_line in scene.actor_lines:
                char = actor_line.get("character", "")
                text = actor_line.get("text", "")
                if char and text:
                    char_dialogue.setdefault(char, []).append(text)

        # 补充：从 raw 对话中模糊匹配已知角色（防止 _match_character 过滤时丢失）
        for scene in scenes:
            for actor_line in scene.actor_lines:
                raw = actor_line.get("raw", "")
                if not raw:
                    continue
                m = re.match(r'【([^】]+)】\s*(.+)', raw)
                if m:
                    raw_name = m.group(1).strip()
                    text = m.group(2).strip()
                    # 尝试匹配到已知角色
                    for known in all_known_chars:
                        if known in raw_name or raw_name in known:
                            if known not in char_dialogue:
                                char_dialogue[known] = []
                            char_dialogue[known].append(text)
                            break

        # 对于已知角色中出场但没有对话记录的，用正文匹配
        for known in all_known_chars:
            if known not in char_dialogue and known in final_text:
                char_dialogue[known] = [f"（在本章正文中被提及）"]

        logger.info(f"[记忆更新] 本章出场角色: {list(char_dialogue.keys())}")

        summary_agent = BaseAgentV2(self.llm, "")

        for char_name, lines in char_dialogue.items():
            profile = self.cfm.get_character(char_name)
            if not profile:
                continue

            # 拼接该角色的全部对话/动作
            dialogue_block = "\n".join(f"- {l[:120]}" for l in lines[:10])

            prompt = f"""请为小说角色"{char_name}"总结第{chapter_num}章的记忆。

角色在本章中自己说的话和做的事：
{dialogue_block}

要求：
- 只写这个角色自己的视角：他/她亲眼看到、亲耳听到、亲手做的事
- 禁止包含其他角色私下的行为或心理（角色不可能知道的事不能写进记忆）
- 用第一人称"我"来写
- 分两部分，用"→"分隔：
  第一部分（事实）：去了哪里、做了什么、对谁说了什么、得到或失去了什么
  第二部分（心理）：经历这些事之后，我现在的情绪状态、对某人的态度变化、接下来想做什么
- 不超过120字
- 格式示例："我在黑市从线人处打听到遗藏图的下落；被苏夜拦住盘问，趁乱脱身 → 对苏夜产生警惕，下次遇到要先发制人；急需找到遗藏图的买主"
- 再举一例："我在比武中输给了陈风，当众被羞辱 → 感到屈辱和愤怒，决心私下找机会报复陈风"

输出记忆（仅一行）："""

            result = summary_agent.call(
                prompt,
                max_tokens=4096,
                input_summary=f"Memory summary: {char_name} ch{chapter_num}",
            )

            summary = result.raw.strip().replace("\n", "；")[:120]
            if not summary:
                summary = f"出现在第{chapter_num}章"

            self.cfm.add_memory(char_name, chapter_num, summary)
            logger.info(f"更新角色记忆: {char_name} 第{chapter_num}章 → {summary[:40]}...")

    # ── 第4步：五道检查关卡 ────────────────────────────────

    def _run_all_reviews(self, chapter_text: str, chapter_num: int, chapter_outline: str) -> dict:
        reports = {}

        # 关卡1：世界观
        logger.info("  [检查1/5] 世界观一致性...")
        reports["world"] = self.world_reviewer.review(
            chapter_text=chapter_text,
            world_setting=self.project.get_world_setting(),
        )
        self._log_review("world", chapter_num, reports["world"])

        # 关卡2：人物
        logger.info("  [检查2/5] 人物一致性...")
        reports["character"] = self.char_reviewer.review(
            chapter_text=chapter_text,
            characters=self.project.get_characters(),
        )
        self._log_review("character", chapter_num, reports["character"])

        # 关卡3：剧情架构
        logger.info("  [检查3/5] 剧情架构...")
        reports["plot"] = self.plot_reviewer.review(
            chapter_text=chapter_text,
            chapter_outline=chapter_outline,
        )
        self._log_review("plot", chapter_num, reports["plot"])

        # 关卡4：伏笔
        logger.info("  [检查4/5] 伏笔管理...")
        reports["foreshadow"] = self.foreshadow_reviewer.review(
            chapter_text=chapter_text,
            chapter_num=chapter_num,
            foreshadow_plan=self.project.get_foreshadow_plan(),
        )
        self._log_review("foreshadow", chapter_num, reports["foreshadow"])

        # 关卡5：AI味
        logger.info("  [检查5/5] AI味检测...")
        reports["ai_flavour"] = self.ai_flavour.detect(chapter_text=chapter_text)
        self._log_review("ai_flavour", chapter_num, reports["ai_flavour"])

        # 质量终检
        logger.info("  [终检] 质量评估...")
        reports["quality"] = self.quality_reviewer.evaluate(
            chapter_text=chapter_text,
            chapter_outline=chapter_outline,
        )
        self._log_review("quality", chapter_num, reports["quality"])

        # 保存 AI 味报告
        self.project.save_ai_flavour(chapter_num, reports["ai_flavour"].raw)

        return reports

    def _log_review(self, check_type: str, chapter_num: int, result: AgentResult):
        """把检查结果写入审计日志 + 检查报告文件"""
        # 审计日志
        entry = AuditEntry(
            agent=check_type,
            chapter=chapter_num,
            phase="review",
            raw_output=result.raw[:500],
            checks_passed=result.checks_passed,
            checks_failed=result.checks_failed,
            issues=[dict(i) for i in result.issues],
        )
        self.project.audit.add(entry)

        # 检查报告文件
        self.project.save_review(
            chapter=chapter_num,
            scope=check_type,
            report_md=f"# {check_type} 检查报告（第{chapter_num}章）\n\n{result.raw}",
        )

    # ── 第5步：重写 ───────────────────────────────────────

    def _rewrite_until_clean(
        self,
        text: str,
        issues: list[dict],
        chapter_title: str,
        chapter_outline: str,
    ) -> tuple:
        """
        循环重写，直到所有问题解决或达到最大轮次。

        流程：
        1. 按检查类型合并同类问题，一次性让写手重写所有问题
        2. 用重写结果替换原文
        3. 重新跑所有检查（因为修改可能引入新问题）
        4. 重复直到干净或达到上限

        返回 (final_text, fixed_count, remaining_count)
        """
        current = text
        total_fixed = 0

        for round_num in range(1, self.max_rewrite_rounds + 1):
            if not issues:
                logger.info(f"  [重写轮次{round_num}] 无待处理问题")
                break

            logger.info(f"  [重写轮次{round_num}] 待修复 {len(issues)} 个问题...")

            # 按类型分组（同一类型的问题合并成一条重写指令）
            by_type: dict[str, list[dict]] = {}
            for iss in issues:
                t = iss.get("type", "general")
                by_type.setdefault(t, []).append(iss)

            # 拼装重写指令（所有问题一次处理）
            rewrite_instruction = self._build_rewrite_instruction(by_type, round_num)
            logger.info(f"  [重写轮次{round_num}] 调用写手重写...")

            rewrite_result = self.writer.rewrite_segment(
                original_segment=current,
                problem_description=f"第{round_num}轮重写：修复 {len(issues)} 个问题。【重要】输出必须保持原文的完整长度（约{len(current)}字），只修改有问题的部分，其他内容原样保留。",
                rewrite_guidance=rewrite_instruction,
            )

            new_text = rewrite_result.raw.strip()

            # 如果写手返回了有效内容，替换原文
            if new_text and not new_text.startswith("[ERROR]") and len(new_text) > 100:
                logger.info(f"  [重写轮次{round_num}] 写手返回 {len(new_text)} 字，接替审查...")
                current = new_text

                # 用新文本重新跑所有检查
                review_reports = self._run_all_reviews(
                    chapter_text=current,
                    chapter_num=self._current_chapter,
                    chapter_outline=chapter_outline,
                )

                # 统计本轮结果
                all_new_issues: list[dict] = []
                for r in review_reports.values():
                    all_new_issues.extend(r.issues)

                issues = all_new_issues
                fixed_this_round = len(issues)  # approximate
                total_fixed += fixed_this_round

                # 检查是否需要整章重写（Quality 判定）
                quality_report = review_reports.get("quality")
                needs_full_rewrite = (
                    quality_report is not None
                    and quality_report.metadata.get("needs_rewrite", False)
                )

                if needs_full_rewrite and round_num < self.max_rewrite_rounds:
                    logger.warning(f"  [重写轮次{round_num}] 质量不达标，进入整章重写模式...")
                    # 整章重写：把大纲+对话记录+检查报告一并给写手
                    full_result = self.writer.write_from_dialogue(
                        dialogue_log=self._get_dialogue_log(),
                        chapter_title=chapter_title,
                        chapter_outline=chapter_outline,
                        foreshadow_notes=self.project.get_foreshadow_plan(),
                        words_target=self.project.meta.words_per_chapter,
                        style_guide=self.project.get_style_guide(),
                    )
                    current = full_result.raw.strip()
                    # 重写后不再检查（避免无限循环）
                    issues = []

                logger.info(
                    f"  [重写轮次{round_num}] 完成，剩余 {len(issues)} 个问题"
                )
            else:
                # 写手返回无效内容，保留原文，记录失败
                logger.warning(f"  [重写轮次{round_num}] 写手返回无效内容，跳过")
                break

            # 保存重写报告
            self.project.save_review(
                chapter=self._current_chapter,
                scope=f"rewrite_{round_num}",
                report_md=(
                    f"# 重写报告（第{self._current_chapter}章，第{round_num}轮）\n\n"
                    f"修复了约 {len(issues)} 个问题\n\n"
                    f"## 写手输出\n{rewrite_result.raw[:500]}"
                ),
            )

            if not issues:
                break

        remaining = sum(1 for iss in issues if not iss.get("fixed"))
        return current, total_fixed, remaining

    def _build_rewrite_instruction(
        self,
        by_type: dict[str, list[dict]],
        round_num: int,
    ) -> str:
        """把分组后的问题拼成一条重写指令给写手"""
        lines = [
            f"【第{round_num}轮重写指令】",
            "请逐一修复以下问题，每次只改问题段落，不要改动其他内容：",
            "",
        ]
        for iss_type, type_issues in by_type.items():
            lines.append(f"\n## [{iss_type}] 共 {len(type_issues)} 个问题：")
            for i, iss in enumerate(type_issues, 1):
                loc = iss.get("location", "整章")
                problem = iss.get("problem", "")
                suggestion = iss.get("suggestion", "")
                lines.append(f"\n{i}. 位置：{loc}")
                lines.append(f"   问题：{problem}")
                if suggestion:
                    lines.append(f"   建议：{suggestion}")

        lines.append(
            "\n\n要求：只修改问题段落，其他内容保持原样。"
            "输出完整修改后的段落，不要加任何解释。"
        )
        return "\n".join(lines)

    def _get_dialogue_log(self) -> str:
        """获取当前章节的对话记录（供整章重写用）"""
        return self.project.get_review(
            chapter=self._current_chapter,
            scope="dialogue_log",
        )

    # ── 第6步：保存 ──────────────────────────────────────

    def _save_chapter_result(
        self,
        chapter_num: int,
        title: str,
        raw_text: str,
        final_text: str,
        scenes: list[SceneRecord],
        review_reports: dict,
        issues_fixed: int,
        issues_remaining: int,
    ):
        # 保存章节正文（用最终版本）
        self.project.save_chapter(chapter_num, title, final_text)

        # 保存导演+演员对话记录
        dialogue_lines = []
        for scene in scenes:
            dialogue_lines.append(f"\n## 场景{scene.scene_idx + 1}: {scene.location}")
            for dl in scene.actor_lines:
                dialogue_lines.append(f"**{dl['character']}**: {dl['text']}")

        self.project.save_review(
            chapter=chapter_num,
            scope="dialogue_log",
            report_md=f"# 对话记录（第{chapter_num}章）\n\n" + "\n".join(dialogue_lines),
        )

        # 更新项目状态
        self.project.update_status("writing", chapter=chapter_num)

        logger.info(f"  已保存第{chapter_num}章：{title}")
