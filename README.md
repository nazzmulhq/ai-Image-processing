# AI Image Processing

A small web app and API for processing images. You can:

- drop images onto a web page;
- resize, convert (JPEG / PNG / WEBP) and compress them;
- apply a photo filter or a one-click enhance;
- optionally let **Google Gemini** find the objects in them and outline each one.

Nothing is stored and there is no login. Each image is processed in a private temporary folder, the result is sent straight back to the page, and the folder is deleted.

---

## Step-by-step setup

There are two ways to run the app. Pick one:

| | **Option A: run on your machine** | **Option B: run with Docker** |
|---|---|---|
| Best for | Development, editing the code | Just running it |
| You install | Git + uv | Git + Docker Desktop |
| Python needed? | No, uv downloads Python 3.13 for you | No |

> These steps are for **macOS and Linux**. On Windows, use WSL2 (Ubuntu) and follow the Linux steps.

### Step 1: Install the tools

**Git** (both options):

```bash
# macOS
brew install git

# Ubuntu / Debian
sudo apt update && sudo apt install -y git
```

**uv** (Option A only):

```bash
# macOS
brew install uv

# macOS or Linux, without Homebrew
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing uv, open a **new terminal** so the `uv` command is found.

**Docker Desktop** (Option B only): install it from <https://www.docker.com/products/docker-desktop/>, then start it.

Check what you installed:

```bash
git --version
uv --version        # Option A
docker --version    # Option B
```

### Step 2: Get the code

The first time, clone the repository:

```bash
git clone https://github.com/nazzmulhq/ai-Image-processing.git
cd ai-Image-processing
```

If you use SSH keys with GitHub, this works too:

```bash
git clone git@github.com:nazzmulhq/ai-Image-processing.git
cd ai-Image-processing
```

> If the repository is private, the owner must add you as a collaborator first.

**Already cloned it before?** Go into the folder and pull the latest code instead. See [Updating to the latest version](#updating-to-the-latest-version).

```bash
cd ai-Image-processing
git pull
```

### Step 3: Install the dependencies (Option A only)

```bash
uv sync
```

This does three things:
- creates a `.venv/` folder inside the project;
- downloads Python 3.13 if you don't have it;
- installs the exact package versions listed in `uv.lock`.

The first run takes about a minute; later runs take a second.

Docker users can skip this step, because Docker installs everything inside the container.

### Step 4: Create your settings file

```bash
cp .env.example .env
```

Open `.env` in any text editor and set these two lines:

```dotenv
# Optional: turns on object detection. Get a free key at https://aistudio.google.com/apikey
GEMINI_API_KEY=your-key-here

# Leave this EMPTY unless your Google Cloud project has billing turned on
GEMINI_IMAGE_EDIT_MODEL=
```

- **Without a Gemini key**, everything works except object detection.
- **Leave `GEMINI_IMAGE_EDIT_MODEL` empty.** `.env.example` pre-fills it, but Gemini image editing has no free tier, so on a free key it only fails.
- **Never commit `.env`**: it holds your secret key. Git already ignores it.

### Step 5: Run it

**Option A: on your machine**

```bash
make dev
```

This is the same as:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Leave this terminal open; the app's logs appear here. The server restarts by itself when you save a code change.

**Option B: with Docker**

Make sure Docker Desktop is running, then:

```bash
docker compose up --build -d
```

The first build takes a few minutes. `-d` runs it in the background. To watch the logs, run:

```bash
docker compose logs -f app
```

### Step 6: Open it and check it works

1. Open **<http://localhost:8000>** in your browser. The top of the page should say **"Ready: …"**.
2. The API documentation is at **<http://localhost:8000/docs>**.
3. From a terminal, check the server's health:

   ```bash
   curl http://localhost:8000/health
   ```

   You should get `"status":"ok"`. `"gemini"` says `"configured"` if your key was picked up, or `"not_configured"` if not.

### Step 7: Stop it

- **Option A:** press **Ctrl + C** in the terminal where `make dev` is running.
- **Option B:** run `docker compose down`.

---

## Updating to the latest version

From inside the project folder:

**Option A: on your machine**

```bash
git pull
uv sync          # installs any new or changed dependencies
make dev
```

**Option B: with Docker**

```bash
git pull
docker compose up --build -d
```

Your `.env` file is not touched by `git pull`. If a new version adds settings, compare the two files and copy over anything new:

```bash
diff .env.example .env
```

If `git pull` says *"Your local changes would be overwritten"*, set your changes aside, pull, then bring them back:

```bash
git stash
git pull
git stash pop
```

---

## Using the page

1. **Add images.** Drag them onto the drop zone, click it to choose files, or paste an image (Cmd/Ctrl + V). JPEG, PNG and WEBP up to 20 MB are accepted.
2. **Pick options:**
   - a filter (Golden hour, Black & white, Old film, Warm, Cool);
   - a size;
   - an output format and quality;
   - **Enhance**;
   - **Find objects and mark them**, which needs a Gemini key.
3. **Click "Process images".** Up to 3 images are processed at a time.
4. **Use the result.** Each result shows the new size, format and file size, plus any objects Gemini found, outlined on the image. From there you can:
   - **Show original** to compare;
   - **Copy image**;
   - **Download** the result;
   - click the image to zoom in.

You can also call the API directly; see **<http://localhost:8000/docs>**. For example:

```bash
curl -s -F image=@photo.jpg -F target_width=800 -F output_format=WEBP \
  http://localhost:8000/api/v1/images/process
```

The processed image comes back in the JSON response as a base64 `data_url`.

---

## Useful commands

| Task | With `make` | Without `make` |
|---|---|---|
| Install dependencies | `make install` | `uv sync` |
| Run with auto-reload | `make dev` | `uv run uvicorn app.main:app --reload --port 8000` |
| Check code style | `make lint` | `uv run ruff check .` |
| Auto-fix style issues | `make format` | `uv run ruff check . --fix` |
| Test your Gemini key | `make check-gemini` | `uv run python scripts/check_gemini.py --edit` |
| Docker: start | `make up` | `docker compose up --build -d` |
| Docker: follow logs | `make logs` | `docker compose logs -f app` |
| Docker: stop | `make down` | `docker compose down` |

---

## Settings

All settings live in `.env`; each one is explained in the comments in [.env.example](.env.example). Restart the app after changing `.env`: press Ctrl + C and run `make dev` again, or run `docker compose up -d` again.

The ones you're most likely to change:

| Setting | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | empty | Turns on object detection. Stays on the server and is never sent to the browser |
| `GEMINI_IMAGE_EDIT_MODEL` | empty | AI editing. Needs Gemini billing; leave empty otherwise |
| `MAX_UPLOAD_BYTES` | 20 MB | Largest file you can upload |
| `RATE_LIMIT_IP_PER_MINUTE` | 30 | Uploads allowed per minute from one computer |
| `MAX_CONCURRENT_PER_IP` | 3 | Images one computer can process at the same time |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv: command not found` | Open a new terminal after installing uv. Or run `source $HOME/.local/bin/env`. |
| `Permission denied (publickey)` when cloning | Use the `https://` clone URL, or add your SSH key to GitHub. |
| `Address already in use` | Something else is using port 8000. Find it with `lsof -i :8000` and stop it, or use another port: `uv run uvicorn app.main:app --reload --port 8001`, then open http://localhost:8001. |
| `Cannot connect to the Docker daemon` | Docker Desktop isn't running. Start it (on macOS: `open -a Docker`), wait until it's ready, and try again. |
| Docker says `.env` not found | You skipped Step 4. Run `cp .env.example .env`. |
| The page says "Gemini isn't configured" | Put your key in `GEMINI_API_KEY` in `.env`, then restart the app. Run `make check-gemini` to test the key. |
| A result shows "Object detection failed … rate limited" | You've hit Gemini's free-tier limit. Wait a minute and try again; the image itself was still processed. |
| "Too many uploads in a short time" | You hit the per-minute limit. Wait a minute, or raise `RATE_LIMIT_IP_PER_MINUTE` in `.env`. |
| "The processed image is … above the response limit" | Ask for a smaller size, or JPEG/WEBP instead of PNG. |

---

## Project layout

```
app/
  main.py          starts the app: process pool, Gemini client, routes, web page
  api/             HTTP routes, middleware, error responses
  core/            settings, limits, logging, error codes
  schemas/         request and response models
  services/        the image pipeline, Pillow operations, Gemini client, temp folders
  utils/           file validation, safe file names
  static/          the web page (index.html, app.js, styles.css)
scripts/           check_gemini.py: tests your Gemini key and models
loadtest/          locustfile.py: load test
Dockerfile, docker-compose.yml, Makefile, pyproject.toml, uv.lock, .env.example
```
