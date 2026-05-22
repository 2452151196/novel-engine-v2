"""小说引擎全局配置"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """大语言模型配置"""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout: float = 120.0

    def __post_init__(self):
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.base_url:
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not self.model:
            self.model = "gpt-4o"

    def to_dict(self) -> dict:
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LLMConfig":
        raw_key = data.get("api_key", "")
        # 如果存储的key太短（被截断了），从环境变量读取
        if len(raw_key) < 20:
            raw_key = os.getenv("OPENAI_API_KEY", "")
        return cls(
            api_key=raw_key,
            base_url=data.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=data.get("model") or "gpt-4o",
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 8192)),
            timeout=float(data.get("timeout", 120.0)),
        )


@dataclass
class NovelConfig:
    """小说设定"""
    title: str = "未命名小说"
    genre: str = "玄幻"
    setting: str = ""
    tone: str = "热血、紧凑"
    chapter_count: int = 10
    words_per_chapter: int = 3000
    protagonist: str = ""
    antagonist: str = ""
    theme: str = ""
    style_reference: str = ""
    custom_prompt: str = ""
    llm: LLMConfig = field(default_factory=LLMConfig)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "genre": self.genre,
            "setting": self.setting,
            "tone": self.tone,
            "chapter_count": self.chapter_count,
            "words_per_chapter": self.words_per_chapter,
            "protagonist": self.protagonist,
            "antagonist": self.antagonist,
            "theme": self.theme,
            "style_reference": self.style_reference,
            "custom_prompt": self.custom_prompt,
            "llm": self.llm.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NovelConfig":
        llm_data = data.get("llm", {})
        return cls(
            title=data.get("title", "未命名小说"),
            genre=data.get("genre", "玄幻"),
            setting=data.get("setting", ""),
            tone=data.get("tone", "热血、紧凑"),
            chapter_count=int(data.get("chapter_count", 10)),
            words_per_chapter=int(data.get("words_per_chapter", 3000)),
            protagonist=data.get("protagonist", ""),
            antagonist=data.get("antagonist", ""),
            theme=data.get("theme", ""),
            style_reference=data.get("style_reference", ""),
            custom_prompt=data.get("custom_prompt", ""),
            llm=LLMConfig.from_dict(llm_data),
        )
