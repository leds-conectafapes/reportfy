from reportfy.ai.prompts import PromptType, PROMPTS

# MarkdownSummarizer imports mistralai — load lazily so the package is
# importable even in environments without the mistralai SDK installed.
def __getattr__(name):
    if name == "MarkdownSummarizer":
        from reportfy.ai.summarizer import MarkdownSummarizer  # noqa: PLC0415
        return MarkdownSummarizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["PromptType", "PROMPTS", "MarkdownSummarizer"]
