"""
角色文件管理器 - 每个角色一个独立文件

每个角色文件包含：
- 基础信息（外貌、性格、背景）
- 记忆（随章节累积）
- 道具（获得/失去）
- 技能（学会/升级）
- 关系（与其他角色的关系变化）
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger("character_file")


def save_md(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_md(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@dataclass
class CharacterSkill:
    """角色技能"""
    name: str                    # 技能名
    level: int = 1               # 等级
    learned_at_chapter: int = 0  # 第几章学会
    description: str = ""        # 技能描述


@dataclass
class CharacterItem:
    """角色道具"""
    name: str                   # 道具名
    quantity: int = 1           # 数量
    description: str = ""       # 描述
    obtained_at_chapter: int = 0  # 第几章获得


@dataclass
class CharacterRelation:
    """角色关系"""
    target: str                 # 目标角色名
    relation_type: str          # 关系类型：朋友/敌人/恋人/家人/师父/徒弟
    level: int = 0              # 关系等级 -100~100
    change_log: list[str] = field(default_factory=list)  # 变化记录


@dataclass
class CharacterMemory:
    """角色记忆条目"""
    chapter: int                # 发生在第几章
    summary: str                # 记忆摘要（AI生成）
    timestamp: str = ""


@dataclass
class CharacterProfile:
    """角色完整档案"""
    # === 基础信息 ===
    name: str = ""
    role_type: str = "配角"      # 主角/配角/反派/NPC
    age: str = ""
    gender: str = ""
    appearance: str = ""        # 外貌描述
    personality: str = ""       # 性格特点
    background: str = ""        # 背景故事

    # === 核心属性 ===
    cultivation_realm: str = ""  # 修为境界
    strength: int = 0           # 实力评分
    sect_or_faction: str = ""  # 门派/势力

    # === 动态数据（随章节变化）===
    skills: list[CharacterSkill] = field(default_factory=list)
    items: list[CharacterItem] = field(default_factory=list)
    relations: list[CharacterRelation] = field(default_factory=list)
    memories: list[CharacterMemory] = field(default_factory=list)

    # === 性格标签 ===
    speech_style: str = ""      # 说话风格：傲慢/谦逊/冷酷/幽默...
    behavioral_traits: list[str] = field(default_factory=list)  # 行为特征列表
    weaknesses: list[str] = field(default_factory=list)  # 弱点
    motivations: list[str] = field(default_factory=list)  # 动机

    def to_md(self) -> str:
        """渲染成 Markdown 格式的角色文件"""
        lines = [
            f"# {self.name} - 角色档案",
            "",
            f"**角色类型**: {self.role_type}  |  **性别**: {self.gender}  |  **年龄**: {self.age}",
            f"**修为境界**: {self.cultivation_realm}  |  **实力评分**: {self.strength}  |  **门派**: {self.sect_or_faction}",
            "",
            "## 外貌",
            self.appearance or "（未设定）",
            "",
            "## 性格",
            self.personality or "（未设定）",
            "",
            "## 背景",
            self.background or "（未设定）",
            "",
            "## 说话风格",
            self.speech_style or "（未设定）",
            "",
            "## 行为特征",
            *([f"- {t}" for t in self.behavioral_traits] if self.behavioral_traits else ["（未设定）"]),
            "",
            "## 弱点",
            *([f"- {w}" for w in self.weaknesses] if self.weaknesses else ["（未设定）"]),
            "",
            "## 动机",
            *([f"- {m}" for m in self.motivations] if self.motivations else ["（未设定）"]),
            "",
            "## 技能",
        ]

        if self.skills:
            for s in self.skills:
                lines.append(f"- **{s.name}** (Lv.{s.level}) - {s.description} [第{s.learned_at_chapter}章]")
        else:
            lines.append("（暂无）")

        lines.extend(["", "## 道具"])
        if self.items:
            for item in self.items:
                lines.append(f"- **{item.name}** x{item.quantity} - {item.description} [第{item.obtained_at_chapter}章]")
        else:
            lines.append("（暂无）")

        lines.extend(["", "## 关系"])
        if self.relations:
            for r in self.relations:
                emoji = "🤝" if r.level >= 50 else "⚔️" if r.level <= -50 else "💬"
                lines.append(f"- {emoji} **{r.target}** ({r.relation_type}) 亲密度: {r.level}")
                for log in r.change_log[-2:]:
                    lines.append(f"  - {log}")
        else:
            lines.append("（暂无）")

        lines.extend(["", "## 记忆"])
        if self.memories:
            for mem in self.memories[-10:]:
                lines.append(f"**第{mem.chapter}章**: {mem.summary}")
        else:
            lines.append("（暂无）")

        return "\n".join(lines)

    def to_compact_md(self) -> str:
        """紧凑版本，给AI看的角色信息（用于角色对话）"""
        lines = [
            f"# {self.name}",
            f"类型: {self.role_type} | 境界: {self.cultivation_realm} | 门派: {self.sect_or_faction}",
            f"性格: {self.personality}",
            f"说话风格: {self.speech_style}",
            f"行为特征: {', '.join(self.behavioral_traits)}",
            f"弱点: {', '.join(self.weaknesses)}",
        ]

        if self.skills:
            skill_names = [f"{s.name}(Lv.{s.level})" for s in self.skills]
            lines.append(f"技能: {', '.join(skill_names)}")

        if self.items:
            item_names = [f"{i.name}×{i.quantity}" for i in self.items]
            lines.append(f"道具: {', '.join(item_names)}")

        if self.memories:
            recent = self.memories[-3:]
            lines.append("近期记忆:")
            for mem in recent:
                lines.append(f"  第{mem.chapter}章: {mem.summary[:60]}")

        return "\n".join(lines)


class CharacterFileManager:
    """
    管理项目中所有角色文件。

    项目文件夹结构：
    project/
    ├── characters/           # 角色文件目录
    │   ├── 张三.md           # 每个角色一个文件
    │   ├── 李四.md
    │   └── ...
    ├── world_setting.md      # 世界观设定
    ├── plot_outline.md        # 剧情大纲
    └── chapters/              # 章节正文
        └── ...

    用法：
        cfm = CharacterFileManager("projects/修仙小说")
        cfm.create_character(name="张三", role_type="主角", ...)
        char = cfm.get_character("张三")
        cfm.add_item("张三", "玄铁剑", "削铁如泥")
        cfm.add_skill("张三", "破天剑诀", level=2)
        cfm.add_memory("张三", 5, "在悬崖边与神秘老者相遇")
        cfm.update_relation("张三", "李四", 20, "救了我一命")
    """

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.characters_dir = os.path.join(project_dir, "characters")
        os.makedirs(self.characters_dir, exist_ok=True)

        # 内存缓存：name -> CharacterProfile
        self._cache: dict[str, CharacterProfile] = {}

    def _char_path(self, name: str) -> str:
        safe = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        # 保存名字映射关系，以便准确还原
        self._save_name_mapping(safe, name)
        return os.path.join(self.characters_dir, f"{safe}.md")

    # ── 创建角色 ──────────────────────────────────────────

    def create_character(
        self,
        name: str,
        role_type: str = "配角",
        gender: str = "",
        age: str = "",
        personality: str = "",
        appearance: str = "",
        background: str = "",
        cultivation_realm: str = "",
        sect_or_faction: str = "",
        speech_style: str = "",
        behavioral_traits: list[str] = None,
        weaknesses: list[str] = None,
        motivations: list[str] = None,
    ) -> CharacterProfile:
        """创建新角色文件"""
        path = self._char_path(name)
        if os.path.exists(path):
            logger.warning(f"角色已存在: {name}")
            return self.get_character(name)

        profile = CharacterProfile(
            name=name,
            role_type=role_type,
            gender=gender,
            age=age,
            personality=personality,
            appearance=appearance,
            background=background,
            cultivation_realm=cultivation_realm,
            sect_or_faction=sect_or_faction,
            speech_style=speech_style,
            behavioral_traits=behavioral_traits or [],
            weaknesses=weaknesses or [],
            motivations=motivations or [],
        )

        self._save(profile)
        self._cache[name] = profile
        logger.info(f"创建角色: {name} ({role_type})")
        return profile

    def ai_create_characters(self, characters_md: str) -> list[CharacterProfile]:
        """
        由 AI 批量创建角色。支持多种格式：

        格式1（标准）：
        ## 角色名
        姓名: 张三
        类型: 主角

        格式2（加粗）：
        ## 一、主角：张三
        **姓名**：张三
        **性格**：热血

        格式3（混合）：
        ## 张三
        - 身份：主角
        - 性格：热血
        """
        created = []
        current = {}
        current_name = ""
        multiline_key = ""  # 用于多行值的累积

        for line in characters_md.split("\n"):
            line_stripped = line.strip()

            # 跳过分隔线
            if line_stripped.startswith("---"):
                continue

            # 检测新角色开始（## 二级标题行）
            if line_stripped.startswith("## "):
                # 保存上一个
                if current_name and current:
                    self._try_create(current, current_name, created)

                multiline_key = ""
                # 从标题提取角色名
                title = re.sub(r'^##\s*', '', line_stripped)
                title = re.sub(r'^[一二三四五六七八九十]+[、.．]\s*', '', title)
                title = re.sub(r'^(主角|反派|配角|主要反派|核心配角|重要配角)[：:]\s*', '', title)
                # 去掉 **..** 包裹和书名号
                title = title.strip("*").strip("《》").strip()
                # 跳过非角色标题（如"关键关系网""主要设定"等）
                skip_words = ["关系", "设定", "总结", "概述", "附录", "说明"]
                if any(sw in title for sw in skip_words):
                    current_name = ""
                    current = {}
                    continue
                # 取角色名（2-4个中文字符）
                m = re.match(r'([\u4e00-\u9fff]{2,4})', title)
                if m:
                    current_name = m.group(1)
                else:
                    current_name = ""
                    current = {}
                    continue

                current = {"name": current_name}
                continue

            # 跳过一级标题（文档总标题）
            if line_stripped.startswith("# "):
                continue

            if not current_name:
                continue

            # 解析字段行（支持多种格式）
            # "**键**：值" / "键: 值" / "- 键：值" / "- **键**：值"
            field_match = re.match(
                r'^[-*]*\s*\**([^*:：\n]+?)\**\s*[：:]\s*(.+)',
                line_stripped
            )
            if field_match:
                key = field_match.group(1).strip()
                val = field_match.group(2).strip().strip("*").strip()

                mapped = self._map_field_key(key)
                if mapped:
                    if mapped in ["behavioral_traits", "weaknesses", "motivations"]:
                        items = re.split(r'[、,，;；]', val)
                        current[mapped] = [x.strip() for x in items if x.strip()]
                    elif mapped in ["personality", "background"] and mapped in current:
                        # 多行累积
                        current[mapped] += "；" + val
                    else:
                        current[mapped] = val
                    multiline_key = mapped
                elif multiline_key and line_stripped.startswith("-"):
                    # 列表续行
                    item = line_stripped.lstrip("- ").strip()
                    if multiline_key in current and isinstance(current[multiline_key], list):
                        current[multiline_key].append(item)
                continue

            # 列表项续行（- 开头但没有冒号）
            if line_stripped.startswith("-") and multiline_key:
                item = line_stripped.lstrip("- ").strip()
                if item:
                    if multiline_key in current:
                        if isinstance(current[multiline_key], list):
                            current[multiline_key].append(item)
                        elif isinstance(current[multiline_key], str):
                            current[multiline_key] += "；" + item

        # 保存最后一个
        if current_name and current:
            self._try_create(current, current_name, created)

        logger.info(f"AI批量创建了 {len(created)} 个角色")
        return created

    def _map_field_key(self, key: str) -> str:
        """将各种字段名映射到 CharacterProfile 属性名"""
        key = key.strip()
        key_map = {
            "姓名": "name",
            "类型": "role_type",
            "角色类型": "role_type",
            "身份": "role_type",
            "性别": "gender",
            "年龄": "age",
            "性格": "personality",
            "性格特点": "personality",
            "性格层次": "personality",
            "核心特质": "personality",
            "外貌": "appearance",
            "外貌描述": "appearance",
            "外貌特征": "appearance",
            "背景": "background",
            "背景故事": "background",
            "境界": "cultivation_realm",
            "修为": "cultivation_realm",
            "修为境界": "cultivation_realm",
            "修炼天赋": "cultivation_realm",
            "门派": "sect_or_faction",
            "势力": "sect_or_faction",
            "说话风格": "speech_style",
            "行为特征": "behavioral_traits",
            "行为模式": "behavioral_traits",
            "弱点": "weaknesses",
            "缺陷": "weaknesses",
            "动机": "motivations",
            "核心目标": "motivations",
            "目标": "motivations",
        }
        return key_map.get(key, "")

    def _try_create(self, current: dict, name: str, created: list):
        """尝试创建角色，过滤无效字段"""
        # 只保留 create_character 接受的参数
        valid_keys = {
            "name", "role_type", "personality", "appearance", "background",
            "cultivation_realm", "sect_or_faction", "speech_style",
            "behavioral_traits", "weaknesses", "motivations",
        }
        filtered = {k: v for k, v in current.items() if k in valid_keys}
        if "name" not in filtered:
            filtered["name"] = name

        try:
            p = self.create_character(**filtered)
            created.append(p)
        except Exception as e:
            logger.warning(f"创建角色失败 {name}: {e}")

    # ── 读取角色 ──────────────────────────────────────────

    def get_character(self, name: str) -> Optional[CharacterProfile]:
        """获取角色档案（带缓存）"""
        if name in self._cache:
            return self._cache[name]

        path = self._char_path(name)
        if not os.path.exists(path):
            return None

        content = load_md(path)
        profile = self._parse_profile(name, content)
        self._cache[name] = profile
        return profile

    def list_characters(self) -> list[str]:
        """列出所有角色名"""
        if not os.path.exists(self.characters_dir):
            return []
        mapping = self._load_name_mapping()
        files = [f for f in os.listdir(self.characters_dir) if f.endswith(".md") and f != "_name_map.json"]
        names = []
        for f in files:
            stem = os.path.splitext(f)[0]
            names.append(mapping.get(stem, stem))
        return names

    def _save_name_mapping(self, safe_name: str, original_name: str):
        """保存文件名→原始名的映射"""
        map_path = os.path.join(self.characters_dir, "_name_map.json")
        mapping = self._load_name_mapping()
        if mapping.get(safe_name) != original_name:
            mapping[safe_name] = original_name
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

    def _load_name_mapping(self) -> dict:
        """加载文件名→原始名映射"""
        map_path = os.path.join(self.characters_dir, "_name_map.json")
        if os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def get_all_characters_compact(self) -> dict[str, str]:
        """获取所有角色的紧凑信息（给AI用）"""
        result = {}
        for name in self.list_characters():
            char = self.get_character(name)
            if char:
                result[name] = char.to_compact_md()
        return result

    def _parse_profile(self, name: str, content: str) -> CharacterProfile:
        """从 Markdown 内容解析回 CharacterProfile"""
        profile = CharacterProfile(name=name)

        current_section = ""
        skill_buffer = []
        item_buffer = []
        relation_buffer = []
        memory_buffer = []

        for line in content.split("\n"):
            line_stripped = line.strip()

            # 处理多字段同行的情况（用 | 分隔）
            if "|" in line_stripped and "**" in line_stripped:
                parts = [p.strip() for p in line_stripped.split("|")]
                for part in parts:
                    self._parse_header_field(part, profile)
            elif line_stripped.startswith("## "):
                current_section = line_stripped.replace("## ", "").strip()
            elif current_section == "外貌":
                profile.appearance += line_stripped + "\n"
            elif current_section == "性格":
                profile.personality += line_stripped + "\n"
            elif current_section == "背景":
                profile.background += line_stripped + "\n"
            elif current_section == "说话风格":
                profile.speech_style += line_stripped + "\n"
            elif current_section == "技能":
                skill_buffer.append(line_stripped)
            elif current_section == "道具":
                item_buffer.append(line_stripped)
            elif current_section == "关系":
                relation_buffer.append(line_stripped)
            elif current_section == "记忆":
                memory_buffer.append(line_stripped)

        # 解析技能
        for sb in skill_buffer:
            if sb.startswith("- **"):
                m = re.search(r"- \*\*(.+?)\*\* \(Lv.(\d+)\)(?: - (.+?))?(?: \[第(\d+)章\])?", sb)
                if m:
                    profile.skills.append(CharacterSkill(
                        name=m.group(1),
                        level=int(m.group(2)),
                        description=m.group(3) or "",
                        learned_at_chapter=int(m.group(4) or 0),
                    ))

        # 解析道具
        for ib in item_buffer:
            if ib.startswith("- **"):
                m = re.search(r"- \*\*(.+?)\*\* [x×](\d+)(?: - (.+?))?(?: \[第(\d+)章\])?", ib)
                if m:
                    profile.items.append(CharacterItem(
                        name=m.group(1),
                        quantity=int(m.group(2)),
                        description=m.group(3) or "",
                        obtained_at_chapter=int(m.group(4) or 0),
                    ))

        # 解析关系
        for rb in relation_buffer:
            if "**" in rb:
                m = re.search(r"\*\*([^\*]+)\*\* \(([^)]+)\)", rb)
                if m:
                    level_m = re.search(r":\s*(-?\d+)", rb)
                    profile.relations.append(CharacterRelation(
                        target=m.group(1).strip(),
                        relation_type=m.group(2).strip(),
                        level=int(level_m.group(1)) if level_m else 0,
                    ))

        # 解析记忆
        for mb in memory_buffer:
            if "**第" in mb:
                m = re.search(r"\*\*第(\d+)章\*\*[:：]\s*(.+)", mb)
                if m:
                    profile.memories.append(CharacterMemory(
                        chapter=int(m.group(1)),
                        summary=m.group(2).strip(),
                        timestamp=datetime.now().strftime("%Y-%m-%d"),
                    ))

        profile.appearance = profile.appearance.strip()
        profile.personality = profile.personality.strip()
        profile.background = profile.background.strip()
        profile.speech_style = profile.speech_style.strip()

        return profile

    def _parse_header_field(self, text: str, profile: CharacterProfile):
        """解析单个头部字段（如 **角色类型**: 主角）"""
        m = re.search(r"\*\*([^\*]+)\*\*[:：]?\s*(.+)", text)
        if not m:
            return
        key = m.group(1).strip()
        val = m.group(2).strip()
        field_map = {
            "角色类型": "role_type",
            "性别": "gender",
            "年龄": "age",
            "修为境界": "cultivation_realm",
            "实力评分": "strength",
            "门派": "sect_or_faction",
        }
        attr = field_map.get(key)
        if attr == "strength":
            try:
                profile.strength = int(val)
            except ValueError:
                pass
        elif attr:
            setattr(profile, attr, val)

    def _extract_value(self, line: str) -> str:
        m = re.search(r"\*\*[^\*]+\*\*[:：]?\s*(.+)", line)
        return m.group(1).strip() if m else ""

    def _save(self, profile: CharacterProfile):
        """保存角色文件"""
        path = self._char_path(profile.name)
        save_md(path, profile.to_md())

    # ── 更新角色 ──────────────────────────────────────────

    def add_skill(
        self,
        name: str,
        skill_name: str,
        level: int = 1,
        description: str = "",
        chapter: int = 0,
    ):
        """给角色添加技能"""
        profile = self.get_character(name)
        if not profile:
            logger.warning(f"角色不存在: {name}")
            return

        for s in profile.skills:
            if s.name == skill_name:
                s.level = level
                s.description = description
                logger.info(f"{name} 技能升级: {skill_name} -> Lv.{level}")
                self._save(profile)
                return

        profile.skills.append(CharacterSkill(
            name=skill_name,
            level=level,
            description=description,
            learned_at_chapter=chapter,
        ))
        logger.info(f"{name} 学会技能: {skill_name} (Lv.{level})")
        self._save(profile)

    def add_item(
        self,
        name: str,
        item_name: str,
        quantity: int = 1,
        description: str = "",
        chapter: int = 0,
    ):
        """给角色添加道具"""
        profile = self.get_character(name)
        if not profile:
            logger.warning(f"角色不存在: {name}")
            return

        for item in profile.items:
            if item.name == item_name:
                item.quantity += quantity
                logger.info(f"{name} 道具增加: {item_name} x{quantity} (共{item.quantity})")
                self._save(profile)
                return

        profile.items.append(CharacterItem(
            name=item_name,
            quantity=quantity,
            description=description,
            obtained_at_chapter=chapter,
        ))
        logger.info(f"{name} 获得道具: {item_name} x{quantity}")
        self._save(profile)

    def remove_item(self, name: str, item_name: str, quantity: int = 1):
        """移除角色道具"""
        profile = self.get_character(name)
        if not profile:
            return
        for item in profile.items:
            if item.name == item_name:
                item.quantity -= quantity
                if item.quantity <= 0:
                    profile.items.remove(item)
                logger.info(f"{name} 失去道具: {item_name}")
                self._save(profile)
                return

    def update_relation(
        self,
        name: str,
        target: str,
        change: int,
        reason: str = "",
    ):
        """更新角色关系"""
        profile = self.get_character(name)
        if not profile:
            return

        for rel in profile.relations:
            if rel.target == target:
                rel.level = max(-100, min(100, rel.level + change))
                if reason:
                    rel.change_log.append(f"[{datetime.now().strftime('%m-%d')}] {change:+d} 原因: {reason}")
                if len(rel.change_log) > 10:
                    rel.change_log = rel.change_log[-10:]
                self._save(profile)
                return

        # 新建关系
        rel_type = "未知"
        if change > 0:
            rel_type = "好感"
        elif change < 0:
            rel_type = "敌意"

        profile.relations.append(CharacterRelation(
            target=target,
            relation_type=rel_type,
            level=max(-100, min(100, change)),
            change_log=[f"[{datetime.now().strftime('%m-%d')}] 初识，{change:+d} 原因: {reason}"] if reason else [],
        ))
        logger.info(f"{name} 与 {target} 关系变化: {change:+d}")
        self._save(profile)

    def add_memory(self, name: str, chapter: int, summary: str):
        """添加角色记忆"""
        profile = self.get_character(name)
        if not profile:
            return

        profile.memories.append(CharacterMemory(
            chapter=chapter,
            summary=summary,
            timestamp=datetime.now().strftime("%Y-%m-%d"),
        ))
        logger.info(f"{name} 第{chapter}章记忆: {summary[:40]}")
        self._save(profile)

    def update_cultivation(self, name: str, realm: str, strength_delta: int = 0):
        """更新角色修为"""
        profile = self.get_character(name)
        if not profile:
            return
        old_realm = profile.cultivation_realm
        profile.cultivation_realm = realm
        profile.strength += strength_delta
        logger.info(f"{name} 修为变化: {old_realm} -> {realm} (强度 {strength_delta:+d})")
        self._save(profile)
