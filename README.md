# Novel Engine v2 / 网文引擎 v2

> **English below** / 英文版本见下方

---

## 中文

### 一句话说明
多智能体协同 AI 网文生成引擎。导演（Director）调度场景 → 演员（Actor）扮演角色 → 写手（Writer）扩写成文 → 编辑（Editor）润色去 AI 味。一条流水线，直接出章节。

### 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Director   │────▶│   Actor     │────▶│   Writer    │────▶│   Editor    │
│  场景调度     │     │  角色扮演     │     │  对话升级     │     │  润色去味     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   plot_outline.md    characters/*.md    review_*.md        ai_flavour/*.md
```

- **Director**: 根据大纲切分场景，给每个场景下指令（谁在场、冲突目标、情绪基调）。
- **Actor**: 每个角色有独立档案，AI 完全沉浸角色，输出动作 + 台词。主角 80–200 字，配角 30–80 字，龙套 10–30 字。
- **Writer**: 把 Actor 的 raw log 升级成完整网文章节。核心能力是**去标签化**——把角色档案里的比喻、术语、情绪标签全部拆解成物理动作和环境描写。
- **Editor**: 扫描 AI 味高危词（缓缓、淡淡、嘴角上扬…），给出修改建议或直接重写。

### 核心优势

| 优势 | 说明 |
|------|------|
| **去 AI 味** | 不是简单替换词库，而是从 prompt 层面禁止比喻、否定定义、情绪标签。输出像人写的。 |
| **物理 prose** | 力量通过环境破坏体现（地板开裂、空气扭曲），不是用"恐怖""不可阻挡"等形容词。 |
| **对话驱动** | 场景由角色台词推进，旁白只负责空间和后果。不解释，只呈现。 |
| **角色分离** | 每个角色独立 prompt，不会串戏。商人不说战斗术语，医师不说金融隐喻。 |
| **快速迭代** | `quick_write.py` 可直接喂对话日志给 Writer，跳过 Director/Actor，5 分钟出样章。 |
| **风格锁定** | 支持上传风格参考文本，AI 自动提取节奏特征，后续章节统一风格。 |

### 快速开始

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

#### 2. 配置 API
复制 `.env.example` 为 `.env`，填入你的 API Key：
```
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro
```

#### 3. 启动 Web UI
```bash
python webui.py
```
打开 http://127.0.0.1:7860 创建项目、上传世界观和角色档案，一键生成章节。

#### 4. 快速测试（命令行）
```bash
# 直接用示例对话日志测试写手
python quick_write.py projects/demo_xiuxian/reviews/review_ch001_dialogue_log.md   -w 3000   -o output.md   --prompt-version v3
```

#### 5. 项目目录结构

```
novel-engine/
├── agents/v2/              # 多智能体核心（可独立调用）
│   ├── base.py             #   BaseAgentV2：所有 Agent 的 LLM 调用基类
│   ├── director.py         #   DirectorAgent：场景切分与调度指令
│   ├── actor.py            #   ActorAgent：角色扮演，输出动作+台词
│   ├── writer.py           #   WriterAgent：对话日志 → 完整章节（去标签化）
│   └── reviewers.py        #   Editor/Quality/Foreshadow/Conflict Agent（审校层）
├── projects/               # 小说项目数据（每个文件夹 = 一本书）
│   └── demo_xiuxian/       #   示例项目：修仙爽文「霜鸣示警」
│       ├── project_meta.json #   项目元数据（标题、章数、模型配置）
│       ├── world_setting.md  #   世界观设定（时代、势力、地理、核心道具）
│       ├── plot_outline.md   #   剧情大纲（分章节拍 + 爽点设计）
│       ├── style_reference.txt # 风格参考（去 AI 味约束、节奏规则）
│       ├── characters/       #   角色档案（每角色一个 .md）
│       │   ├── chuxun.md
│       │   └── linyaoer.md
│       ├── chapters/         #   生成的章节正文（chapter_001.md ...）
│       ├── reviews/          #   审查报告（dialogue_log、scene_review ...）
│       ├── ai_flavour/       #   AI 味检测报告
│       └── memory/           #   角色跨章节记忆（char_memory.md）
├── static/                 # Web UI 静态资源
│   └── js/vue.global.js    #   Vue 3（前端界面）
├── templates/              # Web UI HTML 模板
│   └── index_v2.html       #   主界面（项目管理、生成进度、章节查看）
├── config.py               # LLMConfig / NovelConfig（API 参数、全局配置）
├── project_manager.py      # ProjectManager（创建项目、读写文件、审计日志）
├── character_file_manager.py # CharacterFileManager（角色技能/道具/关系/记忆）
├── style_learner.py        # StyleLearner（从参考文本提取风格特征）
├── studio_v2.py            # 完整流水线引擎（Director→Actor→Writer→Editor）
├── quick_write.py          # CLI 快速测试（跳过 Director/Actor，直出样章）
├── webui.py                # Flask Web UI 入口
├── requirements.txt        # Python 依赖
└── .env.example            # API Key 配置模板
```

| 文件/目录 | 作用 | 用户是否需关注 |
|-----------|------|--------------|
| `agents/v2/writer.py` | **核心**。含 SYSTEM_PROMPT_V3（物理 prose 法则、去标签化），`write_from_dialogue()` 把 raw log 转成章节。 | ⭐ 高频调试 |
| `agents/v2/actor.py` | 角色扮演提示词（字数限制：主角80-200字，配角30-80字）。 | 偶尔调 |
| `agents/v2/director.py` | 场景切分逻辑，决定每场戏谁在场、冲突目标。 | 一般不改 |
| `agents/v2/reviewers.py` | 审校 Agent（AI 味扫描、伏笔检查、冲突审核）。 | 按需改 |
| `project_manager.py` | 项目 CRUD：创建目录、保存章节、读写角色档案。 | 一般不改 |
| `studio_v2.py` | 完整流水线编排：初始化世界观 → 分章 → 每章调用 Director→Actor→Writer→Editor。 | 一般不改 |
| `quick_write.py` | CLI 工具。支持 `--prompt-version v3/cn/cn_old`，`-w` 目标字数。 | ⭐ 高频使用 |
| `webui.py` | Flask 服务。提供 `/api/projects`、`/api/generate` 等 REST 接口 + SSE 进度流。 | 启动即可 |
| `config.py` | 读取 `.env` 的 API Key、Base URL、Model 名。 | 配环境变量 |
| `character_file_manager.py` | 角色持久化：技能升级、道具增减、关系变化、跨章节记忆。 | 进阶用 |
| `style_learner.py` | 分析风格参考文本，提取句式节奏、高频动词、禁用词表。 | 风格迁移用 |

---

## English

### One-liner
A multi-agent collaborative AI web-novel generation engine. Director stages the scene → Actors play characters → Writer upgrades raw dialogue into prose → Editor strips AI flavor. One pipeline, one chapter.

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Director   │────▶│   Actor     │────▶│   Writer    │────▶│   Editor    │
│ Scene split │     │ Roleplay    │     │ Log→Prose   │     │ De-AI-flavor│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   plot_outline.md    characters/*.md    review_*.md        ai_flavour/*.md
```

- **Director**: Splits the outline into scenes, issues instructions (who is present, conflict goal, emotional tone).
- **Actor**: Each character has an independent profile. The AI is fully immersed. Output: action + dialogue. Protagonist 80–200 words, supporting 30–80, extras 10–30.
- **Writer**: Upgrades raw Actor logs into full web-novel chapters. Core skill is **de-labeling** — converting character-profile metaphors, jargon, and emotion tags into physical action and environmental description.
- **Editor**: Scans for AI-flavor high-risk words ("缓缓", "嘴角上扬", "眼中闪过"...) and rewrites.

### Key Advantages

| Advantage | Description |
|-----------|-------------|
| **De-AI-flavor** | Not just a word filter. Bans similes, negative definitions, and emotion labels at the prompt level. Output reads human. |
| **Physical prose** | Power is shown through environmental destruction (cracked floors, displaced air), not adjectives like "terrifying" or "unstoppable". |
| **Dialogue-driven** | Scenes advance through character speech. Narration only carries space and consequence. No explaining, only showing. |
| **Character separation** | Each character gets an independent prompt. Merchants don't use combat metaphors; physicians don't use financial jargon. |
| **Fast iteration** | `quick_write.py` feeds dialogue logs directly to the Writer, bypassing Director/Actor. Sample chapter in 5 minutes. |
| **Style lock** | Upload a style reference text; the AI extracts rhythm features and locks them for subsequent chapters. |

### Quick Start

#### 1. Install
```bash
pip install -r requirements.txt
```

#### 2. Configure API
Copy `.env.example` to `.env` and fill in your key:
```
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro
```

#### 3. Launch Web UI
```bash
python webui.py
```
Open http://127.0.0.1:7860, create a project, upload world/character files, and generate chapters.

#### 4. Quick CLI Test
```bash
python quick_write.py projects/demo_xiuxian/reviews/review_ch001_dialogue_log.md   -w 3000   -o output.md   --prompt-version v3
```

#### 5. Project Directory

```
novel-engine/
├── agents/v2/              # Multi-agent core (callable independently)
│   ├── base.py             #   BaseAgentV2: LLM wrapper for all agents
│   ├── director.py         #   DirectorAgent: scene splitting & instruction
│   ├── actor.py            #   ActorAgent: roleplay, outputs action + dialogue
│   ├── writer.py           #   WriterAgent: dialogue log → full chapter (de-labeling)
│   └── reviewers.py        #   Editor/Quality/Foreshadow/Conflict agents (review layer)
├── projects/               # Novel project data (one folder = one book)
│   └── demo_xiuxian/       #   Demo: xianxia "Frost Sword Warning"
│       ├── project_meta.json #   Metadata (title, chapter count, model config)
│       ├── world_setting.md  #   World-building (era, factions, geography, key items)
│       ├── plot_outline.md   #   Plot outline (chapter beats +爽 points)
│       ├── style_reference.txt # Style constraints (de-AI rules, rhythm guidelines)
│       ├── characters/       #   Character profiles (one .md per character)
│       │   ├── chuxun.md
│       │   └── linyaoer.md
│       ├── chapters/         #   Generated chapters (chapter_001.md ...)
│       ├── reviews/          #   Review reports (dialogue_log, scene_review ...)
│       ├── ai_flavour/       #   AI-flavor detection reports
│       └── memory/           #   Cross-chapter character memory (char_memory.md)
├── static/                 # Web UI static assets
│   └── js/vue.global.js    #   Vue 3 (frontend)
├── templates/              # Web UI HTML templates
│   └── index_v2.html       #   Main UI (project mgmt, progress, chapter viewer)
├── config.py               # LLMConfig / NovelConfig (API params, global settings)
├── project_manager.py      # ProjectManager (CRUD, file I/O, audit logging)
├── character_file_manager.py # CharacterFileManager (skills/items/relations/memory)
├── style_learner.py        # StyleLearner (extract rhythm from reference texts)
├── studio_v2.py            # Full pipeline engine (Director→Actor→Writer→Editor)
├── quick_write.py          # CLI quick test (skip Director/Actor, output sample)
├── webui.py                # Flask Web UI entrypoint
├── requirements.txt        # Python dependencies
└── .env.example            # API Key config template
```

| File / Directory | Purpose | User Attention |
|------------------|---------|----------------|
| `agents/v2/writer.py` | **Core**. Contains SYSTEM_PROMPT_V3 (physical prose law, de-labeling), `write_from_dialogue()` converts raw log to chapter. | ⭐ High-frequency tuning |
| `agents/v2/actor.py` | Roleplay prompt (word limits: protagonist 80-200, supporting 30-80). | Occasional tuning |
| `agents/v2/director.py` | Scene splitting logic: who is present, conflict goal. | Rarely changed |
| `agents/v2/reviewers.py` | Review agents (AI-flavor scan, foreshadow check, conflict audit). | On demand |
| `project_manager.py` | Project CRUD: create dirs, save chapters, read character files. | Rarely changed |
| `studio_v2.py` | Full pipeline orchestration: init world → split chapters → call Director→Actor→Writer→Editor per chapter. | Rarely changed |
| `quick_write.py` | CLI tool. Supports `--prompt-version v3/cn/cn_old`, `-w` target words. | ⭐ High-frequency use |
| `webui.py` | Flask server. REST APIs: `/api/projects`, `/api/generate` + SSE progress stream. | Launch and go |
| `config.py` | Reads `.env` for API Key, Base URL, Model name. | Env setup |
| `character_file_manager.py` | Character persistence: skill upgrades, item changes, relation shifts, cross-chapter memory. | Advanced use |
| `style_learner.py` | Analyzes style reference text, extracts sentence rhythm, high-frequency verbs, taboo word list. | Style migration |

---

## License
MIT
