# ProfileDL — iPhone + Mac/Linux/Windows profile downloader

Local download engine with a thin iOS Shortcuts frontend. Targets supported URL formats on Instagram, TikTok, X/Twitter, YouTube, Facebook, Reddit, Pinterest, Tumblr, Threads. **Support is dependent on the current extractors and platform access; not every profile, post, Reel, Story or Highlight works.** It only downloads media accessible with your authorized access. Never bypass access controls or use it to collect private material without permission.

## Quick start: Mac

```bash
cd profiledl-starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
brew install ffmpeg  # if Homebrew is installed; yt-dlp may require ffmpeg
python -m unittest discover -s tests -v
python profiledl.py submit 'https://www.youtube.com/@example/videos' --media videos --mode recent --limit 3
python profiledl.py list
python profiledl.py status YOUR_JOB_ID
```

For Windows: create `.venv` using `py -m venv .venv`, install packages with `.venv\\Scripts\\python -m pip install -r requirements.txt`, install FFmpeg, run the same commands. Remote SSH shell snippets and launch assumptions require adaptation to PowerShell; Mac/Linux is the tested-target architecture.

**SSH first:** On Mac: System Settings → General → Sharing → Remote Login → On; allow your account. Ensure phone and Mac are on a trusted LAN or private mesh VPN. Add the Mac to the iOS Shortcuts **Run Script over SSH** action using SSH username/host and an SSH key (preferred). Do not forward SSH to the public Internet. The Mac must be powered on, awake, connected. Test `whoami` via Run Script over SSH. On Windows enable OpenSSH Server and adapt the launcher.

## Functionality

- Download one post, a profile/channel or accessible collections, depending on the URL/extractor.
- Mode `all`, `recent` (specified limit), `new` (archives skip items already downloaded). Note: **all modes archive and deduplicate**, while `all` scans the whole accessible feed; `new` also scans rather than stopping after the first existing item (safer for pinned/out-of-order posts).
- `photos` / `videos` / `both`; YouTube supports `videos`/`both` (not photos-only).
- Resume between runs with gallery-dl SQLite archives or yt-dlp ID archives. Partial-file continuation depends on source support.
- Persistent job status and logs in SQLite; workers detached from the initiating SSH session.
- Optional creation of JSON metadata sidecars; no global scraped-user catalog.
- Date filters (engine-specific; some extractors have incomplete dates).

## Directory structure

`data/downloads/<platform>/<profile>-<urlhash>/` (contents may include extractor subfolders), `gallery-archive.sqlite3` or `yt-archive.txt`; `data/jobs.sqlite3`; `data/logs/<jobid>.log`.

## Profile URL examples

- `https://www.instagram.com/username/`
- `https://www.tiktok.com/@username`
- `https://x.com/username`
- `https://www.youtube.com/@username/videos` (videos tab; `/shorts` for Shorts, when supported)
- `https://www.reddit.com/user/username/`
- `https://www.pinterest.com/username/`

Other allowlisted hosts are best-effort. Some profiles require login or extractors may only handle individual posts. Platform authentication can be set up using **local** downloader config files or browser-cookie integration; do not put passwords/cookies into Shortcuts, SSH input, or URLs. This starter uses `--config-ignore` for gallery-dl and `--ignore-config` for yt-dlp to keep execution deterministic; if you require authentication, explicitly extend `build_command()` with tightly scoped, local credential config. Never commit credentials.

## Docs

- [Exact Apple Shortcuts action sequence](docs/APPLE_SHORTCUTS.md)
- [Architecture, behavior and security](docs/ARCHITECTURE.md)
- [Implementation phases](docs/IMPLEMENTATION.md)

## Known limitations

1. Original RoutineHub shortcut [#4448](https://routinehub.co/shortcut/4448/) returned HTTP 403 to automated access. This project is a **new implementation inspired by its share-sheet UX**, not an imported/decompiled `.shortcut`.
2. Social media site APIs/layouts/rate limits and login requirements change. Full profile completeness is not guaranteed. Private or deleted content is not available merely because a URL is provided.
3. A 'completed' job means the subprocess returned success, **not** that every expected post exists; inspect output and logs.
4. Jobs survive a phone disconnect, but an unexpected Mac reboot during a job leaves `running` until you rerun that request. Restarting with the same URL uses the per-profile archive. Explicit interruption/cancellation is not implemented in v1.
5. Shortcuts input is not an authenticated service API: SSH identity is the security boundary. Each authorized SSH account can operate this download service.
