"""A tiny synthetic Facebook export in the layout of docs/export-layout.md.

Every text, name and image here is invented. Strings are written mojibake'd, like the real export.
"""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

OWNER = "Ondrej Vzorový"
FRIEND = "Jana Testová"
YEAR = 2009  # every post is in 2009 except LATER_TEXT (2010)

POSTS_FILE = "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json"
PHOTO = "your_facebook_activity/posts/media/Testalbum_1001/100000000000000001.jpg"
MISSING_PHOTO = "your_facebook_activity/posts/media/Testalbum_1001/100000000000000002.jpg"
VIDEO = "your_facebook_activity/posts/media/Testalbum_1001/100000000000000003.mp4"

MOJIBAKE_TEXT = "Môj prvý príspevok, čaj a život"
SPECIAL_TEXT = "Hviezdička * mriežka # menšie < a ::: koniec"
PHOTO_TEXT = "Výlet na hory"
LATER_TEXT = "Nový rok, nové plány"
OTHERS_TEXT = "Všetko najlepšie k narodeninám!"
GROUP_TEXT = "Ahojte, kto ide v sobotu na stretnutie?"
LIFE_TITLE = "Nová práca"
FRIEND_COMMENT = "Krásna fotka!"
OWNER_REPLY = "Ďakujem, Jana."
FRIEND_WALL_TEXT = "Ahoj Ondrej, pozdravujem z Brna."

# An 8x8 grey JPEG that Typst can decode.
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABALDA4MChAODQ4SERATGCgaGBYWGDEjJR0oOjM9PDkzODdASFxOQERXRTc4UG1R"
    "V19iZ2hnPk1xeXBkeFxlZ2P/wAALCAAIAAgBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAf/EABQQAQAAAAAAAAAAAAAAAAAA"
    "AAD/2gAIAQEAAD8AH//Z"
)


def ts(month, day, hour=12, year=YEAR):
    return int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp())


def mojibake(obj):
    if isinstance(obj, str):
        return obj.encode("utf-8").decode("latin-1")
    if isinstance(obj, dict):
        return {k: mojibake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mojibake(v) for v in obj]
    return obj


def media(uri, when, **extra):
    return {"uri": uri, "creation_timestamp": when, "title": "", "media_metadata": {
        "photo_metadata": {"exif_data": [{"upload_ip": "192.0.2.1"}]}}, **extra}


def label_record(when, entries):
    return {"timestamp": when, "media": [], "label_values": entries}


def make_export(root: Path) -> None:
    root = Path(root)
    photo_ts = ts(3, 16)
    posts = [
        # text with mojibake, plus empty and update_timestamp data entries
        {"timestamp": ts(3, 14, 18), "title": f"{OWNER} updated his status.",
         "data": [{}, {"update_timestamp": ts(3, 14, 19)}, {"post": MOJIBAKE_TEXT}, {}]},
        # Markdown-special characters
        {"timestamp": ts(3, 14, 20), "title": f"{OWNER} updated his status.",
         "data": [{"post": SPECIAL_TEXT}]},
        # share-only: a link with no owner text (dropped)
        {"timestamp": ts(3, 15), "title": f"{OWNER} shared a link.", "data": [{}],
         "attachments": [{"data": [{"external_context": {"url": "https://example.com/clanok"}}]}]},
        # video-only (dropped)
        {"timestamp": ts(3, 15, 14), "title": f"{OWNER} added a new video.", "data": [{}],
         "attachments": [{"data": [{"media": media(VIDEO, ts(3, 15, 13))}]}]},
        # timestamp-only (dropped)
        {"timestamp": ts(3, 15, 16), "title": f"{OWNER} updated his status.",
         "data": [{}, {"update_timestamp": ts(3, 15, 16)}]},
        # photo with text, a friend's comment and the owner's reply
        {"timestamp": photo_ts, "title": f"{OWNER} added a new photo.",
         "data": [{"post": PHOTO_TEXT}],
         "attachments": [{"data": [{"media": media(PHOTO, photo_ts - 60, description=PHOTO_TEXT,
                                                   comments=[
             {"timestamp": photo_ts + 600, "comment": FRIEND_COMMENT, "author": FRIEND},
             {"timestamp": photo_ts + 900, "comment": OWNER_REPLY, "author": OWNER},
         ])}]}]},
        # photo whose file is not in the export, no text (kept for its image)
        {"timestamp": ts(3, 17), "title": f"{OWNER} added a new photo.", "data": [{}],
         "attachments": [{"data": [{"media": media(MISSING_PHOTO, ts(3, 17))}]}]},
        # another year
        {"timestamp": ts(1, 2, year=YEAR + 1), "title": f"{OWNER} updated his status.",
         "data": [{"post": LATER_TEXT}]},
    ]
    files = {
        POSTS_FILE: posts,
        "your_facebook_activity/posts/posts_on_other_pages_and_profiles.json": [
            label_record(ts(4, 1), [
                {"label": "Message", "value": OTHERS_TEXT},
                {"label": "Last modified", "timestamp_value": ts(4, 1)},
                {"label": "Target"},
                {"label": "Publish time", "timestamp_value": 0},
                {"label": "Files", "media": []},
            ]),
            # empty like every record in the owner's export (dropped)
            label_record(ts(4, 2), [{"label": "Message", "value": ""}, {"label": "Target"},
                                    {"label": "Files", "media": []}]),
        ],
        "your_facebook_activity/groups/group_posts_and_comments.json": {"group_posts_v2": [
            {"timestamp": ts(5, 1), "title": f"{OWNER} posted in Testovacia skupina.",
             "data": [{"post": GROUP_TEXT}]},
        ]},
        "personal_information/profile_information/your_experiences.json": [
            label_record(ts(6, 1), [
                {"label": "Start time", "timestamp_value": 0},
                {"label": "Title", "value": LIFE_TITLE},
                {"label": "Description", "value": ""},
                {"label": "Creation time", "timestamp_value": ts(6, 1)},
                {"label": "Eligible as major life event", "value": "false"},
                {"label": "Title"},
                {"label": "Name", "value": "Práca"},
            ]),
        ],
        # friend's post on the owner's timeline, on a day with no owner post (legacy layout)
        "your_facebook_activity/posts/other_people's_posts_to_your_timeline.json": {
            "wall_posts_sent_to_you_v2": [
                {"timestamp": ts(3, 20), "title": f"{FRIEND} wrote on {OWNER}'s timeline.",
                 "data": [{"post": FRIEND_WALL_TEXT}]},
            ]},
        # the owner's comment on someone else's post (not loaded)
        "your_facebook_activity/comments_and_reactions/comments.json": {"comments_v2": [
            {"timestamp": ts(3, 21), "title": f"{OWNER} commented on {FRIEND}'s post.",
             "data": [{"comment": {"timestamp": ts(3, 21), "comment": "Super!", "author": OWNER}}]},
        ]},
        # an album repeating the post photo (not loaded)
        "your_facebook_activity/posts/album/0.json": {
            "name": "Testalbum", "description": "", "last_modified_timestamp": photo_ts,
            "cover_photo": media(PHOTO, photo_ts - 60),
            "photos": [media(PHOTO, photo_ts - 60, description=PHOTO_TEXT)],
        },
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mojibake(content), ensure_ascii=True, indent=2))
    (root / PHOTO).parent.mkdir(parents=True, exist_ok=True)
    (root / PHOTO).write_bytes(TINY_JPEG)
    (root / VIDEO).write_bytes(b"\x00\x00\x00\x18ftypmp42")
