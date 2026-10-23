# Phased implementation

## Phase 1 — Local MVP (delivered)
- Input validation against HTTPS domain allowlist, media choice, mode, date range, archive, job DB, logs.
- yt-dlp for YouTube; gallery-dl for supported social sites; detachable execution, SSH invocation.
- No private-data bypass or third-party cloud service.

## Phase 2 — Shortcut usability
- Improve iOS flows with date pickers, exact limit input, persistent job ID list stored locally in Shortcuts/Files, and push completion notifications via a separately authenticated private service.
- Consider a **localhost** control UI for Mac for login configuration and progress.

## Phase 3 — Higher-quality metadata
- Normalize JSON sidecars to `media` and `posts` tables with source URL, post ID, publish date, local path, media type, caption, and hash.
- Add text-search indexes and export CSV, JSON, ZIP.
- Use platform-specific schemas; do not treat extractor metadata as stable API contracts.

## Phase 4 — Maintenance
- Add integration fixtures and update extractor behavior per platform; run with temporary test profile accounts that you control.
- Gracefully handle rate limits and Terms of Service. Observe permission and copyright requirements.
- Add optional scheduling of *authorized* self-backups only.
