# AI Image Processing

Resize, convert and compress images in the browser, with object detection by Google Gemini. There is no login and nothing is stored.

## Setup

**1. Install the tools.** You need Git and [uv](https://docs.astral.sh/uv/). uv installs Python for you.

```bash
brew install git uv      # macOS
# Linux: sudo apt install git && curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Get the code.**

```bash
git clone https://github.com/nazzmulhq/ai-Image-processing.git
cd ai-Image-processing
```

**3. Install the dependencies.**

```bash
uv sync
```

**4. Create your settings file.**

```bash
cp .env.example .env
```

In `.env`, paste your Gemini key into `GEMINI_API_KEY` to turn on object detection. This is optional; get a key at <https://aistudio.google.com/apikey>.

**5. Run it.**

```bash
make dev
```

Open <http://localhost:8000>. The API docs are at <http://localhost:8000/docs>. Press **Ctrl + C** to stop.

### With Docker instead

Docker replaces steps 1 and 3; you only need Git and Docker Desktop. Do steps 2 and 4, then:

```bash
docker compose up --build -d   # start
docker compose down            # stop
```

## Update

```bash
git pull
uv sync
make dev
```

With Docker, run `git pull && docker compose up --build -d` instead.

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv: command not found` | Open a new terminal after installing uv. |
| `Address already in use` | Port 8000 is busy. Run `uv run uvicorn app.main:app --reload --port 8001` and open port 8001. |
| `Cannot connect to the Docker daemon` | Start Docker Desktop and try again. |
| The page says "Gemini isn't configured" | Set `GEMINI_API_KEY` in `.env`, then restart the app. |
