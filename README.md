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

## 📄 License

MIT © 2452151196
