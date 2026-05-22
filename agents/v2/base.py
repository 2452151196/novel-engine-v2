"""
Agent v2 - 基类（带审计日志支持）

每个 Agent 的 call 方法返回结构化结果：
    AgentResult(raw, issues, checks_passed, checks_failed, metadata)
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from config import LLMConfig

logger = logging.getLogger("agent_v2")


@dataclass
class AgentResult:
    """Agent 操作的标准返回结构"""
    raw: str                    # AI 原始输出
    issues: List[dict]          # 发现的问题 [{type, location, problem, original, fixed}]
    checks_passed: List[str]    # 通过的检查项
    checks_failed: List[str]   # 未通过的检查项
    metadata: dict = field(default_factory=dict)  # 额外信息（token消耗等）
    error: str = ""             # 如果出错


@dataclass
class CheckResult:
    """单次检查的结果"""
    check_name: str     # 检查类型：世界观一致性/人物性格/剧情逻辑/伏笔呼应/AI味
    passed: bool
    score: int = 0      # 0-100
    issues: List[dict] = field(default_factory=list)
    notes: str = ""


class BaseAgentV2:
    """
    Agent v2 基类。

    相比 v1 的改进：
    1. 所有 call 返回 AgentResult（不是裸字符串）
    2. 内置 audit_hook：每次调用自动记录到审计日志
    3. 支持 check_list：可注册多个检查器，调用后自动执行
    """

    name: str = "BaseAgentV2"
    DEFAULT_TIMEOUT = 120
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str = "",
        audit_hook: Optional[Callable] = None,
    ):
        self.client = OpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            timeout=llm_config.timeout,
        )
        self.model = llm_config.model
        self.temperature = llm_config.temperature
        self.max_tokens = llm_config.max_tokens
        self.system_prompt = system_prompt
        self.audit_hook = audit_hook  # callback(agent_name, input_summary, output_raw, result)

    def call(
        self,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        max_retries: Optional[int] = None,
        input_summary: str = "",
        metadata: dict = None,
    ) -> AgentResult:
        """调用 LLM，返回结构化结果"""
        raw = self._call_llm(user_prompt, temperature, max_tokens, json_mode, max_retries)
        metadata = metadata or {}

        result = AgentResult(
            raw=raw,
            issues=[],
            checks_passed=[],
            checks_failed=[],
            metadata=metadata,
        )

        # 自动触发审计钩子
        if self.audit_hook:
            try:
                self.audit_hook(
                    agent_name=self.name,
                    input_summary=input_summary or user_prompt[:200],
                    raw_output=raw,
                    result=result,
                )
            except Exception as e:
                logger.warning(f"[{self.name}] audit_hook 出错: {e}")

        return result

    def _call_llm(
        self,
        user_prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        json_mode: bool,
        max_retries: Optional[int],
    ) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "top_p": 0.95,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        for attempt in range(retries):
            try:
                logger.info(f"[{self.name}] 调用 LLM (尝试 {attempt + 1}/{retries})")
                t0 = time.time()
                response = self.client.chat.completions.create(**kwargs)
                elapsed = time.time() - t0
                choice = response.choices[0] if response.choices else None
                if not choice:
                    logger.warning(f"[{self.name}] API返回空choices，耗时 {elapsed:.1f}s")
                    if attempt < retries - 1:
                        time.sleep(1)
                        continue
                    return ""
                content = choice.message.content or ""
                finish_reason = choice.finish_reason or "unknown"
                if not content:
                    logger.warning(f"[{self.name}] 响应空内容，finish_reason={finish_reason}，耗时 {elapsed:.1f}s")
                    if finish_reason in ("content_filter", "length") and attempt < retries - 1:
                        time.sleep(1)
                        continue
                else:
                    logger.info(f"[{self.name}] 响应 {len(content)} 字符，finish_reason={finish_reason}，耗时 {elapsed:.1f}s")
                return content
            except APITimeoutError:
                logger.warning(f"[{self.name}] 超时 (尝试 {attempt + 1}/{retries})")
                if attempt == retries - 1:
                    return f"[ERROR] 超时: {APITimeoutError.__name__}"
                time.sleep(2 ** attempt)
            except RateLimitError as e:
                logger.warning(f"[{self.name}] 限流 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    return f"[ERROR] 限流: {e}"
                time.sleep(2 ** attempt * 3)
            except APIError as e:
                logger.warning(f"[{self.name}] API错误 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    return f"[ERROR] API错误: {e}"
                time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"[{self.name}] 未知错误: {e}")
                return f"[ERROR] {e}"
        return "[ERROR] 达到最大重试次数"

    def call_with_tools(
        self,
        user_prompt: str,
        tools: list[dict],
        tool_executor: Callable,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_rounds: int = 10,
    ) -> str:
        """
        带 function calling 的 LLM 调用。

        tools: OpenAI tools schema list
        tool_executor: callback(name, args) -> str，执行函数并返回结果字符串
        max_rounds: 最多允许多少轮工具调用
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        for round_num in range(max_rounds):
            try:
                logger.info(f"[{self.name}] tool call 第{round_num + 1}轮")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_completion_tokens=max_tokens or self.max_tokens,
                    tools=tools,
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"[{self.name}] tool call 出错: {e}")
                return f"[ERROR] {e}"

            choice = response.choices[0]

            # 如果 AI 决定不再调用工具，返回最终文本
            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                return choice.message.content or ""

            # 处理工具调用
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info(f"[{self.name}] 调用函数 {fn_name}({list(fn_args.keys())})")
                result_str = tool_executor(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

        return messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""

    def parse_json(self, text: str) -> dict:
        """从文本中解析 JSON"""
        text = text.strip()
        for marker in ["```json", "```JSON", "```"]:
            if text.startswith(marker):
                text = text[len(marker):].strip()
            if text.endswith(marker):
                text = text[:-len(marker)].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r'\{[\s\S]*\}', text)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
            return {"raw": text}
