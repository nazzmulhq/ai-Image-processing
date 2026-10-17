"""Live smoke test of the configured Gemini models (uses GEMINI_API_KEY; costs a few tokens).

    uv run python scripts/check_gemini.py                 # built-in test image
    uv run python scripts/check_gemini.py --image my.jpg  # use your own image

Verifies that the installed google-genai SDK, your API key and the model name in
GEMINI_VISION_MODEL work with the call this service makes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw

from app.core.config import get_settings
from app.services.gemini_service import GeminiError, GoogleGeminiService
from app.services.image_processing_service import encode_for_model


def sample_image() -> Image.Image:
    image = Image.new("RGB", (640, 480), (235, 235, 235))
    draw = ImageDraw.Draw(image)
    draw.ellipse((60, 120, 260, 320), fill=(220, 30, 30))       # red circle
    draw.rectangle((360, 100, 580, 380), fill=(30, 60, 200))    # blue square
    return image


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.gemini_configured:
        print("GEMINI_API_KEY is not set.", file=sys.stderr)
        return 1
    print(f"google-genai {version('google-genai')}")
    image = Image.open(args.image).convert("RGB") if args.image else sample_image()
    service = GoogleGeminiService.from_settings(settings)
    try:
        data, mime = encode_for_model(image, max_side=settings.gemini_detection_max_side)
        print(f"\n[detect] model={settings.gemini_vision_model}")
        try:
            result = await service.detect_objects(data, mime)
        except GeminiError as err:
            print(f"  FAILED: {err.code}: {err.message}  (cause: {err.__cause__!r})")
            return 2
        print(f"  main_subject: {result.main_subject}")
        for obj in result.objects:
            box = (f"({obj.box.x_min:.3f},{obj.box.y_min:.3f})-({obj.box.x_max:.3f},"
                   f"{obj.box.y_max:.3f})" if obj.box else "no box")
            print(f"  - {obj.label} [{obj.category}] {box}")
        print(f"  invalid boxes dropped: {result.invalid_boxes}")
        return 0
    finally:
        await service.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", type=Path, help="image file to send (default: synthetic)")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
