---
name: veo-video
description: Generate videos via Gemini Veo 3.1 API (generateContent endpoint). Supports text-to-video, image-to-video (first/last frame), and reference-image-to-video. Model auto-selected based on input mode and aspect ratio.
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
        howToGet: |
          1. Visit https://aistudio.google.com/apikey
          2. Create an API Key
        url: https://aistudio.google.com/apikey
      GEMINI_BASE_URL:
        required: true
        description: Gemini API Base URL
---

# Veo Video

Generate videos using the Gemini Veo 3.1 API (generateContent endpoint).

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

## Model Auto-Selection

Model is automatically chosen based on input mode and aspect ratio:

| Mode | Trigger | Model |
|------|---------|-------|
| t2v (text-to-video) | No image inputs | `veo_3_1_t2v_fast_landscape` (16:9) / `veo_3_1_t2v_fast_portrait` (9:16) |
| i2v (image-to-video) | `--first_frame` or `--last_frame` | `veo_3_1_i2v_s_fast_fl` |
| r2v (reference-to-video) | `--reference_image` | `veo_3_1_r2v_fast` |

## API Format

Uses the `generateContent` endpoint:

```
POST {GEMINI_BASE_URL}/v1beta/models/{model}:generateContent
```

Request body uses `contents` with `parts`:
- Text prompt as `{"text": "..."}` part
- Local images as `{"inlineData": {"mimeType": "...", "data": "base64..."}}` part
- URL images as `{"fileData": {"mimeType": "...", "fileUri": "https://..."}}` part

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--prompt` | Yes | - | Video description prompt |
| `--filename` | Yes | - | Output file path (.mp4) |
| `--reference_image` | No | - | Reference image path(s)/URL(s), up to 3 (triggers r2v) |
| `--first_frame` | No | - | First frame image (triggers i2v mode) |
| `--last_frame` | No | - | Last frame image (use with first_frame for interpolation) |
| `--ratio` | No | 16:9 | 16:9 or 9:16 |

## Constraints

- **Aspect ratio**: Only 16:9 (landscape) and 9:16 (portrait)
- **Reference images**: Up to 3 images
- **I2V frame order**: First frame must come before last frame (order is fixed)
- **Audio**: Veo 3.x generates audio natively
- **Local files**: Auto base64-encoded as inlineData. URLs passed as fileData (no download).

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
