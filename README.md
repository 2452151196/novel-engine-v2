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

A multi-agent pipeline that generates web-novel chapters by **removing AI flavor at the prompt level** — not filtering words after generation, but banning similes, emotion labels, and professional metaphors *before* the model writes a single sentence.

**Core rule:** Power is shown through **environmental destruction** (cracked floors, displaced air), not adjectives like "terrifying" or "unstoppable". Characters speak; narration carries only space and consequence.

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
Each role gets an independent prompt. A merchant never uses trade vocabulary to describe danger or emotion; a physician never uses medical jargon for social friction. Their profession is shown through *where their eyes go* and *what their hands do*, not through metaphors. No character sounds like the AI.

### 4. 🚀 Fast Iteration
`quick_write.py` feeds dialogue logs directly to the Writer, bypassing Director/Actor. Get a sample chapter in **30 minutes**.

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

## 📝 Sample Chapter (Zero Human Edits)

> **Full chapter generated by Novel Engine v2, untouched.** The pipeline received a Chinese dialogue log + plot outline and produced this English prose in one pass.

---

The auctioneer's gavel struck the block with a heavy crack. Shadow Seven hadn't even processed the sound before his hand shot up, hovering in mid-air of its own accord.

"Sold! For three hundred spirit stones, to the gentleman in the cloak!"

His stomach dropped. A serving boy with ink-stained fingers slid a glass tank across the pitted table. Inside, a fish the length of a palm circled listlessly. Its scales were the color of dead grey, threaded with veins of pulsing emerald green.

Spirit-veined Poison Mullet.

Rumour said a single refined drop of its venom could burn a cultivator's divine sense to ash, leaving them blind to the world for a full month. Shadow Seven had heard whispers of someone looking to inconvenience a rival. He had acted on greed.

He hadn't expected the auctioneer's oily smile, or the words that followed: "Of course, the esteemed buyer understands... this creature demands extreme compatibility. The toxin synthesis is highly unstable. Without the matching primer elixir, the backlash will cause your spiritual energy to reverse along the meridians. The pain, they say, is worse than death."

Shadow Seven's blood ran cold. Three hundred stones for a death sentence.

He seized the tank. Through the glass he felt a clinging warmth. He shoved past masked bidders in heavy coats and plunged into the back alleys of the black market. He needed to offload it. Or find the primer. Cost no longer mattered.

The rear lanes of Ten Thousand Laws City were not streets—they were scars cut into living flesh. Shadow Seven moved like a rat through the shadows, threading between tilted slums. The fish tank pressed against his ribs beneath his leather armor, radiating faint heat like a second heart ready to detonate.

Three blocks from the Emerald Beetle Casino, the pressure in the air changed.

Not a sound. The *absence* of sound. The distant noise of the market vanished. Two figures peeled from the deep shadow ahead, blocking the narrow passage.

Dark crimson robes. Blood Shadow Sect disciples. Silver thread on the hems drank the faint light. Their faces were hidden behind smooth crimson lacquer masks—nothing visible but twin slits of black where eyes should be.

"Shadow Seven." The left one's voice was dry, sand scraping stone. "You crossed a line at the auction."

Shadow Seven's hand found the pouch at his waist. Muscle memory guided his fingers: Ghost Moth powder, Stinkroot dust, and a crystal that would detonate into blinding mist on contact with light. "Gentlemen," he said, his voice sharper than intended, "you've mistaken your fisherman."

"That mullet bears a mark," the second disciple said. "Sect-forged poison. The auction was bait. You bit. Now you, the fish, and the stones come with us."

Shadow Seven's wrist flicked. Powders mixed in his palm. "The auction house is neutral ground!" he shouted, hurling the blend into the air.

A dull pop. Acrid grey smoke bloomed, thick and impenetrable. Shadow Seven spun toward a stack of rotted crates and scrambled for the wall.

*Zheng—!*

A blade's clear song cut through the smoke's hiss. A willow-leaf knife split the haze and cleaved the top crate in two. Wood chips sprayed. Shadow Seven crashed back to the wet flagstones, his spine striking hard.

The Blood Shadow disciples emerged through dying smoke. Crimson masks caught the dim light with an unnatural chill. The blade pointed at his throat. "The Emerald Beetle's rules only protect those inside the walls. Out here, you're wild meat. Fish, stones, two legs. Leave those and you might live."

The knife stabbed down, pinning the stone beside his thigh. Chips stung his skin. He scrambled backward and his hand closed around something round and wet—a discarded rain bucket. He kicked with everything he had. Filthy water splashed across the alley.

In the moment they flinched, he saw it. A narrow door in the side wall, half-open, not a residence—a workshop. He threw himself through, shoulder hammering the rotted wood shut with a heavy *bang*.

The stench and threat vanished.

The workshop air was cold, dense, carrying the smell of metal, ore dust, and something faintly, sickeningly sweet. It ran deeper than it appeared from outside. From the ceiling and shelves hung skeletal frameworks: unfinished metal constructs, coiled copper wire, stacks of matte-black alloy plates.

A puppeteer's forge.

But what froze Shadow Seven was the man at the center.

A spirit lamp hung overhead, casting pale green light. He was tall, lean, dressed in a simple grey robe, his back to the door. On the stone table before him lay a partial skeleton—upper torso and skull only, polished to a sterile gleam. The man held a black cloth, wiping the left eye socket with slow, elegant care.

Shadow Seven's breath caught. He tried to step back. His spine pressed against the door.

The man did not turn. Did not stop.

"Uninvited guests." His voice was calm as stagnant water, carrying a strange rhythm that chilled the bones. "I value silence. Yet today, I find myself... in a mood."

"O-outside," Shadow Seven stammered, eyes locked on the skeleton, "they want to kill me."

"Ah." The man set down the cloth and turned.

A face pale and beautiful as carved marble. Features sharp as knife blades. Eyes black as ink-stones, reflecting no light at all. The corner of his mouth lifted in a perfect smile that never reached his eyes.

"There are always people who wish to kill. After all, they are the finest source of materials." His gaze settled on the bulge beneath Shadow Seven's armor. "You brought trouble to my door. How... convenient."

*Hong—!*

The door shattered.

The two Blood Shadow disciples burst through. Crimson masks flickered under green lamplight. The knife-wielding disciple's eyes swept the room, lingering on the skeleton and the grey-robed man. "Puppeteer, none of your business. Hand over the thief and the goods."

The man's smile did not waver. "A thief? You broke my door in public. By the laws of the lower city, that constitutes malicious intrusion. Disturbing my peace demands... compensation."

He stepped right, resting his hand on a rectangular object draped in black velvet on the nearby workbench.

"I happen to be testing a new array. A small experiment in... kinetic hospitality. Your timing is ideal."

He pulled the cloth away.

Beneath it sat a metal cage. Inside was something that had once been human.

A puppet of black iron and copper tendon. Its head was a featureless dark-gold metal egg, save for two pools of dark-red fire where eyes should be. The cables that had suspended it went slack as the cloth fell. Gears screamed. The puppet landed in a beast's crouch, its crimson gaze flaring.

"Mechanical puppet! Kill them!" one disciple shrieked, drawing a serrated short blade.

The puppet moved.

It did not run. It *unfolded*.

One moment it crouched by the bench. The next it stood before the disciple. A steel-taloned hand shot out and locked around the man's wrist. A dull *crack*—bone gave way. Before the scream could leave his throat, the puppet's other hand cupped the crimson mask's chin.

Shadow Seven heard the cleanest snapping sound of his life.

The disciple folded like a sack of grain. The second disciple roared, willow-leaf knife trailing blood-shadow as it struck the puppet's back.

*Dang!* Sparks sprayed.

The blade bounced, leaving no mark on the black iron ribs. The puppet did not turn. Its neck emitted a hydraulic hiss. Its head rotated one hundred and eighty degrees. The blank metal face stared at the swordsman. Its free hand reached back and closed around the refined steel blade.

*Ga-zhi—*

Hundred-forged steel twisted between its fingers like dough.

The grey-robed man—Shadow Seven's mind finally supplied the name from river-and-lake rumor: Ye Wushang, master of the Forgetful Pavilion—sighed. "Still crude. The cervical joint response is too slow." He stepped forward, pausing before the corpse. He did not look at the puppet. He extended one finger and touched the center of the crushed skull.

Shadow Seven watched the body wither.

Not blood loss. Something worse. Flesh contracted, clinging to bone. Within breaths the corpse became a desiccated husk in a red robe.

Ye Wushang withdrew his finger. A wisp of grey mist coiled around his fingertip, then dispersed. He turned to Shadow Seven, cowering against the wall.

"Now. We discuss cooperation." Ye Wushang's voice was level as weather. "You wish to live. The Blood Shadow Sect will not let this poisoned fish go. The next ones they send will be stronger." He gestured at the two husks. "That was merely... pest control."

Shadow Seven's throat was dust. "Cooperation? You... what you just did was..."

"Cleaning up trash." Ye Wushang returned to his workbench, picking up the cloth, carefully wiping away a speck of dust. "I require something. Word says the Zhong family's young master was buried in the eastern mass grave three days ago. The body vanished. Rumor claims it contained exceptionally pure 'Primordial Chaos Qi.' For me, that is a rare... component."

He paused, fixing Shadow Seven with a direct look. "You deal in information. I want that corpse. You want my protection, and—a solution to your little problem."

He reached out. The fish tank flew from Shadow Seven's chest into his hand. He studied the mullet, emerald veins pulsing against his pale fingertips.

"Crude work. The backlash circuit can be neutralized with a simple oscillation sigil." He set the tank aside. "Find the corpse. The primer is yours. The fish is mine. You live. Fair."

The puppet returned to its suspension like a shadow, cables reattaching. Its crimson gaze dimmed. The workshop fell silent again, save for the mingled smell of rust and blood.

Shadow Seven looked at the two husks. Then at Ye Wushang's unrippled face.

A trap. A gorgeous, lethal, irresistible trap.

He swallowed hard. Nodded.

"Done," he rasped. "But I have conditions."

Ye Wushang's mouth curved in that empty smile. "Of course. A dog that bargains is a useful dog. Speak."

At that moment, a slow rhythmic tapping drifted from the alley outside.

*Da... da... da...*

Not footsteps. More like a cane, or a ring tapping wood, one strike at a time.

Ye Wushang's head tilted, bird-sharp. For the first time, his ink-black eyes moved from Shadow Seven to the shattered doorway. The puppet's crimson gaze reignited, brighter than before.

The tapping stopped. A dry, dusty voice drifted in from the alley.

"The smell of life fades quickly, Master Ye. My disciple's life-lamp just went out, and the malice drifts here. I would hear your explanation for this... coincidence."

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

多智能体协同流水线，**在生成之前就先把 AI 味去掉**——不是后处理替换词库，而是从 prompt 层面禁止比喻、否定定义和情绪标签。

**核心规则：** 力量通过**环境破坏**来体现（地板开裂、空气扭曲），不是形容词。角色说话；旁白只负责空间和后果。

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
每个角色独立 prompt。商人从不用商业术语比喻危险或情绪；医师从不用医学术语描述社交摩擦。职业特征只体现在他们的**眼神落点**和**手部动作**，不是比喻。没有角色听起来像 AI。

#### 4. 🚀 快速迭代
`quick_write.py` 直接把对话日志喂给写手，跳过导演和演员。**30 分钟**出样章。

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

> **完整样章见上方「Sample Chapter (Zero Human Edits)」** — 一段由 Novel Engine v2 一次生成的英文网文章节，零人工修改。
>
> 该章节基于中文对话日志 + 剧情大纲，由 Writer Agent 的 `SYSTEM_PROMPT_V3` 直接扩写为英文 prose。特点是：**无比喻、无情绪标签、无职业术语串戏**，力量通过环境破坏体现（地板碎裂、钢铁扭曲），角色性格通过动作和沉默呈现。

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
