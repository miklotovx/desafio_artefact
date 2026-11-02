# Saves each chat conversation as a separate local Markdown file.
"""Conversation files are independent of the in-memory Streamlit history."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo


LOG_DIR = Path(__file__).resolve().parent / "logs"


def new_log_path() -> Path:
    """Generate a unique filename using the customer's Brazilian timezone."""
    timestamp = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d_%H-%M-%S")
    return LOG_DIR / f"conversa_{timestamp}_{uuid4().hex}.md"


def save_log(path: Path, messages: list[dict]) -> None:
    """Save original visible messages, without API configuration or tool exchanges."""
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = ["# Conversa - Empório da Música\n"]
    for message in messages:
        label = "Cliente" if message["role"] == "user" else "Assistente"
        parts.append(f"## {label}\n\n{message['content']}\n")
    temporary = path.with_suffix(".tmp")
    temporary.write_text("\n".join(parts), encoding="utf-8")
    temporary.replace(path)
