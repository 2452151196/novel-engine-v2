<div align="center">

# 🔥 Novel Engine v2

**Multi-Agent AI Web-Novel Generator — Built for Power Fantasy (爽文)**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Agent Count](https://img.shields.io/badge/agents-5%20co--operative-orange)]()

> *Director stages → Actors roleplay → Writer forges → Editor quenches.*  
> One pipeline. One chapter. No AI flavor.

[中文](#-中文) · [English](#-english) · [Quick Start](#-quick-start)

</div>

---

## 🎯 What This Does

Every AI writing tool generates prose. This one **removes the AI taste** before a single word hits the page.

| ❌ Typical AI Output | ✅ Novel Engine Output |
|---------------------|------------------------|
| "His heart tightened, and he slowly raised his head." | "The floor cracked three inches under his boot." |
| "A terrifying aura spread like a tsunami." | "The air went cold. The hanging lamps frosted over." |
| "She felt angry, her fists clenched white." | "Her breath came out hot. The teacup handle snapped in her grip." |

**The rule is simple:** Power is shown through **environmental destruction**, not adjectives. Characters speak; narration carries only space and consequence.

---

## 🏗️ Architecture

```mermaid
graph LR
    A[📋 Director<br/>Scene Splitter] --> B[🎭 Actor<br/>Roleplay Agent]
    B --> C[✍️ Writer<br/>Log → Prose]
    C --> D[🔍 Editor<br/>De-AI-Flavor]
    D --> E[📖 Chapter.md]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#fce4ec
    style E fill:#f3e5f5
```

| Agent | Duty | Key Feature |
|-------|------|-------------|
| **Director** | Splits outline into scenes, assigns characters, sets conflict goals | Beat-sheet aware (Hook → Pressure → Underestimation → Face-slap) |
| **Actor** | Immersive roleplay per character profile | Word limits: Protagonist 80–200, Supporting 30–80, Extra 10–30 |
| **Writer** | Upgrades raw dialogue logs into full chapters | **De-labeling engine**: converts metaphors/jargon/emotion tags into physical prose |
| **Editor** | Scans for AI-flavor words and rewrites | Zero-tolerance list: 缓缓, 淡淡, 嘴角上扬, 眼中闪过... |
| **Reviewer** | Checks foreshadowing, conflict pacing, world consistency | Cross-chapter memory via `character_file_manager.py` |

---

## ⭐ Core Advantages

### 1. 🚫 De-AI-Flavor at the Prompt Level
Not a post-hoc word filter. The **SYSTEM_PROMPT_V3** bans similes, negative definitions, and emotion labels *before* generation:
- **Zero similes** — "like", "as if", "resembling" are forbidden. Describe weight, texture, light directly.
- **Affirmative only** — No "not A, but B". Say what it IS.
- **Literal nouns** — "Blades of light" becomes "light". "A mask of porcelain" becomes "a face".

### 2. ⚔️ Physical Prose Law
Combat power is measured by environmental impact:
```
Bad:  "His aura was terrifying and unstoppable."
Good: "The stone floor spiderwebbed. Dust hung motionless."
```

### 3. 🎭 Character Separation
Each role gets an independent prompt. Merchants don't use combat metaphors. Physicians don't use financial jargon. No character sounds like the AI.

### 4. 🚀 Fast Iteration
`quick_write.py` feeds dialogue logs directly to the Writer, bypassing Director/Actor. Get a sample chapter in **5 minutes**.

### 5. 🔒 Style Lock
Upload a reference text → `style_learner.py` extracts rhythm, verb frequency, and taboo words → subsequent chapters auto-match.

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/2452151196/novel-engine-v2.git
cd novel-engine-v2
pip install -r requirements.txt
```

### 2. Configure API
```bash
cp .env.example .env
# Edit .env:
# OPENAI_API_KEY=your_key_here
# OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
# OPENAI_MODEL=mimo-v2.5-pro
```

### 3. Test the Writer (Fastest)
```bash
python quick_write.py projects/demo_xiuxian/reviews/review_ch001_dialogue_log.md   -w 3000   -o output.md   --prompt-version v3
```

### 4. Launch Web UI
```bash
python webui.py
# Open http://127.0.0.1:7860
```

---

## 📁 Project Structure

```
novel-engine/
├── agents/v2/              # Multi-agent core
│   ├── base.py             # LLM wrapper for all agents
│   ├── director.py         # Scene splitter & scheduler
│   ├── actor.py            # Character roleplay engine
│   ├── writer.py           # Dialogue log → prose (★ core)
│   └── reviewers.py        # Editor + Quality + Foreshadow + Conflict
├── projects/               # Novel data (1 folder = 1 book)
│   └── demo_xiuxian/       # Demo: "Frost Sword Warning"
│       ├── world_setting.md
│       ├── plot_outline.md
│       ├── style_reference.txt
│       └── characters/
│           ├── chuxun.md
│           └── linyaoer.md
├── project_manager.py      # CRUD for projects/chapters/reviews
├── character_file_manager.py # Skill/item/relation/memory persistence
├── style_learner.py        # Extract rhythm from reference texts
├── studio_v2.py            # Full pipeline orchestrator
├── quick_write.py          # CLI bypass (★ dev tool)
├── webui.py                # Flask Web UI
└── README.md
```

**Files you'll actually touch:**
| File | Why |
|------|-----|
| `agents/v2/writer.py` | Edit `SYSTEM_PROMPT_V3` to tune prose style |
| `quick_write.py` | Daily driver for testing output |
| `projects/*/characters/*.md` | Character profiles |
| `projects/*/plot_outline.md` | Chapter beats &爽 points |

---

## 📝 Example Output

**Input** (Actor raw log):
```
楚询: 拇指推剑出鞘一指宽。 霜进三寸。可战。
林药儿: 手从药囊移到剑刃旁... 药典载'阴寒逢魔瘴，其蔓疾者，瘴已成精'。
```

**Writer Output** (after de-labeling):
> The frost had climbed three inches up the blade. Chu Xun's thumb rested on the guard, the steel half-drawn. The mist thickened where the cold metal touched it, turning from grey to something darker, something that moved against the air current.
>
> Lin Yaoer's hand drifted from her medicine pouch to the sword. Her fingertip hovered an inch from the frost line, close enough to feel the chill. The frost was spreading upstream, against the draft. She said nothing. The frost answered for her.

Notice: No "terrifying". No "like". No "she felt afraid." Just the frost, the thumb, the silence.

---

## 🛠️ Advanced: Tune the Writer

The heart of the engine is `agents/v2/writer.py`. Three prompt versions ship by default:

| Version | Style | Use Case |
|---------|-------|----------|
| `v3` (default) | Physical prose, zero similes, de-labeling | Production |
| `cn` | English output with Chinese prompt framing | Legacy fallback |
| `cn_old` | Full Chinese prompt (original) | Debugging |

Switch via CLI:
```bash
python quick_write.py ... --prompt-version v3
```

Or in Python:
```python
from agents.v2.writer import WriterAgent
writer = WriterAgent(llm_config, prompt_version="v3")
```

---

<a name="chinese"></a>

## 中文

### 🎯 这引擎是干嘛的

别的 AI 写作工具生成文字，这个**在生成之前就先把 AI 味去掉**。

| ❌ 典型 AI 输出 | ✅ Novel Engine 输出 |
|---------------------|------------------------|
| "他心头一紧，缓缓抬起头。" | "他脚下的地板裂开了三寸。" |
| "恐怖的气息如海啸般蔓延。" | "空气变冷了。挂灯的表面结了一层霜。" |
| "她感到愤怒，指节攥得发白。" | "她的呼吸变热了。茶杯柄在她手里断了。" |

**规则很简单：** 力量通过**环境破坏**来体现，不是形容词。角色说话；旁白只负责空间和后果。

---

### 🏗️ 架构

```mermaid
graph LR
    A[📋 导演<br/>场景切分] --> B[🎭 演员<br/>角色扮演]
    B --> C[✍️ 写手<br/>日志 → 散文]
    C --> D[🔍 编辑<br/>去 AI 味]
    D --> E[📖 章节.md]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#fce4ec
    style E fill:#f3e5f5
```

| Agent | 职责 | 核心特性 |
|-------|------|-------------|
| **导演** | 按大纲切分场景，分配角色，设定冲突目标 | 节拍意识（钩子 → 加压 → 低估 → 打脸） |
| **演员** | 按角色档案沉浸式扮演 | 字数限制：主角 80–200 字，配角 30–80 字，龙套 10–30 字 |
| **写手** | 把原始对话日志升级成完整章节 | **去标签化引擎**：把比喻/术语/情绪标签拆解成物理 prose |
| **编辑** | 扫描 AI 味高危词并重写 | 零容忍列表：缓缓、淡淡、嘴角上扬、眼中闪过... |
| **审查** | 检查伏笔、冲突节奏、世界观一致性 | 跨章节记忆通过 `character_file_manager.py` 持久化 |

---

### ⭐ 核心优势

#### 1. 🚫 从 Prompt 层面去 AI 味
不是后处理替换词库。**SYSTEM_PROMPT_V3** 在生成前就禁止比喻、否定定义和情绪标签：
- **零比喻** — 禁用 "like"、"as if"、"resembling"。直接描述重量、质地、光线。
- **肯定式表达** — 不用 "不是 A，而是 B"。直接说它是**什么**。
- **字面名词** — "blades of light" 变成 "light"。"a mask of porcelain" 变成 "a face"。

#### 2. ⚔️ 物理 Prose 法则
战斗力量通过环境破坏来体现：
```
烂："他的气势恐怖且不可阻挡。"
好："石地板裂开了蛛网纹。灰尘悬在空中不动。"
```

#### 3. 🎭 角色隔离
每个角色独立 prompt。商人不说战斗术语，医师不用金融隐喻。没有角色听起来像 AI。

#### 4. 🚀 快速迭代
`quick_write.py` 直接把对话日志喂给写手，跳过导演和演员。**5 分钟**出样章。

#### 5. 🔒 风格锁定
上传参考文本 → `style_learner.py` 提取节奏、动词频率、禁用词表 → 后续章节自动匹配。

---

### 🚀 快速开始

#### 1. 安装
```bash
git clone https://github.com/2452151196/novel-engine-v2.git
cd novel-engine-v2
pip install -r requirements.txt
```

#### 2. 配置 API
```bash
cp .env.example .env
# 编辑 .env：
# OPENAI_API_KEY=your_key_here
# OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
# OPENAI_MODEL=mimo-v2.5-pro
```

#### 3. 测试写手（最快）
```bash
python quick_write.py projects/demo_xiuxian/reviews/review_ch001_dialogue_log.md \
  -w 3000 \
  -o output.md \
  --prompt-version v3
```

#### 4. 启动 Web UI
```bash
python webui.py
# 打开 http://127.0.0.1:7860
```

---

### 📁 项目结构

```
novel-engine/
├── agents/v2/              # 多智能体核心
│   ├── base.py             # 所有 Agent 的 LLM 调用基类
│   ├── director.py         # 场景切分与调度
│   ├── actor.py            # 角色扮演引擎
│   ├── writer.py           # 对话日志 → 散文（★ 核心）
│   └── reviewers.py        # 编辑 + 质量 + 伏笔 + 冲突
├── projects/               # 小说数据（一个文件夹 = 一本书）
│   └── demo_xiuxian/       # 示例：「霜鸣示警」
│       ├── world_setting.md
│       ├── plot_outline.md
│       ├── style_reference.txt
│       └── characters/
│           ├── chuxun.md
│           └── linyaoer.md
├── project_manager.py      # 项目/章节/审查的 CRUD
├── character_file_manager.py # 技能/道具/关系/记忆持久化
├── style_learner.py        # 从参考文本提取节奏
├── studio_v2.py            # 完整流水线编排器
├── quick_write.py          # CLI 快速绕过（★ 开发工具）
├── webui.py                # Flask Web 界面
└── README.md
```

**你实际会修改的文件：**
| 文件 | 原因 |
|------|-----|
| `agents/v2/writer.py` | 编辑 `SYSTEM_PROMPT_V3` 调整文风 |
| `quick_write.py` | 日常测试输出 |
| `projects/*/characters/*.md` | 角色档案 |
| `projects/*/plot_outline.md` | 章节节拍与爽点 |

---

### 📝 示例输出

**输入**（演员原始日志）：
```
楚询: 拇指推剑出鞘一指宽。 霜进三寸。可战。
林药儿: 手从药囊移到剑刃旁... 药典载'阴寒逢魔瘴，其蔓疾者，瘴已成精'。
```

**写手输出**（去标签化后）：
> 霜已经爬上了剑身三寸。楚询的拇指搭在护手上，钢刃半出鞘。雾气在冷金属触及的地方变浓了，从灰色变成某种更暗的东西，某种逆着气流移动的东西。
>
> 林药儿的手从药囊飘向剑身。她的指尖悬在霜线前一寸，近到能感觉到寒意。霜在逆着风蔓延。她没说话。霜替她回答了。

注意：没有"恐怖"。没有"like"。没有"她感到害怕"。只有霜、拇指、和沉默。

---

### 🛠️ 高级：调参写手

引擎的心脏是 `agents/v2/writer.py`。默认自带三个提示词版本：

| 版本 | 风格 | 用途 |
|---------|-------|----------|
| `v3` (默认) | 物理 prose，零比喻，去标签化 | 生产环境 |
| `cn` | 英文输出，中文 prompt 框架 | legacy fallback |
| `cn_old` | 全中文 prompt（原版） | 调试 |

CLI 切换：
```bash
python quick_write.py ... --prompt-version v3
```

Python 中：
```python
from agents.v2.writer import WriterAgent
writer = WriterAgent(llm_config, prompt_version="v3")
```

---

## 📄 License

MIT © 2452151196
