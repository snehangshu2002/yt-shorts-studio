# Publishing: thumbnails, titles, descriptions, upload checklists

The user uploads. The skill prepares everything and walks them through it.

## Contents
1. Thumbnails and covers
2. Titles
3. Descriptions and captions
4. Tags, hashtags, pinned comment, alt text
5. publish_metadata.md template
6. Upload checklist: YouTube Shorts
7. Upload checklist: Instagram Reels (and TikTok)
8. Rights

## 1. Thumbnails and covers
- **Frame:** the peak of the clip, with a face showing a strong emotion and the payoff in view
  (the crash, the money, the reveal). Avoid motion blur and transition frames. Look at the
  contact sheets and pick 2-3 candidates; check each full-size.
- **Shorts/Reels cover (1080x1920):** render a caption-free still of the edit
  (`render_ffmpeg.py OUTDIR spec still.png --still T`) and design on it:
  `thumbnail.py --video still.png --time 0 --text "HE *PASSED OUT*" --out covers/clipNN_cover.jpg`.
  Text sits in the top 30% by default (the grid crops to the centre, and the UI covers the
  bottom). 2-5 words, the key word in `*accent*`.
- **YouTube thumbnail (1280x720):** use the 16:9 mezzanine:
  `--video mezz/clipNN.mp4 --time T --size 1280x720 --focus-x 0.6 --zoom 1.15`, with text at
  the bottom. A 16:9 version is also handy as the Instagram profile-grid preview.
- Thumbnail text must not repeat the title word for word. It adds the emotion or stakes.
- Custom thumbnails for Shorts depend on the account and app. On desktop Studio, if there's
  no upload option, set the frame in the YouTube mobile app (edit → Thumbnail).

## 2. Titles
- YouTube limit is 100 characters; keep it to about 40-60 so it isn't truncated on Shorts.
- Put the hook up front: the stake, the surprise, or the question. Use specific nouns (GTA 6,
  pawn shop, $0) over vague hype. One or two words in caps at most.
- It must be true to the clip. Give 2 alternates per clip (a curiosity angle and a
  benefit/claim angle).
- Patterns: "We Had $0 in X, So We Did THIS" · "The X Who Y During Z" · "Nobody Tells You
  This About X" · "I Tried X for N Hours…" · "The Moment X Realised Y".

## 3. Descriptions and captions
YouTube description: 1-2 sentences of context and hook (searchable keywords), a blank line,
the full-video link with credit, a blank line, 3-5 hashtags ending with `#Shorts`.
Instagram caption: one punchy line plus an emoji, a credit line, 3-5 hashtags (`#Reels`).
TikTok: a short line plus 3-5 hashtags. All of them must describe only what happens inside
this clip's time window, so check the transcript before claiming any detail.

## 4. Tags, hashtags, pinned comment, alt text
- YouTube tags: 8-15 phrases (topic, game/show name, creator name, format words).
- Hashtags: 3-5, from broad to specific. Never stuff unrelated trending tags.
- Pinned comment: a question that invites one-word or opinion replies.
- Instagram alt text: one sentence that literally describes the visuals and layout.

## 5. publish_metadata.md template
```
# <Video> — publishing details
Source: "<title>" (<channel>) — <url>
Common settings: category · audience: not made for kids · altered content: No · language ·
related video link · credit line

## Short NN — <working title>
File: finals/<file> · <duration> · source <mm:ss–mm:ss>
YouTube title (<n> chars): …
Alternate titles: … / …
YouTube description: …
Instagram caption: …
YouTube tags: …
Cover: covers/<file> (frame at <t>) · cover text: …
Pinned comment: …
Instagram alt text: …
```

## 6. Upload checklist: YouTube Shorts (Studio on desktop)
1. Create → Upload videos → choose the final MP4. Vertical and ≤3 min means it becomes a Short.
2. **Details:** paste the title and description. Thumbnail: upload the cover if offered,
   otherwise set it later in the mobile app. Playlist: one series playlist (optional).
   Audience: "No, it's not made for kids".
3. **Show more:** Altered content: No (unless AI-generated scenes were added). Tags: paste.
   Language and caption certification: English / none. Category: as appropriate (Gaming,
   People & Blogs, Education…). Comments: on.
4. **Video elements:** Related video = the full source video (if it's on YouTube and
   searchable).
5. **Checks:** wait for the copyright check. "No issues found" is good; a claim on third-party
   footage usually means monetisation goes to the owner or the video is blocked in some
   regions, so tell the user before they publish.
6. **Visibility:** Public now or Schedule (one Short a day spreads reach). Then post and pin
   the comment.

## 7. Upload checklist: Instagram Reels (and TikTok)
Instagram: + → Reel → select the MP4 (9:16, ≤90 s for full Reels reach) → Next → caption
plus hashtags → Edit cover → "Add from camera roll" (the 1080x1920 cover), and check the grid
crop → Tag people (if they are the creator and agreed) → Advanced settings: Share to Facebook
optional; Alt text → Share.
TikTok: upload → caption plus hashtags → Select cover (frame only, or a text overlay) →
allow comments → Post. Burned-in captions mean you don't need TikTok's auto captions.

## 8. Rights
Clipping another creator's video is their content. Always credit and link the source. Say
plainly that Content ID or a takedown is possible without permission. Prefer clips with added
value (captions, framing, commentary). Never present the clip as the user's own original
footage or impersonate the creator.
