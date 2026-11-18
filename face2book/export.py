"""Data model for a Facebook JSON export, and text repair."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

KINDS = ("timeline", "others-timeline", "groups", "life-events")


class ExportError(Exception):
    pass


@dataclass
class Post:
    when: datetime
    text: str
    images: list[Path]  # relative to the export root
    kind: str
    notes: list[str]  # "Author: text"


@dataclass
class TimelineNote:
    when: datetime
    author: str
    text: str


def fix_text(s: str) -> str:
    # Facebook exports store UTF-8 bytes as latin-1 code points (mojibake).
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def fix_strings(obj):
    if isinstance(obj, str):
        return fix_text(obj)
    if isinstance(obj, dict):
        return {k: fix_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fix_strings(v) for v in obj]
    return obj
