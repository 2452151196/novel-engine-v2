"""
NovelEngine v2 - 项目管理器

每个小说 = 一个独立项目文件夹。
所有内容（角色记忆、检查日志、AI味报告）都存放在项目文件夹内。
"""
import json
import logging
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from config import LLMConfig

logger = logging.getLogger("project")

# ---- Markdown 持久化工具 ----

def save_md(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_md(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---- 项目元数据 ----

@dataclass
class ProjectMeta:
    """项目元数据"""
    title: str
    genre: str = "玄幻"
    tone: str = "热血、紧凑"
    chapter_count: int = 10
    words_per_chapter: int = 3000
    created_at: str = ""
    last_modified: str = ""
    status: str = "planning"  # planning/writing/completed/error
    current_chapter: int = 0
    model: str = "gpt-4o"

    def to_md(self) -> str:
        lines = [
            "# 项目信息",
            "",
            f"- **标题**: {self.title}",
            f"- **类型**: {self.genre}",
            f"- **基调**: {self.tone}",
            f"- **章节数**: {self.chapter_count}",
            f"- **每章字数**: {self.words_per_chapter}",
            f"- **创建时间**: {self.created_at}",
            f"- **最后修改**: {self.last_modified}",
            f"- **状态**: {self.status}",
            f"- **当前章节**: {self.current_chapter}/{self.chapter_count}",
            f"- **模型**: {self.model}",
        ]
        return "\n".join(lines)


# ---- 审计日志条目 ----

@dataclass
class AuditEntry:
    """
    每条AI操作的审计日志。
    记录：谁在什么时间做了什么决策、原始输出是什么、修改了什么、哪里不合理。
    """
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    agent: str = ""            # 操作者：director/actor/writer/world_reviewer/...
    chapter: int = 0           # 章节号（0=全局）
    phase: str = ""            # 阶段：plan/draft/review/rewrite
    scene_or_section: str = "" # 场景名或章节名

    # AI 收到的输入摘要（防止重复调用LLM时丢失上下文）
    input_summary: str = ""

    # AI 的原始输出
    raw_output: str = ""

    # 检查结果（哪些通过了、哪些失败了）
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)

    # 问题列表 + 对应的修改（如果有问题）
    issues: list[dict] = field(default_factory=list)
    #   { "id": 1, "type": "一致性", "location": "第3段", "problem": "...",
    #     "original": "...", "fixed": "..." }

    # AI味的评估
    ai_flavour_score: int = 0   # 0-100，越高越AI
    ai_flavour_notes: str = ""

    # 额外注释（用于调试、复盘）
    notes: str = ""

    def to_md(self) -> str:
        """渲染成一行可读Markdown"""
        lines = [f"## [{self.timestamp}] {self.agent} | 第{self.chapter}章 | {self.phase}"]

        if self.scene_or_section:
            lines.append(f"> 场景：{self.scene_or_section}")

        if self.input_summary:
            lines.append(f"\n**输入摘要**：{self.input_summary}")

        if self.raw_output:
            snippet = self.raw_output[:300].replace("\n", " ")
            lines.append(f"\n**原始输出**：{snippet}{'...' if len(self.raw_output) > 300 else ''}")

        if self.checks_passed or self.checks_failed:
            passed = ", ".join(f"✅ {c}" for c in self.checks_passed)
            failed = ", ".join(f"❌ {c}" for c in self.checks_failed)
            lines.append(f"\n**检查**：{passed}  {failed}")

        if self.issues:
            lines.append(f"\n**问题**（{len(self.issues)}个）：")
            for iss in self.issues:
                lines.append(
                    f"  - [{iss.get('type','?')}] {iss.get('location','')}：{iss.get('problem','')[:80]}"
                )
                if iss.get("fixed"):
                    lines.append(f"    修复：{iss.get('fixed','')[:80]}")

        if self.ai_flavour_score > 0:
            lines.append(f"\n**AI味评分**：{self.ai_flavour_score}/100  {self.ai_flavour_notes}")

        if self.notes:
            lines.append(f"\n**备注**：{self.notes}")

        return "\n".join(lines)


# ---- 审计日志管理器 ----

class AuditLog:
    """
    管理项目所有AI操作的审计日志。
    存储格式：Markdown（方便人读）+ JSON（方便程序解析）。
    """

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self._log_file_md = os.path.join(project_dir, "audit_log.md")
        self._log_file_json = os.path.join(project_dir, "audit_log.json")
        self.entries: list[AuditEntry] = []
        self._load()

    def _load(self):
        """从JSON恢复"""
        if os.path.exists(self._log_file_json):
            try:
                with open(self._log_file_json, "r", encoding="utf-8") as f:
                    self.entries = [AuditEntry(**e) for e in json.load(f)]
            except Exception as e:
                logger.warning(f"加载审计日志失败: {e}")

    def add(self, entry: AuditEntry):
        """追加一条审计记录"""
        self.entries.append(entry)
        self._save()

    def _save(self):
        """同时保存MD和JSON"""
        # JSON
        with open(self._log_file_json, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.entries], f, ensure_ascii=False, indent=2)

        # Markdown
        lines = [
            "# AI 审计日志",
            "",
            f"共 {len(self.entries)} 条记录",
            "",
        ]
        for entry in self.entries:
            lines.append(entry.to_md())
            lines.append("")
            lines.append("---")
            lines.append("")

        with open(self._log_file_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def get_entries_for_chapter(self, chapter: int) -> list[AuditEntry]:
        return [e for e in self.entries if e.chapter == chapter]

    def get_last_entry(self, agent: str = "", chapter: int = 0) -> Optional[AuditEntry]:
        candidates = self.entries
        if agent:
            candidates = [e for e in candidates if e.agent == agent]
        if chapter > 0:
            candidates = [e for e in candidates if e.chapter == chapter]
        return candidates[-1] if candidates else None


# ---- 项目管理器 ----

class ProjectManager:
    """
    管理小说项目文件夹。

    项目文件夹结构：
    project_name/
    ├── project_meta.md          # 项目信息（标题、类型、章节数…）
    ├── world_setting.md         # 世界观设定
    ├── characters.md            # 角色设定
    ├── plot_outline.md          # 剧情大纲
    ├── foreshadow_plan.md       # 伏笔规划
    ├── audit_log.md             # AI审计日志（人读）
    ├── audit_log.json           # AI审计日志（机器读）
    ├── memory/                  # 角色记忆持久化
    │   ├── 角色名_memory.md
    │   └── 角色名_memory.json
    ├── chapters/                # 章节正文
    │   ├── chapter_001.md
    │   ├── chapter_002.md
    │   └── ...
    ├── reviews/                 # 每场/每章的检查报告
    │   ├── review_ch001_scene1.md
    │   ├── review_ch001_chapter.md
    │   └── ...
    ├── ai_flavour/              # AI味检测报告
    │   ├── ai_flavour_ch001.md
    │   └── ...
    └── drama/                   # 戏剧模式数据（如启用）
        └── ...

    用法：
        pm = ProjectManager("my_novels/修仙大作")
        pm.create("修仙", tone="热血", chapters=50)
        # 或
        pm = ProjectManager.load("my_novels/修仙大作")
        pm.continue_writing()  # 断点续写
    """

    # 默认目录（放在用户指定的项目根目录下）
    DEFAULT_ROOT = "novel-engine/projects"

    def __init__(self, project_root: str = "novel-engine/projects"):
        self.root = project_root
        os.makedirs(self.root, exist_ok=True)

    def create(
        self,
        title: str,
        genre: str = "玄幻",
        tone: str = "热血、紧凑",
        chapter_count: int = 10,
        words_per_chapter: int = 3000,
        model: str = "gpt-4o",
    ) -> "ProjectManager":
        """创建新项目"""
        project_dir = os.path.join(self.root, title)
        if os.path.exists(project_dir):
            raise FileExistsError(f"项目已存在: {project_dir}")

        os.makedirs(project_dir)
        os.makedirs(os.path.join(project_dir, "memory"))
        os.makedirs(os.path.join(project_dir, "chapters"))
        os.makedirs(os.path.join(project_dir, "characters"))  # 每个角色独立文件
        os.makedirs(os.path.join(project_dir, "reviews"))
        os.makedirs(os.path.join(project_dir, "ai_flavour"))
        os.makedirs(os.path.join(project_dir, "drama"))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta = ProjectMeta(
            title=title,
            genre=genre,
            tone=tone,
            chapter_count=chapter_count,
            words_per_chapter=words_per_chapter,
            created_at=now,
            last_modified=now,
            status="planning",
            current_chapter=0,
            model=model,
        )

        save_md(os.path.join(project_dir, "project_meta.md"), meta.to_md())
        with open(os.path.join(project_dir, "project_meta.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, ensure_ascii=False, indent=2)

        # 初始化空的审计日志
        audit = AuditLog(project_dir)

        # 初始化角色记忆目录（空）
        save_md(os.path.join(project_dir, "memory", ".gitkeep"), "")

        self.project_dir = project_dir
        self.meta = meta
        self.audit = audit

        logger.info(f"项目已创建: {project_dir}")
        return self

    @staticmethod
    def load(project_path: str) -> "ProjectManager":
        """加载已有项目"""
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"项目不存在: {project_path}")

        meta_json = os.path.join(project_path, "project_meta.json")
        with open(meta_json, "r", encoding="utf-8") as f:
            meta = ProjectMeta(**json.load(f))

        pm = ProjectManager.__new__(ProjectManager)
        pm.root = os.path.dirname(project_path)
        pm.project_dir = project_path
        pm.meta = meta
        pm.audit = AuditLog(project_path)
        return pm

    @staticmethod
    def list_projects(project_root: str = "novel-engine/projects") -> list[dict]:
        """列出所有项目"""
        if not os.path.exists(project_root):
            return []
        results = []
        for name in os.listdir(project_root):
            path = os.path.join(project_root, name)
            if not os.path.isdir(path):
                continue
            meta_path = os.path.join(path, "project_meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    m = json.load(f)
                results.append({
                    "title": m.get("title", name),
                    "path": path,
                    "status": m.get("status", "unknown"),
                    "current_chapter": m.get("current_chapter", 0),
                    "chapter_count": m.get("chapter_count", 0),
                    "last_modified": m.get("last_modified", ""),
                })
        return sorted(results, key=lambda x: x.get("last_modified", ""), reverse=True)

    # ---- 内容读写 ----

    def save_world_setting(self, text: str):
        save_md(os.path.join(self.project_dir, "world_setting.md"), text)
        self._touch_meta()

    def get_world_setting(self) -> str:
        return load_md(os.path.join(self.project_dir, "world_setting.md"))

    def save_characters(self, text: str):
        save_md(os.path.join(self.project_dir, "characters.md"), text)
        self._touch_meta()

    def get_characters(self) -> str:
        return load_md(os.path.join(self.project_dir, "characters.md"))

    def save_plot_outline(self, text: str):
        save_md(os.path.join(self.project_dir, "plot_outline.md"), text)
        self._touch_meta()

    def get_plot_outline(self) -> str:
        return load_md(os.path.join(self.project_dir, "plot_outline.md"))

    def save_foreshadow_plan(self, text: str):
        save_md(os.path.join(self.project_dir, "foreshadow_plan.md"), text)
        self._touch_meta()

    def get_foreshadow_plan(self) -> str:
        return load_md(os.path.join(self.project_dir, "foreshadow_plan.md"))

    def save_style_reference(self, text: str):
        """保存风格参考原文"""
        save_md(os.path.join(self.project_dir, "style_reference.txt"), text)
        self._touch_meta()

    def get_style_reference(self) -> str:
        """读取风格参考原文"""
        path = os.path.join(self.project_dir, "style_reference.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def get_style_guide(self) -> str:
        """读取已分析的风格指南（Markdown）"""
        return load_md(os.path.join(self.project_dir, "style_guide.md"))

    def save_chapter(self, chapter_num: int, title: str, text: str):
        path = os.path.join(self.project_dir, "chapters", f"chapter_{chapter_num:03d}.md")
        save_md(path, f"# {title}\n\n{text}")
        self.meta.current_chapter = max(self.meta.current_chapter, chapter_num)
        self._touch_meta()

    def get_chapter(self, chapter_num: int) -> str:
        path = os.path.join(self.project_dir, "chapters", f"chapter_{chapter_num:03d}.md")
        return load_md(path)

    def get_chapters_done(self) -> list[int]:
        chapters_dir = os.path.join(self.project_dir, "chapters")
        if not os.path.exists(chapters_dir):
            return []
        nums = []
        for fname in os.listdir(chapters_dir):
            if fname.startswith("chapter_") and fname.endswith(".md"):
                try:
                    nums.append(int(fname[8:11]))
                except ValueError:
                    pass
        return sorted(nums)

    # ---- 角色记忆读写 ----

    def save_character_memory(self, char_name: str, memory_md: str):
        safe = char_name.replace("/", "_").replace("\\", "_")
        save_md(os.path.join(self.project_dir, "memory", f"{safe}_memory.md"), memory_md)

    def get_character_memory(self, char_name: str) -> str:
        safe = char_name.replace("/", "_").replace("\\", "_")
        return load_md(os.path.join(self.project_dir, "memory", f"{safe}_memory.md"))

    # ---- 检查报告读写 ----

    def save_review(self, chapter: int, scope: str, report_md: str):
        """scope: "scene1" / "chapter_end" / "rewrite_1" 等"""
        path = os.path.join(self.project_dir, "reviews", f"review_ch{chapter:03d}_{scope}.md")
        save_md(path, report_md)

    def get_review(self, chapter: int, scope: str) -> str:
        path = os.path.join(self.project_dir, "reviews", f"review_ch{chapter:03d}_{scope}.md")
        return load_md(path)

    # ---- AI味报告读写 ----

    def save_ai_flavour(self, chapter: int, report_md: str):
        path = os.path.join(self.project_dir, "ai_flavour", f"ai_flavour_ch{chapter:03d}.md")
        save_md(path, report_md)

    def get_ai_flavour(self, chapter: int) -> str:
        path = os.path.join(self.project_dir, "ai_flavour", f"ai_flavour_ch{chapter:03d}.md")
        return load_md(path)

    # ---- 项目状态 ----

    def update_status(self, status: str, chapter: int = None):
        self.meta.status = status
        if chapter is not None:
            self.meta.current_chapter = chapter
        self._touch_meta()

    def _touch_meta(self):
        """更新最后修改时间并保存"""
        self.meta.last_modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_md(os.path.join(self.project_dir, "project_meta.md"), self.meta.to_md())
        with open(os.path.join(self.project_dir, "project_meta.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(self.meta), f, ensure_ascii=False, indent=2)

    @property
    def project_path(self) -> str:
        return self.project_dir

    def get_summary(self) -> str:
        """项目总览（给WebUI展示）"""
        done = self.get_chapters_done()
        return (
            f"**{self.meta.title}**  |  {self.meta.genre}  |  "
            f"{self.meta.status}  |  第 {self.meta.current_chapter}/{self.meta.chapter_count} 章  |  "
            f"已生成 {len(done)} 章"
        )
