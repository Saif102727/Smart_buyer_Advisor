"""Logging with automatic secret redaction (API keys / bearer tokens never reach the logs)."""
import logging
import re

_SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]+)", re.I)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SECRET.sub("***", record.getMessage())
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger("smart_buyer")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler.addFilter(RedactingFilter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False
    return root.getChild(name)
