#!/usr/bin/env python3
"""
Generate videos using the Veo 3.1 video API.

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
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

DEFAULT_MODEL = "veo-3-1"
DEFAULT_REQUEST_DURATION = 8
MODEL_REQUEST_DURATIONS = {
    "veo-omni-flash": 10,
}
POLL_INTERVAL = 10
TIMEOUT = 1800

SUPPORTED_IMAGE_EXTS = {".jpeg", ".jpg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif"}


def get_config():
    base_url = os.environ.get("VIDEO_API_BASE")
    api_key = os.environ.get("VIDEO_API_KEY")
    model = os.environ.get("VIDEO_MODEL") or DEFAULT_MODEL
    missing = [
        name for name, value in (
            ("VIDEO_API_BASE", base_url),
            ("VIDEO_API_KEY", api_key),
        ) if not value
    ]
    if missing:
        print(f"Error: Required environment variable(s) not set: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return base_url.rstrip("/"), api_key, model


def validate_args(args):
    """Validate CLI arguments for the /v1/videos API."""
    if args.reference_video:
        print("Error: --reference_video is not supported by the new /v1/videos API", file=sys.stderr)
        sys.exit(1)
    if args.resolution:
        print("Error: --resolution is not supported by the new /v1/videos API", file=sys.stderr)
        sys.exit(1)
    if args.person_generation:
        print("Error: --person_generation is not supported by the new /v1/videos API", file=sys.stderr)
        sys.exit(1)
    if args.last_frame and not args.first_frame:
        print("Error: --last_frame requires --first_frame", file=sys.stderr)
        sys.exit(1)
    if args.reference_image and (args.first_frame or args.last_frame):
        print("Error: --reference_image cannot be combined with --first_frame/--last_frame", file=sys.stderr)
        sys.exit(1)
    if args.reference_image and len(args.reference_image) > 3:
        print("Error: --reference_image supports at most 3 images", file=sys.stderr)
        sys.exit(1)

    if args.reference_image:
        mode = "r2v"
    elif args.first_frame:
        mode = "i2v"
    else:
        mode = "t2v"

    return mode


def request_duration_for_model(model):
    return MODEL_REQUEST_DURATIONS.get(model, DEFAULT_REQUEST_DURATION)


def infer_image_mime_type(path_or_url, fallback="image/png"):
    parsed = urlparse(path_or_url)
    path = parsed.path if parsed.scheme else path_or_url
    mime_type = mimetypes.guess_type(path)[0]
    if mime_type and mime_type.startswith("image/"):
        return mime_type
    return fallback


def resolve_image_data_uri(path_or_url):
    """Resolve a path, URL, or existing data URI to data:image/...;base64,..."""
    if path_or_url.startswith("data:image/"):
        return path_or_url

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        print(f"Downloading image: {path_or_url}", file=sys.stderr)
        try:
            resp = requests.get(path_or_url, timeout=120)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error downloading {path_or_url}: {e}", file=sys.stderr)
            sys.exit(1)
        mime_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not mime_type.startswith("image/"):
            mime_type = infer_image_mime_type(path_or_url)
        data = base64.b64encode(resp.content).decode()
        return f"data:{mime_type};base64,{data}"

    path = Path(path_or_url)
    if not path.exists():
        print(f"Error: File not found: {path_or_url}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTS:
        print(f"Error: Unsupported image format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTS))}", file=sys.stderr)
        sys.exit(1)

    mime_type = infer_image_mime_type(str(path))
    data = base64.b64encode(path.read_bytes()).decode()
    print(f"Loaded image: {path_or_url}", file=sys.stderr)
    return f"data:{mime_type};base64,{data}"


def build_request(args, model):
    """Build the API request body."""
    request_body = {
        "model": model,
        "prompt": args.prompt,
        "aspect_ratio": args.ratio,
        "duration": request_duration_for_model(model),
    }

    if args.first_frame:
        images = [resolve_image_data_uri(args.first_frame)]
        if args.last_frame:
            images.append(resolve_image_data_uri(args.last_frame))
        request_body["images"] = images

    if args.reference_image:
        request_body["Ingredients_images"] = [
            resolve_image_data_uri(img_path) for img_path in args.reference_image
        ]

    return request_body


def auth_headers(api_key, content_type=None):
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def submit_task(base_url, api_key, request_body):
    """Submit a video generation task. Returns the initial task response."""
    url = f"{base_url}/v1/videos"
    headers = auth_headers(api_key, "application/json")

    print("Submitting generation task...", file=sys.stderr)

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

    task_id = result.get("task_id") or result.get("id")
    if not task_id:
        print(f"Error: No task_id in response: {result}", file=sys.stderr)
        sys.exit(1)

    status = result.get("status", "unknown")
    progress = result.get("progress", 0)
    print(f"Task submitted: {task_id} ({status}, {progress}%)", file=sys.stderr)
    return result


def fail_with_task_error(result):
    error = result.get("error") or {}
    if isinstance(error, dict):
        message = error.get("message", "no details")
        code = error.get("code", "task_failed")
    else:
        message = str(error)
        code = "task_failed"
    print(f"Error: Task failed - {code}: {message}", file=sys.stderr)
    sys.exit(1)


def poll_task(base_url, api_key, task_id):
    """Poll task status until completion. Returns the response dict on success."""
    url = f"{base_url}/v1/videos/{task_id}"
    headers = auth_headers(api_key)

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

        status = result.get("status", "unknown")
        progress = result.get("progress")
        progress_text = f", {progress}%" if progress is not None else ""
        print(f"[{elapsed}s] Status: {status}{progress_text}", file=sys.stderr)

        if status == "completed":
            return result
        if status == "failed":
            fail_with_task_error(result)

        time.sleep(POLL_INTERVAL)


def extract_video_url(result):
    for key in ("video_url", "url"):
        if result.get(key):
            return result[key]

    metadata = result.get("metadata") or {}
    result_urls = metadata.get("result_urls") or []
    if result_urls:
        return result_urls[0]

    print(f"Error: No video URL in response: {result}", file=sys.stderr)
    sys.exit(1)


def download_video(video_url, output_path):
    """Download the generated video to the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    print("Downloading video...", file=sys.stderr)
    try:
        resp = requests.get(video_url, stream=True, timeout=300, allow_redirects=True)
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
    parser = argparse.ArgumentParser(description="Generate videos via Veo 3.1 video API")
    parser.add_argument("--prompt", "-p", required=True, help="Video description prompt")
    parser.add_argument("--reference_image", nargs="+", help="Reference image path(s), URL(s), or data URI(s), up to 3")
    parser.add_argument("--reference_video", help=argparse.SUPPRESS)
    parser.add_argument("--first_frame", help="First frame image path, URL, or data URI")
    parser.add_argument("--last_frame", help="Last frame image path, URL, or data URI")
    parser.add_argument("--resolution", choices=["720p", "1080p", "4k"], default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--ratio", choices=["16:9", "9:16"], default="16:9",
                        help="Aspect ratio (default: 16:9)")
    parser.add_argument("--person_generation", choices=["allow_all", "allow_adult", "dont_allow"],
                        default=None, help=argparse.SUPPRESS)
    parser.add_argument("--filename", "-f", required=True, help="Output file path")

    args = parser.parse_args()
    mode = validate_args(args)

    base_url, api_key, model = get_config()
    print(f"Mode: {mode}, Model: {model}", file=sys.stderr)
    request_body = build_request(args, model)
    result = submit_task(base_url, api_key, request_body)

    status = result.get("status")
    if status == "failed":
        fail_with_task_error(result)
    if status != "completed":
        task_id = result.get("task_id") or result.get("id")
        result = poll_task(base_url, api_key, task_id)

    video_url = extract_video_url(result)
    saved_path = download_video(video_url, args.filename)
    print(saved_path)


if __name__ == "__main__":
    main()
