# Architecture and security

`Share Sheet → Apple Shortcuts → SSH/stdin → Python CLI → SQLite job DB → detached Python worker → gallery-dl/yt-dlp → media and archives`.

No inbound HTTP API, open port, credentials in remote requests, or paid service required. SSH is the only remote channel.

## Job model

`queued → running → completed | failed`. Workers launched using `start_new_session=True` and redirected standard handles to `/dev/null` so a Shortcut disconnect does not stop a run. Jobs are not automatically retried after host restarts. `status()` reads DB + last log lines. Separate concurrent jobs writing to the **same profile archive** may conflict; avoid duplicate simultaneous submissions for the same URL.

## Extractor routing

- YouTube → yt-dlp, with per-profile text archive.
- Instagram/TikTok/X/Facebook/Reddit/Pinterest/Tumblr/Threads → gallery-dl, with per-profile SQLite archive.
- No scraping fallback or credential circumvention. Some URLs may be unsupported by the selected engine; if so inspect logs and update tool versions.

Media filtering uses gallery-dl's `extension` expression. This is an extractor-specific metadata key; not every extractor sets it or classifies GIF/video consistently. For YouTube, `photos` is rejected instead of returning misleading results.

A limit counts **posts** for gallery-dl and **playlist items** for yt-dlp; totals will differ from file counts, especially with carousels. Date filtering may stop feed traversal or drop posts depending on engine and extractor.

The `new` mode uses archives but intentionally scans the feed rather than stopping on previously downloaded items, to avoid missing out-of-order/pinned items.

## Production-hardening backlog

- SQLite unique active-job lock keyed by canonical account URL (prevent concurrent archive writes).
- Stop/retry and stale-worker detection.
- Manifest of actual downloaded assets + hashes; statistics and progress reporting.
- Strict CPU/storage/size quota; disk-free checks before large jobs.
- Local auth configuration gated behind profile-specific credentials, never exported to the phone.
- Unit and integration coverage for each platform/extractor version.
- Web interface bound to localhost, optional mesh-VPN access with authentication.
