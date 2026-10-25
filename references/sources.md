# Getting footage

## Local files
Any format ffmpeg reads (mp4, mov, webm, mkv, animated gif). Pass the path straight to `video2ascii.py`. Use `--start`/`--dur` instead of trimming by hand; frames are read with `-ss/-t`, so nothing outside the range is decoded.

## URLs
`video2ascii.py URL …` runs `uvx yt-dlp` into a temp dir. With `--start`/`--dur` it passes `--download-sections "*S-E"`, so only that part downloads. This matters for long videos and music-video-length uploads.

| Site | Usually works? | If not |
|---|---|---|
| YouTube, Vimeo, X/Twitter, Reddit, Bilibili | yes | Update yt-dlp (`uvx yt-dlp@latest`), retry once |
| TikTok | sometimes | Ask the user for the file |
| Douyin (v.douyin.com, douyin.com) | rarely; needs fresh cookies | Ask the user for the file |
| Instagram | rarely; needs login | Ask the user for the file |

When a download fails, tell the user why in one sentence (the site needs their logged-in cookies) and ask them to save the video and give you the path. A sandbox can't use their browser's cookies, and guessing at cookie flags wastes turns. Never produce an animation "from" a link you couldn't download.

If a network block (HTTP 403 from a proxy or firewall) stops the download, read the response body and follow its instructions, usually by asking the user to allow the domain.

## Choosing the clip
- User gave a range → use it exactly ("first 9 seconds" = `--start 0 --dur 9`).
- No range → 2–6 s around the main action. Say which range you picked.
- Loops: look at the contact sheet for two frames with matching poses and trim between them. A walk cycle is two steps.
- The subject should fill much of the frame. Crop (`--crop x,y,w,h` in source pixels) before converting rather than after; more cells on the subject means more detail.
- Facing direction: `--mirror` flips horizontally before conversion.
