# Image Light Table

A stateless image processing service with a built-in web page. You can:
- drop images onto the page and pick options;
- resize, convert, compress, apply a photo-filter preset and enhance images with Pillow;
- detect objects in them with Google Gemini.

The page shows the processed image with every detected object outlined, plus labels, descriptions, dimensions, format and file size. You can drag files in, paste an image straight from the clipboard, click a photo to zoom in, copy or download the result, and compare it against the original. It follows your system's light/dark setting.

The page itself only exposes what reliably works without extra setup: resize/convert/compress, the filter presets, deterministic enhancement, and Gemini object detection. The API additionally accepts manual `rotate`/`flip_horizontal`/`flip_vertical`/`brightness`/`contrast`/`saturation`, and a Gemini-powered `ai_edit_prompt`/`remove_background` (see [API](#api) below) — useful from Swagger, a script, or your own frontend, just not surfaced as page controls.

- **No login.** Anyone who can reach the server can use it; per-IP limits keep it fair.
- **No database and no stored files.** Each upload is processed in a private temp folder. The result goes straight back in the response, and the folder is deleted.

| Where | What |
|---|---|
| `http://localhost:8000/` | Web page |
| `/docs` | API reference (Swagger) |
| [docs/frontend-integration.md](docs/frontend-integration.md) | Calling the API from your own frontend |

---

## Quick start

### 1. Get the code

```bash
git clone <your-repository-url> ai-image-processing
cd ai-image-processing
```

Already have it cloned? Pull the latest instead:

```bash
git pull
```

### 2. Run it

Two ways to run it — pick one.

#### Docker (macOS and Linux) — recommended, no local setup

Docker does everything: no local Python, `uv`, or dependency install needed. Just Docker
itself.

```bash
cp .env.example .env
```

Optionally, set `GEMINI_API_KEY` in `.env` to enable detection and AI editing. Then:

```bash
docker compose up --build -d
```

Open http://localhost:8000.

The container runs as a non-root user on a read-only filesystem. Uploads only ever exist in a memory-backed `/tmp` while they are being processed.

#### Without Docker (runs directly on your machine)

You need Python 3.12+ and [uv](https://docs.astral.sh/uv/) installed locally for this path.

**macOS:**
```bash
brew install uv
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, on either platform:

```bash
uv sync
```

```bash
cp .env.example .env
```

```bash
make dev
```

`make dev` serves the page at http://localhost:8000 with auto-reload.

### 3. Turn on Gemini (optional)

1. Get an API key from Google AI Studio and set `GEMINI_API_KEY` in `.env`.
2. Detection uses `GEMINI_VISION_MODEL`, which defaults to `gemini-3.8-flash` and has a real free tier.
3. AI editing (a prompt, or "replace background") needs `GEMINI_IMAGE_EDIT_MODEL`, for example `gemini-nano-banana-2.1`. **This needs a billing-enabled Google Cloud project** — every image-edit model has a free-tier quota of `0`, so it fails with a quota error on a key with no billing attached. Leave `GEMINI_IMAGE_EDIT_MODEL` empty to skip it and use detection only.
4. Check that the key and model names work:

   ```bash
   make check-gemini
   ```

When a feature isn't configured, the page disables its option and the API rejects it with `422 FEATURE_NOT_CONFIGURED`. It never pretends the feature ran.

---

## How it works

```
Browser ──multipart──► FastAPI (async, one process)
                         │ per-IP rate limit and concurrency limit, global capacity limit
                         │ stream upload ──► tmp/imgproc/{request_id}/   (mode 700)
                         │ validate (magic bytes, Pillow decode, pixel limit) ─┐
                         │ [Gemini edit] ── async client, capped and retried    │ Pillow work
                         │ [Gemini detect] ┐                                    │ runs in a
                         │ resize → enhance → encode → verify ┘ (in parallel)   │ process pool
                         │ base64 result in the JSON response                  ─┘
                         └ finally: delete tmp/imgproc/{request_id}/
```

- **Isolation:** every request gets its own random `request_id` and a private temp folder. Nothing is shared between requests, and nothing outlives a request.
- **Never blocks:** all Pillow work runs in a `ProcessPoolExecutor`, which gives real CPU parallelism away from the event loop. Gemini calls use the SDK's async client.
- **Backpressure:** none of these ever queues a request indefinitely.

  | Limit | Response | Setting (default) |
  |---|---|---|
  | Requests per minute from one IP | `429 RATE_LIMITED` | `RATE_LIMIT_IP_PER_MINUTE` (30) |
  | Images processing at once from one IP | `429 TOO_MANY_CONCURRENT_REQUESTS` | `MAX_CONCURRENT_PER_IP` (3) |
  | Images processing at once on the server | `503 SERVER_BUSY` | `MAX_CONCURRENT_REQUESTS` (16) |
  | Concurrent Gemini calls | Waits up to 30 s, then `GEMINI_RATE_LIMITED` | `GEMINI_MAX_CONCURRENCY` (4) |
  | Total processing time | `504 PROCESSING_TIMEOUT` | `REQUEST_TIMEOUT_SECONDS` (150) |

  Every `429` and `503` includes `Retry-After`. Gemini `429`, `5xx` and timeouts are retried with exponential backoff and full jitter, and the server's `RetryInfo` delay is honoured.
- **Scaling:** run **one uvicorn worker per container**; set the number of Pillow processes with `CPU_WORKERS`. Add containers behind a load balancer to scale out.
  - Limits are counted per process, which is the trade-off of having no shared store. With one worker per container they are exact per container.
  - Set `FORWARDED_ALLOW_IPS` to your proxy's address so per-IP limits see real client IPs.
- **Leftovers:** a background sweeper removes temp folders left by a crash. It only removes folders older than `TEMP_MAX_AGE_SECONDS` (default 900 s, longer than the request timeout) that no in-flight request owns.

### Processing steps

1. **Validate.** The file type is decided by its content, not its name or the browser's MIME type.
   - Only JPEG (including multi-picture MPO), PNG and WEBP are accepted.
   - The pixel limit is checked from the header before any decoding.
   - Truncated, corrupted, decompression-bomb and animated files are rejected.
2. **Normalise.** Apply the EXIF orientation, convert any ICC profile to sRGB, and remove all metadata (EXIF, GPS, XMP, ICC, comments).
3. **AI edit** (only via the API, if requested; not a page control — see [What isn't supported](#what-isnt-supported-and-why)). One Gemini call with a downscaled copy and the prompt. The edited image is validated like an upload. If the edit fails, the whole request fails, because an unedited image must never be returned as "edited".
4. **Detect objects** (only if requested) and **transform, resize, adjust, filter, enhance and encode** run concurrently, both starting from the same (normalised / AI-edited) image:
   - Detect: one Gemini call that returns structured JSON, validated with Pydantic. Bad boxes are dropped, never clamped into existence, and a warning is added — bad means the wrong shape, a non-numeric value, a value outside the 0–1000 range, or zero area. If detection fails, the image is still returned with `object_detection_completed: false` and a warning. `confidence` is always `null`, because Gemini gives no calibrated scores.
   - Transform: rotate (0/90/180/270°) and flip, then resize with Lanczos (fits inside the requested box by default; never crops), then brightness/contrast/saturation, then a filter preset, then enhance.
   - Since detection and the transform both start from the same pre-transform image, any requested rotate/flip is applied to the detected boxes algebraically so they still land correctly on the image you get back — detection is never re-run on the transformed copy.
5. **Encode.** JPEG is optimised and progressive, WEBP uses the `quality` setting, and PNG is lossless. The output file is re-opened and checked before it is returned.

---

## API

### `POST /api/v1/images/process` (`multipart/form-data`)

| Field | Type | Notes | On the page? |
|---|---|---|---|
| `image` | file | **Required.** JPEG, PNG or WEBP | ✅ |
| `target_width`, `target_height` | int | Optional. Keeps proportions unless `keep_aspect_ratio=false` | ✅ |
| `keep_aspect_ratio` | bool | Default `true`. Fits inside the box and never crops | ✅ (always on) |
| `output_format` | `JPEG`, `PNG`, `WEBP` | Defaults to the input format | ✅ |
| `quality` | 1–100 | Default 85 (JPEG and WEBP). PNG is lossless and returns a warning | ✅ |
| `detect_objects` | bool | Gemini object detection | ✅ |
| `enhance_image` | bool | Deterministic Pillow enhancement (no AI) | ✅ |
| `filter` | `golden_hour`, `black_and_white`, `vintage`, `warm`, `cool` | A deterministic colour-style preset (no AI). Echoed back as `filter_applied` | ✅ (the "Filters & Styles" chips) |
| `rotate` | `0`, `90`, `180`, `270` | Clockwise rotation. Anything else is a `422` | API only |
| `flip_horizontal`, `flip_vertical` | bool | | API only |
| `brightness`, `contrast`, `saturation` | -100–100 | Each 0 = unchanged | API only |
| `ai_edit_prompt` | string | Gemini image edit. Needs `GEMINI_IMAGE_EDIT_MODEL` (see below) | API only |
| `remove_background` | bool | Gemini edit onto plain white. **Not transparent** | API only |

"API only" fields work from `/docs`, curl, or your own frontend; the built-in page just doesn't have a control for them. `rotate`/flip are applied before detection's boxes are mapped onto the image you get back, so object outlines still land correctly even when you rotate or flip.

```bash
curl -s -X POST localhost:8000/api/v1/images/process \
  -F image=@photo.jpg -F target_width=600 -F output_format=WEBP -F quality=80 -F enhance_image=true
```

This is a real response, with `data_url` shortened:

```json
{
  "success": true,
  "request_id": "0d9e8eba091944468b50b9708a724898",
  "image": {
    "data_url": "data:image/webp;base64,UklGRgACAABXRUJQVlA4IPQBA…",
    "download_filename": "photo-processed.webp",
    "format": "WEBP",
    "width": 600,
    "height": 400,
    "size_bytes": 520,
    "mime_type": "image/webp"
  },
  "original": {
    "filename": "photo.jpg",
    "format": "JPEG",
    "width": 1200,
    "height": 800,
    "size_bytes": 15630,
    "mime_type": "image/jpeg"
  },
  "main_subject": null,
  "detected_objects": [],
  "processing": {
    "object_detection_completed": false,
    "image_enhancement_completed": true,
    "ai_edit_completed": false
  },
  "filter_applied": null,
  "warnings": [],
  "ai_models_used": [],
  "duration_ms": 55
}
```

With `detect_objects=true`, `detected_objects` looks like the example below. Boxes are in pixels of the returned image, and also given as 0–1 fractions. This shape comes from the test suite with a mocked model; real labels come from Gemini.

```json
"main_subject": "a cat on a sofa",
"detected_objects": [
  {"label": "cat", "category": "animal", "description": "A grey cat.",
   "bounding_box": {"x_min": 120, "y_min": 40, "x_max": 420, "y_max": 240},
   "normalized_bounding_box": {"x_min": 0.2, "y_min": 0.1, "x_max": 0.7, "y_max": 0.6},
   "confidence": null},
  {"label": "sofa", "category": "furniture", "description": null,
   "bounding_box": null, "normalized_bounding_box": null, "confidence": null}
]
```

Errors always have the same shape. This one is real:

```json
{"success": false, "request_id": "c5e9c8d83e0146378405f32406bfe31f",
 "error": {"code": "FEATURE_NOT_CONFIGURED",
           "message": "Object detection is not configured on this server (set GEMINI_API_KEY).",
           "details": null}}
```

### Other endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/capabilities` | Which features are enabled, the model names and the size limits. The page uses this to enable its options |
| GET | `/health` | Readiness: temp storage and the processing pool |
| GET | `/health/live` | Liveness |
| GET | `/` | The web page. Set `SERVE_FRONTEND=false` for an API-only deployment |

## Configuration

Every setting is an environment variable; see [.env.example](.env.example). The key ones:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | (empty) | Enables Gemini. Read on the server only and never sent to the browser |
| `GEMINI_VISION_MODEL` / `GEMINI_IMAGE_EDIT_MODEL` | `gemini-3.8-flash` / (empty) | Model names |
| `MAX_UPLOAD_BYTES`, `MAX_IMAGE_PIXELS` | 20 MB, 40 MP | Input limits and decompression-bomb protection |
| `MAX_OUTPUT_DIMENSION`, `MAX_OUTPUT_BYTES` | 8192 px, 15 MB | Output limits; the result must fit in the JSON response |
| `CPU_WORKERS` | CPU count (max 8) | Pillow processes |
| `MAX_CONCURRENT_REQUESTS`, `MAX_CONCURRENT_PER_IP`, `RATE_LIMIT_IP_PER_MINUTE` | 16, 3, 30 | Backpressure |
| `REQUEST_TIMEOUT_SECONDS` | 150 | Hard limit per image |
| `CORS_ALLOWED_ORIGINS` | (empty) | Only needed if another site's frontend calls this API |

## Testing

```bash
make test
```

`make test` runs 186 tests in about 2.3 s. It needs no network, and Gemini is mocked.

```bash
make lint
```

The tests cover:
- **Validation:** spoofed, corrupted, truncated, oversized, too many pixels, decompression bombs, animated images and unsafe extensions.
- **Image processing:** resize and aspect ratio, format conversion, compression, EXIF orientation, metadata and GPS stripping, ICC and colour modes, enhancement (deterministic and mild), the filter presets (including alias resolution and rejecting an unknown name), rotate/flip, and brightness/contrast/saturation.
- **Gemini, mocked async client:** valid output, malformed JSON, invented or out-of-range boxes, timeouts, `429` with the server's retry delay, retries running out, `5xx`, safety blocks, edit output, the concurrency cap, and the queue timeout.
- **Pipeline:** the temp folder is deleted on success, on failure and on timeout. AI edit happens before detection. Partial results when detection fails, the output-size limit, a run on the real multi-process pool, and that a rotated or flipped image still gets correctly placed detection boxes even though detection runs before the transform (for latency).
- **API and page:** inline result, the page and its static files, capabilities, error shape, body-size limit, per-IP rate limit, and that the removed endpoints are really gone.
- **Concurrency:**
  - 50 simultaneous uploads from 5 clients on the real process pool; every response holds its own pixels and size, and nothing is left in the temp folder;
  - the per-IP concurrency limit returns `429`;
  - the global capacity limit returns `503`.

### Load test

With the server running:

```bash
uv run locust -f loadtest/locustfile.py --host http://localhost:8000 \
  --users 30 --spawn-rate 10 --run-time 1m --headless
```

All simulated users share one IP, so they hit the per-IP limits; those `429`s are expected. Raise `RATE_LIMIT_IP_PER_MINUTE` and `MAX_CONCURRENT_PER_IP` to measure raw throughput.

---

## What isn't supported, and why

- **Login and accounts.** By design: anyone who can reach the server can use it. Put it behind your own gateway or VPN if it must be private.
- **History, job polling, idempotency keys and async jobs.** Nothing is stored, so there is nothing to look up later. Every request is answered with its result, or an error, within `REQUEST_TIMEOUT_SECONDS`. A frontend retry processes the image again.
- **Very large outputs.** The result is returned as base64 inside the JSON response. Outputs over `MAX_OUTPUT_BYTES` get `422 OUTPUT_TOO_LARGE`; ask for a smaller size or JPEG/WEBP instead.
- **Confidence scores** are always `null`, because Gemini doesn't return calibrated scores.
- **`remove_background`** produces a **white** background, not transparency, because Gemini image models don't document alpha output. A `BACKGROUND_NOT_TRANSPARENT` warning is included.
- **AI-edited images** carry Google's invisible SynthID watermark, and their aspect ratio may shift slightly. The closest supported ratio is requested.
- **Input formats:** HEIC, GIF, TIFF, SVG and animated images are rejected.
- **Gemini API:** this uses `generate_content` from google-genai 2.31, which Google lists as fully supported. Google now recommends its newer Interactions API for new projects. Only `app/services/gemini_service.py` would change if you switch.
- **Image editing needs a billing-enabled Google Cloud project.** Every image-edit model (`gemini-nano-banana-2.1`, `gemini-2.5-flash-image`, `gemini-3.1-flash-lite-image`, …) returns a free-tier quota of `0` on an API key with no billing attached — this is a 429 that never clears, not a transient rate limit. Object detection (`GEMINI_VISION_MODEL`) has a real free tier and works without billing. If `make check-gemini --edit` reports `GEMINI_RATE_LIMITED` with "limit: 0" in the message, enable billing on the Google Cloud project behind your key, or leave `GEMINI_IMAGE_EDIT_MODEL` empty and use detection only. Because of that, `ai_edit_prompt`/`remove_background` aren't exposed as page controls — they work from `/docs` once billing is on.
- **Manual rotate/flip/brightness/contrast/saturation** aren't page controls either, by choice, to keep the page to one click-through per image (upload, pick a filter, optionally detect). They're still there in the API for a script or your own frontend.

## Project layout

```
app/
  main.py                 app factory: process pool, Gemini client, sweeper, routes, page
  api/                    deps.py, middleware.py (request id, body limit), errors.py
  api/routes/             images.py (process, capabilities), health.py
  schemas/                image.py, errors.py   (Pydantic models)
  services/               processing_service.py (async pipeline), pipeline_stages.py (process pool),
                          image_processing_service.py (Pillow), gemini_service.py, workspace.py
  core/                   config.py, concurrency.py (limits), logging.py, errors.py
  utils/                  image_validation.py, filenames.py
  static/                 index.html, styles.css, app.js   (the web page)
tests/                    186 tests
scripts/check_gemini.py   live Gemini check
loadtest/locustfile.py    load test
docs/                     frontend-integration.md
```
