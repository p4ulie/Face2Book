"""Data model for a Facebook JSON export, and text repair."""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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


POSTS_DIR = "your_facebook_activity/posts"
MAIN_POSTS = f"{POSTS_DIR}/your_posts__check_ins__photos_and_videos_1.json"
OTHERS_FILE = f"{POSTS_DIR}/posts_on_other_pages_and_profiles.json"
WALL_FILE = f"{POSTS_DIR}/other_people's_posts_to_your_timeline.json"
GROUPS_FILE = "your_facebook_activity/groups/group_posts_and_comments.json"
LIFE_FILE = "personal_information/profile_information/your_experiences.json"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".webm"}


def _read(root: Path, rel: str):
    with open(root / rel, encoding="utf-8") as f:
        return fix_strings(json.load(f))


def _images(uris: list[str]) -> list[Path]:
    # Typst loads only IMAGE_EXT; videos drop silently, anything else with a warning.
    keep = []
    for uri in uris:
        ext = Path(uri).suffix.lower()
        if ext in IMAGE_EXT:
            keep.append(Path(uri))
        elif ext not in VIDEO_EXT:
            print(f"warning: unsupported image {uri}", file=sys.stderr)
    return keep


def _media(record: dict) -> list[dict]:
    return [d["media"] for a in record.get("attachments", []) for d in a.get("data", [])
            if "media" in d]


def _post_text(record: dict) -> str:
    return "\n\n".join(d["post"] for d in record.get("data", []) if d.get("post"))


def _timeline_post(rec: dict, kind: str, tz: ZoneInfo) -> Post:
    media = _media(rec)
    text = _post_text(rec) or next((m["description"] for m in media if m.get("description")), "")
    notes = [f"{c['author']}: {c['comment']}" for m in media for c in m.get("comments", [])]
    return Post(datetime.fromtimestamp(rec["timestamp"], tz), text,
                _images([m["uri"] for m in media if "uri" in m]), kind, notes)


def _label(rec: dict, name: str) -> dict:
    return next((e for e in rec["label_values"] if e.get("label") == name), {})


def _others_post(rec: dict, tz: ZoneInfo) -> Post:
    files = _label(rec, "Files").get("media", []) + rec.get("media", [])
    return Post(datetime.fromtimestamp(rec["timestamp"], tz), _label(rec, "Message").get("value", ""),
                _images([m["uri"] for m in files if "uri" in m]), "others-timeline", [])


def _life_event(rec: dict, tz: ZoneInfo) -> Post:
    parts = [_label(rec, n).get("value", "") for n in ("Title", "Description")]
    text = "\n\n".join(p for p in parts if p) or _label(rec, "Name").get("value", "")
    return Post(datetime.fromtimestamp(rec["timestamp"], tz), text, [], "life-events", [])


def load(export_root: Path, tz: ZoneInfo, include: set[str],
         year_from: int | None, year_to: int | None) -> tuple[list[Post], list[TimelineNote]]:
    root = Path(export_root)
    if not (root / MAIN_POSTS).is_file():
        raise ExportError(f"not a Facebook JSON export: {MAIN_POSTS} missing")
    posts: list[Post] = []
    notes: list[TimelineNote] = []
    if "timeline" in include:
        for f in sorted((root / POSTS_DIR).glob("your_posts__check_ins__photos_and_videos_*.json")):
            posts += [_timeline_post(r, "timeline", tz) for r in _read(root, str(f.relative_to(root)))]
        if (root / WALL_FILE).is_file():
            for r in _read(root, WALL_FILE)["wall_posts_sent_to_you_v2"]:
                if text := _post_text(r):
                    # ponytail: no author key in the legacy layout, so the whole title stands in.
                    notes.append(TimelineNote(datetime.fromtimestamp(r["timestamp"], tz),
                                              r.get("title", ""), text))
    if "others-timeline" in include and (root / OTHERS_FILE).is_file():
        posts += [_others_post(r, tz) for r in _read(root, OTHERS_FILE)]
    if "groups" in include and (root / GROUPS_FILE).is_file():
        posts += [_timeline_post(r, "groups", tz) for r in _read(root, GROUPS_FILE)["group_posts_v2"]]
    if "life-events" in include and (root / LIFE_FILE).is_file():
        posts += [_life_event(r, tz) for r in _read(root, LIFE_FILE)]

    def wanted(when: datetime) -> bool:
        return (year_from is None or when.year >= year_from) and (year_to is None or when.year <= year_to)

    posts = sorted((p for p in posts if (p.text or p.images) and wanted(p.when)), key=lambda p: p.when)
    notes = sorted((n for n in notes if wanted(n.when)), key=lambda n: n.when)
    return posts, notes
