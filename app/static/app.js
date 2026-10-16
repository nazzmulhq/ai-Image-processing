// Image Light Table: client for POST /api/v1/images/process.
// Every server-provided string is rendered with textContent (never innerHTML).
"use strict";

const API = "/api/v1";
const MAX_PARALLEL = 3;     // matches the server's default per-client limit
const MAX_RETRIES = 4;      // for 429 / 503 with Retry-After
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const TOAST_MS = 2200;

const $ = (id) => document.getElementById(id);
const els = {
  status: $("server-status"),
  form: $("controls"),
  dropzone: $("dropzone"),
  fileInput: $("file-input"),
  tray: $("tray"),
  clearTray: $("clear-tray"),
  maxSize: $("max-size"),
  width: $("target-width"),
  height: $("target-height"),
  keepAspect: $("keep-aspect"),
  format: $("output-format"),
  quality: $("quality"),
  qualityValue: $("quality-value"),
  enhance: $("enhance"),
  filterChips: $("filter-chips"),
  process: $("process"),
  formError: $("form-error"),
  empty: $("empty"),
  prints: $("prints"),
  template: $("print-template"),
  lightbox: $("lightbox"),
  lightboxPhoto: $("lightbox-photo"),
  lightboxClose: $("lightbox-close"),
  toast: $("toast"),
};

let currentFilter = "";

let capabilities = null;
let staged = [];            // { file, url }
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// --- Helpers -------------------------------------------------------------------------
function formatBytes(n) {
  const trim = (x, digits) => x.toFixed(digits).replace(/\.?0+$/, "");
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${trim(n / 1024, 1)} KB`;
  return `${trim(n / 1024 / 1024, 2)} MB`;
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

const FRIENDLY = {
  FILE_TOO_LARGE: "Choose a smaller file.",
  IMAGE_TOO_LARGE: "The image has too many pixels. Resize it before uploading.",
  CORRUPTED_IMAGE: "The file looks damaged. Try exporting it again.",
  ANIMATED_IMAGE_UNSUPPORTED: "Animated images aren't supported. Use a still frame.",
  FEATURE_NOT_CONFIGURED: "Turn this option off, or ask the server owner to configure Gemini.",
  GEMINI_SAFETY_BLOCKED: "Gemini declined this image. Try another image or prompt.",
  RATE_LIMITED: "Too many uploads in a short time. Try again in a minute.",
  PROCESSING_TIMEOUT: "Processing took too long. Try a smaller image.",
  NETWORK: "Check your connection and try again.",
};

let toastTimer = null;
function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { els.toast.hidden = true; }, TOAST_MS);
}

// --- Server capabilities ---------------------------------------------------------------
async function loadCapabilities() {
  try {
    const res = await fetch(`${API}/capabilities`);
    if (!res.ok) throw new Error(String(res.status));
    capabilities = await res.json();
  } catch {
    els.status.dataset.state = "down";
    els.status.textContent = "Can't reach the server. Reload to try again.";
    return;
  }
  els.maxSize.textContent = `, up to ${formatBytes(capabilities.max_upload_bytes)}`;
  els.width.max = els.height.max = capabilities.max_output_dimension;
  els.quality.value = capabilities.default_quality;
  els.qualityValue.textContent = capabilities.default_quality;
  els.quality.disabled = els.format.value === "PNG";

  if (capabilities.object_detection) {
    els.status.dataset.state = "ok";
    els.status.textContent = `Ready: object detection with ${capabilities.vision_model}`;
  } else {
    els.status.dataset.state = "limited";
    els.status.textContent = "Ready: Gemini isn't configured, so only resize, convert and enhance are available";
  }
}

// --- Choosing files --------------------------------------------------------------------
function addFiles(fileList) {
  els.formError.hidden = true;
  const rejected = [];
  let added = 0;
  for (const file of fileList) {
    if (!ACCEPTED.includes(file.type)) { rejected.push(`${file.name} isn't JPEG, PNG or WEBP`); continue; }
    if (capabilities && file.size > capabilities.max_upload_bytes) {
      rejected.push(`${file.name} is larger than ${formatBytes(capabilities.max_upload_bytes)}`);
      continue;
    }
    staged.push({ file, url: URL.createObjectURL(file) });
    added++;
  }
  if (rejected.length) showFormError(`Skipped: ${rejected.join("; ")}.`);
  renderTray();
  return added;
}

function renderTray() {
  els.tray.replaceChildren(...staged.map((item, index) => {
    const li = document.createElement("li");
    const img = document.createElement("img");
    img.src = item.url;
    img.alt = item.file.name;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Remove ${item.file.name}`);
    remove.addEventListener("click", () => {
      URL.revokeObjectURL(item.url);
      staged.splice(index, 1);
      renderTray();
    });
    li.append(img, remove);
    return li;
  }));
  const n = staged.length;
  els.process.disabled = n === 0;
  els.process.textContent = n === 0 ? "Process images" : n === 1 ? "Process 1 image" : `Process ${n} images`;
  els.clearTray.hidden = n < 2;
}

function showFormError(message) {
  els.formError.textContent = message;
  els.formError.hidden = false;
}

function readOptions() {
  const fields = {};
  if (els.width.value) fields.target_width = els.width.value;
  if (els.height.value) fields.target_height = els.height.value;
  if (!els.keepAspect.checked) fields.keep_aspect_ratio = "false";
  if (els.format.value) fields.output_format = els.format.value;
  if (els.format.value !== "PNG") fields.quality = els.quality.value;
  if (els.enhance.checked) fields.enhance_image = "true";
  // Always detect objects whenever the server has Gemini configured.
  if (capabilities?.object_detection) fields.detect_objects = "true";

  if (currentFilter) fields.filter = currentFilter;

  return fields;
}

// --- Uploading -------------------------------------------------------------------------
function upload(file, fields, onProgress) {
  return new Promise((resolve) => {
    const form = new FormData();
    form.append("image", file);
    for (const [k, v] of Object.entries(fields)) form.append(k, v);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/images/process`);
    xhr.responseType = "json";
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    });
    xhr.upload.addEventListener("load", () => onProgress(1));
    xhr.addEventListener("load", () => resolve({
      status: xhr.status,
      body: xhr.response,
      retryAfter: Number(xhr.getResponseHeader("Retry-After")) || null,
    }));
    xhr.addEventListener("error", () => resolve({ status: 0, body: null, retryAfter: null }));
    xhr.send(form);
  });
}

async function processOne(item, fields, view) {
  for (let attempt = 0; ; attempt++) {
    view.setProgress("Uploading…", 0);
    const res = await upload(item.file, fields, (p) => {
      view.setProgress(p < 1 ? `Uploading ${Math.round(p * 100)}%` : "Processing…", p);
    });
    if (res.status === 200 && res.body && res.body.success) {
      view.showResult(res.body);
      return;
    }
    const retryable = res.status === 503 ||
      (res.status === 429 && res.body?.error?.code !== "RATE_LIMITED");
    if (retryable && attempt < MAX_RETRIES) {
      const wait = res.retryAfter ?? 2 ** attempt;
      view.setProgress(`Server busy, retrying in ${wait}s…`, 1, true);
      await sleep(wait * 1000);
      continue;
    }
    view.showError(res.status === 0
      ? { code: "NETWORK", message: "The upload didn't reach the server." }
      : res.body?.error ?? { code: `HTTP_${res.status}`, message: "The server returned an unexpected response." },
      res.body?.request_id, () => processOne(item, fields, view));
    return;
  }
}

async function runQueue(items, fields) {
  const queue = items.map((item) => ({ item, view: createPrint(item) }));
  // Bring the newest result into view (it is first in the list).
  els.prints.firstElementChild?.scrollIntoView({
    behavior: reduceMotion ? "auto" : "smooth", block: "start",
  });
  let next = 0;
  async function worker() {
    while (next < queue.length) {
      const { item, view } = queue[next++];
      await processOne(item, fields, view);
    }
  }
  await Promise.all(Array.from({ length: Math.min(MAX_PARALLEL, queue.length) }, worker));
}

// --- Photo crossfade -------------------------------------------------------------------
function swapPhoto(img, src, alt) {
  if (reduceMotion) {
    img.src = src;
    img.alt = alt;
    return;
  }
  img.dataset.fade = "true";
  const apply = () => {
    img.src = src;
    img.alt = alt;
    requestAnimationFrame(() => { delete img.dataset.fade; });
  };
  setTimeout(apply, 160);
}

// --- Lightbox ----------------------------------------------------------------------------
let lightboxReturnFocus = null;
function openLightbox(src, alt, trigger) {
  lightboxReturnFocus = trigger;
  els.lightboxPhoto.src = src;
  els.lightboxPhoto.alt = alt;
  els.lightbox.hidden = false;
  document.body.classList.add("lightbox-open");
  els.lightboxClose.focus();
}
function closeLightbox() {
  els.lightbox.hidden = true;
  els.lightboxPhoto.src = "";
  document.body.classList.remove("lightbox-open");
  lightboxReturnFocus?.focus();
  lightboxReturnFocus = null;
}
els.lightboxClose.addEventListener("click", closeLightbox);
els.lightbox.addEventListener("click", (e) => { if (e.target === els.lightbox) closeLightbox(); });
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !els.lightbox.hidden) closeLightbox();
});

// --- Copy to clipboard -------------------------------------------------------------------
const CAN_COPY_IMAGES = Boolean(navigator.clipboard?.write && window.ClipboardItem);

async function copyImageToClipboard(dataUrl) {
  // Re-encode to PNG via canvas first: clipboard image writes are most reliably
  // supported for image/png across browsers, regardless of the source format.
  const source = await new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = dataUrl;
  });
  const canvas = document.createElement("canvas");
  canvas.width = source.naturalWidth;
  canvas.height = source.naturalHeight;
  canvas.getContext("2d").drawImage(source, 0, 0);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
}

// --- Rendering a result ------------------------------------------------------------------
function createPrint(item) {
  els.empty.hidden = true;
  const node = els.template.content.firstElementChild.cloneNode(true);
  const q = (sel) => node.querySelector(sel);
  const photo = q(".photo");
  const marks = q(".marks");
  const zoom = q(".zoom");
  const developing = q(".developing");
  const developingText = q(".developing-text");
  const barFill = q(".bar-fill");
  const actions = q(".print-actions");
  const toggle = q(".toggle-original");
  const copyBtn = q(".copy-image");
  const download = q(".download");

  q(".print-title").textContent = item.file.name;
  photo.src = item.url;  // show the original while it develops
  photo.alt = `Original: ${item.file.name}`;
  els.prints.prepend(node);

  let resultUrl = null;
  let showingResult = false;

  zoom.hidden = false;
  zoom.addEventListener("click", () => openLightbox(photo.src, photo.alt, zoom));
  if (!CAN_COPY_IMAGES) copyBtn.remove();

  function setProgress(text, fraction, indeterminate = false) {
    developingText.textContent = text;
    barFill.style.width = `${Math.round(fraction * 100)}%`;
    barFill.toggleAttribute("data-indeterminate", indeterminate);
  }

  function showResult(body) {
    const { image } = body;
    developing.hidden = true;
    resultUrl = image.data_url;
    showingResult = true;
    swapPhoto(photo, resultUrl, `Processed: ${item.file.name}`);
    download.href = resultUrl;
    download.download = image.download_filename;
    download.textContent = `Download ${image.format}`;
    actions.hidden = false;

    if (body.main_subject) {
      const subject = q(".subject");
      subject.textContent = body.main_subject;
      subject.hidden = false;
    }
    renderFacts(q(".facts"), body);
    renderFlags(q(".flags"), body);
    renderObjects(q(".objects"), marks, body.detected_objects);
    renderWarnings(q(".warnings"), body.warnings);

    toggle.addEventListener("click", () => {
      showingResult = !showingResult;
      toggle.setAttribute("aria-pressed", String(!showingResult));
      toggle.textContent = showingResult ? "Show original" : "Show result";
      swapPhoto(photo, showingResult ? resultUrl : item.url,
        `${showingResult ? "Processed" : "Original"}: ${item.file.name}`);
      marks.hidden = !showingResult;
    });

    copyBtn?.addEventListener("click", async () => {
      try {
        await copyImageToClipboard(resultUrl);
        showToast("Copied image to clipboard");
      } catch {
        showToast("Couldn't copy the image");
      }
    });
  }

  function showError(error, requestId, retry) {
    developing.hidden = true;
    photo.style.opacity = "0.35";
    zoom.hidden = true;
    const box = q(".error");
    const title = document.createElement("strong");
    title.textContent = error.message || "Processing failed.";
    const hint = document.createElement("p");
    hint.textContent = [FRIENDLY[error.code], requestId ? `Reference: ${requestId}` : null]
      .filter(Boolean).join(" ");
    const children = [title, hint];
    if (retry) {
      const retryBtn = document.createElement("button");
      retryBtn.type = "button";
      retryBtn.className = "retry";
      retryBtn.textContent = "Try again";
      retryBtn.addEventListener("click", () => {
        box.hidden = true;
        photo.style.opacity = "";
        developing.hidden = false;
        retry();
      });
      children.push(retryBtn);
    }
    box.replaceChildren(...children);
    box.hidden = false;
  }

  return { setProgress, showResult, showError };
}

function renderFacts(dl, body) {
  const { image, original } = body;
  const rows = [
    ["Size", `${image.width} × ${image.height} px`,
      original.width !== image.width || original.height !== image.height
        ? `was ${original.width} × ${original.height}` : null],
    ["Format", image.format, original.format !== image.format ? `was ${original.format}` : null],
    ["File size", formatBytes(image.size_bytes), `was ${formatBytes(original.size_bytes)}`],
    ["Time", `${(body.duration_ms / 1000).toFixed(1)} s`, null],
  ];
  for (const [term, value, before] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = before ? `${value} (${before})` : value;
    dl.append(dt, dd);
  }
  dl.hidden = false;
}

function renderFlags(ul, body) {
  const p = body.processing;
  const flags = [];
  if (p.object_detection_completed) flags.push(`${body.detected_objects.length} objects found`);
  if (p.image_enhancement_completed) flags.push("Enhanced");
  if (p.ai_edit_completed) flags.push("Edited by AI");
  for (const text of flags) {
    const li = document.createElement("li");
    li.textContent = text;
    ul.append(li);
  }
  ul.hidden = flags.length === 0;
}

function renderObjects(list, marks, objects) {
  if (!objects.length) return;
  objects.forEach((obj, i) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.className = "object-name";
    name.textContent = obj.label;
    if (obj.category) {
      const cat = document.createElement("small");
      cat.textContent = obj.category;
      name.append(cat);
    }
    li.append(name);
    if (obj.description) {
      const desc = document.createElement("span");
      desc.className = "object-desc";
      desc.textContent = obj.description;
      li.append(desc);
    }

    const box = obj.normalized_bounding_box;
    if (box) {
      // Only draw a mark when the server returned a validated box; never invent one.
      const mark = document.createElement("div");
      mark.className = "mark";
      mark.style.left = `${box.x_min * 100}%`;
      mark.style.top = `${box.y_min * 100}%`;
      mark.style.width = `${(box.x_max - box.x_min) * 100}%`;
      mark.style.height = `${(box.y_max - box.y_min) * 100}%`;
      if (box.y_min < 0.08) mark.dataset.below = "true";
      const label = document.createElement("span");
      label.className = "mark-label";
      label.textContent = obj.label;
      mark.append(label);
      marks.append(mark);

      li.dataset.hasBox = "true";
      li.tabIndex = 0;
      const on = () => { mark.dataset.active = "true"; li.dataset.active = "true"; };
      const off = () => { delete mark.dataset.active; delete li.dataset.active; };
      li.addEventListener("mouseenter", on);
      li.addEventListener("mouseleave", off);
      li.addEventListener("focus", on);
      li.addEventListener("blur", off);
    } else {
      const none = document.createElement("span");
      none.className = "object-nobox";
      none.textContent = "No location given";
      li.append(none);
    }
    li.setAttribute("aria-label", `${i + 1}. ${obj.label}`);
    list.append(li);
  });
  list.hidden = false;
}

function renderWarnings(ul, warnings) {
  for (const w of warnings) {
    const li = document.createElement("li");
    li.textContent = w.message;
    ul.append(li);
  }
  ul.hidden = warnings.length === 0;
}

// --- Wiring ------------------------------------------------------------------------------
els.fileInput.addEventListener("change", () => {
  addFiles(els.fileInput.files);
  els.fileInput.value = "";
});

for (const type of ["dragenter", "dragover"]) {
  els.dropzone.addEventListener(type, (e) => {
    e.preventDefault();
    els.dropzone.dataset.over = "true";
  });
}
for (const type of ["dragleave", "drop"]) {
  els.dropzone.addEventListener(type, (e) => {
    e.preventDefault();
    els.dropzone.dataset.over = "false";
  });
}
els.dropzone.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
// Dropping anywhere else on the page shouldn't navigate away.
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

// Paste an image from the clipboard anywhere on the page (not while typing in a field).
window.addEventListener("paste", (e) => {
  const target = e.target;
  const typing = target instanceof HTMLElement &&
    (target.tagName === "TEXTAREA" || target.tagName === "INPUT");
  if (typing) return;
  const files = Array.from(e.clipboardData?.files ?? []).filter((f) => ACCEPTED.includes(f.type));
  if (!files.length) return;
  e.preventDefault();
  const added = addFiles(files);
  if (added) showToast(added === 1 ? "Pasted 1 image" : `Pasted ${added} images`);
});

els.clearTray.addEventListener("click", () => {
  for (const item of staged) URL.revokeObjectURL(item.url);
  staged = [];
  renderTray();
});

els.quality.addEventListener("input", () => { els.qualityValue.textContent = els.quality.value; });
els.format.addEventListener("change", () => { els.quality.disabled = els.format.value === "PNG"; });

if (els.filterChips) {
  els.filterChips.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    els.filterChips.querySelectorAll(".chip").forEach((c) => {
      c.classList.remove("active");
      c.setAttribute("aria-pressed", "false");
    });
    chip.classList.add("active");
    chip.setAttribute("aria-pressed", "true");
    currentFilter = chip.dataset.filter || "";
  });
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!staged.length) return;
  els.formError.hidden = true;
  const items = staged;
  staged = [];
  renderTray();
  runQueue(items, readOptions());
});

loadCapabilities();
