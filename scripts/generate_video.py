#!/usr/bin/env python3
"""
Generate videos using Gemini Veo 3.1 API.

Requires: requests (pip install requests)

Usage:
    python3 generate_video.py --prompt "description" --filename "output.mp4" \
        [--reference_image path1 path2] [--reference_video path] \
        [--first_frame path] [--last_frame path] \
        [--resolution 720p|1080p|4k] [--ratio 16:9|9:16] [--duration 8]
"""

import argparse
import base64
import mimetypes
import os
import sys
import time
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
POLL_INTERVAL = 10
TIMEOUT = 1800

SUPPORTED_IMAGE_EXTS = {".jpeg", ".jpg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
SUPPORTED_VIDEO_EXTS = {".mp4", ".mov"}


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


def resolve_media(path_or_url, media_type="image"):
    """Resolve a path or URL to inlineData dict {"mimeType": ..., "data": base64}.

    For local files, read and base64-encode directly.
    For URLs, download first, then base64-encode.
    """
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        print(f"Downloading {media_type}: {path_or_url}", file=sys.stderr)
        try:
            resp = requests.get(path_or_url, timeout=120)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error downloading {path_or_url}: {e}", file=sys.stderr)
            sys.exit(1)
        mime_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not mime_type:
            mime_type = "image/png" if media_type == "image" else "video/mp4"
        data = base64.b64encode(resp.content).decode()
        return {"mimeType": mime_type, "data": data}

    path = Path(path_or_url)
    if not path.exists():
        print(f"Error: File not found: {path_or_url}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if media_type == "image" and ext not in SUPPORTED_IMAGE_EXTS:
        print(f"Error: Unsupported image format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTS))}", file=sys.stderr)
        sys.exit(1)
    elif media_type == "video" and ext not in SUPPORTED_VIDEO_EXTS:
        print(f"Error: Unsupported video format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_VIDEO_EXTS))}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(str(path))[0]
    if not mime_type:
        defaults = {"image": "image/png", "video": "video/mp4"}
        mime_type = defaults.get(media_type, "application/octet-stream")

    data = base64.b64encode(path.read_bytes()).decode()
    print(f"Loaded {media_type}: {path_or_url}", file=sys.stderr)
    return {"mimeType": mime_type, "data": data}


def build_request(args):
    """Build the API request body."""
    instance = {"prompt": args.prompt}

    if args.first_frame:
        instance["image"] = {"inlineData": resolve_media(args.first_frame, "image")}

    if args.last_frame:
        instance["lastFrame"] = {"inlineData": resolve_media(args.last_frame, "image")}

    if args.reference_image:
        ref_images = []
        for img_path in args.reference_image:
            ref_images.append({
                "image": {"inlineData": resolve_media(img_path, "image")},
                "referenceType": "asset",
            })
        instance["referenceImages"] = ref_images

    if args.reference_video:
        instance["video"] = {"inlineData": resolve_media(args.reference_video, "video")}

    parameters = {
        "aspectRatio": args.ratio,
        "durationSeconds": args.duration,
        "resolution": args.resolution,
        "numberOfVideos": 1,
    }

    return {"instances": [instance], "parameters": parameters}


def submit_task(base_url, api_key, model, request_body):
    """Submit a video generation task. Returns the operation name."""
    url = f"{base_url}/v1beta/models/{model}:predictLongRunning"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    print(f"Submitting generation task...", file=sys.stderr)

    try:
        resp = requests.post(url, json=request_body, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"API error {e.response.status_code}: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)

    operation_name = result.get("name")
    if not operation_name:
        print(f"Error: No operation name in response: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"Task submitted: {operation_name}", file=sys.stderr)
    return operation_name


def poll_task(base_url, api_key, operation_name):
    """Poll task status until completion. Returns the response dict on success."""
    url = f"{base_url}/v1beta/{operation_name}"
    headers = {
        "x-goog-api-key": api_key,
    }

    start_time = time.time()
    consecutive_errors = 0

    while True:
        elapsed = int(time.time() - start_time)
        if elapsed > TIMEOUT:
            print(f"Error: Timeout after {TIMEOUT}s", file=sys.stderr)
            sys.exit(1)

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print(f"Error: {consecutive_errors} consecutive poll failures: {e}", file=sys.stderr)
                sys.exit(1)
            print(f"[{elapsed}s] Poll error (attempt {consecutive_errors}/3): {e}", file=sys.stderr)
            time.sleep(POLL_INTERVAL)
            continue

        is_done = result.get("done", False)
        print(f"[{elapsed}s] Done: {is_done}", file=sys.stderr)

        if is_done:
            error = result.get("error")
            if error:
                print(f"Error: Task failed - {error.get('code', 'unknown')}: {error.get('message', 'no details')}", file=sys.stderr)
                sys.exit(1)
            return result

        time.sleep(POLL_INTERVAL)


def download_video(video_uri, api_key, output_path):
    """Download the generated video to the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading video...", file=sys.stderr)
    try:
        headers = {"x-goog-api-key": api_key}
        resp = requests.get(video_uri, headers=headers, stream=True, timeout=300, allow_redirects=True)
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"Error downloading video: {e}", file=sys.stderr)
        sys.exit(1)

    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Video saved: {path.resolve()} ({size_mb:.1f}MB)", file=sys.stderr)
    return str(path.resolve())


def main():
    parser = argparse.ArgumentParser(description="Generate videos via Gemini Veo 3.1 API")
    parser.add_argument("--prompt", "-p", required=True, help="Video description prompt")
    parser.add_argument("--reference_image", nargs="+", help="Reference image path(s) or URL(s), up to 3")
    parser.add_argument("--reference_video", help="Video to extend (single path or URL)")
    parser.add_argument("--first_frame", help="First frame image path or URL")
    parser.add_argument("--last_frame", help="Last frame image path or URL")
    parser.add_argument("--resolution", choices=["720p", "1080p", "4k"], default="720p",
                        help="Output resolution (default: 720p)")
    parser.add_argument("--ratio", choices=["16:9", "9:16"], default="16:9",
                        help="Aspect ratio (default: 16:9)")
    parser.add_argument("--duration", default="8",
                        help="Video duration in seconds: 4, 5, 6, 8 (default: 8)")
    parser.add_argument("--filename", "-f", required=True, help="Output file path")

    args = parser.parse_args()

    base_url, api_key = get_config()
    model = select_model(args)
    request_body = build_request(args)
    operation_name = submit_task(base_url, api_key, model, request_body)
    result = poll_task(base_url, api_key, operation_name)

    try:
        video_uri = result["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
    except (KeyError, IndexError):
        print(f"Error: No video URI in response: {result}", file=sys.stderr)
        sys.exit(1)

    saved_path = download_video(video_uri, api_key, args.filename)
    print(saved_path)


if __name__ == "__main__":
    main()
