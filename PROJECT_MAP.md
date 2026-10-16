# Project Map / প্রজেক্ট ম্যাপ — AI Image Processing

This is a detailed reference for every file and every function in this project. For each one it covers:

- what it does;
- how it works, step by step;
- what goes in and what comes out;
- which errors it raises;
- who calls it.

Every explanation is written in **English** first, then in **বাংলা**.

এটি এই প্রজেক্টের প্রতিটি ফাইল ও প্রতিটি ফাংশনের বিস্তারিত রেফারেন্স। প্রতিটির জন্য এখানে আছে:

- এটি কী করে;
- ধাপে ধাপে কীভাবে কাজ করে;
- কী ইনপুট নেয় আর কী আউটপুট দেয়;
- কোন এরর দেয়;
- কে এটাকে কল করে।

প্রতিটি ব্যাখ্যা আগে **English**-এ, তারপর **বাংলা**-য় লেখা।

> ⚠️ **`tests/` and `docs/` are missing.** These folders do not exist on disk right now.
> - `make test` (`uv run pytest -q`) finds no tests and exits with code 5.
> - The README's link to `docs/frontend-integration.md` is broken.
>
> Both stay that way until the folders are restored or those references are removed.
>
> ⚠️ **`tests/` ও `docs/` ফোল্ডার নেই।** এই মুহূর্তে ফোল্ডার দুটো ডিস্কে নেই।
> - `make test` (`uv run pytest -q`) কোনো টেস্ট খুঁজে পায় না এবং exit code 5 দিয়ে বন্ধ হয়।
> - README-তে `docs/frontend-integration.md`-এর লিংকটি কাজ করে না।
>
> ফোল্ডারগুলো ফিরিয়ে আনা বা ওই রেফারেন্সগুলো মুছে ফেলা না পর্যন্ত এই অবস্থাই থাকবে।

---

## Contents / সূচিপত্র

1. What this project is / প্রজেক্টটি কী
2. File tree / ফাইল ট্রি
3. Life of one request / একটি রিকোয়েস্টের পুরো যাত্রা
4. Concurrency and safety model / একসাথে অনেক কাজ ও নিরাপত্তা
5. File-by-file, function-by-function reference / প্রতিটি ফাইল ও ফাংশনের বিস্তারিত
6. HTTP API reference / API রেফারেন্স
7. Error codes and warnings / এরর কোড ও ওয়ার্নিং
8. Settings (environment variables) / সেটিংস
9. How to run / কীভাবে চালাবেন
10. Troubleshooting / সমস্যা ও সমাধান

---

## 1. What this project is / প্রজেক্টটি কী

**EN.** This is a **stateless** web service with its own web page.

- **What you send:** a JPEG, PNG or WEBP image.
- **What the server does:**
  - optionally asks **Google Gemini** to find the objects in it;
  - uses **Pillow** to rotate/flip, resize, adjust, filter, enhance and re-encode it.
- **What you get back:** the processed image, inside the JSON response as a base64 `data:` URL.
- **What there isn't:** no login, no database, no queue and no stored files.
- **Where the upload lives:** in a private temp folder, only while it is being processed. That folder is deleted as soon as the request ends.

**বাংলা।** এটি একটি **stateless** (কোনো ডেটা জমা রাখে না এমন) ওয়েব সার্ভিস, সাথে নিজস্ব ওয়েব পেজ আছে।

- **আপনি পাঠান:** একটি JPEG, PNG বা WEBP ছবি।
- **সার্ভার যা করে:**
  - চাইলে **Google Gemini**-কে দিয়ে ছবির ভেতরের বস্তুগুলো খুঁজে বের করায়;
  - **Pillow** দিয়ে ছবিটি ঘোরায়/উল্টায়, সাইজ বদলায়, রং ঠিক করে, ফিল্টার দেয়, এনহ্যান্স করে এবং নতুন ফরম্যাটে সেভ করে।
- **আপনি ফেরত পান:** প্রসেস করা ছবি, JSON রেসপন্সের ভেতরেই base64 `data:` URL হিসেবে।
- **যা নেই:** লগইন নেই, ডাটাবেস নেই, কিউ নেই, কোনো ফাইল সেভ থাকে না।
- **আপলোড কোথায় থাকে:** শুধু প্রসেসিং চলার সময় একটি প্রাইভেট টেম্প ফোল্ডারে। রিকোয়েস্ট শেষ হলেই ফোল্ডারটি মুছে ফেলা হয়।

| Part / অংশ | Technology / টেকনোলজি |
|---|---|
| Web framework / ওয়েব ফ্রেমওয়ার্ক | FastAPI + uvicorn, Python 3.13 |
| Image processing / ছবি প্রসেসিং | Pillow, run in a process pool (প্রসেস পুলে চলে) |
| AI | Google Gemini via `google-genai` 2.31 (object detection / বস্তু শনাক্তকরণ) |
| Validation / যাচাই | Pydantic v2, pydantic-settings |
| Frontend / ফ্রন্টএন্ড | Plain HTML + CSS + JavaScript in `app/static/`, served at `/` |
| Tooling / টুলস | uv, ruff, pytest, Docker, locust |

**What the web page exposes vs. what the API accepts / পেজে কী আছে আর API কী নেয়**

- **The page:** filter presets, size, output format and quality, enhance, and Gemini object detection.
  **পেজে আছে:** ফিল্টার প্রিসেট, সাইজ, আউটপুট ফরম্যাট ও কোয়ালিটি, এনহ্যান্স, এবং Gemini অবজেক্ট ডিটেকশন।
- **The API also accepts:**
  - `rotate`, `flip_horizontal`, `flip_vertical`;
  - `brightness`, `contrast`, `saturation`;
  - `ai_edit_prompt`, `remove_background`.

  **API এগুলোও নেয়:** উপরের তালিকার সব ফিল্ড।
- **AI editing is off by default**, because `GEMINI_IMAGE_EDIT_MODEL` is empty. While it is off, `ai_edit_prompt` and `remove_background` return `422 FEATURE_NOT_CONFIGURED`.
  **AI এডিটিং ডিফল্টভাবে বন্ধ**, কারণ `GEMINI_IMAGE_EDIT_MODEL` খালি। বন্ধ থাকা অবস্থায় `ai_edit_prompt` বা `remove_background` পাঠালে `422 FEATURE_NOT_CONFIGURED` আসে।

---

## 2. File tree / ফাইল ট্রি

```
AI Image Processing/
├── app/                                  The application (মূল অ্যাপ্লিকেশন)
│   ├── main.py                           App factory, startup/shutdown, middleware order
│   │                                     (অ্যাপ তৈরি, চালু/বন্ধের কাজ, middleware-এর ক্রম)
│   ├── api/                              HTTP layer (HTTP স্তর)
│   │   ├── deps.py                       Shared resources + request helpers (শেয়ার্ড রিসোর্স)
│   │   ├── errors.py                     Exceptions → JSON error responses (এরর → JSON)
│   │   ├── middleware.py                 Request ID, security headers, access log, body-size limit
│   │   │                                 (রিকোয়েস্ট আইডি, সিকিউরিটি হেডার, লগ, বডি-সাইজ লিমিট)
│   │   └── routes/
│   │       ├── health.py                 GET /health, GET /health/live (সার্ভার ঠিক আছে কিনা)
│   │       └── images.py                 POST /api/v1/images/process, GET /api/v1/capabilities
│   │                                     (মূল প্রসেসিং এন্ডপয়েন্ট)
│   ├── core/                             Cross-cutting basics (সব জায়গায় লাগে এমন জিনিস)
│   │   ├── config.py                     Settings from env vars / .env (সেটিংস)
│   │   ├── concurrency.py                Rate limiter, admission control, backoff
│   │   │                                 (রেট লিমিট, একসাথে কতগুলো রিকোয়েস্ট, retry-র অপেক্ষা)
│   │   ├── errors.py                     AppError + ErrorCode + HTTP status map (এরর টাইপ ও কোড)
│   │   └── logging.py                    JSON logs with request_id (JSON লগ)
│   ├── schemas/                          Request/response shapes (রিকোয়েস্ট/রেসপন্সের গঠন)
│   │   ├── errors.py                     ErrorBody, ErrorResponse
│   │   └── image.py                      ProcessOptions + every response model
│   ├── services/                         The real work (আসল কাজ)
│   │   ├── processing_service.py         Runs one request end to end (একটি রিকোয়েস্টের পুরো কাজ)
│   │   ├── pipeline_stages.py            CPU-heavy steps that run in the process pool
│   │   │                                 (প্রসেস পুলে চলা ভারী ধাপগুলো)
│   │   ├── image_processing_service.py   Pure Pillow functions (শুধু Pillow-এর ফাংশন)
│   │   ├── gemini_service.py             Google Gemini client: detect + edit (Gemini ক্লায়েন্ট)
│   │   └── workspace.py                  Per-request temp folder + sweeper (টেম্প ফোল্ডার)
│   ├── utils/
│   │   ├── filenames.py                  Random IDs, safe display names (নিরাপদ আইডি ও নাম)
│   │   └── image_validation.py           Checks that an upload is a real, safe image
│   │                                     (আপলোড আসল ও নিরাপদ ছবি কিনা যাচাই)
│   └── static/                           The web page (ওয়েব পেজ)
│       ├── index.html                    Page markup (পেজের HTML)
│       ├── app.js                        Page logic: upload, retry, draw results (পেজের লজিক)
│       └── styles.css                    Page design, dark/light, animations (ডিজাইন)
├── scripts/check_gemini.py               Live test of your Gemini key/models (Gemini লাইভ টেস্ট)
├── loadtest/locustfile.py                Load test with many fake users (লোড টেস্ট)
├── pyproject.toml / uv.lock              Dependencies + tool config (ডিপেন্ডেন্সি)
├── .python-version                       Python version for uv: 3.13
├── .env.example → .env                   Settings template → your real settings (never commit .env)
├── .gitignore                            Files git must ignore
├── Dockerfile                            Container image (ডকার ইমেজ)
├── docker-compose.yml                    One-command run with Docker (ডকারে এক কমান্ডে চালানো)
├── Makefile                              Short commands: make dev, make up … (শর্টকাট কমান্ড)
├── README.md                             User guide (ব্যবহারকারীর গাইড)
└── PROJECT_MAP.md                        This file (এই ফাইল)
```

Every `__init__.py` file is empty and only marks its folder as a Python package.
প্রতিটি `__init__.py` ফাইল খালি; এরা শুধু ফোল্ডারটিকে Python package হিসেবে চিহ্নিত করে।

---

## 3. Life of one request / একটি রিকোয়েস্টের পুরো যাত্রা

### 3.1 Picture / ছবিতে

```
Browser (app.js)  ── POST /api/v1/images/process  (multipart: image + option fields)
   │
   ▼
RequestContextMiddleware ── new request_id, X-Request-ID + security headers, access log, 500 safety net
   ▼
[CORSMiddleware]          ── only when CORS_ALLOWED_ORIGINS is set
   ▼
BodySizeLimitMiddleware   ── 413 if the body is larger than MAX_UPLOAD_BYTES + 1 MB
   ▼
routes/images.py : process_image
   ├─ ProcessOptions(...)             → 422 VALIDATION_ERROR on bad options
   ├─ ip_rate_limiter.hit(ip)         → 429 RATE_LIMITED + Retry-After
   └─ admission.admit(ip)             → 429 TOO_MANY_CONCURRENT_REQUESTS / 503 SERVER_BUSY
        ▼
ImageProcessor.process  (services/processing_service.py)
   ├─ check_features                  → 422 FEATURE_NOT_CONFIGURED
   ├─ TempWorkspace.create            tmp/imgproc/<request_id>/  (mode 700, thread)
   ├─ copy_upload                     → .../upload  (1 MB chunks, size limit, thread)
   ├─ stage_validate                  (process pool) → ImageInfo
   └─ _pipeline   (whole thing limited to REQUEST_TIMEOUT_SECONDS)
        ├─ [AI edit]                  only when GEMINI_IMAGE_EDIT_MODEL is set
        ├─ TaskGroup ┬─ _detect:      stage_model_input (pool) → Gemini detect_objects
        │            └─ stage_finish (pool): transform → resize → adjust → filter → enhance → encode
        ├─ output size check          → 422 OUTPUT_TOO_LARGE
        ├─ read output bytes
        └─ boxes: transform_box → to_pixel_box
   finally: delete tmp/imgproc/<request_id>/
        ▼
_response → ProcessResponse JSON  (image.data_url = base64 of the result)
```

### 3.2 Step by step / ধাপে ধাপে

| # | English | বাংলা |
|---|---|---|
| 0 | **Startup (once per process).** `create_app` registers `lifespan`, which calls `build_resources`. That step sets Pillow's pixel limit, creates the temp root (mode 700), starts the process pool and warms it, and creates the Gemini client if a key is set. It also builds the `ImageProcessor`, `AdmissionControl` and `SlidingWindowLimiter`, then starts the background temp-folder sweeper. | **চালু হওয়ার সময় (প্রতি প্রসেসে একবার)।** `create_app` একটি `lifespan` রেজিস্টার করে, যেটি `build_resources` কল করে। এই ধাপে Pillow-এর পিক্সেল লিমিট সেট হয়, টেম্প রুট ফোল্ডার (mode 700) তৈরি হয়, প্রসেস পুল চালু করে গরম (warm) করা হয়, আর key থাকলে Gemini ক্লায়েন্ট তৈরি হয়। এরপর `ImageProcessor`, `AdmissionControl` ও `SlidingWindowLimiter` বানানো হয় এবং ব্যাকগ্রাউন্ডে টেম্প ফোল্ডার পরিষ্কারের কাজ শুরু হয়। |
| 1 | **Browser.** `readOptions()` collects the form choices. `upload()` sends a multipart form (`image` plus the fields) with XHR so upload progress can be shown. | **ব্রাউজার।** `readOptions()` ফর্মের অপশনগুলো জোগাড় করে। `upload()` XHR দিয়ে multipart ফর্ম (`image` ও ফিল্ডগুলো) পাঠায়, যাতে আপলোডের অগ্রগতি দেখানো যায়। |
| 2 | **`RequestContextMiddleware`** creates a random 32-hex `request_id` and stores it in `scope["state"]` and in a contextvar for logs. Every response gets `X-Request-ID` and the security headers. | **`RequestContextMiddleware`** একটি র‍্যান্ডম ৩২-অক্ষরের hex `request_id` তৈরি করে, `scope["state"]`-এ এবং লগের জন্য একটি contextvar-এ রাখে। প্রতিটি রেসপন্সে `X-Request-ID` ও সিকিউরিটি হেডার যোগ হয়। |
| 3 | **`BodySizeLimitMiddleware`** rejects bodies over `MAX_UPLOAD_BYTES + 1 MB` (22,020,096 bytes by default) with `413`. It checks the `Content-Length` header first and keeps counting while the body streams in. | **`BodySizeLimitMiddleware`** `MAX_UPLOAD_BYTES + 1 MB` (ডিফল্টে 22,020,096 বাইট)-এর বড় বডি `413` দিয়ে বাতিল করে। প্রথমে `Content-Length` হেডার দেখে, তারপর বডি আসার সময়ও গুনতে থাকে। |
| 4 | **FastAPI parses the form.** The file becomes an `UploadFile`: in memory up to 1 MB, then a temporary file in the OS temp folder. A field of the wrong type gives `422`. | **FastAPI ফর্ম পার্স করে।** ফাইলটি `UploadFile` হয়: ১ MB পর্যন্ত মেমোরিতে থাকে, তার বেশি হলে OS-এর টেম্প ফোল্ডারে। ভুল টাইপের ফিল্ড হলে `422`। |
| 5 | **`process_image`** builds `ProcessOptions`. Its validators normalise the format, check rotate and filter, strip the prompt, and forbid using edit and remove-background together. If any check fails, the result is `422 VALIDATION_ERROR`. | **`process_image`** `ProcessOptions` তৈরি করে। এর validator-গুলো ফরম্যাট ঠিক করে, rotate ও filter যাচাই করে, prompt ছাঁটে, এবং edit ও remove-background একসাথে নিষেধ করে। কোনো যাচাই ব্যর্থ হলে ফল `422 VALIDATION_ERROR`। |
| 6 | **Rate limit.** `ip_rate_limiter.hit(ip)` allows at most 30 requests per IP per minute; above that it returns `429 RATE_LIMITED` with `Retry-After`. | **রেট লিমিট।** `ip_rate_limiter.hit(ip)` প্রতি IP-তে মিনিটে সর্বোচ্চ ৩০টি রিকোয়েস্ট দেয়; বেশি হলে `Retry-After` সহ `429 RATE_LIMITED`। |
| 7 | **Admission.** `admission.admit(ip)` allows at most 3 at once per IP (else `429`) and 16 at once in total (else `503`). It never makes a request wait in a queue. | **অ্যাডমিশন।** `admission.admit(ip)` একটি IP থেকে একসাথে সর্বোচ্চ ৩টি (না হলে `429`) এবং মোট ১৬টি (না হলে `503`) চলতে দেয়। কোনো রিকোয়েস্টকে লাইনে বসিয়ে রাখে না। |
| 8 | **`ImageProcessor.process`:**<br>• checks the requested features are configured;<br>• creates `tmp/imgproc/<request_id>/`;<br>• copies the upload in 1 MB chunks;<br>• validates the image in the pool;<br>• runs `_pipeline` with a time limit of `REQUEST_TIMEOUT_SECONDS`. | **`ImageProcessor.process`:**<br>• চাওয়া ফিচারগুলো কনফিগার করা আছে কিনা দেখে;<br>• `tmp/imgproc/<request_id>/` তৈরি করে;<br>• আপলোড ১ MB করে কপি করে;<br>• পুলে ছবি যাচাই করে;<br>• `REQUEST_TIMEOUT_SECONDS` সময়সীমার মধ্যে `_pipeline` চালায়। |
| 9 | **`_pipeline`** runs the optional AI edit first. It then runs **Gemini detection and Pillow processing at the same time** (`asyncio.TaskGroup`), checks the output size and reads the bytes. Finally it rotates/flips the boxes and converts them to pixels. | **`_pipeline`** প্রথমে ঐচ্ছিক AI এডিট চালায়। তারপর **Gemini ডিটেকশন আর Pillow প্রসেসিং একসাথে** চালায় (`asyncio.TaskGroup`), আউটপুট সাইজ চেক করে এবং বাইটগুলো পড়ে। শেষে বক্সগুলো ঘুরিয়ে/উল্টে পিক্সেলে রূপান্তর করে। |
| 10 | **`finally`.** The request ID leaves `active_requests` and the temp folder is deleted, whether the request succeeded or failed. | **`finally`।** সফল বা ব্যর্থ যা-ই হোক, request ID `active_requests` থেকে সরানো হয় আর টেম্প ফোল্ডার মুছে ফেলা হয়। |
| 11 | **`_response`** turns the internal result into `ProcessResponse`, with `image.data_url = "data:image/...;base64,..."`. | **`_response`** ভেতরের ফলাফলকে `ProcessResponse`-এ রূপান্তর করে, যেখানে `image.data_url = "data:image/...;base64,..."`। |
| 12 | **Any error** becomes `{success:false, request_id, error:{code,message,details}}` via `api/errors.py` or the middleware. | **যেকোনো এরর** `api/errors.py` বা middleware-এর মাধ্যমে `{success:false, request_id, error:{code,message,details}}` হয়ে যায়। |
| 13 | **Access log.** The middleware writes one JSON line: method, path (no query string), status, duration. | **অ্যাক্সেস লগ।** Middleware এক লাইনের JSON লগ লেখে: method, path (query string ছাড়া), status, সময়। |
| 14 | **Browser.** `showResult()` swaps in the processed image, draws boxes from the normalised coordinates, and lists facts, flags, objects and warnings. On `503`, or on a `429` that is not `RATE_LIMITED`, it waits `Retry-After` seconds and retries (up to 4 times). | **ব্রাউজার।** `showResult()` প্রসেস করা ছবি বসায়, normalized কো-অর্ডিনেট থেকে বক্স আঁকে, এবং তথ্য, ফ্ল্যাগ, বস্তু ও ওয়ার্নিং দেখায়। `503` বা `RATE_LIMITED` নয় এমন `429` এলে `Retry-After` সেকেন্ড অপেক্ষা করে আবার চেষ্টা করে (সর্বোচ্চ ৪ বার)। |

---

## 4. Concurrency and safety model / একসাথে অনেক কাজ ও নিরাপত্তা

| Topic / বিষয় | English | বাংলা |
|---|---|---|
| Event loop | Only does async I/O and bookkeeping. It never runs Pillow and never blocks. | শুধু async I/O আর হিসাব রাখার কাজ করে। কখনো Pillow চালায় না, কখনো আটকে থাকে না। |
| Threads | File work (mkdir, copy, read, rmtree) runs through `anyio.to_thread.run_sync`. | ফাইলের কাজ (mkdir, কপি, পড়া, মুছে ফেলা) `anyio.to_thread.run_sync` দিয়ে থ্রেডে চলে। |
| Process pool | All decoding, encoding and image math run in a `ProcessPoolExecutor` with `CPU_WORKERS` processes:<br>• real parallelism, with no GIL;<br>• a crash cannot kill the server;<br>• each worker is replaced after 200 tasks (`max_tasks_per_child`), which uses the `spawn` start method. | সব ডিকোড, এনকোড ও ছবির হিসাব `CPU_WORKERS` সংখ্যক প্রসেসের `ProcessPoolExecutor`-এ চলে:<br>• সত্যিকারের সমান্তরাল কাজ, GIL-এর বাধা নেই;<br>• ক্র্যাশ হলেও সার্ভার বন্ধ হয় না;<br>• ২০০ কাজের পর প্রতিটি worker নতুন করে চালু হয় (`max_tasks_per_child`), যা `spawn` পদ্ধতি ব্যবহার করে। |
| Gemini | At most `GEMINI_MAX_CONCURRENCY` (4) calls at once per process (asyncio semaphore), waiting at most 30 s for a slot. Calls retry with exponential backoff plus jitter and honour Google's `RetryInfo`. | প্রতি প্রসেসে একসাথে সর্বোচ্চ `GEMINI_MAX_CONCURRENCY` (৪)টি কল (asyncio semaphore); জায়গার জন্য সর্বোচ্চ ৩০ সেকেন্ড অপেক্ষা। কল ব্যর্থ হলে exponential backoff ও jitter দিয়ে আবার চেষ্টা হয়, Google-এর `RetryInfo` মেনে। |
| Backpressure | A rate limit per IP, plus caps on concurrent requests per IP and in total. A full server answers at once with `Retry-After` instead of hanging. | প্রতি IP-র রেট লিমিট, আর প্রতি IP ও মোট একসাথে চলা রিকোয়েস্টের সীমা। সার্ভার ভরে গেলে ঝুলে না থেকে সাথে সাথে `Retry-After` দিয়ে উত্তর দেয়। |
| Timeouts | The whole pipeline has `REQUEST_TIMEOUT_SECONDS` (150). Each Gemini call has its own HTTP timeout (60 s detect, 120 s edit). | পুরো পাইপলাইনের সময়সীমা `REQUEST_TIMEOUT_SECONDS` (১৫০)। প্রতিটি Gemini কলের নিজস্ব HTTP টাইমআউট (ডিটেক্ট ৬০, এডিট ১২০ সেকেন্ড)। |
| Isolation | Each request works in its own folder, named by a random ID. The user's file name never touches the disk. The folder is deleted in `finally`, and a sweeper removes leftovers after a crash. | প্রতিটি রিকোয়েস্ট র‍্যান্ডম আইডির নিজস্ব ফোল্ডারে কাজ করে। ব্যবহারকারীর ফাইলের নাম কখনো ডিস্কে ব্যবহার হয় না। `finally`-তে ফোল্ডার মুছে যায়, আর ক্র্যাশের পর পড়ে থাকা ফোল্ডার sweeper সরিয়ে দেয়। |
| Hostile files | The content is checked by magic bytes, never by name or Content-Type. Pixel count is checked before decoding (decompression-bomb guard). Truncated and animated files are rejected. | ফাইলের ধরন magic bytes দেখে ঠিক হয়, নাম বা Content-Type দেখে নয়। ডিকোডের আগেই পিক্সেল সংখ্যা চেক হয় (decompression bomb থেকে রক্ষা)। ভাঙা ও অ্যানিমেটেড ফাইল বাতিল। |
| Privacy | Output images carry no EXIF, GPS, XMP or ICC data. Logs never contain image bytes, API keys or query strings. Error messages never contain paths or stack traces. | আউটপুট ছবিতে কোনো EXIF, GPS, XMP বা ICC তথ্য থাকে না। লগে কখনো ছবির বাইট, API key বা query string থাকে না। এরর মেসেজে কখনো path বা stack trace থাকে না। |
| Browser safety | Every response carries `nosniff`, `no-referrer` and `X-Frame-Options: DENY`. The page renders server text with `textContent` only, never `innerHTML`. | প্রতিটি রেসপন্সে `nosniff`, `no-referrer` ও `X-Frame-Options: DENY` থাকে। পেজ সার্ভারের লেখা শুধু `textContent` দিয়ে দেখায়, `innerHTML` দিয়ে কখনো নয়। |

---

## 5. File-by-file reference / প্রতিটি ফাইল ও ফাংশনের বিস্তারিত

**How to read each entry / প্রতিটি এন্ট্রি কীভাবে পড়বেন:**

- The heading is the function's signature.
  হেডিং হলো ফাংশনের সিগনেচার।
- **EN** and **বাংলা** explain what it does.
  **EN** ও **বাংলা** ব্যাখ্যা করে এটি কী করে।
- Then come its steps, return value, errors and callers.
  তারপর থাকে ধাপ, রিটার্ন, এরর ও কে কল করে।

---

### 5.1 `app/main.py` — app factory / অ্যাপ তৈরির কারখানা

**EN.** This module builds the FastAPI app. It wires the long-lived resources (process pool, Gemini client, limiters) into startup and shutdown, sets the middleware order, mounts the routes and the web page, and exposes `app` lazily so that importing the module has no side effects.

**বাংলা।** এই মডিউল FastAPI অ্যাপ তৈরি করে। দীর্ঘস্থায়ী রিসোর্সগুলো (প্রসেস পুল, Gemini ক্লায়েন্ট, লিমিটার) চালু ও বন্ধ হওয়ার সাথে যুক্ত করে, middleware-এর ক্রম ঠিক করে, রাউট আর ওয়েব পেজ যোগ করে, এবং `app`-কে lazy ভাবে দেয়, যাতে শুধু import করলে কোনো side effect না হয়।

| Name | Meaning / অর্থ |
|---|---|
| `STATIC_DIR` | Path to `app/static/`. / `app/static/` ফোল্ডারের পাথ। |
| `_MULTIPART_OVERHEAD = 1 MB` | Extra body allowance for multipart framing and form fields on top of the image. / ছবির উপর multipart-এর বাড়তি অংশ ও ফর্ম ফিল্ডের জন্য অতিরিক্ত জায়গা। |
| `ResourcesFactory` | Type: an async function `Settings → AppResources`. Tests can pass a fake one. / টাইপ: async ফাংশন `Settings → AppResources`। টেস্টে নকল ফাংশন দেওয়া যায়। |

#### `_warm() -> None`
**EN.** Does nothing. Running it once per pool worker at startup forces every worker process to start before the first real request arrives.
**বাংলা।** কিছুই করে না। চালু হওয়ার সময় প্রতিটি worker-এ একবার চালালে প্রথম আসল রিকোয়েস্ট আসার আগেই সব worker প্রসেস চালু হয়ে যায়।
- **Called by / কে কল করে:** `build_resources`.

#### `async build_resources(settings) -> AppResources`
**EN.** This is the default startup factory. It creates everything that lives for the whole life of the process.
**বাংলা।** এটি ডিফল্ট স্টার্টআপ ফ্যাক্টরি। প্রসেস যতক্ষণ চলে, ততক্ষণ যা যা লাগে সব তৈরি করে।

| # | English | বাংলা |
|---|---|---|
| 1 | Set `Image.MAX_IMAGE_PIXELS = settings.max_image_pixels` in the main process. | মূল প্রসেসে `Image.MAX_IMAGE_PIXELS` সেট করে। |
| 2 | `ensure_temp_root(settings.temp_dir)` creates the scratch root with mode 700. | `ensure_temp_root` দিয়ে টেম্প রুট ফোল্ডার (mode 700) তৈরি করে। |
| 3 | Create `ProcessPoolExecutor(max_workers=cpu_workers, initializer=init_worker, initargs=(max_image_pixels,), max_tasks_per_child=200)`. | উপরের সেটিংসে প্রসেস পুল তৈরি করে। |
| 4 | Run `_warm` once per worker in parallel (`asyncio.gather`) so the processes start now. | প্রতিটি worker-এ একসাথে `_warm` চালায়, যাতে প্রসেসগুলো এখনই চালু হয়। |
| 5 | If `settings.gemini_configured`, create `GoogleGeminiService.from_settings(settings)`; otherwise use `None`. | key থাকলে Gemini সার্ভিস তৈরি করে, না থাকলে `None`। |
| 6 | Return `assemble_resources(settings, executor, gemini)`. | `assemble_resources` কল করে ফলাফল ফেরত দেয়। |

- **Called by / কে কল করে:** `lifespan` inside `create_app` (as the default `resources_factory`).

#### `assemble_resources(settings, executor, gemini) -> AppResources`
**EN.** Puts the parts together:
- `ImageProcessor(settings, executor, gemini)`;
- `AdmissionControl(max_total=MAX_CONCURRENT_REQUESTS, max_per_client=MAX_CONCURRENT_PER_IP)`;
- `SlidingWindowLimiter(RATE_LIMIT_IP_PER_MINUTE, 60 s)`.

It is a separate function so tests can pass a fake executor and a fake Gemini.

**বাংলা।** অংশগুলো জোড়া লাগায়:
- `ImageProcessor`;
- `AdmissionControl`;
- `SlidingWindowLimiter`।

এটা আলাদা ফাংশন, যাতে টেস্টে নকল executor ও নকল Gemini দেওয়া যায়।

#### `async close_resources(resources) -> None`
**EN.** Shutdown work:
1. Closes the Gemini HTTP client, ignoring any error.
2. Shuts the process pool down in a thread with `wait=True, cancel_futures=True`.

**বাংলা।** বন্ধের সময়ের কাজ:
1. Gemini-র HTTP ক্লায়েন্ট বন্ধ করে (এরর হলে উপেক্ষা করে)।
2. থ্রেডে প্রসেস পুল বন্ধ করে (`wait=True, cancel_futures=True`)।

#### `async _sweep_forever(resources) -> None`
**EN.** A background loop that runs forever:
1. In a thread, call `sweep_temp_dirs(temp_dir, max_age_seconds=TEMP_MAX_AGE_SECONDS, active=<copy of processor.active_requests>)`.
2. Log a warning if that fails.
3. Sleep `TEMP_SWEEP_INTERVAL_SECONDS` (300 s), then repeat.

It is cancelled at shutdown.

**বাংলা।** ব্যাকগ্রাউন্ডে চলতে থাকা লুপ:
1. থ্রেডে `sweep_temp_dirs` চালায়; এখন চলমান রিকোয়েস্টগুলো (`active_requests`) বাদ রাখে।
2. ব্যর্থ হলে warning লগ করে।
3. ৩০০ সেকেন্ড ঘুমায়, তারপর আবার।

বন্ধের সময় এটি cancel হয়।

#### `create_app(settings=None, resources_factory=build_resources) -> FastAPI`
**EN.** Builds and returns the configured FastAPI app.
**বাংলা।** কনফিগার করা FastAPI অ্যাপ তৈরি করে ফেরত দেয়।

| # | English | বাংলা |
|---|---|---|
| 1 | `settings = settings or get_settings()`; then `configure_logging(settings.log_level)`. | সেটিংস নেয়, JSON লগিং চালু করে। |
| 2 | Defines `lifespan`. On startup it calls `resources_factory(settings)`, stores the result on `app.state.resources` and starts `_sweep_forever`. On shutdown it cancels the sweeper and calls `close_resources`. | `lifespan` তৈরি করে। চালুর সময় রিসোর্স বানিয়ে `app.state.resources`-এ রাখে ও sweeper চালু করে। বন্ধের সময় sweeper থামিয়ে `close_resources` কল করে। |
| 3 | Creates `FastAPI(title=APP_NAME, version="2.0.0", description=…, lifespan=lifespan)`. | FastAPI অবজেক্ট তৈরি করে। |
| 4 | `register_exception_handlers(app)`. | এরর হ্যান্ডলারগুলো যোগ করে। |
| 5 | Adds middleware. Starlette runs the **last-added middleware first**, so the order is: `BodySizeLimitMiddleware` (limit = upload + 1 MB) → optional `CORSMiddleware` → `RequestContextMiddleware`. That makes RequestContext the outermost. CORS settings: no credentials; methods GET/POST/OPTIONS; header `Content-Type`; exposes `Retry-After` and `X-Request-ID`; `max_age` 600. | Middleware যোগ করে। Starlette **সবশেষে যোগ করা middleware আগে চালায়**, তাই ক্রম: `BodySizeLimitMiddleware` → (ঐচ্ছিক) `CORSMiddleware` → `RequestContextMiddleware`। ফলে RequestContext সবার বাইরে থাকে। |
| 6 | `include_router(images.router)` and `include_router(health.router)`. | রাউটারগুলো যোগ করে। |
| 7 | If `SERVE_FRONTEND`, mounts `/static` and adds `GET /`, which returns `index.html` with `Cache-Control: no-cache`. | `SERVE_FRONTEND` চালু থাকলে `/static` ও `GET /` (index.html) যোগ করে। |

- **Called by / কে কল করে:** `__getattr__` below, and tests (with a fake `resources_factory`).

#### `__getattr__(name) -> FastAPI` (module level)
**EN.** Runs when something reads `app.main.app`, such as uvicorn or `fastapi dev`. On first access it builds the app with `create_app()` and caches it in `globals()`. Any other name raises `AttributeError`. Because the app is built only when asked for, `import app.main` alone does not configure logging or start a pool.
**বাংলা।** কেউ `app.main.app` পড়তে চাইলে (যেমন uvicorn বা `fastapi dev`) এটি চলে। প্রথমবার `create_app()` দিয়ে অ্যাপ বানিয়ে `globals()`-এ রেখে দেয়। অন্য কোনো নাম চাইলে `AttributeError`। অ্যাপ শুধু চাওয়া হলেই তৈরি হয়, তাই শুধু `import app.main` করলে লগিং কনফিগার হয় না বা পুল চালু হয় না।

#### `__dir__() -> list[str]`
**EN.** Adds `"app"` to `dir(app.main)`. `fastapi dev` looks for the app with `"app" in dir(module)`, and `dir()` does not see lazy `__getattr__` names on its own.
**বাংলা।** `dir(app.main)`-এ `"app"` যোগ করে। `fastapi dev` অ্যাপ খোঁজে `"app" in dir(module)` দিয়ে, আর `dir()` নিজে থেকে lazy `__getattr__`-এর নাম দেখতে পায় না।

---

### 5.2 `app/api/deps.py` — shared resources / শেয়ার্ড রিসোর্স

#### `class AppResources` (dataclass)
**EN.** Holds the per-process objects that every request uses. There is one instance per process, stored on `app.state.resources`.
**বাংলা।** প্রতিটি রিকোয়েস্ট যে প্রসেস-ভিত্তিক অবজেক্টগুলো ব্যবহার করে, সেগুলো রাখে। প্রতি প্রসেসে একটিই থাকে, `app.state.resources`-এ।

| Field | Type | Meaning / অর্থ |
|---|---|---|
| `settings` | `Settings` | All configuration. / সব সেটিংস। |
| `executor` | `Executor` | The Pillow process pool. / Pillow-এর প্রসেস পুল। |
| `gemini` | `GeminiService \| None` | `None` when there is no API key. / API key না থাকলে `None`। |
| `processor` | `ImageProcessor` | Runs the pipeline. / পাইপলাইন চালায়। |
| `admission` | `AdmissionControl` | Concurrency caps. / একসাথে চলার সীমা। |
| `ip_rate_limiter` | `SlidingWindowLimiter` | Requests per IP per minute. / প্রতি IP-তে মিনিটে কতগুলো রিকোয়েস্ট। |

#### `get_resources(request) -> AppResources`
**EN.** A FastAPI dependency that returns `request.app.state.resources`.
**বাংলা।** FastAPI dependency; `request.app.state.resources` ফেরত দেয়।
- **Used by / ব্যবহার করে:** `process_image`, `capabilities`, `ready`.

#### `get_request_id(request) -> str`
**EN.** Returns `request.state.request_id`, which `RequestContextMiddleware` set.
**বাংলা।** `RequestContextMiddleware`-এর সেট করা `request.state.request_id` ফেরত দেয়।
- **Used by / ব্যবহার করে:** `process_image`.

#### `client_ip(request) -> str`
**EN.** Returns `request.client.host`, or `"unknown"`. Behind a proxy or load balancer this is the real user IP only when uvicorn runs with `--proxy-headers` and `--forwarded-allow-ips` includes that proxy; docker-compose already does this.
**বাংলা।** `request.client.host` বা `"unknown"` ফেরত দেয়। প্রক্সি/লোড ব্যালান্সারের পেছনে এটি আসল ব্যবহারকারীর IP হয় শুধু তখনই, যখন uvicorn `--proxy-headers` দিয়ে চলে এবং `--forwarded-allow-ips`-এ ওই প্রক্সি থাকে; docker-compose এটা আগেই করে রেখেছে।
- **Used by / ব্যবহার করে:** `process_image` (rate limit and admission key / রেট লিমিট ও অ্যাডমিশনের key)।

---

### 5.3 `app/api/errors.py` — errors to JSON / এরর থেকে JSON

**EN.** Every error leaves the server in one shape: `{success: false, request_id, error: {code, message, details}}`. It never includes stack traces, file paths, upstream payloads or secrets.
**বাংলা।** সব এরর একই আকারে সার্ভার থেকে বের হয়: `{success: false, request_id, error: {code, message, details}}`। এতে কখনো stack trace, file path, বাইরের সার্ভিসের কাঁচা উত্তর বা গোপন তথ্য থাকে না।

`_HTTP_CODES` maps plain HTTP errors to our codes / সাধারণ HTTP এররকে আমাদের কোডে রূপান্তর করে:
- 400 → `BAD_REQUEST`
- 404 → `NOT_FOUND`
- 405 → `METHOD_NOT_ALLOWED`
- 413 → `FILE_TOO_LARGE`

#### `error_response(*, status_code, code, message, request_id, details=None, headers=None) -> JSONResponse`
**EN.** Builds an `ErrorResponse` model and returns it as JSON with the given status and headers, such as `Retry-After`.
**বাংলা।** `ErrorResponse` মডেল বানিয়ে নির্দিষ্ট status ও হেডারসহ (যেমন `Retry-After`) JSON হিসেবে ফেরত দেয়।

#### `validation_details(errors) -> list[dict]`
**EN.** Turns Pydantic errors into `[{field, message, type}]`:
- `field` is the error location joined with `.`, with the `"body"` part removed;
- the user's submitted value (`input`) is **never** echoed back.

**বাংলা।** Pydantic এররকে `[{field, message, type}]`-এ রূপান্তর করে:
- `field` হলো এররের লোকেশন `.` দিয়ে জোড়া, `"body"` অংশ বাদ দিয়ে;
- ব্যবহারকারীর পাঠানো মান (`input`) **কখনো** ফেরত দেখানো হয় না।

- **Used by / ব্যবহার করে:** the 422 handler, and `process_image` when `ProcessOptions` fails.

#### `_request_id(request) -> str | None`
**EN.** Reads `request.state.request_id` safely: if it is missing, returns `None` instead of raising.
**বাংলা।** নিরাপদে `request.state.request_id` পড়ে; না থাকলে এরর না দিয়ে `None` দেয়।

#### `register_exception_handlers(app) -> None`
**EN.** Registers three handlers:

| Handler | Exception | Response |
|---|---|---|
| `_app_error` | `AppError` | Its own status, `code`, `message`, `details` and `headers` (for example `Retry-After`). |
| `_validation_error` | `RequestValidationError` (bad form field types) | `422 VALIDATION_ERROR` "Request validation failed." plus `validation_details`. |
| `_http_error` | `StarletteHTTPException` (404, 405, 413 …) | Mapped through `_HTTP_CODES`; unknown codes become `BAD_REQUEST`, and any status ≥ 500 becomes `INTERNAL_ERROR`. Keeps headers such as `Allow`. |

Truly unexpected exceptions are caught by `RequestContextMiddleware` instead.

**বাংলা।** তিনটি হ্যান্ডলার যোগ করে:
- **`AppError`:** তার নিজের status, কোড, মেসেজ ও হেডার দিয়ে উত্তর।
- **ফর্ম ফিল্ডের ভুল টাইপ:** `422 VALIDATION_ERROR`।
- **সাধারণ HTTP এরর:** `_HTTP_CODES` অনুযায়ী কোড। ৫০০-এর বেশি status হলে `INTERNAL_ERROR`।

একেবারে অপ্রত্যাশিত এরর ধরে `RequestContextMiddleware`।

---

### 5.4 `app/api/middleware.py` — request ID, headers, size limit / রিকোয়েস্ট আইডি, হেডার, সাইজ লিমিট

**EN.** These are written as pure ASGI middleware, not `BaseHTTPMiddleware`, so streaming bodies and contextvars behave correctly.
**বাংলা।** এগুলো pure ASGI middleware হিসেবে লেখা (`BaseHTTPMiddleware` নয়), যাতে streaming বডি ও contextvar ঠিকমতো কাজ করে।

`_SECURITY_HEADERS` — added to every response / প্রতিটি রেসপন্সে যোগ হয়:

| Header | Purpose / উদ্দেশ্য |
|---|---|
| `X-Content-Type-Options: nosniff` | The browser must not guess file types. / ব্রাউজার ফাইলের ধরন অনুমান করবে না। |
| `Referrer-Policy: no-referrer` | The URL is not leaked to other sites. / অন্য সাইটে URL ফাঁস হবে না। |
| `X-Frame-Options: DENY` | The page cannot be embedded in a frame. / পেজটি অন্য সাইটের frame-এ বসানো যাবে না। |

#### `_error_body(code, message, request_id) -> bytes`
**EN.** Encodes the standard error JSON to bytes. Middleware sends it directly, where FastAPI's handlers cannot run.
**বাংলা।** স্ট্যান্ডার্ড এরর JSON বাইট হিসেবে তৈরি করে। যেখানে FastAPI হ্যান্ডলার চলতে পারে না, সেখানে middleware এটি সরাসরি পাঠায়।

#### `class RequestContextMiddleware` → `async __call__(scope, receive, send)`
**EN.** The outermost middleware. It gives every request an ID, headers and a log line, and acts as the last-resort 500 handler.
**বাংলা।** সবচেয়ে বাইরের middleware। প্রতিটি রিকোয়েস্টকে আইডি, হেডার ও লগ লাইন দেয়, আর শেষ ভরসার ৫০০ হ্যান্ডলার হিসেবে কাজ করে।

| # | English | বাংলা |
|---|---|---|
| 1 | Non-HTTP scopes (lifespan, websocket) are passed straight through. | HTTP নয় এমন scope সরাসরি পার করে দেয়। |
| 2 | `request_id = new_id()`; stores it in `scope["state"]["request_id"]` and `request_id_var`. | নতুন আইডি বানিয়ে scope ও contextvar-এ রাখে। |
| 3 | Wraps `send` as `send_wrapper`. On `http.response.start` it records the status and appends `x-request-id` plus the security headers. | `send`-কে মুড়ে দেয়; রেসপন্স শুরুর সময় status রেকর্ড করে ও হেডার যোগ করে। |
| 4 | Calls the app. On any `Exception` it logs `unhandled_exception` with the traceback (server log only). If nothing has been sent yet, it sends `500 INTERNAL_ERROR` JSON. | অ্যাপ চালায়। এরর হলে traceback শুধু সার্ভার লগে লেখে; রেসপন্স শুরু না হয়ে থাকলে `500 INTERNAL_ERROR` JSON পাঠায়। |
| 5 | `finally`: logs `request` with `method`, `path` (never the query string), `status`, `duration_ms`. | সবশেষে `method`, `path` (query string ছাড়া), `status`, `duration_ms` লগ করে। |

#### `class BodySizeLimitMiddleware(app, max_body_bytes)` → `async __call__(scope, receive, send)`
**EN.** Stops oversized uploads before they waste memory or disk.
**বাংলা।** অতিরিক্ত বড় আপলোড মেমোরি বা ডিস্ক নষ্ট করার আগেই থামিয়ে দেয়।

| # | English | বাংলা |
|---|---|---|
| 1 | Only HTTP `POST`/`PUT`/`PATCH` are checked; everything else passes through. | শুধু `POST`/`PUT`/`PATCH` চেক হয়; বাকি সব পার হয়ে যায়। |
| 2 | If the `Content-Length` header is larger than the limit, it calls `_reject` and sends `413` at once without reading the body. An invalid header counts as 0. | `Content-Length` লিমিটের বেশি হলে বডি না পড়েই `_reject` দিয়ে সাথে সাথে `413`। ভুল হেডার হলে ০ ধরা হয়। |
| 3 | Otherwise it wraps `receive` as `limited_receive`, which counts body bytes as they stream in. Above the limit it raises `HTTPException(413)`, and `_http_error` turns that into `FILE_TOO_LARGE` JSON. This catches chunked uploads that have no `Content-Length`. | না হলে `receive`-কে `limited_receive` দিয়ে মুড়ে দেয়, যা আসতে থাকা বাইট গোনে। লিমিট ছাড়ালে `HTTPException(413)`, যা `FILE_TOO_LARGE` JSON হয়ে যায়। `Content-Length` ছাড়া chunked আপলোডও এভাবে ধরা পড়ে। |

#### `_reject(scope, send)`
**EN.** Sends a `413 FILE_TOO_LARGE` JSON response with `connection: close`.
**বাংলা।** `connection: close` হেডারসহ `413 FILE_TOO_LARGE` JSON রেসপন্স পাঠায়।

---

### 5.5 `app/api/routes/health.py` — health checks / সার্ভারের স্বাস্থ্য পরীক্ষা

#### `_ping() -> str`
**EN.** Returns `"pong"`. It runs **inside a pool process** to prove the pool is alive.
**বাংলা।** `"pong"` ফেরত দেয়। পুল বেঁচে আছে কিনা প্রমাণ করতে এটি **পুলের প্রসেসের ভেতরে** চলে।

#### `GET /health/live` → `live() -> {"status": "ok"}`
**EN.** The liveness check: is the process up? It checks nothing else. Docker's `HEALTHCHECK` uses it.
**বাংলা।** লাইভনেস চেক: প্রসেস চালু আছে কিনা। আর কিছু চেক করে না। Docker-এর `HEALTHCHECK` এটি ব্যবহার করে।

#### `GET /health` → `ready(resources) -> JSONResponse`
**EN.** The readiness check: can the server actually process images?
**বাংলা।** রেডিনেস চেক: সার্ভার আসলেই ছবি প্রসেস করতে পারবে কিনা।

| # | English | বাংলা |
|---|---|---|
| 1 | `temp_writable` (in a thread): writes and deletes `TEMP_DIR/.health-<id>`. Sets `checks.temp_storage` to `ok` or `error`. | থ্রেডে টেম্প ফোল্ডারে একটি ফাইল লিখে মুছে দেখে; `ok` বা `error`। |
| 2 | Runs `_ping` in the pool with a 5 s timeout. Sets `checks.processing_pool`. | ৫ সেকেন্ড সময় দিয়ে পুলে `_ping` চালায়। |
| 3 | Returns `200` with `status: "ok"` if every check passed, else `503` with `"degraded"`. Also includes `gemini` (`configured`/`not_configured`) and `in_flight_requests`. | সব ঠিক থাকলে `200`, না হলে `503 degraded`। সাথে Gemini-র অবস্থা ও চলমান রিকোয়েস্টের সংখ্যা দেয়। |

---

### 5.6 `app/api/routes/images.py` — the main endpoints / মূল এন্ডপয়েন্ট

`router = APIRouter(prefix="/api/v1")`. `_ERRORS` tells Swagger that statuses 413/415/422/429/500/502/503/504 return `ErrorResponse`.
`_ERRORS` Swagger-কে জানায় যে এই status-গুলোতে `ErrorResponse` আসে।

#### `_response(result, request_id) -> ProcessResponse`
**EN.** Converts the internal `ProcessResult` into the public response model:
- pixel tuples become `BoundingBox`;
- `NormalizedBox` becomes `NormalizedBoundingBox`;
- `image.data_url = to_data_url(bytes, mime)` and `size_bytes = len(bytes)`;
- original-image info, processing flags, `filter_applied`, warnings, `ai_models_used` and `duration_ms` are copied across.

**বাংলা।** ভেতরের `ProcessResult`-কে পাবলিক রেসপন্স মডেলে রূপান্তর করে:
- পিক্সেল টাপল থেকে `BoundingBox` হয়;
- `NormalizedBox` থেকে `NormalizedBoundingBox` হয়;
- ছবির বাইট base64 `data_url` হয়, আর সাইজ বসানো হয়;
- মূল ছবির তথ্য, ফ্ল্যাগ, ফিল্টার, ওয়ার্নিং, মডেলের নাম ও সময় যোগ হয়।

#### `POST /api/v1/images/process` → `async process_image(...) -> ProcessResponse`
**EN.** Takes an upload and returns the processed image. The form fields are listed in section 6.
**বাংলা।** আপলোড নেয়, প্রসেস করা ছবি ফেরত দেয়। ফর্ম ফিল্ডের তালিকা সেকশন ৬-এ।

| # | English | বাংলা |
|---|---|---|
| 1 | Builds `ProcessOptions(...)` from the form fields. The `filter` field arrives in the Python parameter `image_filter`, because `filter` is a Python builtin. On `ValidationError` it raises `422 VALIDATION_ERROR` "Invalid processing options." with `details`. | ফর্ম ফিল্ড থেকে `ProcessOptions` বানায় (`filter` নামটি Python-এর built-in, তাই প্যারামিটারের নাম `image_filter`)। ভুল হলে `422 VALIDATION_ERROR`। |
| 2 | `ip = client_ip(request)`; `wait = ip_rate_limiter.hit(ip)`; if `wait > 0`, raises `429 RATE_LIMITED` with `Retry-After`. | IP বের করে রেট লিমিট চেক করে; বেশি হলে `429`। |
| 3 | `with admission.admit(ip):` awaits `processor.process(request_id=…, upload=image.file, filename=image.filename, options=…)`. | অ্যাডমিশন পেলে `processor.process` চালায়। |
| 4 | Returns `_response(result, request_id)`. | `_response` দিয়ে উত্তর বানিয়ে ফেরত দেয়। |

#### `GET /api/v1/capabilities` → `async capabilities(resources) -> CapabilitiesResponse`
**EN.** Tells clients what this server can do:
- `object_detection` and `ai_edit` (true/false);
- model names (`null` when a feature is off);
- accepted and output formats;
- the limits (`max_upload_bytes`, `max_image_pixels`, `max_output_dimension`, `default_quality`).

The web page calls it at load time to set up the controls.

**বাংলা।** ক্লায়েন্টকে জানায় সার্ভার কী কী পারে:
- ডিটেকশন ও এডিট চালু আছে কিনা;
- মডেলের নাম (ফিচার বন্ধ থাকলে `null`);
- কোন ফরম্যাট নেয় আর কোন ফরম্যাটে দেয়;
- সীমাগুলো।

ওয়েব পেজ লোড হওয়ার সময় এটি কল করে কন্ট্রোলগুলো সাজায়।

---

### 5.7 `app/core/config.py` — settings / সেটিংস

#### `_default_cpu_workers() -> int`
**EN.** Returns `max(1, min(8, os.cpu_count() or 2))`: the number of CPUs, between 1 and 8.
**বাংলা।** CPU-র সংখ্যা, তবে কমপক্ষে ১ ও সর্বোচ্চ ৮।

#### `class Settings(BaseSettings)`
**EN.** Reads every field from environment variables (the field name in upper case, e.g. `MAX_UPLOAD_BYTES`) and from `.env` (UTF-8). Unknown variables are ignored, and every field is validated. The full table is in section 8.
**বাংলা।** প্রতিটি ফিল্ড environment variable (ফিল্ডের নাম বড় হাতের অক্ষরে, যেমন `MAX_UPLOAD_BYTES`) আর `.env` ফাইল থেকে পড়ে। অজানা ভেরিয়েবল উপেক্ষা করে, প্রতিটি মান যাচাই করে। পূর্ণ তালিকা সেকশন ৮-এ।

| Member | English | বাংলা |
|---|---|---|
| `_split_csv` (validator) | `CORS_ALLOWED_ORIGINS="https://a.com, https://b.com"` → `["https://a.com", "https://b.com"]`. `NoDecode` stops pydantic-settings from trying to parse it as JSON. | কমা দিয়ে আলাদা লেখাকে লিস্টে ভাঙে। |
| `_blank_to_none` (validator) | An empty `GEMINI_VISION_MODEL` / `GEMINI_IMAGE_EDIT_MODEL` becomes `None`, which turns that feature off. | খালি মডেল নাম `None` হয়ে যায়, ফলে ফিচারটি বন্ধ থাকে। |
| `gemini_configured` (property) | True when `GEMINI_API_KEY` is set and not empty. | API key দেওয়া থাকলে True। |
| `detection_enabled` (property) | Key set **and** a vision model set. | key **এবং** vision মডেল দুটোই থাকলে True। |
| `ai_edit_enabled` (property) | Key set **and** an edit model set. | key **এবং** edit মডেল দুটোই থাকলে True। |

#### `get_settings() -> Settings`
**EN.** Wrapped in `@lru_cache`, so the settings are read once per process and reused.
**বাংলা।** `@lru_cache` থাকায় প্রতি প্রসেসে সেটিংস একবারই পড়া হয়, তারপর একই অবজেক্ট বারবার ব্যবহার হয়।

---

### 5.8 `app/core/concurrency.py` — limits and backoff / লিমিট ও অপেক্ষা

**EN.** These counters exist only to apply backpressure. They live **in memory, per server process**: run one uvicorn worker per container and the limits are exact.
**বাংলা।** এই কাউন্টারগুলো শুধু চাপ নিয়ন্ত্রণের জন্য। এগুলো **মেমোরিতে, প্রতিটি সার্ভার প্রসেসে আলাদা** থাকে। প্রতি কন্টেইনারে একটি uvicorn worker চালালে লিমিট একদম সঠিক থাকে।

#### `backoff_delay(attempt, *, base=1.0, cap=30.0, rng=None) -> float`
**EN.** Exponential backoff with full jitter: `uniform(0, min(cap, base * 2**attempt))`.
- attempt 0 → 0–1 s
- attempt 1 → 0–2 s
- attempt 2 → 0–4 s
- … never more than 30 s

The randomness keeps many clients from retrying at the same moment.

**বাংলা।** "Full jitter" সহ exponential backoff: প্রতিবার অপেক্ষার সর্বোচ্চ সীমা দ্বিগুণ হয় (সর্বোচ্চ ৩০ সেকেন্ড), আর আসল অপেক্ষা ০ থেকে সেই সীমার মধ্যে র‍্যান্ডম। এতে অনেক ক্লায়েন্ট একই মুহূর্তে আবার চেষ্টা করে না।

- **Used by / ব্যবহার করে:** `GoogleGeminiService._call`.

#### `class SlidingWindowLimiter(limit, window=60.0, clock=time.monotonic, max_keys=100_000)`
**EN.** Allows at most `limit` events per `window` seconds per key (here the key is the client IP). It keeps a `deque` of timestamps for each key. It needs no locks because it only runs on the single event-loop thread.
**বাংলা।** প্রতিটি key-তে (এখানে key হলো ক্লায়েন্টের IP) `window` সেকেন্ডে সর্বোচ্চ `limit`টি ইভেন্ট দেয়। প্রতিটি key-র জন্য সময়ের একটি `deque` রাখে। শুধু একটি event-loop থ্রেডে চলে বলে lock লাগে না।

- **`hit(key) -> float`:**
  1. Gets or creates the key's deque. If there are already `max_keys` keys, it first calls `_prune`.
  2. Drops timestamps older than the window.
  3. If `len >= limit`, it returns the seconds until the oldest one expires (at least 0.001). The event is **not** recorded.
  4. Otherwise it records `now` and returns `0`.

  **বাংলা:**
  1. key-র তালিকা নেয় বা নতুন বানায়; key খুব বেশি হলে আগে `_prune` করে।
  2. পুরোনো সময়গুলো বাদ দেয়।
  3. লিমিট ভরা থাকলে কত সেকেন্ড পর জায়গা খালি হবে তা ফেরত দেয় (ইভেন্ট রেকর্ড হয় না)।
  4. না হলে এখনকার সময় রেকর্ড করে `0` ফেরত দেয়।

- **`_prune(now)`:** deletes keys whose deque is empty or whose newest event is outside the window. This keeps memory bounded.
  **বাংলা:** যেসব key-র কোনো সাম্প্রতিক ইভেন্ট নেই সেগুলো মুছে মেমোরি সীমিত রাখে।

#### `class AdmissionControl(*, max_total, max_per_client)`
**EN.** Caps how many requests run at once, globally and per client. It **never queues**: when it is full, the caller gets an error straight away.
**বাংলা।** একসাথে কতগুলো রিকোয়েস্ট চলবে, তা মোট হিসেবে ও প্রতি ক্লায়েন্টে সীমিত করে। **কখনো লাইনে রাখে না**: ভরা থাকলে সাথে সাথে এরর।

- **`in_flight` (property):** the number of requests running now. `/health` shows it.
  **বাংলা:** এখন কতগুলো চলছে; `/health`-এ দেখায়।
- **`admit(client)` (context manager):**
  1. If this client already has `max_per_client` running, it raises `429 TOO_MANY_CONCURRENT_REQUESTS` with `Retry-After: 2`.
  2. If the total is at `max_total`, it raises `503 SERVER_BUSY` with `Retry-After: 5`.
  3. Otherwise it increments both counters, `yield`s, and decrements them in `finally` (removing the client entry at zero).

  **বাংলা:**
  1. এই ক্লায়েন্টের সীমা ভরা থাকলে `429`।
  2. মোট সীমা ভরা থাকলে `503`।
  3. না হলে দুটো কাউন্টার বাড়ায়, কাজ শেষে `finally`-তে কমায়।

---

### 5.9 `app/core/errors.py` — error type and codes / এরর টাইপ ও কোড

#### `class ErrorCode(StrEnum)`
**EN.** The stable error codes clients can rely on. The full list, with meanings, is in section 7.
**বাংলা।** ক্লায়েন্ট নির্ভর করতে পারে এমন স্থায়ী এরর কোড। অর্থসহ পূর্ণ তালিকা সেকশন ৭-এ।

#### `HTTP_STATUS_FOR_CODE: dict[ErrorCode, int]`
**EN.** The default HTTP status for each code (for example `UNSUPPORTED_FILE_TYPE` → 415).
**বাংলা।** প্রতিটি কোডের ডিফল্ট HTTP status (যেমন `UNSUPPORTED_FILE_TYPE` → 415)।

#### `class AppError(Exception)`
**EN.** An expected failure that carries a client-safe message.
- **`__init__(code, message, *, status_code=None, details=None, headers=None)`:**
  - `status_code` defaults to `HTTP_STATUS_FOR_CODE[code]`, or 400 if the code is not in the map;
  - `headers` defaults to `{}`.
- **`__reduce__()`:** makes it **picklable**. When a pool worker raises `AppError`, it is pickled back to the main process with the same code, status, details and headers. It is rebuilt through `_rebuild_app_error(code_str, message, status_code, details, headers)`.
- **`__repr__()`:** a short debug string such as `AppError(code=…, status=…, message=…)`.

**বাংলা।** প্রত্যাশিত ব্যর্থতা, যার মেসেজ ক্লায়েন্টকে দেখানো নিরাপদ।
- **`__init__`:** status না দিলে ম্যাপ থেকে নেয় (ম্যাপে না থাকলে ৪০০)।
- **`__reduce__`:** এর ফলে এররটি **pickle** করা যায়। পুলের worker-এ `AppError` হলে সেটি একই কোড, status, details ও হেডারসহ মূল প্রসেসে ফিরে আসে।
- **`__repr__`:** ডিবাগের জন্য ছোট বর্ণনা দেয়।

#### `retry_after_error(code, message, retry_after) -> AppError`
**EN.** Builds an `AppError` with a `Retry-After` header and `details.retry_after_seconds`. The seconds are rounded **up** to a whole number, with a minimum of 1: `0.2 → 1`, `12.3 → 13`.
**বাংলা।** `Retry-After` হেডার ও `details.retry_after_seconds` সহ `AppError` বানায়। সেকেন্ডকে **উপরের দিকে** পূর্ণ সংখ্যায় নেয়, কমপক্ষে ১ (০.২ → ১, ১২.৩ → ১৩)।

- **Used by / ব্যবহার করে:** `process_image` (rate limit), `AdmissionControl.admit`.

---

### 5.10 `app/core/logging.py` — JSON logs / JSON লগ

| Name | Meaning / অর্থ |
|---|---|
| `request_id_var` | A ContextVar holding the current request ID, so every log line in that request gets it. / বর্তমান রিকোয়েস্টের আইডি রাখে, যাতে সেই রিকোয়েস্টের প্রতিটি লগে আইডি থাকে। |
| `_STANDARD_ATTRS` | Built-in `LogRecord` attribute names; these are not copied as extra fields. / LogRecord-এর নিজস্ব ফিল্ড, যা extra হিসেবে কপি হয় না। |
| `_SAFE_TYPES` | `str, int, float, bool, None`: the only extra values that are logged. / শুধু এই সরল টাইপগুলোই লগ হয়। |

#### `JsonFormatter.format(record) -> str`
**EN.** Builds one JSON object per log line:
1. Always: `ts` (UTC, milliseconds), `level`, `logger`, `msg`.
2. `request_id`, taken from the record or the contextvar.
3. Each `extra=` field, **only** if it is a simple value or a list of simple values. Anything else, including bytes and objects, is silently dropped, so image data or secrets cannot leak into logs.
4. `exc`, the formatted traceback, when an exception was attached.
5. Serialised with `ensure_ascii=False`, so Bangla text stays readable.

**বাংলা।** প্রতিটি লগ লাইনকে একটি JSON অবজেক্ট বানায়:
1. সবসময় থাকে সময়, লেভেল, লগারের নাম ও মেসেজ।
2. রিকোয়েস্ট আইডি যোগ হয়।
3. extra ফিল্ড যোগ হয় **শুধু** সরল মান হলে। বাইট বা অবজেক্ট বাদ পড়ে, তাই ছবির ডেটা বা গোপন তথ্য লগে যেতে পারে না।
4. এরর থাকলে traceback যোগ হয়।
5. `ensure_ascii=False`, তাই বাংলা লেখা পড়া যায়।

Example / উদাহরণ:

```json
{"ts": "2026-10-16T09:12:03.512+00:00", "level": "INFO", "logger": "app.access", "msg": "request",
 "request_id": "3f2a…", "method": "POST", "path": "/api/v1/images/process", "status": 200, "duration_ms": 842.7}
```

#### `configure_logging(level="INFO") -> None`
**EN.**
1. Installs a single stdout handler with `JsonFormatter` on the root logger and sets the level.
2. **Disables `uvicorn.access`**, because our own access log omits query strings.
3. Turns `httpx`, `httpcore`, `google_genai`, `urllib3` and `PIL` down to `WARNING`.

**বাংলা।**
1. root logger-এ একটি stdout হ্যান্ডলার (JSON ফরম্যাটে) বসায় এবং লেভেল সেট করে।
2. uvicorn-এর নিজের access log বন্ধ করে, কারণ আমাদের নিজের লগে query string থাকে না।
3. বেশি কথা বলা লাইব্রেরিগুলোকে `WARNING` লেভেলে নামিয়ে আনে।

---

### 5.11 `app/schemas/errors.py` — error shape / এররের গঠন

| Model | Fields / ফিল্ড |
|---|---|
| `ErrorBody` | `code: str`, `message: str`, `details: Any \| None` |
| `ErrorResponse` | `success: false` (always / সবসময়), `request_id: str \| None`, `error: ErrorBody` |

```json
{"success": false, "request_id": "9b1c…", "error": {"code": "UNSUPPORTED_FILE_TYPE",
 "message": "Unsupported file type. Upload a JPEG, PNG or WEBP image.", "details": null}}
```

---

### 5.12 `app/schemas/image.py` — options and response models / অপশন ও রেসপন্স মডেল

#### Constants / ধ্রুবক

| Name | Value / মান | Meaning / অর্থ |
|---|---|---|
| `VALID_ROTATIONS` | `(0, 90, 180, 270)` | Allowed clockwise rotations. / অনুমোদিত ঘড়ির কাঁটার দিকে ঘোরানো। |
| `FILTER_ALIASES` | see below / নিচে দেখুন | Canonical filter → accepted aliases. / মূল ফিল্টারের নাম → বিকল্প নাম। |
| `VALID_FILTER_NAMES` | 15 names / ১৫টি নাম | `none` + 5 canonical + 9 aliases. / `none` + ৫টি মূল + ৯টি বিকল্প। |
| `REMOVE_BACKGROUND_PROMPT` | text | The Gemini prompt used by `remove_background`: keep the subject, plain white `#FFFFFF` background. / সাবজেক্ট ঠিক রেখে সাদা ব্যাকগ্রাউন্ড দেওয়ার নির্দেশ। |
| `OutputFormat` | `JPEG`, `PNG`, `WEBP` | Allowed output formats. / অনুমোদিত আউটপুট ফরম্যাট। |

| Canonical / মূল নাম | Aliases / বিকল্প | UI label |
|---|---|---|
| `golden_hour` | `sunset`, `golden` | Golden hour |
| `black_and_white` | `bw`, `monochrome` | Black & white |
| `vintage` | `old_film`, `retro` | Old film |
| `warm` | `cozy` | Warm |
| `cool` | `cold`, `cyber` | Cool |

#### `class ProcessOptions(BaseModel)` — `extra="forbid"`

| Field | Type / default | Rule / নিয়ম | Meaning / অর্থ |
|---|---|---|---|
| `target_width` | `int \| None` = None | 1–16383 | Output width in px. / আউটপুটের প্রস্থ। |
| `target_height` | `int \| None` = None | 1–16383 | Output height in px. / আউটপুটের উচ্চতা। |
| `keep_aspect_ratio` | `bool` = True | | Fit inside the box, never crop. / অনুপাত ঠিক রেখে বক্সের ভেতরে বসানো, কাটা হয় না। |
| `output_format` | `OutputFormat \| None` = None | `JPG` → `JPEG` | None = same as the input. / না দিলে ইনপুটের ফরম্যাট। |
| `quality` | `int \| None` = None | 1–100 | JPEG/WEBP quality; ignored for PNG. / কোয়ালিটি; PNG-তে উপেক্ষিত। |
| `detect_objects` | `bool` = False | | Run Gemini detection. / Gemini দিয়ে বস্তু খোঁজা। |
| `enhance_image` | `bool` = False | | Fixed enhancement recipe. / নির্দিষ্ট এনহ্যান্স রেসিপি। |
| `ai_edit_prompt` | `str \| None` = None | 1–2000 chars, stripped | Gemini edit instruction. / Gemini-কে এডিটের নির্দেশ। |
| `remove_background` | `bool` = False | not together with `ai_edit_prompt` | White background via Gemini. / Gemini দিয়ে সাদা ব্যাকগ্রাউন্ড। |
| `filter` | `str \| None` = None | must be in `VALID_FILTER_NAMES` | Style preset. / স্টাইল ফিল্টার। |
| `brightness` / `contrast` / `saturation` | `int` = 0 | −100…100 | Manual colour adjustments. / উজ্জ্বলতা/কনট্রাস্ট/রঙের গাঢ়ত্ব। |
| `rotate` | `int` = 0 | 0, 90, 180, 270 | Clockwise rotation. / ঘড়ির কাঁটার দিকে ঘোরানো। |
| `flip_horizontal` / `flip_vertical` | `bool` = False | | Mirror the image. / আয়নার মতো উল্টানো। |

| Validator / property | English | বাংলা |
|---|---|---|
| `_normalize_format` (before) | Strip and upper-case; `""` → None; `"JPG"` → `"JPEG"`. | ফাঁকা বাদ দিয়ে বড় হাতের অক্ষর করে; `JPG` হয় `JPEG`। |
| `_check_rotate` | The value must be in `VALID_ROTATIONS`; otherwise "rotate must be one of …". | মান ০/৯০/১৮০/২৭০ না হলে এরর। |
| `_check_filter` (before) | Strip and lower-case; `""` → None; an unknown name raises an error listing every valid name. | ছোট হাতের অক্ষর করে; অজানা নাম হলে সব বৈধ নামের তালিকাসহ এরর। |
| `_strip_prompt` (before) | Strip whitespace; an empty prompt becomes None. | prompt-এর ফাঁকা অংশ ছাঁটে; খালি হলে None। |
| `_check_combinations` (after) | `ai_edit_prompt` **and** `remove_background` together → error. | দুটো একসাথে দিলে এরর। |
| `wants_ai_edit` | True if there is a prompt or `remove_background`. | এডিট চাওয়া হয়েছে কিনা। |
| `effective_edit_prompt` | `REMOVE_BACKGROUND_PROMPT` if `remove_background`, else the user prompt. | আসলে কোন prompt যাবে। |

#### Response models / রেসপন্স মডেল

| Model | Fields / ফিল্ড | Notes / মন্তব্য |
|---|---|---|
| `ProcessedImage` | `data_url, download_filename, format, width, height, size_bytes, mime_type` | The result image. / ফলাফলের ছবি। |
| `OriginalImage` | `filename, format, width, height, size_bytes, mime_type` | The upload, as detected from its content. / আপলোডের আসল তথ্য। |
| `BoundingBox` | `x_min, y_min, x_max, y_max` (int) | Pixels in the **processed** image. / প্রসেস করা ছবির পিক্সেলে। |
| `NormalizedBoundingBox` | same, float 0–1 | Fractions of width/height. / প্রস্থ/উচ্চতার ভগ্নাংশ। |
| `DetectedObjectOut` | `label, category, description, bounding_box, normalized_bounding_box, confidence` | `confidence` is always `null`: Gemini gives no calibrated scores. / Gemini নির্ভরযোগ্য স্কোর দেয় না, তাই সবসময় `null`। |
| `ProcessingFlags` | `object_detection_completed, image_enhancement_completed, ai_edit_completed` | What actually happened. / আসলে কী কী হয়েছে। |
| `ProcessingWarning` | `code, message` | Non-fatal problems. / যে সমস্যায় কাজ থামেনি। |
| `ProcessResponse` | `success: true, request_id, image, original, main_subject, detected_objects, processing, filter_applied, warnings, ai_models_used, duration_ms` | Full success body. / সফল রেসপন্সের পূর্ণ রূপ। |
| `CapabilitiesResponse` | `object_detection, ai_edit, vision_model, image_edit_model, accepted_formats, output_formats, max_upload_bytes, max_image_pixels, max_output_dimension, default_quality` | Body of `/api/v1/capabilities`. |

---

### 5.13 `app/services/processing_service.py` — runs one request / একটি রিকোয়েস্ট চালায়

#### `class PixelDetection` (frozen dataclass)
**EN.** One detected object, ready for the response:
- `label`, `category`, `description`;
- `box`: a pixel tuple `(x_min, y_min, x_max, y_max)` or `None`;
- `normalized`: a `NormalizedBox` or `None`;
- `confidence`: always `None`.

**বাংলা।** রেসপন্সের জন্য প্রস্তুত একটি শনাক্ত বস্তু: পিক্সেল বক্স ও normalized বক্সসহ।

#### `class ProcessResult` (dataclass)
**EN.** Everything the route needs to build the response:
- the image bytes and their format, MIME type and size;
- the download name and the original-image info;
- detections and processing flags;
- the models used, the filter, warnings and duration.

**বাংলা।** রেসপন্স বানাতে রাউটের যা যা লাগে সব: ছবির বাইট ও তার ফরম্যাট, MIME, সাইজ; ডাউনলোডের নাম ও মূল ছবির তথ্য; শনাক্ত বস্তু ও ফ্ল্যাগ; ব্যবহৃত মডেল, ফিল্টার, ওয়ার্নিং ও সময়।

#### `to_pixel_box(box, width, height) -> (x_min, y_min, x_max, y_max)`
**EN.** Converts a 0–1 box to integer pixels. Minimums are floored and maximums ceiled, so the box always covers the object. The result is clamped inside the image and is always at least 1 px wide and tall.
Example: `(0.25, 0.25, 0.75, 0.75)` on 800×600 → `(200, 150, 600, 450)`.
**বাংলা।** ০–১ বক্সকে পূর্ণসংখ্যার পিক্সেলে রূপান্তর করে। ছোট মান নিচের দিকে, বড় মান উপরের দিকে রাউন্ড হয়, যাতে বক্স পুরো বস্তু ঢাকে। ছবির ভেতরে আটকে রাখে, আর কমপক্ষে ১ পিক্সেল চওড়া ও লম্বা রাখে।

#### `_first_error(group) -> BaseException`
**EN.** `asyncio.TaskGroup` wraps failures in an `ExceptionGroup`. This function walks the group and returns the first `AppError` it finds (or else the first error of any kind), so the client gets a meaningful error code.
**বাংলা।** `TaskGroup` এররগুলোকে একটি `ExceptionGroup`-এ মুড়ে দেয়। এই ফাংশন ভেতর থেকে প্রথম `AppError` (না থাকলে যেকোনো প্রথম এরর) বের করে, যাতে ক্লায়েন্ট অর্থবহ এরর কোড পায়।

#### `class ImageProcessor`

##### `__init__(*, settings, executor, gemini)`
**EN.** Stores its dependencies and builds `Limits(max_pixels, max_output_dimension, default_quality)`. It also creates `active_requests: set[str]`, the request IDs running now, which the sweeper must not touch.
**বাংলা।** নির্ভরতাগুলো রাখে, `Limits` বানায়, আর `active_requests` সেট তৈরি করে। এটি এখন চলমান রিকোয়েস্টের আইডি রাখে, যেগুলো sweeper ছোঁবে না।

##### `async _cpu(fn, *args) -> T`
**EN.** Runs `fn(*args)` in the process pool via `loop.run_in_executor` and awaits the result. Exceptions, including a pickled `AppError`, come back unchanged.
**বাংলা।** `fn(*args)` প্রসেস পুলে চালিয়ে ফলাফলের জন্য অপেক্ষা করে। এরর হলে (যেমন pickle হয়ে আসা `AppError`) সেটি যেমন ছিল তেমনই ফিরে আসে।

##### `check_features(options) -> None`
**EN.** Fails fast, before any file work:
- `detect_objects` without detection configured → `422 FEATURE_NOT_CONFIGURED` ("set GEMINI_API_KEY").
- An AI edit without an edit model configured → `422 FEATURE_NOT_CONFIGURED`.
- `target_width` or `target_height` above `MAX_OUTPUT_DIMENSION` → `422 VALIDATION_ERROR`.

**বাংলা।** ফাইলের কাজ শুরুর আগেই দ্রুত ব্যর্থ করে:
- ডিটেকশন কনফিগার না থাকলে `422`।
- এডিট মডেল না থাকলে `422`।
- চাওয়া সাইজ সীমার বেশি হলে `422`।

##### `async process(*, request_id, upload, filename, options) -> ProcessResult`
**EN.** The outer flow of one request. It guarantees cleanup no matter what happens.
**বাংলা।** একটি রিকোয়েস্টের বাইরের কাঠামো। যা-ই ঘটুক, পরিষ্কারের কাজ নিশ্চিত করে।

| # | English | বাংলা |
|---|---|---|
| 1 | `check_features(options)`. | ফিচার চেক। |
| 2 | `TempWorkspace(temp_dir, request_id).create()` in a thread. This makes `tmp/imgproc/<id>/` with mode 700. | থ্রেডে টেম্প ফোল্ডার তৈরি (mode 700)। |
| 3 | Adds `request_id` to `active_requests`. | আইডি চলমান তালিকায় যোগ করে। |
| 4 | `copy_upload(upload, workspace/upload, MAX_UPLOAD_BYTES)` in a thread → `(size, sha256)`. | থ্রেডে আপলোড কপি করে, সাইজ ও হ্যাশ পায়। |
| 5 | `stage_validate(...)` in the pool → `ImageInfo` (real format and size). | পুলে ছবি যাচাই করে, আসল ফরম্যাট ও মাপ পায়। |
| 6 | `async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS)`: `_pipeline(...)`. A timeout becomes `504 PROCESSING_TIMEOUT`. | সময়সীমার মধ্যে `_pipeline` চালায়; সময় পেরোলে `504`। |
| 7 | Fills in `original`, the sanitised `original_filename`, `original_size_bytes`, `download_filename` and `duration_ms`. | মূল ছবির তথ্য, নিরাপদ নাম, সাইজ, ডাউনলোড নাম ও সময় বসায়। |
| 8 | `finally`: removes the ID from `active_requests` and runs `workspace.cleanup()` in a thread, so the folder is deleted **on success and on failure**. | সবশেষে আইডি সরিয়ে ফোল্ডার মুছে দেয়, **সফল বা ব্যর্থ যা-ই হোক**। |

##### `async _pipeline(workspace, info, options) -> ProcessResult`
**EN.** The image work itself.
**বাংলা।** ছবির আসল কাজ।

| # | English | বাংলা |
|---|---|---|
| 1 | **AI edit (only if requested).**<br>• `stage_model_input` makes a ≤2048 px JPEG.<br>• `gemini.edit_image(prompt, aspect_ratio=closest_aspect_ratio(...))` edits it.<br>• The result is written to `edited` and re-validated; an invalid image gives `502 GEMINI_INVALID_RESPONSE`.<br>• Processing continues from the edited image.<br>• `remove_background` adds the warning `BACKGROUND_NOT_TRANSPARENT`.<br>• A Gemini failure here **fails the request**, because returning an unedited image would mislead the user. | **AI এডিট (চাইলে)।**<br>• ছোট JPEG কপি বানানো হয়।<br>• Gemini দিয়ে এডিট করানো হয়।<br>• ফলাফল যাচাই করা হয়, এরপর সেটির উপর বাকি কাজ চলে।<br>• এখানে Gemini ব্যর্থ হলে **পুরো রিকোয়েস্ট ব্যর্থ**, কারণ এডিট ছাড়া ছবি ফেরত দিলে ব্যবহারকারী বিভ্রান্ত হবেন। |
| 2 | **Run in parallel with `asyncio.TaskGroup`:**<br>• `_detect(source, warnings)`, if `detect_objects`;<br>• `stage_finish(...)` in the pool.<br>If either raises, `_first_error` picks the error to report. | **`TaskGroup`-এ একসাথে চলে:** ডিটেকশন আর পুলে Pillow-এর কাজ। কোনোটা এরর দিলে `_first_error` দিয়ে কোন এরর জানানো হবে তা বাছাই করা হয়। |
| 3 | Merges `finish.warnings` and records the model names used. | ওয়ার্নিং একত্র করে, ব্যবহৃত মডেলের নাম রাখে। |
| 4 | If the encoded size is above `MAX_OUTPUT_BYTES`, raises `422 OUTPUT_TOO_LARGE` with a hint to use a smaller size or JPEG/WEBP. | আউটপুট খুব বড় হলে `422 OUTPUT_TOO_LARGE`। |
| 5 | Reads the output bytes in a thread. | থ্রেডে আউটপুট বাইট পড়ে। |
| 6 | For each detection:<br>• if `rotate`/`flip` was used, `transform_box` moves the box to the new geometry;<br>• `to_pixel_box` maps it onto the **final** width and height.<br>Detection ran on the un-rotated image and resizing never crops, so the boxes line up exactly. | প্রতিটি বস্তুর জন্য:<br>• rotate/flip হলে বক্সও ঘোরানো/উল্টানো হয়;<br>• চূড়ান্ত ছবির মাপে পিক্সেলে রূপান্তর হয়।<br>রিসাইজ কখনো ছবি কাটে না, তাই বক্স একদম মিলে যায়। |
| 7 | Returns `ProcessResult`. `object_detection_completed` is true only if detection actually succeeded. | `ProcessResult` ফেরত দেয়; ডিটেকশন আসলেই সফল হলে তবেই flag true হয়। |

##### `async _detect(source, warnings) -> DetectionResult | None`
**EN.**
1. `stage_model_input` in the pool makes a ≤1536 px JPEG.
2. `gemini.detect_objects(...)` runs on it.
3. On `GeminiError` it **does not raise**. It logs, adds the warning `OBJECT_DETECTION_FAILED`, and returns `None`. The user still gets the processed image.
4. It adds `INVALID_BOUNDING_BOXES_OMITTED` if some boxes were invalid, and `DETECTIONS_TRUNCATED` if there were more than 50 objects.

**বাংলা।**
1. পুলে ছোট JPEG বানায়।
2. Gemini দিয়ে বস্তু খোঁজে।
3. Gemini ব্যর্থ হলে **এরর ছোড়ে না**: ওয়ার্নিং যোগ করে `None` দেয়, ব্যবহারকারী তবুও প্রসেস করা ছবি পান।
4. কিছু বক্স ভুল হলে বা ৫০টির বেশি বস্তু হলে সেই অনুযায়ী ওয়ার্নিং যোগ করে।

#### `to_data_url(data, mime_type) -> str`
**EN.** Returns `"data:<mime>;base64,<base64 of data>"`, the form in which the image travels inside the JSON.
**বাংলা।** `"data:<mime>;base64,..."` তৈরি করে; এই রূপেই ছবিটি JSON-এর ভেতরে যায়।
- **Used by / ব্যবহার করে:** `_response` in `routes/images.py`.

---

### 5.14 `app/services/pipeline_stages.py` — work done in the process pool / প্রসেস পুলের কাজ

**EN.** Every stage is a **top-level function that takes only plain values** (strings, ints, dicts, small dataclasses), so it can be pickled and sent to another process. Options travel as a plain dict and are re-validated inside the worker.
**বাংলা।** প্রতিটি ধাপ **টপ-লেভেল ফাংশন এবং শুধু সরল মান নেয়** (string, int, dict, ছোট dataclass), যাতে pickle করে অন্য প্রসেসে পাঠানো যায়। অপশনগুলো dict হিসেবে যায় এবং worker-এর ভেতরে আবার যাচাই হয়।

| Dataclass | Fields / ফিল্ড | Meaning / অর্থ |
|---|---|---|
| `Limits` | `max_pixels, max_output_dimension, default_quality` | Limits passed to workers. / worker-কে দেওয়া সীমা। |
| `ModelInput` | `data, mime_type, width, height` | The JPEG copy for Gemini. Width and height are the normalised original's size, before downscaling. / Gemini-র জন্য JPEG কপি; মাপ হলো ছোট করার আগের মাপ। |
| `FinishResult` | `encoded, image_enhancement_completed, filter_applied, warnings` | Output of `stage_finish`. / `stage_finish`-এর ফলাফল। |

#### `init_worker(max_pixels) -> None`
**EN.** The pool initializer. It runs once in each new worker process and sets `Image.MAX_IMAGE_PIXELS` there too, so Pillow's decompression-bomb guard matches our limit.
**বাংলা।** প্রতিটি নতুন worker প্রসেসে একবার চলে এবং সেখানেও `Image.MAX_IMAGE_PIXELS` সেট করে, যাতে Pillow-এর নিরাপত্তা সীমা আমাদের সীমার সাথে মেলে।

#### `stage_validate(path, original_filename, max_pixels) -> ImageInfo`
**EN.** A thin wrapper around `validate_image_file`. It is used for the upload, with the user's filename, and for the AI-edited image, with no filename.
**বাংলা।** `validate_image_file`-এর পাতলা মোড়ক। আপলোডের জন্য (ফাইলের নামসহ) ও AI-এডিট করা ছবির জন্য (নাম ছাড়া) ব্যবহার হয়।

#### `stage_model_input(path, max_side, max_pixels) -> ModelInput`
**EN.**
1. `load_normalized` applies orientation, converts to sRGB and strips metadata.
2. `encode_for_model` flattens transparency onto white, shrinks the longest side to `max_side`, and saves as JPEG at quality 90.
3. The image is closed in `finally`.

**বাংলা।**
1. ছবি লোড করে ঠিক দিকে ঘোরায়, sRGB করে, মেটাডেটা মুছে দেয়।
2. স্বচ্ছ অংশ সাদা করে, বড় দিকটি `max_side`-এ ছোট করে, JPEG বানায়।
3. সবশেষে ছবিটি বন্ধ করে।

#### `stage_finish(path, work_dir, options, default_format, limits) -> FinishResult`
**EN.** All of the Pillow processing for the returned image, in a fixed order.
**বাংলা।** ফেরত দেওয়া ছবির সব Pillow প্রসেসিং, একটি নির্দিষ্ট ক্রমে।

| # | English | বাংলা |
|---|---|---|
| 1 | `ProcessOptions.model_validate(options)` re-validates inside the worker. | worker-এর ভেতরে অপশন আবার যাচাই। |
| 2 | `load_normalized`: EXIF orientation, sRGB, RGB/RGBA, no metadata. | ছবি লোড ও স্বাভাবিক করা। |
| 3 | **Transform**: `apply_transform` (rotate/flip), if requested. | **ঘোরানো/উল্টানো** (চাইলে)। |
| 4 | **Resize**: `compute_target_size` → `check_output_size` (422 if too big) → `resize_image`. | **রিসাইজ**: মাপ হিসাব, সীমা চেক, তারপর রিসাইজ। |
| 5 | **Adjust**: `apply_adjustments`, if brightness, contrast or saturation ≠ 0. | **রং ঠিক করা** (কোনো মান ০ না হলে)। |
| 6 | **Filter**: `apply_filter`, and `filter_applied = canonical_filter_name(...)` (so `"bw"` is reported as `"black_and_white"`). | **ফিল্টার**; রেসপন্সে মূল নাম দেখায় (`bw` → `black_and_white`)। |
| 7 | **Enhance**: `enhance_image`, if requested. | **এনহ্যান্স** (চাইলে)। |
| 8 | Chooses the output format: the requested one or `default_format` (the input's format).<br>• PNG with a quality setting → warning `QUALITY_IGNORED_FOR_PNG`.<br>• JPEG of an image with real transparency → warning `TRANSPARENCY_REMOVED`. | আউটপুট ফরম্যাট বাছাই (না দিলে ইনপুটের ফরম্যাট); দরকার হলে ওয়ার্নিং যোগ করে। |
| 9 | `encode_image` writes `work_dir/output.<jpg\|png\|webp>`, using `quality` or `DEFAULT_QUALITY`, and verifies the file. | `output.<ext>` ফাইলে সেভ করে এবং যাচাই করে। |
| 10 | Returns `FinishResult`; the image is closed in `finally`. | ফলাফল ফেরত দেয়, ছবি বন্ধ করে। |

---

### 5.15 `app/services/image_processing_service.py` — Pillow functions / Pillow ফাংশন

**EN.** These are deterministic, synchronous functions. Each returns a new image and never changes its input. They run only inside pool workers.
**বাংলা।** নির্দিষ্ট ফল দেয় এমন synchronous ফাংশন; প্রতিটি নতুন ছবি ফেরত দেয়, ইনপুট বদলায় না। শুধু পুলের worker-এর ভেতরে চলে।

`GEMINI_ASPECT_RATIOS` = `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9`: the aspect ratios Gemini image models accept. / Gemini ইমেজ মডেল যেসব অনুপাত নেয়।

`EncodedImage` (dataclass): `path, format, mime_type, width, height, size_bytes`.

#### Loading and normalising / লোড ও স্বাভাবিক করা

| Function | English | বাংলা |
|---|---|---|
| `load_normalized(path, *, max_pixels) -> Image` | `open_image` (full decode, with all safety checks), then `normalize_image`. | নিরাপদে পুরো ছবি খোলে, তারপর স্বাভাবিক করে। |
| `normalize_image(image) -> Image` | 1. `ImageOps.exif_transpose`: rotate the photo the way the camera intended.<br>2. `_to_srgb`.<br>3. `_normalize_mode`.<br>4. Copy the pixels into a brand-new image, so **no metadata** (EXIF, GPS, XMP, ICC, comments) survives. | ১. ক্যামেরার নির্দেশ মতো ছবি সোজা করে।<br>২. sRGB রঙে আনে।<br>৩. মোড ঠিক করে।<br>৪. শুধু পিক্সেল নতুন ছবিতে কপি করে, তাই কোনো মেটাডেটা (GPS সহ) থাকে না। |
| `_to_srgb(image) -> Image` | If the image has an ICC profile and is RGB/RGBA/CMYK, converts it to sRGB (RGBA stays RGBA). If conversion fails, it logs `icc_conversion_failed` and keeps the image. | ICC প্রোফাইল থাকলে রং sRGB-তে রূপান্তর করে; ব্যর্থ হলে ছবি যেমন আছে রাখে। |
| `_has_alpha(image) -> bool` | True for RGBA/LA/PA/La/RGBa, or for palette images with a `transparency` entry. | ছবিতে স্বচ্ছতা আছে কিনা। |
| `_normalize_mode(image) -> Image` | • RGB/RGBA: unchanged.<br>• 16/32-bit grayscale: divided by 256 into 8-bit (not clipped to white), then RGB.<br>• Float (`F`): converted to L, then RGB.<br>• Everything else (L, P, CMYK, LA …): RGBA if it has alpha, otherwise RGB. | সব ছবিকে RGB বা RGBA-তে আনে; ১৬-বিটের ধূসর ছবি সাদা না করে সঠিকভাবে ৮-বিটে নামায়। |

#### Geometry / মাপ ও জ্যামিতি

| Function | English | বাংলা |
|---|---|---|
| `compute_target_size(w, h, tw, th, keep) -> (W, H)` | • No target → original size.<br>• `keep=False` → exactly the target (a missing side keeps the original).<br>• `keep=True` → scale to fit inside the box.<br>Examples (4000×3000): width 800 → 800×600; box 800×800 → 800×600; box 800×800 without keep → 800×800. | • কিছু না দিলে আসল মাপ।<br>• অনুপাত না রাখলে ঠিক চাওয়া মাপ।<br>• অনুপাত রাখলে বক্সের ভেতরে বসানো (কাটা হয় না)। |
| `check_output_size(size, *, max_dimension, max_pixels)` | Either side > `max_dimension` or `W×H` > `max_pixels` → `422 VALIDATION_ERROR`. | মাপ সীমার বেশি হলে `422`। |
| `resize_image(image, size) -> Image` | Same size → returns the image untouched. Otherwise LANCZOS with `reducing_gap=3.0` (high quality, faster when shrinking a lot). | একই মাপ হলে কিছু করে না; না হলে উচ্চমানের LANCZOS দিয়ে রিসাইজ। |
| `closest_aspect_ratio((w, h)) -> str` | Picks the nearest of `GEMINI_ASPECT_RATIOS`, using an inner `distance` helper that compares `w/h` ratios (1920×1080 → `16:9`, 3000×4000 → `3:4`). | Gemini-র অনুপাতগুলোর মধ্যে সবচেয়ে কাছেরটি বেছে নেয়। |

#### Enhance / এনহ্যান্স

#### `enhance_image(image) -> Image`
**EN.** A fixed recipe with no AI; the same input always gives the same output.
1. A 3×3 median filter removes noise.
2. Autocontrast (0.5% cutoff, tone-preserving) is blended **50%** with the original, so the effect stays mild.
3. Contrast ×1.05.
4. Colour ×1.05.
5. Unsharp mask (radius 1.5, 60%, threshold 3) sharpens.

Transparency (alpha) is kept.

**বাংলা।** AI ছাড়া নির্দিষ্ট রেসিপি; একই ইনপুটে সবসময় একই ফল।
১. হালকা noise দূর করে।
২. অটো-কনট্রাস্ট আসলের সাথে ৫০% মেশায়, যাতে প্রভাব হালকা থাকে।
৩. কনট্রাস্ট ×১.০৫।
৪. রং ×১.০৫।
৫. হালকা শার্প করে।

স্বচ্ছতা অপরিবর্তিত থাকে।

#### Encoding / এনকোড

| Function | English | বাংলা |
|---|---|---|
| `has_visible_transparency(image) -> bool` | RGBA **and** at least one pixel with alpha < 255. | সত্যিই কোনো স্বচ্ছ পিক্সেল আছে কিনা। |
| `flatten_alpha(image, background=white) -> Image` | Pastes RGBA onto a solid white RGB background; other modes are just converted to RGB. | স্বচ্ছ অংশ সাদা করে RGB বানায়। |
| `encode_image(image, dest, *, image_format, quality) -> EncodedImage` | • **JPEG:** flatten alpha, `quality`, `optimize=True`, `progressive=True`.<br>• **WEBP:** `quality`, `method=4`.<br>• **PNG:** lossless, `compress_level=7`.<br>No metadata is written. Then `validate_output`, and the size is read from disk. | ফরম্যাট অনুযায়ী সেভ করে (মেটাডেটা ছাড়া), তারপর যাচাই করে সাইজসহ ফলাফল দেয়। |
| `validate_output(path, *, image_format, size)` | Re-opens the file: `verify()`, then a full `load()`. Format and size must match exactly, otherwise `500 PROCESSING_FAILED`. | সেভ হওয়া ফাইল আবার খুলে পরীক্ষা করে; ফরম্যাট/মাপ না মিললে `500`। |
| `encode_for_model(image, *, max_side, quality=90) -> (bytes, "image/jpeg")` | Flatten to white, shrink so the longest side ≤ `max_side`, JPEG in memory. Normalised box coordinates are unaffected by uniform scaling. | Gemini-র জন্য ছোট JPEG বানায়। সমানভাবে ছোট করলে normalized বক্স বদলায় না। |

#### Transform, adjust, filter / ঘোরানো, রং, ফিল্টার

| Function | English | বাংলা |
|---|---|---|
| `apply_transform(image, *, rotate, flip_horizontal, flip_vertical)` | Rotate **clockwise** (90 → Pillow `ROTATE_270`, 180 → `ROTATE_180`, 270 → `ROTATE_90`), then mirror left-right, then top-bottom. | **ঘড়ির কাঁটার দিকে** ঘোরায়, তারপর বাঁ-ডান ও উপর-নিচ উল্টায়। |
| `apply_adjustments(image, *, brightness, contrast, saturation)` | For each non-zero value: `factor = max(0, 1 + v/100)`. −100 → 0 (black/flat/grey), 0 → unchanged, +100 → ×2. | প্রতিটি মান থেকে গুণক বানায়: −১০০ মানে শূন্য, +১০০ মানে দ্বিগুণ। |
| `canonical_filter_name(name) -> str \| None` | None/`"none"` → None; canonical → itself; alias → canonical; unknown → `422 VALIDATION_ERROR`. | বিকল্প নাম থেকে মূল নাম বের করে। |
| `apply_filter(image, name) -> Image` | Validates the name against `VALID_FILTER_NAMES` (unknown → 422), then applies the recipe below. Alpha is preserved. | নাম যাচাই করে নিচের রেসিপি প্রয়োগ করে; স্বচ্ছতা রাখে। |

Filter recipes (R, G, B are 0–255 channel values; results are clamped) / ফিল্টার রেসিপি:

| Filter | Recipe | Look / দেখতে কেমন |
|---|---|---|
| `black_and_white` | grayscale → contrast ×1.1 | Crisp monochrome. / সাদা-কালো, একটু তীক্ষ্ণ। |
| `golden_hour` | R×1.15+12, G×1.04+4, B×0.88−6 → colour ×1.15 → contrast ×1.08 | Warm sunset glow. / সূর্যাস্তের সোনালি আভা। |
| `vintage` | R×1.10+20, G×1.02+12, B×0.85+24 (min 15) → contrast ×0.94 → colour ×0.85 | Faded old film with lifted blacks. / পুরোনো ফিল্মের মতো ফিকে রং। |
| `warm` | R×1.08+8, B×0.92 | Slightly warmer tones. / একটু উষ্ণ রং। |
| `cool` | R×0.92, B×1.10+10 → contrast ×1.05 | Bluish, cooler tones. / নীলচে, ঠান্ডা রং। |

#### `transform_box(box, *, rotate, flip_horizontal, flip_vertical) -> NormalizedBox`
**EN.** Moves a 0–1 box the same way the image was rotated or flipped, so the marks stay on the right object. With `(x0, y0, x1, y1)`:

| Operation | New box |
|---|---|
| rotate 90° (clockwise) | `(1−y1, x0, 1−y0, x1)` |
| rotate 180° | `(1−x1, 1−y1, 1−x0, 1−y0)` |
| rotate 270° | `(y0, 1−x1, y1, 1−x0)` |
| flip horizontal | `x0, x1 = 1−x1, 1−x0` |
| flip vertical | `y0, y1 = 1−y1, 1−y0` |

The result is ordered (min ≤ max) and clamped to 0–1. Example: `(0.1, 0.2, 0.3, 0.4)` rotated 90° → `(0.6, 0.1, 0.8, 0.3)`.

**বাংলা।** ছবি যেভাবে ঘোরানো বা উল্টানো হয়েছে, বক্সটিকেও ঠিক সেভাবে সরায়, যাতে দাগ সঠিক বস্তুর উপরেই থাকে। শেষে মানগুলো ০–১-এর মধ্যে আটকে রাখে।

---

### 5.16 `app/services/gemini_service.py` — Google Gemini client / Gemini ক্লায়েন্ট

**EN.** All calls use the SDK's **async** client (`client.aio.models.generate_content`), so they never block the event loop. The SDK's own retries are off; this module does its own retries.
**বাংলা।** সব কল SDK-র **async** ক্লায়েন্ট দিয়ে হয়, তাই event loop আটকে থাকে না। SDK-র নিজস্ব retry বন্ধ; এই মডিউল নিজেই retry করে।

| Constant | Meaning / অর্থ |
|---|---|
| `DETECTION_PROMPT` | Asks for JSON with each object's `label`, `category`, a one-line `description`, `box_2d = [ymin, xmin, ymax, xmax]` on a 0–1000 scale (only when it can be located), plus `main_subject`; at most 25 objects. / প্রতিটি বস্তুর নাম, শ্রেণি, বর্ণনা ও ০–১০০০ স্কেলে বক্স চায়। |
| `DETECTION_JSON_SCHEMA` | The JSON Schema Gemini must follow (`response_json_schema`). / Gemini-কে যে JSON গঠন মানতে হবে। |
| `MAX_OBJECTS = 50` | Server-side cap on returned objects. / সার্ভার সর্বোচ্চ ৫০টি বস্তু নেয়। |
| `MAX_EDIT_OUTPUT_BYTES = 40 MB` | Largest edited image accepted. / এডিট করা ছবির সর্বোচ্চ সাইজ। |
| `_SAFETY_FINISH_REASONS` | Finish reasons that mean "blocked by safety". / যে কারণগুলোর মানে নিরাপত্তার জন্য আটকানো। |
| `_RETRY_DELAY_RE` | Parses Google's `"12s"` / `"1.5s"` retry delays. / Google-এর অপেক্ষার সময় পড়ে। |

#### Types / টাইপ

| Type | English | বাংলা |
|---|---|---|
| `GeminiError(code, message, *, retryable=False, retry_after=None)` | Internal Gemini failure, with a flag saying whether retrying might help. | Gemini-র ব্যর্থতা, সাথে আবার চেষ্টা করলে কাজ হতে পারে কিনা। |
| `NormalizedBox` | `x_min, y_min, x_max, y_max` as 0–1 fractions. | ০–১ ভগ্নাংশে বক্স। |
| `Detection` | `label, category, description, box, confidence=None`. | একটি শনাক্ত বস্তু। |
| `DetectionResult` | `model, main_subject, objects, invalid_boxes, truncated_objects`. | ডিটেকশনের পূর্ণ ফলাফল। |
| `EditedImage` | `data, mime_type, model`. | এডিট করা ছবি। |
| `GeminiService` (Protocol) | The interface: `detect_objects`, `edit_image`, `aclose`. Tests can plug in a fake that has the same methods. | ইন্টারফেস; টেস্টে একই মেথডওয়ালা নকল সার্ভিস বসানো যায়। |

#### Model-output validation / মডেলের উত্তর যাচাই

| Function / class | English | বাংলা |
|---|---|---|
| `_clean_text(value, max_len)` | None → None; a non-string raises; whitespace is collapsed; cut to `max_len`; empty → None. | লেখা পরিষ্কার করে ও দৈর্ঘ্য সীমিত করে। |
| `_RawObject` | Validators `_label`, `_category` and `_description` (all via `_clean_text`): `label` required and non-empty (≤200 chars); `category` ≤100; `description` ≤1000. `box_2d` is accepted as anything and checked separately, so one bad box does not reject the whole answer. | প্রতিটি বস্তুর কাঁচা রূপ; ভুল বক্সের জন্য পুরো উত্তর বাতিল হয় না। |
| `_RawDetection` | Validator `_main_subject`: `main_subject` ≤500 chars; `objects` list required. | পুরো উত্তরের কাঁচা রূপ। |
| `normalize_box(box_2d) -> NormalizedBox \| None` | Must be exactly 4 finite numbers (not booleans), each 0–1000, with `ymin<ymax` and `xmin<xmax`. Reorders `[y,x,y,x]` → `x/y` and divides by 1000. Anything invalid → `None`; coordinates are **never guessed or clamped into existence**. `[100,200,500,800]` → x 0.2–0.8, y 0.1–0.5. | ঠিক ৪টি বৈধ সংখ্যা চাই; ভুল হলে `None`। কো-অর্ডিনেট **কখনো অনুমান করে বানানো হয় না**। |
| `parse_detection_payload(text, *, model) -> DetectionResult` | Empty text → `GEMINI_INVALID_RESPONSE`. Invalid JSON or schema → `GEMINI_INVALID_RESPONSE`. Keeps the first 50 objects, normalises each box, and counts `invalid_boxes` and `truncated_objects`. An object whose box is invalid is kept, with `box=None`. | JSON পার্স ও যাচাই করে; ভুল বক্সওয়ালা বস্তু রাখে কিন্তু বক্স বাদ দেয়, কতগুলো বাদ গেল গোনে। |

#### Error classification / এরর শ্রেণিবিভাগ

#### `_retry_delay_from_details(details) -> float | None`
**EN.** Finds Google's `RetryInfo.retryDelay` (e.g. `"12s"`) in the error details and returns the seconds, capped at 60. Returns `None` if there isn't one.
**বাংলা।** Google-এর এরর থেকে কত সেকেন্ড পরে আবার চেষ্টা করতে হবে তা বের করে (সর্বোচ্চ ৬০)।

#### `classify_api_error(exc) -> GeminiError`

| Google error | Our code | Retry? | HTTP to client (edit only) |
|---|---|---|---|
| 429 / `RESOURCE_EXHAUSTED` | `GEMINI_RATE_LIMITED` | ✅ (uses `RetryInfo`) | 503 |
| 500/502/503/504, `UNAVAILABLE`, `INTERNAL` | `GEMINI_UNAVAILABLE` | ✅ | 502 |
| 408 / `DEADLINE_EXCEEDED` | `GEMINI_TIMEOUT` | ✅ | 504 |
| 401/403/404, `PERMISSION_DENIED`, `UNAUTHENTICATED`, `NOT_FOUND` | `GEMINI_CONFIGURATION_ERROR` (logged as an error; the client sees a generic message) | ❌ | 503 |
| anything else (e.g. 400) | `GEMINI_REQUEST_REJECTED` | ❌ | 502 |

**বাংলা।** Google-এর এররকে আমাদের কোডে রূপান্তর করে এবং ঠিক করে আবার চেষ্টা করা যাবে কিনা। ভুল key বা মডেলের নাম হলে সার্ভার লগে বিস্তারিত থাকে, কিন্তু ক্লায়েন্ট শুধু সাধারণ মেসেজ পায়।

#### `raise_if_blocked(response) -> None`
**EN.**
- `prompt_feedback.block_reason` is set → `GEMINI_SAFETY_BLOCKED`.
- No candidates → `GEMINI_INVALID_RESPONSE`.
- The first candidate's `finish_reason` is a safety reason → `GEMINI_SAFETY_BLOCKED`.

None of these are retried.

**বাংলা।** Gemini নিরাপত্তার কারণে আটকালে বা কোনো উত্তর না দিলে এরর দেয়; এগুলোতে আবার চেষ্টা করা হয় না।

#### `class GoogleGeminiService`

| Method | English | বাংলা |
|---|---|---|
| `__init__(*, client, settings, sleep=asyncio.sleep, rng=None)` | Stores the client and settings, and creates `Semaphore(GEMINI_MAX_CONCURRENCY)`. `sleep` and `rng` can be replaced in tests, so retries run instantly and predictably. | ক্লায়েন্ট ও সেটিংস রাখে, একসাথে কলের সীমার জন্য semaphore বানায়। টেস্টে `sleep`/`rng` বদলানো যায়। |
| `from_settings(settings)` (classmethod) | `genai.Client(api_key=GEMINI_API_KEY)`, wrapped in the service. | API key দিয়ে ক্লায়েন্ট বানায়। |
| `async aclose()` | Closes the async HTTP client. | HTTP ক্লায়েন্ট বন্ধ করে। |
| `async detect_objects(image, mime) -> DetectionResult` | 1. No vision model → `GEMINI_CONFIGURATION_ERROR`.<br>2. Config: JSON output with the schema, HTTP timeout = `GEMINI_DETECTION_TIMEOUT_SECONDS`.<br>3. `_call(model, [image part, DETECTION_PROMPT], config)`.<br>4. Finish reason `MAX_TOKENS` → `GEMINI_INVALID_RESPONSE` (truncated).<br>5. `parse_detection_payload`. | ছবি ও prompt পাঠিয়ে JSON উত্তর চায়; উত্তর কেটে গেলে এরর; শেষে উত্তর পার্স করে। |
| `async edit_image(image, mime, *, prompt, aspect_ratio) -> EditedImage` | 1. No edit model → `GEMINI_CONFIGURATION_ERROR`.<br>2. Config: `response_modalities=["TEXT","IMAGE"]`, `ImageConfig(aspect_ratio)`, HTTP timeout = `GEMINI_EDIT_TIMEOUT_SECONDS`.<br>3. `_call`, then `_extract_image`. | ছবি ও নির্দেশ পাঠিয়ে এডিট করা ছবি চায়। |
| `_extract_image(response, model)` (static) | Keeps the parts that are not "thought" parts and have non-empty `inline_data` with an `image/*` MIME type, then takes the **last** one. None → `GEMINI_INVALID_RESPONSE`; larger than 40 MB → `GEMINI_INVALID_RESPONSE`. | উত্তর থেকে শেষ ছবির অংশটি নেয়; না থাকলে বা খুব বড় হলে এরর। |
| `async _call(*, model, contents, config)` | Retry loop with `attempts = GEMINI_MAX_RETRIES + 1` (default 4):<br>1. `_call_once` → `raise_if_blocked` → log `gemini_call_ok` and return.<br>2. On `GeminiError`, log `gemini_call_failed`.<br>3. If the error is not retryable, or this was the last attempt, raise it.<br>4. Otherwise sleep for `retry_after` (from Google) or `backoff_delay(attempt)`, then try again. | আবার চেষ্টার লুপ (ডিফল্ট ৪ বার)। সফল হলে ফেরত; আবার চেষ্টা করার মতো এরর হলে অপেক্ষা করে পুনরায় চেষ্টা; না হলে বা শেষ চেষ্টা হলে এরর। |
| `async _call_once(*, model, contents, config)` | 1. Waits at most `GEMINI_QUEUE_TIMEOUT_SECONDS` (30) for a semaphore slot, else `GEMINI_RATE_LIMITED` "busy".<br>2. `client.aio.models.generate_content(...)`.<br>3. Maps `APIError` → `classify_api_error`, `httpx.TimeoutException` → `GEMINI_TIMEOUT` (retryable), `httpx.TransportError` → `GEMINI_UNAVAILABLE` (retryable).<br>4. Always releases the slot in `finally`. | ১. semaphore-এ জায়গার জন্য সর্বোচ্চ ৩০ সেকেন্ড অপেক্ষা।<br>২. Gemini কল।<br>৩. নেটওয়ার্ক বা API এরর আমাদের কোডে রূপান্তর।<br>৪. সবসময় জায়গা ছেড়ে দেয়। |

#### `_ms_since(started) -> int`
**EN.** Milliseconds elapsed since a `time.monotonic()` value, used in the call logs.
**বাংলা।** কত মিলিসেকেন্ড পার হলো, লগের জন্য।

---

### 5.17 `app/services/workspace.py` — temp folders / টেম্প ফোল্ডার

`_COPY_CHUNK = 1 MB` is the copy block size. / কপি করার ব্লকের সাইজ।

#### `class TempWorkspace(temp_root, request_id)`

| Member | English | বাংলা |
|---|---|---|
| `__init__` | Refuses any `request_id` that is not 32 lowercase hex characters (`ValueError`), so a path like `../x` can never be built. Sets `path = temp_root / request_id`. | আইডি ঠিক ৩২ অক্ষরের hex না হলে বাতিল করে, তাই `../` দিয়ে অন্য ফোল্ডারে যাওয়া অসম্ভব। |
| `upload_path` (property) | `path / "upload"`. | আপলোড ফাইলের পাথ। |
| `create()` | `mkdir(mode=0o700)`; fails if the folder already exists. Request IDs are unique, so it never should. | শুধু মালিক পড়তে/লিখতে পারে এমন ফোল্ডার বানায়; আগে থেকে থাকলে ব্যর্থ। |
| `exists()` | `path.is_dir()`. Not called anywhere in the current code. | ফোল্ডার আছে কিনা; বর্তমান কোডে কোথাও কল হয় না। |
| `cleanup()` | `shutil.rmtree(path, ignore_errors=True)`. | পুরো ফোল্ডার মুছে দেয়। |

#### `ensure_temp_root(temp_root) -> None`
**EN.** Creates the root folder (and its parents) with mode 700. If it already exists, it tries to tighten it to 700, ignoring any error.
**বাংলা।** মূল টেম্প ফোল্ডার তৈরি করে (mode 700); আগে থেকে থাকলে অনুমতি 700 করার চেষ্টা করে।

#### `copy_upload(src, dest, max_bytes) -> (size, sha256_hex)`
**EN.**
1. Seeks `src` to the start and opens `dest` in exclusive-create mode (`"xb"`).
2. Reads 1 MB at a time and adds to the running size.
3. If the size passes `max_bytes`, raises `413 FILE_TOO_LARGE` with `details.max_bytes`.
4. Updates the SHA-256 and writes the chunk.
5. A 0-byte file raises `422 VALIDATION_ERROR` "The uploaded file is empty."

The whole file is never held in memory.

**বাংলা।**
১. ফাইলের শুরুতে যায় এবং নতুন ফাইল খোলে।
২. ১ MB করে পড়ে, সাইজ যোগ করতে থাকে।
৩. সীমা ছাড়ালে `413`।
৪. হ্যাশ হিসাব করে ও লেখে।
৫. খালি ফাইল হলে `422`।

পুরো ফাইল কখনো একসাথে মেমোরিতে রাখা হয় না।

#### `sweep_temp_dirs(temp_root, *, max_age_seconds, active, now=None) -> int`
**EN.** Removes leftover request folders, for example after a crash. A folder is deleted only if **all** of these hold:
- it is a real directory, not a symlink;
- its name is a 32-hex ID;
- its ID is not in `active`;
- it is older than `max_age_seconds` (900 s by default, longer than any request can run).

Returns how many were removed and logs `temp_dirs_swept`.

**বাংলা।** পড়ে থাকা পুরোনো ফোল্ডার মুছে দেয়। একটি ফোল্ডার মোছা হয় শুধু তখনই, যখন এই সব শর্ত মেলে:
- এটি আসল ফোল্ডার (symlink নয়);
- নাম ৩২ অক্ষরের hex আইডি;
- এখন চলমান নয়;
- ১৫ মিনিটের বেশি পুরোনো।

কয়টি মুছল তা ফেরত দেয়।

- **Called by / কে কল করে:** `_sweep_forever` in `main.py`.

---

### 5.18 `app/utils/filenames.py` — IDs and safe names / আইডি ও নিরাপদ নাম

| Name | English | বাংলা |
|---|---|---|
| `OUTPUT_EXTENSIONS` | `JPEG→jpg, PNG→png, WEBP→webp` | ফরম্যাট থেকে এক্সটেনশন। |
| `MIME_TYPES` | `JPEG→image/jpeg, PNG→image/png, WEBP→image/webp` | ফরম্যাট থেকে MIME টাইপ। |
| `HEX_ID_RE` | `^[0-9a-f]{32}$`, the only allowed request-ID shape. | অনুমোদিত আইডির একমাত্র রূপ। |
| `_UNSAFE_CHARS_RE` | Anything except letters, digits, `_`, space, `.`, `(`, `)`, `-`. | এর বাইরের সব অক্ষর অনিরাপদ। |

#### `new_id() -> str`
**EN.** `uuid4().hex`: 32 random lowercase hex characters (128 bits).
**বাংলা।** ৩২ অক্ষরের র‍্যান্ডম আইডি।
- **Used by / ব্যবহার করে:** request IDs and the health probe file name.

#### `extension_of(filename) -> str | None`
**EN.** Returns the lower-cased extension of the last path part.
- `"photo.tar.gz"` → `"gz"`
- `".bashrc"` → `None`
- `"file."` → `None`
- `"C:\\x\\a.PNG"` → `"png"`

**বাংলা।** ফাইলের শেষ অংশের এক্সটেনশন ছোট হাতের অক্ষরে দেয়; না থাকলে `None`।

#### `sanitize_original_filename(filename, max_length=200) -> str | None`
**EN.** Makes a client file name safe to **display**. It is never used as a path.
1. Keeps only the last path part.
2. Applies Unicode NFKC.
3. Removes control characters.
4. Replaces unsafe characters with `_`.
5. Trims spaces and strips leading dots.
6. Shortens long names while keeping the extension.

`"../../etc/My Photo<1>.JPG"` → `"My Photo_1_.JPG"`.

**বাংলা।** ক্লায়েন্টের ফাইলের নাম শুধু **দেখানোর** জন্য নিরাপদ করে; কখনো পাথ হিসেবে ব্যবহার হয় না। ফোল্ডারের অংশ, কন্ট্রোল অক্ষর ও বিপজ্জনক অক্ষর সরিয়ে দেয়, আর লম্বা নাম ছোট করে।

#### `download_filename(original, image_format) -> str`
**EN.** The suggested save name: `<safe stem>-processed.<ext>`.
- `"My Photo<1>.JPG"` + `WEBP` → `"My Photo_1_-processed.webp"`
- no name → `"image-processed.jpg"`

**বাংলা।** ডাউনলোডের জন্য প্রস্তাবিত নাম তৈরি করে।

---

### 5.19 `app/utils/image_validation.py` — is it a real, safe image? / আসল ও নিরাপদ ছবি কিনা

**EN.** The file's **content** decides; the client's filename and Content-Type are not trusted.
**বাংলা।** ফাইলের **ভেতরের কনটেন্ট** দেখে সিদ্ধান্ত হয়; ক্লায়েন্টের দেওয়া নাম বা Content-Type বিশ্বাস করা হয় না।

| Name | Meaning / অর্থ |
|---|---|
| `ALLOWED_EXTENSIONS` | `jpg, jpeg, jpe, jfif, png, webp`. |
| `_PILLOW_FORMATS` | The Pillow formats accepted for each sniffed type. `MPO` (multi-picture JPEG from phones) counts as JPEG. / ফোনের MPO ছবিও JPEG হিসেবে গণ্য। |
| `_DECODE_ERRORS` | Exceptions that mean "broken file". / যেসব এররের মানে ফাইল ভাঙা। |
| `ImageInfo` | `format` (`JPEG`/`PNG`/`WEBP`), `mime_type`, `width`, `height`. |

| Function | English | বাংলা |
|---|---|---|
| `sniff_format(head) -> str \| None` | Magic bytes: `FF D8 FF` → JPEG; `89 50 4E 47 0D 0A 1A 0A` → PNG; `RIFF....WEBP` → WEBP; anything else → None. | ফাইলের শুরুর বাইট দেখে আসল ধরন চেনে। |
| `_unsupported()` / `_corrupted()` / `_too_large(max_pixels)` | Build `415 UNSUPPORTED_FILE_TYPE`, `422 CORRUPTED_IMAGE` and `413 IMAGE_TOO_LARGE` errors. | তিন ধরনের এরর তৈরি করে। |
| `check_filename_extension(name)` | If the name has an extension and it is not allowed → 415. A name without an extension is fine. | নামে ভুল এক্সটেনশন থাকলে `415`; এক্সটেনশন না থাকলে সমস্যা নেই। |
| `normalized_format(image) -> str` | `MPO` → `JPEG`; otherwise Pillow's format name. | MPO-কে JPEG বলে। |

#### `open_image(path, *, max_pixels, reduced_decode=False) -> Image`
**EN.** The core safety check. It returns a fully decoded image (frame 0).
**বাংলা।** মূল নিরাপত্তা পরীক্ষা। পুরোপুরি ডিকোড করা ছবি (প্রথম ফ্রেম) ফেরত দেয়।

| # | English | বাংলা |
|---|---|---|
| 1 | Reads the first 16 bytes → `sniff_format`; unknown → 415. | প্রথম ১৬ বাইট দেখে ধরন চেনে; অজানা হলে `415`। |
| 2 | Turns Pillow's `DecompressionBombWarning` into an error. | Pillow-এর "বোমা" সতর্কতাকে এরর বানায়। |
| 3 | Opens the **header only**. Pillow's format must match the sniffed type (else 415). Width and height must be ≥ 1 (else 422). `w×h` must be ≤ `max_pixels` (else 413). More than one frame (APNG, animated WEBP) → `422 ANIMATED_IMAGE_UNSUPPORTED`, except MPO. Then `verify()`. | শুধু **হেডার** খোলে: ধরন মেলে কিনা, মাপ শূন্য কিনা, পিক্সেল সীমা ও অ্যানিমেশন চেক করে; তারপর `verify()`। পিক্সেল ডিকোডের **আগেই** সব হয়। |
| 4 | Re-opens the file (`verify()` leaves the image unusable). With `reduced_decode` on a JPEG, `draft()` decodes at 1/8 scale, which is cheap but still reads the whole bitstream. Then `load()` performs the full decode and catches truncated files. | আবার খোলে এবং পুরো ডিকোড করে (ভাঙা বা কাটা ফাইল এখানে ধরা পড়ে)। যাচাইয়ের সময় JPEG ১/৮ মাপে ডিকোড হয়, তাই কাজটা সস্তা। |
| 5 | Error mapping: `AppError` passes through; a decompression bomb → 413; decode errors → 422 `CORRUPTED_IMAGE`. | এররগুলোকে আমাদের কোডে রূপান্তর করে। |

#### `validate_image_file(path, *, original_filename, max_pixels) -> ImageInfo`
**EN.**
1. `check_filename_extension`.
2. `open_image(..., reduced_decode=True)` → `normalized_format`.
3. Re-reads the **true** width and height from the header, because draft mode shrinks `image.size`.
4. Returns `ImageInfo`.

**বাংলা।** এক্সটেনশন চেক করে, কম খরচে পুরো ফাইল যাচাই করে, তারপর হেডার থেকে আসল মাপ নিয়ে `ImageInfo` ফেরত দেয়।

---

### 5.20 `app/static/index.html` — page markup / পেজের গঠন

| Part | English | বাংলা |
|---|---|---|
| `<head>` | Title, description, theme colours for dark/light, an inline SVG favicon, Google Fonts (Archivo, Kalam), `styles.css`, and `app.js` (`defer`). | টাইটেল, থিম রং, আইকন, ফন্ট, CSS ও JS। |
| `header.masthead` | A hidden `<h1>` for screen readers, and `#server-status`, which shows whether the server and Gemini are ready. | স্ক্রিন রিডারের জন্য লুকানো শিরোনাম, আর সার্ভার/Gemini প্রস্তুত কিনা তা দেখানোর জায়গা। |
| `form#controls` → intake | `label#dropzone` wraps `input#file-input` (multiple JPEG/PNG/WEBP); `#tray` holds thumbnails; `#clear-tray`; a paste tip. | ড্রপজোন, ফাইল বাছাই, থাম্বনেইলের সারি, সব মুছুন বোতাম। |
| `#filters-group` | Chips: Normal, Golden hour, Black & white, Old film (`vintage`), Warm, Cool. | ফিল্টারের চিপ বোতাম। |
| Size | `#target-width`, `#target-height`, `#keep-aspect`. | প্রস্থ, উচ্চতা, অনুপাত রাখা। |
| Output | `#output-format`, `#quality` (+ `#quality-value`), `#enhance`. | ফরম্যাট, কোয়ালিটি, এনহ্যান্স। |
| `#ai-group` | `#detect`: "Find objects and mark them". | বস্তু খুঁজে চিহ্নিত করার চেকবক্স। |
| `#process`, `#form-error` | The submit button and the form error line. | প্রসেস বোতাম ও এরর লাইন। |
| `section.table` | `#empty` (the message shown before any result) and `ol#prints` (result cards). | ফলাফলের জায়গা। |
| `template#print-template` | One result card: photo frame with `.marks` boxes, zoom button, "developing" progress overlay; actions (show original, copy, download); notes (title, subject, facts, flags, objects, warnings, error). | একটি ফলাফল কার্ডের ছাঁচ। |
| `#lightbox`, `#toast` | Full-screen zoom view; a small pop-up message. | বড় করে দেখা; ছোট পপ-আপ বার্তা। |

---

### 5.21 `app/static/app.js` — page logic / পেজের লজিক

**EN.** Plain JavaScript with no framework. Every string from the server is shown with `textContent`, never `innerHTML`, so server text can never inject HTML.
**বাংলা।** কোনো ফ্রেমওয়ার্ক ছাড়া সাধারণ JavaScript। সার্ভারের সব লেখা `textContent` দিয়ে দেখানো হয়, তাই HTML ঢুকিয়ে আক্রমণ সম্ভব নয়।

| Constant / state | Meaning / অর্থ |
|---|---|
| `API = "/api/v1"` | API base path. |
| `MAX_PARALLEL = 3` | Uploads at once; matches the server's per-IP limit. / একসাথে ৩টি আপলোড। |
| `MAX_RETRIES = 4` | Automatic retries for "busy" answers. / ব্যস্ত থাকলে সর্বোচ্চ ৪ বার আবার চেষ্টা। |
| `ACCEPTED` | `image/jpeg`, `image/png`, `image/webp`. |
| `TOAST_MS = 2200` | How long a toast stays visible. / পপ-আপ কতক্ষণ থাকে। |
| `els` | Cached DOM elements. / পেজের এলিমেন্টগুলো। |
| `currentFilter` | The chosen filter chip (`""` = Normal). / বাছাই করা ফিল্টার। |
| `capabilities` | Result of `/api/v1/capabilities`. |
| `staged` | `[{file, url}]` waiting in the tray. / ট্রেতে অপেক্ষমাণ ছবি। |
| `reduceMotion` | The user asked the OS for less animation. / ব্যবহারকারী কম অ্যানিমেশন চান কিনা। |
| `FRIENDLY` | Extra hint text for each error code. / প্রতিটি এরর কোডের জন্য সহজ পরামর্শ। |

| Function | English | বাংলা |
|---|---|---|
| `formatBytes(n)` | `512 B`, `1.5 KB`, `2.25 MB`. | বাইটকে পড়ার মতো করে লেখে। |
| `sleep(ms)` | A Promise that resolves after `ms`. | কিছুক্ষণ অপেক্ষা। |
| `showToast(message)` | Shows the toast for 2.2 s. | ছোট বার্তা দেখায়। |
| `loadCapabilities()` | Fetches `/capabilities`. On failure, status shows "Can't reach the server". On success it sets the max-size hint, the width/height maximum, the default quality, the status text and whether **detect** is enabled. | সার্ভারের ক্ষমতা জেনে কন্ট্রোল সাজায়; Gemini না থাকলে ডিটেক্ট বন্ধ করে। |
| `addFiles(fileList) -> number` | Skips non-image and too-large files (listing them in `#form-error`), adds the rest to `staged` with an object URL, re-renders the tray, and returns the count added. | ছবি ট্রেতে যোগ করে; ভুল বা বড় ফাইল বাদ দিয়ে জানায়। |
| `renderTray()` | Draws thumbnails with × buttons (removing one revokes its URL). Updates the button text ("Process 3 images") and shows "Clear all" for 2+ files. | থাম্বনেইল আঁকে, বোতামের লেখা বদলায়। |
| `showFormError(msg)` | Shows the form error line. | ফর্মের এরর দেখায়। |
| `readOptions() -> fields` | Builds the form fields: width, height, `keep_aspect_ratio=false` only when unchecked, format, quality (not for PNG), `enhance_image`, `detect_objects` (only if enabled), `filter`. | ফর্ম থেকে পাঠানোর ফিল্ড বানায়। |
| `upload(file, fields, onProgress) -> Promise<{status, body, retryAfter}>` | Sends multipart with `XMLHttpRequest`, so upload progress can be shown. It never rejects: a network error resolves with `status: 0`. | XHR দিয়ে আপলোড করে অগ্রগতি জানায়; নেটওয়ার্ক এরর হলে `status: 0`। |
| `processOne(item, fields, view)` | Uploads once. 200 → `view.showResult`. 503, or a 429 whose code is not `RATE_LIMITED` (i.e. too many at once) → waits `Retry-After` (or 2^attempt s) and retries, up to 4 times. Otherwise → `view.showError(...)` with a "Try again" button. | একটি ছবি পাঠায়। সফল হলে দেখায়; ব্যস্ত থাকলে অপেক্ষা করে আবার চেষ্টা করে; অন্য এরর হলে "Try again" বোতামসহ এরর দেখায়। |
| `runQueue(items, fields)` | Creates a result card for every image, scrolls to the newest, then runs up to 3 "workers" that take items from the shared list one by one. | প্রতিটি ছবির কার্ড বানিয়ে একসাথে সর্বোচ্চ ৩টি করে প্রসেস করে। |
| `swapPhoto(img, src, alt)` | Crossfades to a new image (instant if reduced motion). | ছবি বদলানোর সময় হালকা fade। |
| `openLightbox(src, alt, trigger)` / `closeLightbox()` | Full-screen view. Focus moves to Close and returns to the zoom button afterwards. Esc or a click on the backdrop closes it. | বড় করে দেখা; Esc বা বাইরে ক্লিক করলে বন্ধ। |
| `copyImageToClipboard(dataUrl)` | Draws the image on a canvas, converts it to PNG and writes it with `navigator.clipboard.write`. The button is removed if the browser cannot copy images. | ছবি PNG করে ক্লিপবোর্ডে কপি করে। |
| `createPrint(item) -> {setProgress, showResult, showError}` | Clones the template, shows the original while it "develops", and returns three controls. `setProgress` drives the text and bar. `showResult` swaps in the result, wires download/copy/toggle and fills the notes. `showError` dims the photo and shows the message, the `FRIENDLY` hint, the request ID and a retry button. | একটি ফলাফল কার্ড বানিয়ে তিনটি নিয়ন্ত্রক ফাংশন দেয়: অগ্রগতি, ফলাফল ও এরর দেখানো। |
| `renderFacts(dl, body)` | Size, format, file size, time, with "was …" when something changed. | মাপ, ফরম্যাট, সাইজ, সময় দেখায়। |
| `renderFlags(ul, body)` | "N objects found", "Enhanced", "Edited by AI". | কী কী হয়েছে তা দেখায়। |
| `renderObjects(list, marks, objects)` | Lists each object with its category and description. If a validated box exists, it draws a `.mark` positioned by **percent** from the normalised box (so it scales with the image). Hovering or focusing the list item highlights the mark; the label goes below if the box is near the top. If there is no box: "No location given". It never invents a box. | প্রতিটি বস্তুর তালিকা দেখায় এবং normalized বক্স থেকে শতাংশ হিসেবে ছবির উপর দাগ আঁকে। বক্স না থাকলে "No location given" লেখে; কখনো বক্স বানিয়ে নেয় না। |
| `renderWarnings(ul, warnings)` | Lists the warning messages. | ওয়ার্নিং দেখায়। |

**Event wiring / ইভেন্ট সংযোগ:**
- file input `change` → `addFiles`.
- `dragenter`/`dragover` → `data-over="true"`, which turns on the marching-ants border in CSS. `dragleave`/`drop` → `"false"`.
- Drops elsewhere on the page are ignored, so the browser doesn't navigate away.
- `paste` anywhere (except inside inputs) adds pasted images.
- "Clear all" empties the tray.
- The quality slider updates its number. Choosing PNG disables quality.
- A filter chip click sets `currentFilter` and `aria-pressed`.
- Form `submit` → takes everything staged, clears the tray, and calls `runQueue`.
- Finally, `loadCapabilities()` runs once.

**বাংলা:**
- ফাইল বাছাই, ড্র্যাগ-ড্রপ ও পেস্ট — তিনভাবেই ছবি যোগ করা যায়।
- ড্র্যাগ করার সময় ড্রপজোনে চলন্ত দাগের বর্ডার দেখা যায়।
- PNG বাছলে কোয়ালিটি বন্ধ হয়।
- ফিল্টার চিপে ক্লিক করলে ফিল্টার বাছাই হয়।
- সাবমিট করলে ট্রের সব ছবি প্রসেসের লাইনে যায়।

---

### 5.22 `app/static/styles.css` — design / ডিজাইন

| Section | English | বাংলা |
|---|---|---|
| Design tokens (`:root`) | Colours, radii, shadows and fonts as CSS variables. Dark is the default; `@media (prefers-color-scheme: light)` overrides it. | রং, কোণ, ছায়া ও ফন্ট ভেরিয়েবলে; ডিফল্ট ডার্ক, সিস্টেম লাইট হলে লাইট। |
| Reset & base | Box sizing, body font and background. | মৌলিক স্টাইল। |
| Masthead | Server-status text with a coloured dot (`ok`/`limited`/`down`) and a `pulse-dot` animation. | সার্ভারের অবস্থা রঙিন বিন্দুসহ। |
| Layout | A two-column grid (controls \| results) that stacks under 900 px. | দুই কলাম; ছোট স্ক্রিনে একটার নিচে আরেকটা। |
| Drop zone | While a file is dragged over it, a **marching-ants** dashed border moves (`marching-ants`). The icon bounces once on hover or drag (`icon-bounce`); it never loops forever. | ফাইল টেনে আনলে চলন্ত ড্যাশ বর্ডার; আইকন একবার লাফায়। |
| Tray, form groups, inputs, range, chips, checkboxes, process button | Control styling; tray items animate in (`tray-item-in`). | কন্ট্রোলগুলোর ডিজাইন। |
| Results | Frame, zoom button, "grease-pencil" object marks, the developing overlay (`spin`, `indeterminate` bar), action buttons, notes column. | ফলাফলের কার্ড, বস্তুর দাগ, লোডিং অ্যানিমেশন। |
| Lightbox, toast | `lightbox-in`, `lightbox-photo-in`, `toast-in` animations. | বড় দেখা ও পপ-আপের অ্যানিমেশন। |
| `print-in` | New result cards slide in. | নতুন কার্ড স্লাইড করে আসে। |
| `prefers-reduced-motion` | All animations and transitions become effectively instant. | কম অ্যানিমেশন চাইলে সব অ্যানিমেশন প্রায় বন্ধ। |
| Scrollbar | A thin themed scrollbar. | পাতলা স্ক্রলবার। |

---

### 5.23 `scripts/check_gemini.py` — live Gemini test / লাইভ Gemini টেস্ট

**EN.** Proves that your API key, the installed SDK and the configured model names really work. It spends a few tokens.
**বাংলা।** আপনার API key, ইনস্টল করা SDK আর মডেলের নাম সত্যিই কাজ করে কিনা প্রমাণ করে। এতে কিছু টোকেন খরচ হয়।

| Function | English | বাংলা |
|---|---|---|
| `sample_image()` | A 640×480 grey image with a red circle and a blue square. | লাল বৃত্ত ও নীল বর্গসহ একটি পরীক্ষামূলক ছবি। |
| `async run(args) -> int` | 1. No key → prints a message, exit **1**.<br>2. Prints the `google-genai` version.<br>3. Uses `--image` or the sample.<br>4. Detects objects and prints the subject, each object and its box; a failure exits **2**.<br>5. With `--edit` and an edit model configured, tries one edit ("Make the background light green") and prints the result size; a failure exits **3**.<br>6. Always closes the client. | ১. key না থাকলে exit ১।<br>২. SDK ভার্সন দেখায়।<br>৩. নিজের ছবি বা নমুনা ছবি নেয়।<br>৪. ডিটেকশন চালিয়ে ফল দেখায়; ব্যর্থ হলে exit ২।<br>৫. `--edit` দিলে একটি এডিট চেষ্টা করে; ব্যর্থ হলে exit ৩।<br>৬. সবশেষে ক্লায়েন্ট বন্ধ করে। |
| `main()` | Parses `--image PATH` and `--edit`, then runs `run`. | কমান্ড-লাইন অপশন পড়ে চালায়। |

```bash
uv run python scripts/check_gemini.py                 # detection only / শুধু ডিটেকশন
uv run python scripts/check_gemini.py --image my.jpg  # your own image / নিজের ছবি
uv run python scripts/check_gemini.py --edit          # also try an edit / এডিটও চেষ্টা
```

---

### 5.24 `loadtest/locustfile.py` — load test / লোড টেস্ট

| Name | English | বাংলা |
|---|---|---|
| `EXPECTED = {200, 429, 503}` | 429 and 503 are the designed backpressure, so they count as success. | ৪২৯/৫০৩ ইচ্ছাকৃত চাপ-নিয়ন্ত্রণ, তাই সফল ধরা হয়। |
| `make_png(w, h)` | A solid random-colour PNG in memory. | র‍্যান্ডম রঙের একটি PNG বানায়। |
| `ImageUser.on_start` | Each fake user prepares 5 PNGs of 200–1200 px. | প্রতিটি নকল ব্যবহারকারী ৫টি ছবি বানায়। |
| `resize_to_webp` (weight 5) | Width 256, WEBP, quality 80. | ছোট করে WEBP। |
| `enhance` (weight 2) | `enhance_image=true`. | এনহ্যান্স। |
| `capabilities` (weight 1) | `GET /api/v1/capabilities`. | ক্ষমতা জানতে চাওয়া। |
| `_process(data)` | Posts a random image with `data` and marks unexpected statuses as failures. | ছবি পাঠায়; অপ্রত্যাশিত status হলে ব্যর্থ ধরে। |

```bash
uv run locust -f loadtest/locustfile.py --host http://localhost:8000 \
    --users 30 --spawn-rate 10 --run-time 1m --headless
```

All fake users share your IP, so per-IP limits apply to all of them together. Raise `RATE_LIMIT_IP_PER_MINUTE` and `MAX_CONCURRENT_PER_IP` to measure raw speed.
সব নকল ব্যবহারকারী আপনার একই IP ব্যবহার করে, তাই প্রতি-IP সীমা সবার উপর একসাথে খাটে। আসল গতি মাপতে ওই দুটি সেটিং বাড়ান।

---

### 5.25 Root files / রুট ফাইল

| File | English | বাংলা |
|---|---|---|
| `pyproject.toml` | Runtime deps: fastapi, uvicorn[standard], pydantic(-settings), python-multipart, pillow, google-genai ~2.31, anyio, httpx. Dev deps: fastapi-cli, pytest, pytest-asyncio, ruff, locust. Also holds the ruff rules (line length 100) and pytest settings (`testpaths = ["tests"]`, DecompressionBombWarning = error). | ডিপেন্ডেন্সি, ruff ও pytest-এর সেটিং। |
| `uv.lock` | Exact pinned versions; `uv sync` installs exactly these. | হুবহু ভার্সন লক; `uv sync` এগুলোই ইনস্টল করে। |
| `.python-version` | `3.13`; uv uses this Python. | uv কোন Python ব্যবহার করবে। |
| `.env.example` → `.env` | The settings template. Copy it to `.env` and fill it in. `.env` holds your secret key and is git-ignored. | সেটিংসের নমুনা; `.env`-এ কপি করে পূরণ করুন। `.env` গিটে যায় না। |
| `.gitignore` | Ignores `.venv/`, caches, `.env*` (except `.env.example`), `tmp/`, editor folders. | গিট যেসব ফাইল উপেক্ষা করবে। |
| `Dockerfile` | Two stages:<br>• **builder:** python:3.13-slim + uv, `uv sync --frozen --no-dev`.<br>• **runtime:** non-root `app` user, `/tmp/imgproc` with mode 700, `HEALTHCHECK` on `/health/live`, one uvicorn worker with `--proxy-headers --no-access-log`. | দুই ধাপের ইমেজ; root ছাড়া চলে, স্বাস্থ্য পরীক্ষা আছে। |
| `docker-compose.yml` | One `app` service on port 8000 using `.env`.<br>• **Read-only container**; `/tmp` is a 1 GB in-memory `tmpfs`.<br>• `--forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}`.<br>• `restart: unless-stopped`. | একটি সার্ভিস। কন্টেইনার read-only, আপলোড শুধু মেমোরির `/tmp`-এ থাকে। |
| `Makefile` | Shortcuts (see section 9). | শর্টকাট কমান্ড। |
| `README.md` | The user guide: setup, usage, API. | ব্যবহারকারীর গাইড। |

---

## 6. HTTP API reference / API রেফারেন্স

| Method & path | Purpose / কাজ |
|---|---|
| `GET /` | Web page (when `SERVE_FRONTEND=true`). / ওয়েব পেজ। |
| `GET /static/*` | CSS / JS files. |
| `POST /api/v1/images/process` | Process one image. / একটি ছবি প্রসেস। |
| `GET /api/v1/capabilities` | Features and limits. / ফিচার ও সীমা। |
| `GET /health` | Readiness (200 / 503). |
| `GET /health/live` | Liveness (200). |
| `GET /docs`, `/redoc`, `/openapi.json` | Interactive API docs generated by FastAPI. / স্বয়ংক্রিয় API ডকস। |

### `POST /api/v1/images/process` form fields / ফর্ম ফিল্ড

The request is `multipart/form-data`. / রিকোয়েস্টটি `multipart/form-data`।

| Field | Type | Default | Meaning / অর্থ |
|---|---|---|---|
| `image` | file (required / আবশ্যক) | — | JPEG, PNG or WEBP. |
| `target_width`, `target_height` | int | — | Output size in px (≤ `MAX_OUTPUT_DIMENSION`). / আউটপুটের মাপ। |
| `keep_aspect_ratio` | bool | `true` | Fit inside, never crop. / অনুপাত রাখা। |
| `output_format` | `JPEG`/`JPG`/`PNG`/`WEBP` | input format | |
| `quality` | 1–100 | 85 | JPEG/WEBP only. |
| `filter` | name or alias | — | `golden_hour`, `black_and_white`, `vintage`, `warm`, `cool` (+ aliases). |
| `enhance_image` | bool | `false` | Fixed enhancement. |
| `detect_objects` | bool | `false` | Gemini object detection. |
| `brightness`, `contrast`, `saturation` | −100…100 | 0 | API only, not in the page. / শুধু API-তে। |
| `rotate` | 0/90/180/270 | 0 | Clockwise. API only. |
| `flip_horizontal`, `flip_vertical` | bool | `false` | API only. |
| `ai_edit_prompt` | text ≤2000 | — | Needs an edit model. / এডিট মডেল লাগে। |
| `remove_background` | bool | `false` | Needs an edit model; result has a white background, not transparency. / সাদা ব্যাকগ্রাউন্ড, স্বচ্ছ নয়। |

### Examples / উদাহরণ

```bash
# Resize to 800 px wide, WEBP, detect objects (jq is optional, it just trims the output)
curl -s -F image=@photo.jpg -F target_width=800 -F output_format=WEBP -F detect_objects=true \
  http://localhost:8000/api/v1/images/process \
  | jq '{size: .image.size_bytes, subject: .main_subject, objects: [.detected_objects[].label], warnings}'

# Save the processed image to a file / প্রসেস করা ছবি ফাইলে সেভ করা
curl -s -F image=@photo.jpg -F filter=vintage -F output_format=PNG \
  http://localhost:8000/api/v1/images/process \
  | jq -r '.image.data_url' | sed 's/^data:[^,]*,//' | base64 --decode > out.png
```

Success response (shortened) / সফল রেসপন্স (সংক্ষেপে):

```json
{
  "success": true,
  "request_id": "5d0c9e3f8a1b4c6d9e2f7a8b3c4d5e6f",
  "image": {"data_url": "data:image/webp;base64,UklGR…", "download_filename": "photo-processed.webp",
            "format": "WEBP", "width": 800, "height": 600, "size_bytes": 48211, "mime_type": "image/webp"},
  "original": {"filename": "photo.jpg", "format": "JPEG", "width": 4000, "height": 3000,
               "size_bytes": 3145728, "mime_type": "image/jpeg"},
  "main_subject": "a dog on a beach",
  "detected_objects": [
    {"label": "dog", "category": "animal", "description": "A brown dog running.",
     "bounding_box": {"x_min": 160, "y_min": 210, "x_max": 480, "y_max": 540},
     "normalized_bounding_box": {"x_min": 0.2, "y_min": 0.35, "x_max": 0.6, "y_max": 0.9},
     "confidence": null}
  ],
  "processing": {"object_detection_completed": true, "image_enhancement_completed": false,
                 "ai_edit_completed": false},
  "filter_applied": null,
  "warnings": [],
  "ai_models_used": ["gemini-3.8-flash"],
  "duration_ms": 2140
}
```

Every response, success or error, carries an `X-Request-ID` header with the same ID as `request_id`. Quote it when reporting a problem.
প্রতিটি রেসপন্সে (সফল বা এরর) `X-Request-ID` হেডার থাকে, যা `request_id`-এর সমান। সমস্যা জানানোর সময় এটি উল্লেখ করুন।

---

## 7. Error codes and warnings / এরর কোড ও ওয়ার্নিং

### 7.1 Errors (request fails) / এরর (রিকোয়েস্ট ব্যর্থ)

| Code | HTTP | When (English) | কখন (বাংলা) |
|---|---|---|---|
| `BAD_REQUEST` | 400 | The body could not be parsed. | বডি পড়া যায়নি। |
| `NOT_FOUND` | 404 | Unknown URL. | ভুল URL। |
| `METHOD_NOT_ALLOWED` | 405 | Wrong HTTP method. | ভুল HTTP মেথড। |
| `VALIDATION_ERROR` | 422 | Bad option or field, empty file, target size over limits, unknown filter. | ভুল অপশন, খালি ফাইল, সীমার বেশি মাপ, অজানা ফিল্টার। |
| `UNSUPPORTED_FILE_TYPE` | 415 | Content is not JPEG/PNG/WEBP, or the extension is not allowed. | ফাইল JPEG/PNG/WEBP নয়। |
| `FILE_TOO_LARGE` | 413 | Upload/body larger than `MAX_UPLOAD_BYTES`. | ফাইল খুব বড়। |
| `IMAGE_TOO_LARGE` | 413 | Width × height above `MAX_IMAGE_PIXELS`. | পিক্সেল সংখ্যা সীমার বেশি। |
| `OUTPUT_TOO_LARGE` | 422 | The result is above `MAX_OUTPUT_BYTES`. | ফলাফলের ফাইল খুব বড়। |
| `CORRUPTED_IMAGE` | 422 | Cannot be decoded, or truncated. | ফাইল ভাঙা বা অসম্পূর্ণ। |
| `ANIMATED_IMAGE_UNSUPPORTED` | 422 | Animated PNG/WEBP. | অ্যানিমেটেড ছবি সমর্থিত নয়। |
| `FEATURE_NOT_CONFIGURED` | 422 | Detection without a Gemini key, or an edit without an edit model. | ফিচারটি সার্ভারে চালু নেই। |
| `RATE_LIMITED` | 429 | More than `RATE_LIMIT_IP_PER_MINUTE` from your IP (`Retry-After`). | এক মিনিটে অনেক বেশি রিকোয়েস্ট। |
| `TOO_MANY_CONCURRENT_REQUESTS` | 429 | More than `MAX_CONCURRENT_PER_IP` at once (`Retry-After: 2`). | একসাথে অনেকগুলো চলছে। |
| `SERVER_BUSY` | 503 | `MAX_CONCURRENT_REQUESTS` reached (`Retry-After: 5`). | সার্ভার ব্যস্ত। |
| `GEMINI_RATE_LIMITED` | 503 | Gemini quota or rate limit (edit only). | Gemini-র কোটা শেষ (শুধু এডিটে)। |
| `GEMINI_SAFETY_BLOCKED` | 422 | Gemini refused for safety (edit only). | নিরাপত্তার কারণে Gemini অস্বীকার করেছে। |
| `GEMINI_INVALID_RESPONSE` | 502 | Bad, empty or oversized Gemini output (edit only). | Gemini-র উত্তর ভুল বা খালি। |
| `GEMINI_REQUEST_REJECTED` | 502 | Gemini rejected the request (edit only). | Gemini রিকোয়েস্ট নেয়নি। |
| `GEMINI_UNAVAILABLE` | 502 | Gemini is down or unreachable (edit only). | Gemini পাওয়া যাচ্ছে না। |
| `GEMINI_TIMEOUT` | 504 | Gemini timed out (edit only). | Gemini সময়মতো উত্তর দেয়নি। |
| `GEMINI_CONFIGURATION_ERROR` | 503 | Wrong key or model name (edit only). | key বা মডেলের নাম ভুল। |
| `PROCESSING_FAILED` | 500 | The encoded output failed verification. | আউটপুট যাচাইয়ে ব্যর্থ। |
| `PROCESSING_TIMEOUT` | 504 | The pipeline took longer than `REQUEST_TIMEOUT_SECONDS`. | প্রসেসিংয়ে অনেক বেশি সময় লেগেছে। |
| `INTERNAL_ERROR` | 500 | Unexpected bug; details are only in the server log. | অপ্রত্যাশিত সমস্যা; বিস্তারিত শুধু সার্ভার লগে। |

> **Detection never fails a request.** If Gemini detection fails, you still get the image (200), with the warning `OBJECT_DETECTION_FAILED`. The `GEMINI_*` errors above only happen for AI editing.
> **ডিটেকশন কখনো রিকোয়েস্ট ব্যর্থ করে না।** Gemini ডিটেকশন ব্যর্থ হলেও ছবি পাবেন (200), সাথে `OBJECT_DETECTION_FAILED` ওয়ার্নিং। উপরের `GEMINI_*` এররগুলো শুধু AI এডিটে হয়।

### 7.2 Warnings (request succeeds) / ওয়ার্নিং (রিকোয়েস্ট সফল)

| Code | When (English) | কখন (বাংলা) |
|---|---|---|
| `OBJECT_DETECTION_FAILED` | Gemini detection failed; the image is still returned. | ডিটেকশন ব্যর্থ, তবে ছবি ফেরত এসেছে। |
| `INVALID_BOUNDING_BOXES_OMITTED` | Some boxes from Gemini were invalid. Those objects are kept without a box. | কিছু বক্স ভুল ছিল; বস্তু আছে কিন্তু বক্স নেই। |
| `DETECTIONS_TRUNCATED` | More than 50 objects; the rest were dropped. | ৫০টির বেশি বস্তু; বাকিগুলো বাদ। |
| `QUALITY_IGNORED_FOR_PNG` | `quality` was sent with PNG output. | PNG-তে কোয়ালিটি কাজ করে না। |
| `TRANSPARENCY_REMOVED` | JPEG output of an image with transparency; it was filled with white. | JPEG-এ স্বচ্ছতা নেই, তাই সাদা করা হয়েছে। |
| `BACKGROUND_NOT_TRANSPARENT` | `remove_background` produced a white, not transparent, background. | ব্যাকগ্রাউন্ড সাদা, স্বচ্ছ নয়। |

---

## 8. Settings (environment variables) / সেটিংস

Set these in `.env` (local) or in the environment (Docker). Restart the server after changing them.
`.env`-এ (লোকাল) বা environment-এ (Docker) সেট করুন। বদলানোর পর সার্ভার রিস্টার্ট করুন।

| Variable | Default | Meaning (English) | অর্থ (বাংলা) |
|---|---|---|---|
| `APP_NAME` | `AI Image Processing` | Title in `/docs`. | ডকসের শিরোনাম। |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`. | লগের বিস্তারিত মাত্রা। |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated extra browser origins. The built-in page needs none. | অন্য ডোমেইনের ফ্রন্টএন্ডের অনুমতি (কমা দিয়ে)। |
| `SERVE_FRONTEND` | `true` | `false` = API only. | `false` দিলে শুধু API, পেজ নয়। |
| `TEMP_DIR` | `tmp/imgproc` (Docker: `/tmp/imgproc`) | Private scratch folder. | প্রাইভেট টেম্প ফোল্ডার। |
| `GEMINI_API_KEY` | empty | Server-side only. Empty disables detection and editing. | Gemini key; খালি থাকলে AI বন্ধ। |
| `GEMINI_VISION_MODEL` | `gemini-3.8-flash` | Detection model; empty disables detection. | ডিটেকশনের মডেল। |
| `GEMINI_IMAGE_EDIT_MODEL` | empty in code (`.env.example` pre-fills `gemini-nano-banana-2.1`) | Edit model; empty disables editing. Leave it empty unless your Google project has billing, because the free tier returns "limit: 0". | এডিট মডেল। বিলিং চালু না থাকলে খালি রাখুন, কারণ ফ্রি টিয়ারে "limit: 0" আসে। |
| `GEMINI_DETECTION_TIMEOUT_SECONDS` | `60` | HTTP timeout per detection call. | প্রতি ডিটেকশন কলের সময়সীমা। |
| `GEMINI_EDIT_TIMEOUT_SECONDS` | `120` | HTTP timeout per edit call. | প্রতি এডিট কলের সময়সীমা। |
| `GEMINI_MAX_RETRIES` | `3` (0–10) | Extra attempts after the first one. | প্রথমবারের পর কতবার আবার চেষ্টা। |
| `GEMINI_MAX_CONCURRENCY` | `4` | Simultaneous Gemini calls per process. | একসাথে কতগুলো Gemini কল। |
| `GEMINI_QUEUE_TIMEOUT_SECONDS` | `30` | Maximum wait for a free Gemini slot. | Gemini-র খালি জায়গার জন্য সর্বোচ্চ অপেক্ষা। |
| `GEMINI_DETECTION_MAX_SIDE` | `1536` (256–4096) | Longest side of the copy sent for detection. | ডিটেকশনে পাঠানো ছবির সর্বোচ্চ দিক। |
| `GEMINI_EDIT_MAX_SIDE` | `2048` (256–4096) | Longest side of the copy sent for editing. | এডিটে পাঠানো ছবির সর্বোচ্চ দিক। |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MB) | Largest upload. | সর্বোচ্চ আপলোড সাইজ। |
| `MAX_IMAGE_PIXELS` | `40000000` | Largest width × height (bomb guard). | সর্বোচ্চ পিক্সেল সংখ্যা। |
| `MAX_OUTPUT_DIMENSION` | `8192` (16–16383) | Largest output side. | আউটপুটের সর্বোচ্চ দিক। |
| `MAX_OUTPUT_BYTES` | `15728640` (15 MB) | Largest result (it travels inside the JSON). | ফলাফলের সর্বোচ্চ সাইজ। |
| `DEFAULT_QUALITY` | `85` | JPEG/WEBP quality when none is given. | ডিফল্ট কোয়ালিটি। |
| `CPU_WORKERS` | number of CPUs (1–8) | Pillow worker processes. | Pillow worker প্রসেসের সংখ্যা। |
| `MAX_CONCURRENT_REQUESTS` | `16` | Total requests at once. | মোট একসাথে কতগুলো রিকোয়েস্ট। |
| `MAX_CONCURRENT_PER_IP` | `3` | Requests at once per IP. | প্রতি IP-তে একসাথে কতগুলো। |
| `RATE_LIMIT_IP_PER_MINUTE` | `30` | Requests per minute per IP. | প্রতি IP-তে মিনিটে কতগুলো। |
| `REQUEST_TIMEOUT_SECONDS` | `150` | Hard limit for the pipeline. | পাইপলাইনের সর্বোচ্চ সময়। |
| `TEMP_MAX_AGE_SECONDS` | `900` (≥60) | The sweeper deletes leftover folders older than this. | এর চেয়ে পুরোনো পড়ে থাকা ফোল্ডার মোছা হয়। |
| `TEMP_SWEEP_INTERVAL_SECONDS` | `300` (≥10) | How often the sweeper runs. | কতক্ষণ পরপর পরিষ্কার হয়। |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | docker-compose only: proxy IPs whose `X-Forwarded-For` is trusted. | শুধু docker-compose: কোন প্রক্সির IP হেডার বিশ্বাস করা হবে। |

---

## 9. How to run / কীভাবে চালাবেন

### 9.1 Local, with uv / লোকালি uv দিয়ে

```bash
# 1. Get the code / কোড আনুন
git clone <your-repository-url> ai-image-processing
cd ai-image-processing
# Already cloned? Update instead / আগে থেকে থাকলে আপডেট করুন:
git pull

# 2. Install dependencies (Python 3.13 + everything in uv.lock) / ডিপেন্ডেন্সি ইনস্টল
uv sync

# 3. Settings / সেটিংস
cp .env.example .env
#    Put GEMINI_API_KEY=... in .env (optional; without it detection is off).
#    .env-এ GEMINI_API_KEY=... দিন (ঐচ্ছিক; না দিলে ডিটেকশন বন্ধ থাকবে)।
#    Keep GEMINI_IMAGE_EDIT_MODEL= empty unless you have Gemini billing.
#    Gemini বিলিং না থাকলে GEMINI_IMAGE_EDIT_MODEL= খালি রাখুন।

# 4. Run with auto-reload / চালান
make dev                 # = uv run uvicorn app.main:app --reload --port 8000
# or / অথবা
uv run fastapi dev
```

Open / খুলুন: **http://localhost:8000** (page / পেজ) · **http://localhost:8000/docs** (API docs).

### 9.2 Docker (no local Python or uv needed) / Docker (লোকাল Python বা uv লাগবে না)

```bash
git clone <your-repository-url> ai-image-processing && cd ai-image-processing
cp .env.example .env     # add GEMINI_API_KEY if you want detection / চাইলে key দিন
docker compose up --build        # or: make up   (runs in background / ব্যাকগ্রাউন্ডে)
make logs                        # follow logs / লগ দেখুন
make down                        # stop / বন্ধ করুন
```

### 9.3 Other commands / অন্যান্য কমান্ড

| Command | What it does (English) | কী করে (বাংলা) |
|---|---|---|
| `make install` | `uv sync`. | ডিপেন্ডেন্সি ইনস্টল। |
| `make lint` | `uv run ruff check .`. | কোডের মান যাচাই। |
| `make format` | `uv run ruff check . --fix`. | ছোটখাটো সমস্যা নিজে ঠিক করে। |
| `make check-gemini` | Live Gemini check (detection + edit attempt). | Gemini লাইভ পরীক্ষা। |
| `make test` | `uv run pytest -q`. **Currently has nothing to run** (`tests/` is missing, exit 5). | টেস্ট চালায়; **এখন `tests/` নেই**, তাই কিছু চলে না। |
| `curl localhost:8000/health` | Readiness check. | সার্ভার প্রস্তুত কিনা। |
| `curl localhost:8000/api/v1/capabilities` | What is enabled. | কী কী চালু আছে। |

### 9.4 Production notes / প্রোডাকশনের জন্য

**EN.**
- Run **one uvicorn worker per container**; CPU parallelism comes from `CPU_WORKERS`.
- Scale out with more containers behind a load balancer.
- Set `FORWARDED_ALLOW_IPS` to your proxy's IP, so per-IP limits see real client IPs.

**বাংলা।**
- প্রতি কন্টেইনারে **একটি uvicorn worker** চালান; CPU-র সমান্তরাল কাজ আসে `CPU_WORKERS` থেকে।
- বেশি লোড সামলাতে লোড ব্যালান্সারের পেছনে আরও কন্টেইনার যোগ করুন।
- `FORWARDED_ALLOW_IPS`-এ আপনার প্রক্সির IP দিন, যাতে প্রতি-IP সীমা আসল ব্যবহারকারীর IP দেখে।

---

## 10. Troubleshooting / সমস্যা ও সমাধান

| Problem / সমস্যা | Fix (English) | সমাধান (বাংলা) |
|---|---|---|
| `Address already in use` (port 8000) | Another server is running. Stop it, or use `--port 8001`. `lsof -i :8000` shows who holds the port. | অন্য সার্ভার চলছে; সেটা বন্ধ করুন বা অন্য পোর্ট দিন। |
| `uv run fastapi dev` cannot find the app | Run `uv sync` (it installs `fastapi-cli`) from the project root. | প্রজেক্টের মূল ফোল্ডারে `uv sync` চালান। |
| "Gemini isn't configured" / detect checkbox disabled | Set `GEMINI_API_KEY` in `.env` and restart. | `.env`-এ key দিয়ে রিস্টার্ট করুন। |
| Warning `OBJECT_DETECTION_FAILED … rate limited` | Gemini free-tier quota hit; wait a minute. `make check-gemini` tests the key. | Gemini-র ফ্রি কোটা শেষ; একটু অপেক্ষা করুন। |
| AI edit returns errors / "limit: 0" | Image-edit models need billing; keep `GEMINI_IMAGE_EDIT_MODEL` empty. | এডিট মডেলের জন্য বিলিং লাগে; মডেল খালি রাখুন। |
| `422 OUTPUT_TOO_LARGE` | Ask for a smaller size, or JPEG/WEBP instead of PNG. | ছোট মাপ বা JPEG/WEBP নিন। |
| `429` / `503` while uploading many images | Expected backpressure; the page retries by itself. Raise the limits in `.env` if needed. | স্বাভাবিক চাপ-নিয়ন্ত্রণ; পেজ নিজেই আবার চেষ্টা করে। দরকার হলে সীমা বাড়ান। |
| `Cannot connect to the Docker daemon` | Start Docker Desktop (`open -a Docker` on macOS) and retry. | Docker Desktop চালু করুন। |
| `make test` exits with code 5 | `tests/` is missing (see the warning at the top). | `tests/` ফোল্ডার নেই (উপরের সতর্কতা দেখুন)। |
| Something failed with `INTERNAL_ERROR` | Find the `request_id` in the server log (JSON lines) to see the traceback. | সার্ভার লগে `request_id` খুঁজলে বিস্তারিত পাবেন। |
