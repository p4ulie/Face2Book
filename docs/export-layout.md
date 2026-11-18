# Facebook export layout

What Task 6 (`face2book.export.load`) reads, based on the owner's own "Download Your Information"
export in JSON format (downloaded November 2026, 303 JSON files). Only key names, types and counts
are recorded here. `tests/fixture.py` (`make_export`) writes a synthetic export in this layout.

## General

- All paths are relative to the export root (the folder that holds `your_facebook_activity/`,
  `personal_information/`, ...). Every media `uri` is also relative to that root, for example
  `your_facebook_activity/posts/media/<Album>_<id>/<digits>.jpg`.
- Every string is mojibake (UTF-8 bytes stored as `\u00XX` code points). Run `fix_strings` on every
  loaded file.
- Timestamps are Unix seconds (`int`, 10 digits). Use the record's top-level `timestamp`. Other
  timestamps disagree with it and are not the post time: `data[].update_timestamp` (edit time, differs
  in 50 posts), `media.creation_timestamp` (upload time, differs in 6 of 20 photos), and the
  label-value timestamps described below (often 0 or ~1970).
- Records are **not** sorted. Sort after loading.
- `title` is English UI text naming the owner ("<OWNER> updated his status.", "... shared a link.").
  Nothing below depends on it, except as the author of a friend's timeline post (see there).
- Media extensions referenced by posts and albums: `.jpg` (all but 4), `.avif` (3), `.mp4` (1). Videos are dropped by
  extension (`.mp4 .mov .webm`). AVIF may not render in every output format.
- The fixture's main posts file is `_1`. Facebook splits large exports into `_1`, `_2`, ...; read
  every `your_posts__check_ins__photos_and_videos_*.json` (the owner's export has only `_1`).

## Kind `timeline` (owner's own posts)

File: `your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_*.json`.
A missing `_1` file means "not a Facebook JSON export" (`ExportError`).

Top level: a JSON **list** of post records (4270 in the owner's export).

| Key | Type | Notes |
|---|---|---|
| `timestamp` | int | post time |
| `title` | str | always present, ignore |
| `data` | list[dict] | 0-5 entries. Each entry is `{}` (9224 of 12856), `{"update_timestamp": int}` or `{"post": str}`. At most one `post` per record. |
| `attachments` | list[dict] | optional, 0 or 1 entries, each `{"data": list[dict]}` |
| `attachments[].data[]` | dict | exactly one of `external_context` {url, maybe name, source} (shared link/post/reel), `media` (photo/video), `name` (shared group), `text` (shared memory) |
| `attachments[].data[].media` | dict | `uri`, `creation_timestamp`, `title`, `media_metadata`, optional `description` |
| `tags` | list[{name}] | rare (1 record), ignore |

Rule:
- text = the non-empty `data[].post` strings joined with a blank line. `attachments[].data[].name`
  and `.text` are not the owner's words; ignore them.
- If text is empty, use the first non-empty `media.description` (the photo caption). In the owner's
  export `media.description` equals the post text in 13 posts and is the only text in 1 post.
- images = `media.uri` of every `attachments[].data[].media`, minus videos.
- `external_context` alone (a share) adds nothing, so a share without owner text is dropped by the
  keep rule.
- comments = `media.comments` (see "Comments" below).

Owner's export by structure: 1442 records with no text, media or link (mostly
"updated his status." with every `data` entry empty), 1725 link-only shares, 1084 text posts
(573 with a link), 18 photo posts (14 with text), 1 video-only post. So about 1100 posts are book
content.

## Kind `others-timeline` (owner's posts on other people's timelines and pages)

File: `your_facebook_activity/posts/posts_on_other_pages_and_profiles.json`.

Top level: a JSON list of records in the newer "label_values" format:
`{"timestamp": int, "media": list, "label_values": list[dict]}`. Each label-value entry is
`{"label": str, <one value key>}` where the value key is `value` (str), `timestamp_value` (int),
`vec`, `dict` or `media` (lists); some entries have only `label`, a few have `title` instead of
`label`. The labels are fixed English field names, the same in every record.

| Label | Key | Use |
|---|---|---|
| `Message` | `value` | the owner's text (always the first entry) |
| `Files` | `media` | images, list of media dicts (`uri`) |
| `Target` | (none) | whose timeline. Empty in every record, so the target is not known. |
| `Publish time`, `Last modified` | `timestamp_value` | ignore, use top-level `timestamp` |

Rule: one post per record, time = `timestamp`, text = `value` of the `Message` entry, images = `uri`
of each dict in the `Files` entry's `media` list and in the top-level `media` list.

Told apart by file. **Surprise:** in the owner's export all 26 records (2008-2009) have an empty
`Message` and empty media lists, so this kind yields 0 posts for the owner. The shape of a non-empty
`Files.media` item was never seen; the fixture assumes `{"uri", "creation_timestamp"}` like media
elsewhere, so read only `uri`.

## Kind `groups` (owner's posts in groups)

File: `your_facebook_activity/groups/group_posts_and_comments.json`.

Top level: `{"group_posts_v2": list}`. Each record has `timestamp`, `data` (list of `{"post": str}`),
optional `title`, optional `attachments` (same shape as timeline, only `external_context` seen).

Rule: same as `timeline` (text from `data[].post`, images from `attachments[].data[].media`). Told
apart by file. Owner's export: 11 records, all with text, none with media.

`your_facebook_activity/groups/your_comments_in_groups.json` (`group_comments_v2`) holds the
owner's comments in groups: not loaded.

## Kind `life-events`

File: `personal_information/profile_information/your_experiences.json`.

Top level: a JSON list of label-value records (same format as `others-timeline`), 4 in the
owner's export. Labels per record: `Start date`, `Start time`, `End date`, `End time`, `Title`,
`Description`, `Ongoing`, `Hidden`, `Creation time`, `Last update time`, `Show description`,
`Show tagged users`, `Show location`, `Eligible as major life event`, a second label-only set
(`Start time`, `End time`, `Starting description`, `Description`, `Tags`, `Starting title`, `Title`),
`Name`, and two title-only entries. `media` lists are empty.

Rule: one post per record, time = top-level `timestamp` (equal to `Creation time`; `Start time` is
0 for the owner), text = the non-empty `value`s of the **first** `Title` and `Description` entries
joined with a blank line; if both are empty, use the `Name` entry's `value`. Told apart by file.

**Surprise:** for the owner all 4 records (2011) have empty `Title` and `Description`; only `Name`
(1-2 words) is set. Whether `Name` is worth a book entry is the owner's call; the fallback above
puts it in.

`profile_update_history.json` (351 "added X to his profile" records) is not a life event and is
not loaded.

## Friends' posts on the owner's timeline -> `TimelineNote`

**Not in the owner's export.** No file or key mentions another person's post to the owner's
timeline, and every record in the main posts file names the owner in its `title`. Facebook's
current export omits them.

The fixture still writes one, in the layout older exports used, so the loader can keep the feature:
file `your_facebook_activity/posts/other_people's_posts_to_your_timeline.json`, top level
`{"wall_posts_sent_to_you_v2": list}`, records shaped like timeline records (`timestamp`, `title`,
`data[].post`). This layout is **unverified**. Rule: if the file exists, one `TimelineNote` per
record with non-empty text; when = `timestamp`, text = `data[].post` joined, author = `title`
(it names the friend; there is no author key, and the note never reaches the printed book).

## Comments -> `Post.notes`

**Not in the owner's export.** No file outside Messenger has a `comments` key; comments other
people wrote on the owner's posts and photos are gone, and so are the owner's replies to them.
Comments on text-only posts were never exported.

The old Face2Book read them from `attachments[].data[].media.comments`, a list of
`{"timestamp": int, "comment": str, "author": str}` (the same dict shape as a comment in
`comments.json`). The fixture writes that. Rule: for every media dict of a kept post, each comment
becomes the note `f"{author}: {comment}"`, in list order, the owner's replies included.

`your_facebook_activity/comments_and_reactions/comments.json` (`comments_v2`, 878 records, one
author: the owner) holds the owner's comments on any post. A record has `timestamp`, `title`,
optional `data[].comment` {timestamp, comment, author} and optional `attachments`. Nothing links a
comment to a post, so it is **not loaded** (this also covers the owner's comments on other people's
posts).

## Photos in albums

`your_facebook_activity/posts/album/<n>.json` (16 files): `{"name", "description",
"last_modified_timestamp", "cover_photo", "photos": [{uri, creation_timestamp, title,
media_metadata?, description?}]}`. 382 photos; 19 of the 20 photos attached to posts are also in an
album (same `uri`). Albums are **not loaded**: a photo becomes book content only through a post.
About 360 album photos (one album of 200) appear in no post, so they are not in the book. The fixture
writes one album that repeats a post photo, so the loader must not count it twice.

Also not loaded: `your_uncategorized_photos.json` (`other_photos_v2`, 1 photo),
`your_videos.json` (`videos_v2`, 1 video), `other_activity/notes.json` (`notes_v2`: 80 Facebook
Notes from 2008-2011 with `title`, `text` (HTML in 42), `created_timestamp`; 53 have text. These are
the owner's own writing and could become a fifth kind later.)

## Kind mapping summary

| Kind | Source | Owner's export |
|---|---|---|
| `timeline` | `posts/your_posts__check_ins__photos_and_videos_*.json` | ~1100 kept of 4270 |
| `others-timeline` | `posts/posts_on_other_pages_and_profiles.json` | 26 records, all empty: 0 |
| `groups` | `groups/group_posts_and_comments.json` | 11 |
| `life-events` | `personal_information/profile_information/your_experiences.json` | 4, `Name` only |

Every kind is told apart by file, so no kind is merged into `timeline`.
