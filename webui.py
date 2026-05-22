"""
Web UI v2 - 对接 StudioV2 项目架构

路由：
  GET  /                  - 主界面
  POST /api/projects      - 创建项目
  GET  /api/projects      - 列出所有项目
  GET  /api/projects/<id> - 获取项目详情
  POST /api/projects/<id>/generate - 生成指定章节
  GET  /api/projects/<id>/chapters  - 获取章节列表
  GET  /api/projects/<id>/chapters/<n> - 获取章节正文
  GET  /api/projects/<id>/audit    - 获取审计日志
  GET  /api/projects/<id>/reviews/<scope> - 获取检查报告
  GET  /api/projects/<id>/ai_flavour/<n> - 获取AI味报告
  GET  /api/events/<id>  - SSE进度流
"""
import json
import logging
import os
import re
import sys
import threading
import uuid
from queue import Queue

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response

from config import NovelConfig, LLMConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.jinja_env.variable_start_string = "<<"
app.jinja_env.variable_end_string = ">>"
app.jinja_env.block_start_string = "<%"
app.jinja_env.block_end_string = "%>"

# 全局：当前激活的项目
active_projects: dict[str, dict] = {}  # project_id -> {pm, studio, config, status, event_queue}
event_queues: dict[str, Queue] = {}


def get_project(project_id: str):
    return active_projects.get(project_id)


def send_event(project_id: str, step: str, progress: float, detail: str = ""):
    if project_id in event_queues:
        event_queues[project_id].put({"step": step, "progress": progress, "detail": detail})


# ===== 页面路由 =====

@app.route("/")
def index():
    return render_template("index_v2.html")


@app.route("/test")
def test():
    return render_template("test.html")


# ===== 项目管理 API =====

@app.route("/api/projects", methods=["POST"])
def api_create_project():
    """创建新项目"""
    data = request.json or {}

    title = data.get("title", "未命名小说")
    # 生成项目ID（用标题拼音或简单slug）
    project_id = data.get("project_id", title.replace(" ", "_").replace("/", "_"))

    if project_id in active_projects:
        return jsonify({"error": f"项目 {project_id} 已在运行中"}), 400

    llm_config = LLMConfig(
        api_key=data.get("api_key", os.getenv("OPENAI_API_KEY", "")),
        base_url=data.get("base_url", os.getenv("OPENAI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")),
        model=data.get("model", "mimo-v2.5-pro"),
        temperature=float(data.get("temperature", 0.7)),
        max_tokens=int(data.get("max_tokens", 4096)),
    )

    if not llm_config.api_key:
        return jsonify({"error": "请提供 API Key"}), 400

    try:
        from project_manager import ProjectManager
        pm = ProjectManager(project_root="novel-engine/projects")
        pm.create(
            title=title,
            genre=data.get("genre", "玄幻"),
            tone=data.get("tone", "热血、紧凑"),
            chapter_count=int(data.get("chapter_count", 10)),
            words_per_chapter=int(data.get("words_per_chapter", 3000)),
            model=llm_config.model,
        )

        event_queue = Queue()
        event_queues[project_id] = event_queue

        novel_config = NovelConfig(
            title=title,
            genre=data.get("genre", "玄幻"),
            tone=data.get("tone", "热血、紧凑"),
            chapter_count=int(data.get("chapter_count", 10)),
            words_per_chapter=int(data.get("words_per_chapter", 3000)),
            llm=llm_config,
        )

        active_projects[project_id] = {
            "pm": pm,
            "config": novel_config,
            "llm_config": llm_config,
            "status": "planning",
            "current_chapter": 0,
        }

        send_event(project_id, "项目创建", 0.01, f"项目 '{title}' 已创建")
        logger.info(f"项目已创建: {project_id}")

        return jsonify({
            "message": "项目已创建",
            "project_id": project_id,
            "project_path": pm.project_path,
        })
    except FileExistsError:
        return jsonify({"error": f"项目 '{project_id}' 已存在"}), 409
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects", methods=["GET"])
def api_list_projects():
    """列出所有项目"""
    from project_manager import ProjectManager
    projects = ProjectManager.list_projects("novel-engine/projects")
    running = [{"id": k, "status": v["status"], "chapter": v["current_chapter"]}
               for k, v in active_projects.items()]
    return jsonify({
        "projects": projects,
        "running": running,
    })


@app.route("/api/projects/<project_id>", methods=["GET"])
def api_get_project(project_id: str):
    """获取项目详情"""
    if project_id in active_projects:
        p = active_projects[project_id]
        pm = p["pm"]
        meta = pm.meta
        return jsonify({
            "project_id": project_id,
            "status": p["status"],
            "current_chapter": p["current_chapter"],
            "meta": {
                "title": meta.title,
                "genre": meta.genre,
                "tone": meta.tone,
                "chapter_count": meta.chapter_count,
                "words_per_chapter": meta.words_per_chapter,
                "status": meta.status,
                "created_at": meta.created_at,
                "last_modified": meta.last_modified,
            },
            "chapters_done": pm.get_chapters_done(),
        })

    # 从磁盘加载
    from project_manager import ProjectManager
    try:
        pm = ProjectManager.load(os.path.join("novel-engine", "projects", project_id))
        meta = pm.meta
        return jsonify({
            "project_id": project_id,
            "status": meta.status,
            "current_chapter": meta.current_chapter,
            "meta": {
                "title": meta.title,
                "genre": meta.genre,
                "tone": meta.tone,
                "chapter_count": meta.chapter_count,
                "words_per_chapter": meta.words_per_chapter,
                "status": meta.status,
                "created_at": meta.created_at,
                "last_modified": meta.last_modified,
            },
            "chapters_done": pm.get_chapters_done(),
        })
    except FileNotFoundError:
        return jsonify({"error": "项目不存在"}), 404


# ===== 风格参考 API =====

@app.route("/api/projects/<project_id>/style_reference", methods=["POST"])
def api_upload_style_reference(project_id: str):
    """上传风格参考（文件或文本）"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404

    text = ""

    # 方式1：文件上传
    if "file" in request.files:
        f = request.files["file"]
        if f.filename:
            raw = f.read()
            for enc in ("utf-8", "gbk", "gb18030", "big5"):
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if not text:
                return jsonify({"error": "无法解码文件，请使用 UTF-8 编码"}), 400

    # 方式2：文本粘贴
    if not text:
        data = request.json or {}
        text = data.get("text", "")

    if not text or len(text.strip()) < 100:
        return jsonify({"error": "参考文本太短（至少100字）"}), 400

    # 保存原文
    pm.save_style_reference(text)

    # 分析风格
    llm_config = None
    if project_id in active_projects:
        llm_config = active_projects[project_id].get("llm_config")

    try:
        from style_learner import StyleLearner
        learner = StyleLearner(pm.project_dir, llm_config)
        guide = learner.analyze_text(text)
        logger.info(f"风格分析完成: {guide.genre}, 对话占比{guide.dialogue_ratio:.0%}")

        return jsonify({
            "message": "风格参考已保存并分析",
            "chars": len(text),
            "style_summary": {
                "genre": guide.genre,
                "tone": guide.tone,
                "pacing": guide.pacing,
                "dialogue_ratio": f"{guide.dialogue_ratio:.0%}",
                "dialogue_style": guide.dialogue_style,
                "action_style": guide.action_style,
                "inner_monologue": guide.inner_monologue,
            },
        })
    except Exception as e:
        logger.error(f"风格分析失败: {e}", exc_info=True)
        return jsonify({
            "message": "参考文本已保存，但风格分析失败",
            "chars": len(text),
            "error": str(e),
        })


@app.route("/api/projects/<project_id>/style_reference", methods=["GET"])
def api_get_style_reference(project_id: str):
    """获取风格参考信息"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404

    ref_text = pm.get_style_reference()
    guide_text = pm.get_style_guide()

    return jsonify({
        "has_reference": bool(ref_text),
        "reference_chars": len(ref_text),
        "reference_preview": ref_text[:500] if ref_text else "",
        "style_guide": guide_text,
    })


# ===== 生成 API =====

@app.route("/api/projects/<project_id>/generate", methods=["POST"])
def api_generate(project_id: str):
    """启动章节生成（后台线程）"""
    data = request.json or {}

    if project_id not in active_projects:
        return jsonify({"error": "项目未激活，请先创建或加载项目"}), 400

    p = active_projects[project_id]
    if p["status"] == "running":
        return jsonify({"error": "项目正在生成中，请等待完成"}), 409

    chapter_num = data.get("chapter_num", p["current_chapter"] + 1)
    start_from = data.get("start_from", 1)  # 从第几章开始

    def run_generation():
        try:
            p["status"] = "running"
            send_event(project_id, "开始生成", 0.01, f"准备第{start_from}章...")

            from studio_v2 import StudioV2
            studio = StudioV2(p["pm"], p["llm_config"])

            # 先确保有基础设定（世界观/角色/大纲）
            if not p["pm"].get_world_setting():
                send_event(project_id, "世界观构建", 0.02, "正在构建世界观...")
                _generate_world_setting(project_id, p)
            if not p["pm"].get_characters():
                send_event(project_id, "角色设计", 0.05, "正在设计角色...")
                _generate_characters(project_id, p)
            if not p["pm"].get_plot_outline():
                send_event(project_id, "剧情大纲", 0.08, "正在规划剧情...")
                _generate_plot_outline(project_id, p)

            # 生成章节
            for ch in range(start_from, p["pm"].meta.chapter_count + 1):
                p["current_chapter"] = ch
                send_event(project_id, f"第{ch}章", 0.1, f"开始生成第{ch}章...")

                # 提取章节大纲
                chapter_outline = _extract_chapter_outline(p["pm"], ch)
                chapter_title = _extract_chapter_title(p["pm"], ch)
                foreshadow = p["pm"].get_foreshadow_plan()

                result = studio.produce_chapter(
                    chapter_num=ch,
                    chapter_outline=chapter_outline,
                    chapter_title=chapter_title,
                    foreshadow_notes=foreshadow,
                )

                p["pm"].update_status("writing", chapter=ch)
                send_event(
                    project_id, f"第{ch}章完成",
                    0.1 + 0.8 * (ch / p["pm"].meta.chapter_count),
                    f"第{ch}章完成，修复{result.issues_fixed}个问题"
                )

            p["pm"].update_status("completed", chapter=p["pm"].meta.chapter_count)
            send_event(project_id, "全部完成", 1.0, "小说生成完毕！")
            p["status"] = "completed"

        except Exception as e:
            logger.error(f"生成失败: {e}", exc_info=True)
            p["status"] = "error"
            send_event(project_id, "错误", -1, str(e))

    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()

    return jsonify({
        "message": "生成已启动",
        "project_id": project_id,
        "start_from": start_from,
    })


def _generate_world_setting(project_id: str, p: dict):
    """生成世界观设定"""
    from agents.v2 import DirectorAgent
    dir_agent = DirectorAgent(p["llm_config"])
    prompt = f"""为一部{p['pm'].meta.genre}小说设计世界观。

类型：{p['pm'].meta.genre}
基调：{p['pm'].meta.tone}

请创建以下内容（用中文输出）：
1. 地理世界（国家、城市、区域、重要地点）
2. 力量体系（修炼等级、武道境界）
3. 社会结构（宗门、帝国、势力）
4. 关键历史和冲突
5. 货币、科技水平、文化

输出一份详细的世界观设定文档。"""
    result = dir_agent.call(prompt, max_tokens=4096, input_summary="World building")
    text = result.raw
    p["pm"].save_world_setting(text)


def _generate_characters(project_id: str, p: dict):
    """生成角色设定 — 通过 function calling 逐个创建角色文件"""
    from agents.v2 import DirectorAgent
    from character_file_manager import CharacterFileManager

    dir_agent = DirectorAgent(p["llm_config"])
    cfm = CharacterFileManager(p["pm"].project_dir)
    world = p["pm"].get_world_setting()

    # ── 定义 create_character 工具 ──
    CREATE_CHAR_TOOL = {
        "type": "function",
        "function": {
            "name": "create_character",
            "description": "创建一个小说角色，生成角色文件。每个角色调用一次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":              {"type": "string", "description": "角色姓名（2-4个中文字）"},
                    "role_type":         {"type": "string", "enum": ["主角", "反派", "配角", "NPC"], "description": "角色类型"},
                    "gender":            {"type": "string", "description": "性别"},
                    "age":               {"type": "string", "description": "年龄"},
                    "personality":       {"type": "string", "description": "性格特点（详细描述）"},
                    "appearance":        {"type": "string", "description": "外貌描述"},
                    "background":        {"type": "string", "description": "背景故事（2-3句话）"},
                    "cultivation_realm": {"type": "string", "description": "修为境界/实力等级"},
                    "sect_or_faction":   {"type": "string", "description": "所属门派或势力"},
                    "speech_style":      {"type": "string", "description": "说话风格（如：冷淡、热血、阴沉）"},
                    "behavioral_traits": {"type": "array", "items": {"type": "string"}, "description": "行为特征列表"},
                    "weaknesses":        {"type": "array", "items": {"type": "string"}, "description": "弱点列表"},
                    "motivations":       {"type": "array", "items": {"type": "string"}, "description": "核心动机列表"},
                    "skills":            {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}}, "required": ["name", "description"]}, "description": "技能/功法列表，每项包含名称和描述"},
                    "items":             {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}}, "required": ["name", "description"]}, "description": "随身道具/法器列表，每项包含名称和描述"},
                },
                "required": ["name", "role_type", "gender", "age", "personality", "appearance", "background", "speech_style", "behavioral_traits", "weaknesses", "motivations", "skills", "items"],
            },
        },
    }

    created_names = []

    def tool_executor(fn_name: str, fn_args: dict) -> str:
        if fn_name == "create_character":
            name = fn_args.get("name", "")
            if not name:
                return "错误：缺少角色名"
            # 分离出 create_character 接受的参数
            valid_keys = {
                "name", "role_type", "gender", "age", "personality", "appearance", "background",
                "cultivation_realm", "sect_or_faction", "speech_style",
                "behavioral_traits", "weaknesses", "motivations",
            }
            filtered = {k: v for k, v in fn_args.items() if k in valid_keys}
            # 提取 skills 和 items（结构化数据，需要转换成 dataclass）
            raw_skills = fn_args.get("skills", [])
            raw_items = fn_args.get("items", [])
            try:
                profile = cfm.create_character(**filtered)
                # 追加技能
                for sk in raw_skills:
                    if isinstance(sk, dict) and sk.get("name"):
                        cfm.add_skill(name, sk["name"], description=sk.get("description", ""))
                # 追加道具
                for it in raw_items:
                    if isinstance(it, dict) and it.get("name"):
                        cfm.add_item(name, it["name"], description=it.get("description", ""))
                created_names.append(name)
                logger.info(f"[function calling] 创建角色: {name} ({filtered.get('role_type', '配角')})")
                return f"角色 {name} 创建成功。已创建 {len(created_names)} 个角色。"
            except Exception as e:
                return f"创建失败: {e}"
        return f"未知函数: {fn_name}"

    # ── 调用 AI ──
    prompt = f"""你是小说角色设计师。请为以下小说设计角色。

世界观：
{world[:2000]}

类型：{p['pm'].meta.genre}
基调：{p['pm'].meta.tone}

要求：
- 1个主角、1个反派、2-3个配角
- 每个角色必须填写 behavioral_traits（至少3条）、weaknesses（至少2条）、motivations（至少2条）
- 每个角色必须有 skills（至少1-2个功法/技能，含名称和具体效果描述）和 items（至少1个随身道具/法器，含名称和描述）
- 技能要具体：不是"剑法"，而是"破风三式——以快制胜的近身剑法，第三式可以短暂突破音障"
- 道具要具体：不是"一把剑"，而是"霜鸣剑——师父遗物，剑身嵌有寒铁，出鞘时会发出低频嗡鸣"

反套路规则（违反任何一条就是失败设计）：
- 主角禁止是"废柴逆袭"：不能是天赋被封印、被欺负、意外获得传承的模板
- 主角必须有真实缺陷（不是"太善良"这种伪缺陷），缺陷要影响剧情走向
- 反派禁止是纯粹邪恶的脸谱化反派，必须有让读者能理解（甚至同情）的动机
- 配角不是工具人，每个配角要有自己的目标，且目标和主角不完全一致
- 角色之间的关系不能是简单的敌/友二元对立，要有灰色地带
- 说话风格要具体到能区分人，不能都是"沉稳""霸气""温柔"这种泛泛之词

请为每个角色调用 create_character 函数。每个角色调用一次，直到所有角色创建完毕。"""

    summary = dir_agent.call_with_tools(
        user_prompt=prompt,
        tools=[CREATE_CHAR_TOOL],
        tool_executor=tool_executor,
        max_tokens=4096,
        max_rounds=8,
    )

    # 同时保存一份纯文本 characters.md（供其他模块 fallback 使用）
    all_chars = cfm.list_characters()
    md_lines = [f"# 角色设定（共{len(all_chars)}人）\n"]
    for cname in all_chars:
        char = cfm.get_character(cname)
        if char:
            md_lines.append(char.to_md())
            md_lines.append("\n---\n")
    p["pm"].save_characters("\n".join(md_lines))
    logger.info(f"通过 function calling 创建了 {len(created_names)} 个角色: {created_names}")


def _generate_plot_outline(project_id: str, p: dict):
    """生成剧情大纲"""
    from agents.v2 import DirectorAgent
    dir_agent = DirectorAgent(p["llm_config"])
    world = p["pm"].get_world_setting()
    chars = p["pm"].get_characters()
    prompt = f"""为一部{p['pm'].meta.genre}小说创建逐章剧情大纲。

世界观：
{world[:1500]}

角色：
{chars[:1500]}

章节数：{p['pm'].meta.chapter_count}
类型：{p['pm'].meta.genre}
基调：{p['pm'].meta.tone}

每章提供（用中文输出）：
- 章节号和标题（格式：第X章 标题）
- 2-3句话描述关键事件
- 主要冲突或转折点

反套路规则（违反任何一条就是失败大纲）：
- 第1章禁止"被欺负→觉醒"开局。要从一个有趣的事件切入，让读者好奇而不是同情。
- 禁止"升级打怪"流水线：不能每章都是"遇到敌人→打不过→突破→打过了"。
- 每个转折必须出乎意料但事后合理。不能靠巧合、天降奇遇推剧情。
- 角色成长要付出真实代价（失去某样东西、做出痛苦选择），不能白捡好处。
- 主角不能每次都赢。至少有2章以真正的失败收场（不是"虽败犹荣"）。
- 配角要有自己的剧情线，不是只围着主角转。

节奏要刺激，但不是爽文的"爽"——是"好故事"的刺激。"""
    result = dir_agent.call(prompt, max_tokens=4096, input_summary="Plot outline")
    text = result.raw
    p["pm"].save_plot_outline(text)


def _extract_chapter_outline(pm, chapter_num: int) -> str:
    outline = pm.get_plot_outline()
    if not outline:
        return f"第{chapter_num}章内容（请根据整体大纲自行规划）"
    lines = outline.split("\n")
    result = []
    capturing = False
    for line in lines:
        if f"第{chapter_num}章" in line or f"第 {chapter_num} 章" in line:
            capturing = True
            continue
        if capturing and any(
            f"第{n}章" in line or f"第 {n} 章" in line
            for n in range(1, pm.meta.chapter_count + 1)
            if n != chapter_num
        ):
            break
        if capturing:
            result.append(line)
    return "\n".join(result).strip() if result else f"第{chapter_num}章"


def _extract_chapter_title(pm, chapter_num: int) -> str:
    outline = pm.get_plot_outline()
    if not outline:
        return f"第{chapter_num}章"
    colon = chr(0xff1a)
    for line in outline.split("\n"):
        m = re.search(r"第\s*(\d+)\s*章[" + colon + r":]\s*[\"'`]?([^\"'#*\n]+)[\"'`]?", line)
        if m and int(m.group(1)) == chapter_num:
            return m.group(2).strip() or f"第{chapter_num}章"
    return f"第{chapter_num}章"


# ===== 章节 API =====

@app.route("/api/projects/<project_id>/chapters")
def api_chapter_list(project_id: str):
    """获取章节列表"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404
    done = pm.get_chapters_done()
    titles = {}
    for ch in done:
        content = pm.get_chapter(ch)
        title_match = __import__('re').search(r'^#\s*(.+?)$', content, __import__('re').MULTILINE)
        titles[ch] = title_match.group(1) if title_match else f"第{ch}章"
    return jsonify({"chapters": [{"num": ch, "title": titles.get(ch, f"第{ch}章")} for ch in done]})


@app.route("/api/projects/<project_id>/chapters/<int:chapter_num>")
def api_chapter_text(project_id: str, chapter_num: int):
    """获取章节正文"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404
    text = pm.get_chapter(chapter_num)
    if not text:
        return jsonify({"error": f"第{chapter_num}章尚未生成"}), 404
    return jsonify({"chapter": chapter_num, "text": text})


def _get_pm(project_id: str):
    if project_id in active_projects:
        return active_projects[project_id]["pm"]
    from project_manager import ProjectManager
    path = os.path.join("novel-engine", "projects", project_id)
    if os.path.exists(path):
        return ProjectManager.load(path)
    return None


# ===== 审计/报告 API =====

@app.route("/api/projects/<project_id>/audit")
def api_audit(project_id: str):
    """获取审计日志摘要"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404
    entries = pm.audit.entries[-50:]  # 最近50条
    return jsonify({
        "total": len(pm.audit.entries),
        "recent": [
            {
                "timestamp": e.timestamp,
                "agent": e.agent,
                "chapter": e.chapter,
                "phase": e.phase,
                "input_summary": e.input_summary[:100],
                "checks_passed": e.checks_passed,
                "checks_failed": e.checks_failed,
                "issues_count": len(e.issues),
                "ai_flavour_score": e.ai_flavour_score,
            }
            for e in entries
        ]
    })


@app.route("/api/projects/<project_id>/reviews/<check_type>/<int:chapter_num>")
def api_review_report(project_id: str, check_type: str, chapter_num: int):
    """获取指定检查报告"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404
    report = pm.get_review(chapter_num, check_type)
    if not report:
        return jsonify({"error": f"第{chapter_num}章 {check_type} 检查报告不存在"}), 404
    return jsonify({"report": report})


@app.route("/api/projects/<project_id>/ai_flavour/<int:chapter_num>")
def api_ai_flavour(project_id: str, chapter_num: int):
    """获取AI味检测报告"""
    pm = _get_pm(project_id)
    if not pm:
        return jsonify({"error": "项目不存在"}), 404
    report = pm.get_ai_flavour(chapter_num)
    return jsonify({"report": report})


# ===== SSE 进度流 =====

@app.route("/api/events/<project_id>")
def api_events(project_id: str):
    """SSE 事件流"""
    if project_id not in event_queues:
        event_queues[project_id] = Queue()

    def generate():
        q = event_queues[project_id]
        while True:
            try:
                event = q.get(timeout=60)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception:
                yield f"data: {json.dumps({'step': 'heartbeat', 'progress': -1, 'detail': ''})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ===== 旧兼容路由（迁移期间） =====

@app.route("/api/status")
def api_status():
    if not active_projects:
        return jsonify({"status": "idle", "progress": 0})
    # 返回第一个运行中的项目状态
    for pid, p in active_projects.items():
        return jsonify({
            "status": p["status"],
            "progress": p["current_chapter"] / max(p["pm"].meta.chapter_count, 1),
            "current_chapter": p["current_chapter"],
            "total_chapters": p["pm"].meta.chapter_count,
        })
    return jsonify({"status": "idle", "progress": 0})


@app.route("/api/world")
def api_world():
    if active_projects:
        pid = list(active_projects.keys())[0]
        return jsonify({"content": active_projects[pid]["pm"].get_world_setting()})
    return jsonify({"content": ""})


@app.route("/api/characters")
def api_characters():
    if active_projects:
        pid = list(active_projects.keys())[0]
        return jsonify({"content": active_projects[pid]["pm"].get_characters()})
    return jsonify({"content": ""})


@app.route("/api/plot")
def api_plot():
    if active_projects:
        pid = list(active_projects.keys())[0]
        return jsonify({"content": active_projects[pid]["pm"].get_plot_outline()})
    return jsonify({"content": ""})


# ===== 启动 =====

def run_webui(host="0.0.0.0", port=7860, debug=False):
    print(f"[*] Novel Engine Web UI v2 启动中...")
    print(f"   访问地址: http://localhost:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Novel Engine Web UI v2")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    run_webui(host=args.host, port=args.port, debug=args.debug)
