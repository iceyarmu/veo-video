---
name: veo-video
description: Generate videos via Gemini Veo. Supports text-to-video, image-to-video (first/last frame), and reference-image-to-video with aspect ratio control.
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      bins: [python3]
      env: [GEMINI_API_KEY, GEMINI_BASE_URL]
      pip: [requests]
    primaryEnv: GEMINI_API_KEY
    envHelp:
      GEMINI_API_KEY:
        required: true
        description: Gemini API Key
      GEMINI_BASE_URL:
        required: true
        description: Gemini API Base URL
---

# Veo Video

Generate videos using Gemini Veo.

## Configuration

```bash
export GEMINI_BASE_URL="https://generativelanguage.googleapis.com"
export GEMINI_API_KEY="your-api-key"
```

## Command

```bash
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "description" --filename "output.mp4" \
  [--reference_image path1 path2] \
  [--first_frame path] [--last_frame path] \
  [--ratio 16:9|9:16]
```

Always run from user's working directory, do NOT cd to skill directory.

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--prompt` | Yes | - | Video description prompt |
| `--filename` | Yes | - | Output file path (.mp4) |
| `--reference_image` | No | - | Reference image path(s) or URL(s), up to 3 |
| `--first_frame` | No | - | First frame image path or URL |
| `--last_frame` | No | - | Last frame image path or URL (use with `--first_frame` for interpolation) |
| `--ratio` | No | 16:9 | `16:9` or `9:16` |

Image arguments accept either a local file path or an `http(s)://` URL.

## Constraints

- **Aspect ratio**: only `16:9` (landscape) and `9:16` (portrait)
- **Reference images**: up to 3 images
- **Frame order**: `--first_frame` must be provided before (or together with) `--last_frame`; do not pass `--last_frame` alone

## Examples

```bash
# Text-to-video (landscape)
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "A cat walking on a beach at sunset" \
  --ratio 16:9 --filename output.mp4

# Image-to-video with first frame
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "The scene comes alive with gentle motion" \
  --first_frame photo.jpg --filename output.mp4

# Image-to-video with first and last frame
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "Smooth transition between two scenes" \
  --first_frame start.jpg --last_frame end.jpg --filename output.mp4

# Reference-image-to-video
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "Product showcase video" \
  --reference_image product1.jpg product2.jpg \
  --filename output.mp4

# Reference image via URL
python3 ~/.openclaw/workspace/skills/veo-video/scripts/generate_video.py \
  --prompt "Make this character walk through a forest" \
  --reference_image https://example.com/ref.jpg \
  --filename output.mp4
```

## Filename

Pattern: `yyyy-mm-dd-hh-mm-ss-descriptive-name.mp4`

## Output

- Progress and status printed to stderr
- Final saved file path printed to stdout

## Preflight

- `command -v python3`
- `python3 -c "import requests"`
- Verify env vars: `[ -n "$GEMINI_API_KEY" ] && [ -n "$GEMINI_BASE_URL" ]`
