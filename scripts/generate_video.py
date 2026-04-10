#!/usr/bin/env python3
"""
Generate videos using Gemini Veo 3.1 API (generateContent endpoint).

Requires: requests (pip install requests)

Usage:
    python3 generate_video.py --prompt "description" --filename "output.mp4" \
        [--reference_image path1 path2] \
        [--first_frame path] [--last_frame path] \
        [--ratio 16:9|9:16]
"""

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path

import requests

MODELS = {
    ("t2v", "16:9"): "veo_3_1_t2v_fast_ultra_relaxed",
    ("t2v", "9:16"): "veo_3_1_t2v_fast_portrait_ultra_relaxed",
    ("i2v", "16:9"): "veo_3_1_i2v_s_fast_ultra_relaxed",
    ("i2v", "9:16"): "veo_3_1_i2v_s_fast_portrait_ultra_relaxed",
    ("r2v", "16:9"): "veo_3_1_r2v_fast_ultra_relaxed",
    ("r2v", "9:16"): "veo_3_1_r2v_fast_portrait_ultra_relaxed",
}

SUPPORTED_IMAGE_EXTS = {".jpeg", ".jpg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif"}


def get_config():
    base_url = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(1)
    return base_url.rstrip("/"), api_key


def select_model(args):
    """Auto-select model based on input mode and aspect ratio."""
    if args.first_frame or args.last_frame:
        mode = "i2v"
    elif args.reference_image:
        mode = "r2v"
    else:
        mode = "t2v"

    key = (mode, args.ratio)
    model = MODELS.get(key)
    if not model:
        print(f"Error: No model for mode={mode}, ratio={args.ratio}", file=sys.stderr)
        sys.exit(1)

    print(f"Mode: {mode}, Model: {model}", file=sys.stderr)
    return model


def resolve_media_part(path_or_url, media_type="image"):
    """Resolve a path or URL to an API part dict.

    For URLs: returns {"fileData": {"mimeType": ..., "fileUri": ...}}
    For local files: returns {"inlineData": {"mimeType": ..., "data": base64...}}
    """
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        mime_type = mimetypes.guess_type(path_or_url.split("?")[0])[0]
        if not mime_type:
            mime_type = "image/jpeg" if media_type == "image" else "video/mp4"
        print(f"Using URL {media_type}: {path_or_url}", file=sys.stderr)
        return {"fileData": {"mimeType": mime_type, "fileUri": path_or_url}}

    path = Path(path_or_url)
    if not path.exists():
        print(f"Error: File not found: {path_or_url}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if media_type == "image" and ext not in SUPPORTED_IMAGE_EXTS:
        print(f"Error: Unsupported image format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTS))}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(str(path))[0]
    if not mime_type:
        mime_type = "image/png" if media_type == "image" else "video/mp4"

    data = base64.b64encode(path.read_bytes()).decode()
    print(f"Loaded {media_type}: {path_or_url}", file=sys.stderr)
    return {"inlineData": {"mimeType": mime_type, "data": data}}


def build_request(args):
    """Build the generateContent request body."""
    parts = [{"text": args.prompt}]

    # I2V mode: first frame then optionally last frame (order matters)
    if args.first_frame:
        parts.append(resolve_media_part(args.first_frame, "image"))
    if args.last_frame:
        parts.append(resolve_media_part(args.last_frame, "image"))

    # R2V mode: reference images (up to 3)
    if args.reference_image:
        for img_path in args.reference_image:
            parts.append(resolve_media_part(img_path, "image"))

    return {
        "contents": [{
            "role": "user",
            "parts": parts,
        }]
    }


def generate(base_url, api_key, model, request_body):
    """Call generateContent and return the response."""
    url = f"{base_url}/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    print(f"Generating video...", file=sys.stderr)

    try:
        resp = requests.post(url, json=request_body, headers=headers, timeout=1800)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"API error {e.response.status_code}: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)


def save_video(result, api_key, output_path):
    """Extract and save video from the generateContent response."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        candidates = result.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates in response: {result}")

        parts = candidates[0].get("content", {}).get("parts", [])

        for part in parts:
            # base64 inline video
            if "inlineData" in part:
                inline = part["inlineData"]
                video_data = base64.b64decode(inline["data"])
                with open(path, "wb") as f:
                    f.write(video_data)
                size_mb = path.stat().st_size / (1024 * 1024)
                print(f"Video saved: {path.resolve()} ({size_mb:.1f}MB)", file=sys.stderr)
                return str(path.resolve())

            # file URI to download
            if "fileData" in part:
                file_uri = part["fileData"]["fileUri"]
                print(f"Downloading video from URI...", file=sys.stderr)
                headers = {"x-goog-api-key": api_key}
                resp = requests.get(file_uri, headers=headers, stream=True, timeout=300, allow_redirects=True)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                size_mb = path.stat().st_size / (1024 * 1024)
                print(f"Video saved: {path.resolve()} ({size_mb:.1f}MB)", file=sys.stderr)
                return str(path.resolve())

        raise ValueError(f"No video data in response parts: {parts}")

    except Exception as e:
        print(f"Error: Could not extract video from response: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate videos via Gemini Veo 3.1 API")
    parser.add_argument("--prompt", "-p", required=True, help="Video description prompt")
    parser.add_argument("--reference_image", nargs="+", help="Reference image path(s) or URL(s), up to 3")
    parser.add_argument("--first_frame", help="First frame image path or URL")
    parser.add_argument("--last_frame", help="Last frame image path or URL")
    parser.add_argument("--ratio", choices=["16:9", "9:16"], default="16:9",
                        help="Aspect ratio (default: 16:9)")
    parser.add_argument("--filename", "-f", required=True, help="Output file path")

    args = parser.parse_args()

    base_url, api_key = get_config()
    model = select_model(args)
    request_body = build_request(args)
    result = generate(base_url, api_key, model, request_body)

    saved_path = save_video(result, api_key, args.filename)
    print(saved_path)


if __name__ == "__main__":
    main()
