# AI Clip Studio

A Telegram Mini App that turns any long video into viral-ready short clips using AI. Paste a YouTube, Twitch, Kick, or direct MP4 link into the bot, and the AI:

1. Downloads the video
2. Transcribes the audio with Whisper
3. Identifies the most viral-worthy moments using an LLM
4. Writes a title, hook, and virality score for each moment
5. Cuts, crops to 9:16, burns captions, and sends every clip back to your Telegram chat

No manual timecodes. No editing. Just one link in, multiple ready-to-post clips out.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Telegram Bot   │  /start → Web App button
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Mini App (app/static/)                      │
│  Runs inside Telegram WebView                │
└────────┬─────────────────────────────────────┘
         │  POST /api/v1/clips
         │  Header: X-Telegram-Init-Data
         ▼
┌──────────────────────────────────────────────┐
│  FastAPI Web Service (app/)                  │
│  • Validates initData                        │
│  • Enqueues Celery task                      │
│  • Serves static Mini App                    │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Redis (Render Key Value)                    │
│  Message broker + result backend             │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Celery Worker (worker/)                     │
│  1. yt-dlp   → download video                │
│  2. FFmpeg   → extract 16 kHz mono audio     │
│  3. Whisper  → word-level transcript         │
│  4. LLM      → find viral moments + titles   │
│  5. FFmpeg   → cut, crop 9:16, burn captions │
│  6. Bot API  → sendVideo to user's chat      │
└──────────────────────────────────────────────┘
```

Three services on Render:

| Service | Type | Plan | Purpose |
|---|---|---|---|
| `clip-api` | Web Service | Free (or Starter) | FastAPI + Aiogram webhook |
| `clip-worker` | **Background Worker** | **Starter or Standard (paid)** | Celery + FFmpeg + Whisper |
| `clip-redis` | Key Value | Free | Queue + result backend |

> ⚠️ **Background Workers are not available on Render's free tier.** The worker must be on a paid plan (Starter $7/mo, or Standard $25/mo — Standard is realistically what you need for real videos).

---

## 📁 Project Structure

```
tg-clip-studio/
├── app/                          # FastAPI Web Service
│   ├── main.py                   # App entrypoint + Telegram webhook
│   ├── config.py                 # Settings via pydantic-settings
│   ├── bot/
│   │   ├── dispatcher.py         # Aiogram Dispatcher
│   │   └── handlers/start.py     # /start → Web App button
│   ├── api/v1/clips.py           # POST /api/v1/clips, GET /api/v1/health/redis
│   ├── core/
│   │   ├── celery_app.py         # Celery instance
│   │   └── security.py           # initData validation
│   ├── models/job.py             # Pydantic schemas
│   └── static/                   # Mini App frontend (HTML/CSS/JS)
│
├── worker/                       # Celery Background Worker
│   ├── celery_app.py             # Celery app + task registration
│   ├── tasks.py                  # ai_clip_video task
│   └── utils/
│       ├── downloader.py         # yt-dlp wrapper
│       ├── transcribe.py         # faster-whisper wrapper
│       ├── ai_analyzer.py        # LLM prompt + clip validation
│       └── ffmpeg.py             # Audio extraction, cut, crop, ASS captions
│
├── Dockerfile                    # Shared image (FFmpeg + yt-dlp + Whisper baked in)
├── docker-compose.yml            # Local development
├── render.yaml                   # Render Blueprint (infra-as-code)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Local Development

### Prerequisites

- Docker and Docker Compose
- A Telegram bot token ([@BotFather](https://t.me/BotFather) → `/newbot`)
- An LLM API key (OpenAI, OpenRouter, or a local Ollama instance)

### Setup

```bash
git clone https://github.com/your-user/tg-clip-studio.git
cd tg-clip-studio
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=123456:ABC-DEF...
REDIS_URL=redis://localhost:6379/0
WEBHOOK_BASE_URL=http://localhost:8000
WEBAPP_URL=http://localhost:8000/static/index.html

LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
WHISPER_MODEL=base
MAX_CLIPS=6
```

Start the stack:

```bash
docker compose up --build
```

Expose the web service to Telegram with [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Update `.env`:

```env
WEBHOOK_BASE_URL=https://<your-ngrok-subdomain>.ngrok.io
WEBAPP_URL=https://<your-ngrok-subdomain>.ngrok.io/static/index.html
```

Restart the API:

```bash
docker compose restart api
```

Send `/start` to your bot, tap **🎬 Open Clip Studio**, paste a link, and watch the clips arrive.

---

## ☁️ Deploying on Render

### 1. Create the Redis (Key Value) instance

Dashboard → **New → Key Value** → name it `clip-redis` (or any name — but remember it for `render.yaml`) → Free plan → same region as your web service.

Copy the **Internal Connection String** — it looks like `redis://red-xxxxxxxx:6379`.

### 2. Deploy the Blueprint

Push the repo to GitHub, then:

Render Dashboard → **New → Blueprint** → select the repo → Render auto-detects `render.yaml`.

### 3. Set the secret environment variables

The Blueprint marks these as `sync: false`, meaning you must fill them in manually in the dashboard:

| Variable | Where to get it |
|---|---|
| `BOT_TOKEN` | @BotFather |
| `WEBHOOK_BASE_URL` | `https://<your-service>.onrender.com` |
| `WEBAPP_URL` | `https://<your-service>.onrender.com/static/index.html` |
| `LLM_API_KEY` | OpenAI / OpenRouter / etc. |
| `REDIS_URL` | Render Key Value → **Internal Connection String** |

> ⚠️ **`REDIS_URL` must be set on BOTH the web service AND the worker.** If it's only on one, jobs go into the queue and die there forever.

### 4. Register the Mini App URL with BotFather

Telegram → [@BotFather](https://t.me/BotFather) → `/mybots` → your bot → **Bot Settings → Menu Button** → paste your `WEBAPP_URL`.

This is what makes the Web App button appear in the chat.

### 5. Verify

```bash
curl https://<your-service>.onrender.com/health
# → {"status":"ok"}

curl https://<your-service>.onrender.com/api/v1/health/redis
# → {"redis":"ok"}
```

If both return successfully, the pipeline is wired correctly. Send `/start` to your bot and try a short video (2–3 minutes) first.

---

## ⚙️ Configuration

All settings are read from environment variables via `app/config.py`:

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — | **Required.** Telegram bot token |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `WEBHOOK_BASE_URL` | `http://localhost:8000` | Public URL of the web service |
| `WEBAPP_URL` | `http://localhost:8000/static/index.html` | URL of the Mini App |
| `LLM_API_KEY` | `""` | **Required.** API key for the LLM provider |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint (works with OpenRouter, Ollama, Groq, etc.) |
| `LLM_MODEL` | `gpt-4o-mini` | Model used for moment selection |
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `MAX_CLIPS` | `6` | Maximum clips per video |
| `MIN_CLIP_SECONDS` | `15` | Reject clips shorter than this |
| `MAX_CLIP_SECONDS` | `90` | Reject clips longer than this |

### Tuning the AI

The prompt that determines what "viral" means lives in **`worker/utils/ai_analyzer.py`**. Edit `ANALYSIS_PROMPT` to change the emotion targets, style, or hook rules for your niche.

---

## ⚠️ Known Limitations & Gotchas

### Telegram Bot API

- **File upload limit**: 50 MB per video. Longer or higher-bitrate clips must be compressed more aggressively (`-crf 28`) or split.
- **Webhook rate limit**: Telegram rate-limits `set_webhook` aggressively. The app retries with backoff on startup, but running multiple Gunicorn workers can trigger `FloodWait`. The Dockerfile uses `--workers 1` to avoid this.

### Render

- **Free web tier cold starts**: The web service spins down after 15 minutes of inactivity and takes 30–60 seconds to wake up. Use a free uptime pinger (UptimeRobot, cron-job.org) hitting `/health` every 10 minutes to keep it warm.
- **Workers are paid only**: There is no free tier for background workers. Starter ($7/mo) has 512 MB RAM and **will OOM-kill** on real Whisper jobs. Plan on Standard ($25/mo) for anything beyond toy testing.
- **Ephemeral filesystem**: Attach a **2 GB persistent disk mounted at `/tmp`** to the worker — without it, the container crashes when trying to write video files.

### Dependency versions

These pins are not arbitrary — each was chosen to resolve a specific conflict:

- `redis==6.4.0` — Celery's Redis transport requires `redis-py >= 6.1.0`. Older versions throw `Queue unavailable: Redis transport requires redis-py versions 6.1.0 or later`.
- `pydantic==2.9.2` — `aiogram 3.15.0` requires `pydantic<2.10`. Pinning `2.10.x` throws a `ResolutionImpossible` error.
- `openai>=1.59.2,<2.0` — `1.59.0` does not exist on PyPI; versions jump from `1.58.1` to `1.59.2`.

### Dockerfile `$PORT` expansion

The `CMD` is in **shell form** (`sh -c "exec gunicorn ..."`), not exec form. This is intentional — Docker's exec form does **not** expand `$PORT`, which Render injects at runtime. Using exec form produces `Error: '$PORT' is not a valid port number`.

---

## 🧪 Testing the Pipeline

To verify the pipeline without spending money:

1. **Web tier check** — the two health endpoints above return `{"redis":"ok"}` and `{"status":"ok"}`.
2. **Bot check** — `/start` in Telegram returns the "🎬 Open Clip Studio" button.
3. **Mini App check** — tapping the button loads the form with a URL input.
4. **Queue check** — pasting a URL and tapping Generate returns `✅ AI is analyzing the video...` in the Mini App. The job is now sitting in Redis.
5. **Worker check** — open the worker's **Logs** tab on Render. Within 30 seconds of submitting a job, you should see the task being picked up.

If steps 1–4 pass but clips never arrive, the worker is either offline, OOM-killed, or can't reach Redis. Check worker logs first.

---

## 💡 Running the Worker Locally (Free Alternative)

If you don't want to pay for a Render worker yet, you can run the Celery worker on your own laptop while keeping the web service on Render:

```bash
git clone https://github.com/your-user/tg-clip-studio.git
cd tg-clip-studio
pip install -r requirements.txt

export REDIS_URL="rediss://red-xxxxxxxx:6379"   # EXTERNAL, with TLS (note the double 's')
export BOT_TOKEN="your-bot-token"
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o-mini"
export WHISPER_MODEL="base"
export MAX_CLIPS="6"

celery -A worker.celery_app worker --loglevel=info --concurrency=1
```

When the terminal shows `celery@... ready` and `. worker.tasks.ai_clip_video`, the worker is listening. Submit a clip from the Mini App and watch it process.

**Trade-off**: your laptop must be on while processing. Use the **External** Redis URL (starts with `rediss://`), not the internal one.

---

## 🤔 Why Not Cloudflare Workers?

Cloudflare Workers (V8 isolates) **cannot run native FFmpeg** — only `ffmpeg.wasm`, which is limited to 128 MB memory and 5 minutes of CPU time. Whisper alone uses ~500 MB. Cloudflare Containers technically can, but require replacing Celery with Cloudflare Queues, Redis with Durable Objects, and local disk with R2 — weeks of re-engineering to save $25/mo. Not worth it at this scale.

---

## 📄 License

MIT — free to fork, modify, and deploy. Attribution appreciated but not required.

---

## 🙏 Acknowledgements

Built on the shoulders of:

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — fast local speech transcription
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — the gold standard for video downloading
- **[FFmpeg](https://ffmpeg.org/)** — the entire rendering pipeline
- **[aiogram](https://github.com/aiogram/aiogram)** — Telegram bot framework
- **[FastAPI](https://fastapi.tiangolo.com/)** — web framework
- **[Celery](https://docs.celeryq.dev/)** — distributed task queue
