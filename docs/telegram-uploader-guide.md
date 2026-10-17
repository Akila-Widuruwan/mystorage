# Episode → Telegram uploader — complete setup guide

Turn one anime episode page URL into a **full MP4 posted in your own Telegram channel** — using only free tiers and GitHub's free runners. No VPS needed for this, no storage quota on your side: the file lives on Telegram (2 GB per file on a free account) and is posted **from your own account**, in one single streamable video.

```
episode page URL ──▶ resolve stream (animesuge) ──▶ download HLS ──▶ ffmpeg remux
      ──▶ upload to your Telegram channel (up to 20 parallel connections, live % in the log)
```

The workflow file is [`tools/github-workflows/episode-to-telegram.yml`](../tools/github-workflows/episode-to-telegram.yml) — a single self-contained file (the whole downloader is written by the workflow itself, there is nothing else to install).

> Prefer abyss instead? The same workflow still supports it: run with **target = `abyss`** (needs the `ABYSS_KEY` secret). Everything below is for the default `telegram` target.

---

## Part 1 — Get your Telegram API credentials (2 minutes)

1. Open **<https://my.telegram.org>** and log in with your phone number.
2. Click **API development tools**.
3. Fill *App title* (anything, e.g. `uploader`) and *Short name* → **Create**.
4. Note the two values shown:
   - **App api_id** — a number
   - **App api_hash** — a 32-character string

## Part 2 — Create your session string (one time, ~3 minutes)

A "session string" is a portable login for your own Telegram account. GitHub runners have no keyboard, so this login is done **once, on a machine you control** (your PC or your own VPS) using the helper script [`tools/github-workflows/generate-telegram-session.py`](../tools/github-workflows/generate-telegram-session.py).

```bash
pip install telethon
# Debian 12/13 VPS? If pip says "error: externally-managed-environment", use:
# pip install telethon --break-system-packages

wget https://raw.githubusercontent.com/Akila-Widuruwan/mystorage/main/tools/github-workflows/generate-telegram-session.py
python3 generate-telegram-session.py
```

It asks for (in order):

| Prompt | What to enter |
|---|---|
| `api_id` | the number from Part 1 |
| `api_hash` | the 32-char string from Part 1 |
| `your phone number` | **your own number**, international format, e.g. `+94771234567` |
| `the code you received` | the code Telegram sends to your Telegram app |
| 2FA password | only if you enabled two-factor verification |

Expected output:

```
Logged in as: Your Name @yourusername   <- user account, correct

== DONE. Add this string to your repo secrets as TG_SESSION ==

1BQANOTEuMTA4L...=
```

Copy that long string — it is your `TG_SESSION` secret.

**⚠️ Two rules:**

- Enter your **phone number**, never a bot token. A bot token creates a bot session, which the workflow detects and rejects (bots are capped at 50 MB — the whole reason this uses your account).
- The string **is** your logged-in account. Treat it like a password. If it ever leaks: Telegram → Settings → Devices → terminate the session, then generate a new one.

## Part 3 — Pick the target channel

The workflow can post to any channel/group **your account is in**. You need one of:

- the channel's **@username** (public channels), or
- the channel's **numeric id** like `-1001234567890` (private channels — the normal case).

Don't know the id? Any of these works:

- Post any message in the channel, forward it to `@usernamerawbot` (or similar) and read the id, **or**
- Just run the workflow once with your best guess: if the channel can't be resolved, the job log **prints every channel your account can post to with its id** — copy the right one.

The channel NAME (e.g. `server1`) does **not** work — only `@username` or the numeric id.

## Part 4 — Add the 4 repo secrets

In the repo where the workflow will run: **Settings → Secrets and variables → Actions → New repository secret**, repeat 4×:

| Name | Value |
|---|---|
| `TG_API_ID` | number from Part 1 |
| `TG_API_HASH` | 32-char string from Part 1 |
| `TG_SESSION` | long string from Part 2 |
| `TG_CHANNEL` | `@username` or `-100...` id from Part 3 |

GitHub always masks secrets in logs; never put them in the workflow file itself.

## Part 5 — Install the workflow

**Use a private repo for this** (e.g. `anime-worker`): free private repos include 2,000 Actions-minutes/month (~150+ episodes) and keeps your run history out of public view.

1. Create the private repo on github.com.
2. **Add file → Create new file**, type the path exactly (the slashes create the folders):
   ```
   .github/workflows/episode-to-telegram.yml
   ```
3. Paste the full content of [`tools/github-workflows/episode-to-telegram.yml`](../tools/github-workflows/episode-to-telegram.yml) → **Commit changes**.
4. Add the 4 secrets **in that same repo** (Part 4).

From the terminal instead: `mkdir -p .github/workflows`, copy the file in, commit, push — same result.

## Part 6 — Run it

Repo → **Actions** → **Convert episode to mp4 -> Telegram (single file)** → **Run workflow**:

| Input | Meaning | Example |
|---|---|---|
| `page` | episode page url | `https://animesuge.cz/anime/<slug>/ep-3` |
| `name` | output file name (no spaces) | `Black-Clover-S02E03` |
| `quality` | `best`, `1080`, `720`, `480`, `360` | `best` |
| `lang` | `sub` or `dub` | `sub` |
| `server` | force one server (empty = try all) | *(empty)* |
| `limit` | first N seconds only — **use `20` for your first test** | `0` = full episode |
| `target` | `telegram` (default) or `abyss` | `telegram` |

Expected log of a successful run:

```
posting as: Your Name (@yourusername)
posting /home/runner/work/.../Black-Clover-S02E03.mp4 (487.2 MB) to My Channel [parallel upload, up to 20 connections]
upload:  10% (48 / 487 MB)
upload:  20% (97 / 487 MB)
...
upload: 100% (487 / 487 MB)
uploaded: https://t.me/c/1234567890/12
```

Typical timing for a full episode: **10–25 minutes total** (download 5–15 min, remux 1–3 min, upload 2–5 min). The upload is posted by **your account** and plays inline in Telegram (streamable video, with an auto-generated thumbnail).

## Performance notes

- Uploads use **FastTelethon** (up to 20 parallel MTProto connections) + **cryptg** (C-speed encryption) — roughly 10–20× faster than Telethon's default single connection.
- If the parallel uploader ever errors, the workflow **automatically falls back** to the normal uploader instead of failing.
- Telegram throttles datacenter IPs at times; speeds vary run to run. Too many parallel connections can trigger FloodWait — the workflow retries up to 3 times automatically.

## Troubleshooting

| Symptom in the log | Cause & fix |
|---|---|
| `secret TG_* is not set` | A secret from Part 4 is missing/misnamed in **that** repo |
| `TG_SESSION is not authorized` | Session string wrong or revoked — redo Part 2, update the secret |
| `TG_SESSION is a BOT session` | You entered a bot token in Part 2 — redo it with your phone number |
| `could not resolve TG_CHANNEL` (+ a channel list) | Id/username not visible to your account — copy the correct `id=` from the list printed right below into `TG_CHANNEL` |
| `blocked by Cloudflare` | The site challenged the runner's IP — just re-run; persistent cases usually clear within hours |
| `... MB - Telegram accounts allow 2 GB per file` | Episode too large — run with `quality: 1080` or `720` |
| `FloodWait: sleeping Ns` | Normal Telegram rate-limit — the job sleeps and continues by itself |
| `upload failed after 3 attempts` | Re-run the workflow; if it repeats, lower `quality` or try again later |
| Run fails only at "Verify the output" | Stream died mid-download — the download step already retries 3× with a fresh link; re-run once more |

## Storage, limits and staying safe

- Files live in your **Telegram channel** — no total quota (2 GB **per file** free, 4 GB with Telegram Premium). Your VPS and GitHub store nothing.
- **Keep the channel private.** Public channels are reachable by takedown requests; private channels are not indexed and only members (and anyone with an invite) can open them.
- The resolved stream URL is short-lived and bound to the runner's IP — it is resolved fresh at every run and never reused.
- The debug artifact only contains `resolved.json` (the resolved link), never the video — the free 500 MB artifact quota is untouched.

## Using it with AnimeLK Storage

Files posted this way are ordinary channel posts, so you can register them in your self-hosted manager via the built-in importer: open **`/telegram-import`** in your AnimeLK Storage dashboard and click **Scan channel & import**. Playback of files over 20 MB needs the self-hosted Bot API server proxy from the main [README](../README.md#full-file-telegram-uploads-one-clean-mp4-no-chunks).
