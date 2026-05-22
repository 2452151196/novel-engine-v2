"""
Quick Writer — 跳过完整流水线，直接用对话记录生成正文。

用法:
    python quick_write.py <dialogue_log.md> [--out output.md] [--words 3000] [--title "第X章"]

示例:
    python quick_write.py projects/232222/reviews/review_ch001_dialogue_log.md
    python quick_write.py projects/232222/reviews/review_ch001_dialogue_log.md --out test_output.md --words 2000
"""
import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from config import LLMConfig
from agents.v2.writer import WriterAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quick_write")


def main():
    parser = argparse.ArgumentParser(description="Quick Writer — 对话记录直接生成正文")
    parser.add_argument("dialogue_log", help="对话记录文件路径 (.md)")
    parser.add_argument("--out", "-o", default="", help="输出文件路径 (默认: 同目录下 _written.md)")
    parser.add_argument("--words", "-w", type=int, default=3000, help="目标字数 (默认3000)")
    parser.add_argument("--title", "-t", default="", help="章节标题")
    parser.add_argument("--outline", default="", help="章节大纲 (可选)")
    parser.add_argument("--style", default="", help="风格参考文件路径 (可选)")
    parser.add_argument("--prev", default="", help="前情提要文件路径 (可选)")
    parser.add_argument("--model", default="", help="模型名 (默认从环境变量读取)")
    parser.add_argument("--base-url", default="", help="API base URL (默认从环境变量读取)")
    parser.add_argument("--api-key", default="", help="API key (默认从环境变量读取)")
    parser.add_argument("--prompt-version", default="v3", choices=["v3", "cn", "cn_old"], help="写手提示词版本: v3(新), cn(旧英文), cn_old(旧中文)")
    args = parser.parse_args()

    # 读取对话记录
    if not os.path.exists(args.dialogue_log):
        logger.error(f"文件不存在: {args.dialogue_log}")
        sys.exit(1)

    with open(args.dialogue_log, "r", encoding="utf-8") as f:
        dialogue_log = f.read()

    logger.info(f"已读取对话记录: {len(dialogue_log)} 字符")

    # 推断章节标题
    title = args.title
    if not title:
        basename = os.path.splitext(os.path.basename(args.dialogue_log))[0]
        title = basename.replace("review_", "").replace("_dialogue_log", "")

    # 读取可选文件
    outline = args.outline
    if args.outline and os.path.exists(args.outline):
        with open(args.outline, "r", encoding="utf-8") as f:
            outline = f.read()

    style_guide = ""
    if args.style and os.path.exists(args.style):
        with open(args.style, "r", encoding="utf-8") as f:
            style_guide = f.read()

    prev_summary = ""
    if args.prev and os.path.exists(args.prev):
        with open(args.prev, "r", encoding="utf-8") as f:
            prev_summary = f.read()

    # 构建 LLM 配置
    llm_config = LLMConfig(
        api_key=args.api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=args.base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7,
        max_tokens=8192,
    )

    logger.info(f"模型: {llm_config.model}")
    logger.info(f"Base URL: {llm_config.base_url}")
    logger.info(f"目标字数: {args.words}")

    # 创建 Writer
    writer = WriterAgent(llm_config, prompt_version=args.prompt_version)
    logger.info(f"提示词版本: {args.prompt_version}")

    # 生成
    t0 = time.time()
    logger.info("开始生成...")
    result = writer.write_from_dialogue(
        dialogue_log=dialogue_log,
        chapter_title=title,
        chapter_outline=outline,
        words_target=args.words,
        style_guide=style_guide,
        prev_summary=prev_summary,
    )
    elapsed = time.time() - t0

    if result.error:
        logger.error(f"生成失败: {result.error}")
        sys.exit(1)

    logger.info(f"生成完成，耗时 {elapsed:.1f}s，输出 {len(result.raw)} 字符")

    # 确定输出路径
    out_path = args.out
    if not out_path:
        dirname = os.path.dirname(args.dialogue_log) or "."
        basename = os.path.splitext(os.path.basename(args.dialogue_log))[0]
        out_path = os.path.join(dirname, f"{basename}_written.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.raw)

    logger.info(f"已保存到: {out_path}")

    # 打印前200字预览
    preview = result.raw[:200]
    print(f"\n{'='*60}")
    print(f"预览 (前200字):")
    print(f"{'='*60}")
    print(preview)
    print(f"{'='*60}")
    print(f"完整内容: {out_path}")


if __name__ == "__main__":
    main()
