# Actual Apple Shortcuts actions (iOS)

Create **two** Shortcuts in Apple's Shortcuts app: `ProfileDL — Start` and `ProfileDL — Status`. The standard editor is used; no signed `.shortcut` can be generated reliably without the Apple Shortcuts environment.

## Prerequisites

- Mac has Python installed and `profiledl.py` available at a known absolute path.
- Mac: System Settings → General → Sharing → Remote Login enabled.
- iPhone: Shortcuts can connect to the Mac using `Run Script over SSH` using your SSH user and key; test with script `whoami` first.
- Replace `/Users/YOUR_USER/profiledl-starter` in the scripts below with the **actual project folder**, including `.venv/bin/python`.
- iPhone and Mac must reach each other via local network or private VPN. Enable only trusted access.

## Shortcut 1: ProfileDL — Start

In Shortcut Details: **Show in Share Sheet** ON; accepted input types **URLs** and **Safari web pages** (availability/naming may differ by iOS version).

Add these actions in this order:

1. **Get URLs from Input** (`Shortcut Input`) → URL. If working with pasted text rather than Share Sheet, insert **Ask for Input** (Type: URL) and use that as URL instead. Profile URLs must begin with `https://`.
2. **Choose from Menu** (`Media type?`): `Both`, `Photos`, `Videos`. Inside each option add a **Text** action containing exactly `both`, `photos`, or `videos`, followed by **Set Variable** → `Media`. Make the three branches meet after menu.
3. **Choose from Menu** (`Download mode?`): `All accessible`, `Recent 50`, `New only`. Each branch: **Text** value `all`/`recent`/`new`, **Set Variable** → `Mode`. For `Recent 50`, set `Limit` to number `50`; for the others `0`.
4. **Dictionary** action: add these keys (all text unless noted): `url` → URL variable (Text), `media` → Media variable (Text), `mode` → Mode variable (Text), `limit` → Limit (Number), `metadata` → `true` (Boolean). Add `after` and `before` only if using explicit `YYYY-MM-DD` dates.
5. **Get Text from Input** (Dictionary) is *not* a reliable JSON serialization on every iOS version. Instead use **Get Dictionary from Input** only if your constructed input is already JSON. For guaranteed JSON, add **Get Contents of URL**? That is not needed here. Use **Get Text from Input** on the Dictionary and first verify its output starts with `{` and parses as JSON. Prefer **Get JSON from Dictionary** / **Get Text from Dictionary** if offered in your iOS version. To avoid editor version differences, use **Text** below with native variable interpolation and quote-escaping caveat. **Recommended robust procedure:** add **Set Name** not needed; use **Dictionary** → **Get Text from Input** and inspect with **Quick Look** before wiring SSH; use the result only if valid JSON.
6. **Run Script over SSH** with Host (Mac IP or mesh VPN name), User, SSH key, Script:
   ```sh
   /Users/YOUR_USER/profiledl-starter/.venv/bin/python /Users/YOUR_USER/profiledl-starter/profiledl.py submit-stdin
   ```
   Set the action's **Input** to the JSON dictionary text from the previous step (passed over stdin). The shortcut waits only for job creation.
7. **Get Dictionary from Input** on SSH output (a JSON result). Then **Get Dictionary Value** → `id`; **Set Variable** → `JobID`.
8. **Show Result**: `Started ProfileDL job: [JobID]`. Optionally **Copy to Clipboard** the JobID so you can check progress later.

### Safer alternative when dictionary-to-JSON is troublesome

Use a **Text** action containing a single JSON object, interpolating only the URL if the URL is from Shortcuts' URL parser, e.g. `{"url":"[URL]","media":"both","mode":"all","limit":0,"metadata":true}`. Do not interpolate arbitrary free-form text into JSON; URLs can contain quotes or escapes. You can instead create this JSON in a **Scriptable** helper app, or use the CLI variant with shell-safe encoding. The project includes a CLI with `submit-stdin` precisely to avoid shell injection.

## Shortcut 2: ProfileDL — Status

1. **Ask for Input** (Text): `Enter ProfileDL job ID` → `JobID`.
2. **Run Script over SSH** (same Mac and SSH user), **Input** = JobID, script:
   ```sh
   read -r JOB_ID
   case "$JOB_ID" in (*[!a-f0-9]*|'') echo '{"error":"Invalid job id"}'; exit 1;; esac
   /Users/YOUR_USER/profiledl-starter/.venv/bin/python /Users/YOUR_USER/profiledl-starter/profiledl.py status "$JOB_ID"
   ```
3. **Get Dictionary from Input** on SSH output.
4. **Get Dictionary Value** `status` and **Show Result** with its value. Optionally also display `folder` and `error`.

## Testing

1. Run the Start shortcut with a single publicly accessible *post* first, not a large profile.
2. Confirm it returns a 16-character job ID.
3. Run Status; look for `completed` or `failed`.
4. Verify files in `data/downloads` and detailed job log in `data/logs`.
5. Try `Recent 50` on a known public profile; use `All accessible` only after verifying the target extractor supports profile URLs.

**No `.shortcut` file is supplied:** a plain-text sequence of actions is portable and avoids handing out an untrusted serialized shortcut that silently requires iCloud permissions or an external signer.
