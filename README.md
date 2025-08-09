
# Chess Video Analyzer — Auto CPU (Deploy-ready)

This repository contains a simple **Auto CPU** version of a Chess Video Analyzer, prepared for quick deployment on platforms like **Render** (free tier).

**What it does (simple):**
- Web UI to upload a chess-game video.
- Backend samples frames, finds the board, warps to top-down view, and performs a simple per-square analysis to detect moves.
- Integrates a basic validation step using python-chess and returns a `.pgn` (best-effort).

**Notes & limitations (important, short):**
- This CPU version uses a *very simple* visual method. It **works best** when the camera is relatively steady, the whole board is visible, and pieces are clearly contrasted. It will struggle with heavy occlusions (hands), very fast blitz moves, or unusual boards.
- For high accuracy you'd want a trained YOLO model and a GPU. This repo is meant to get you up and running quickly and test the interface and pipeline.

## Deploying (Auto, Render in 2–3 clicks)

1. Create a GitHub repository and push this project there (or upload the ZIP contents).
2. Go to https://dashboard.render.com and create an account (or sign in).
3. Click **New -> Web Service**, connect your GitHub repo, select the `render.yaml` (or the repo root), and deploy. Render's free plan will run the service (CPU-only, may sleep when idle).

## Running locally (if you want to test locally)
You can use Docker Compose (requires Docker installed):

```bash
docker compose up --build
# - Backend will be available on http://localhost:8000
# - Frontend dev server will be available on http://localhost:3000 (proxying /api to backend in docker-compose)
```

## Quick test after deployment
- Open the web app URL provided by Render.
- Upload a short video of a chess game (preferably steady top-down or slightly oblique).
- Watch the progress bar, then download the PGN when done.

---
If you want, I can now:
- produce a ZIP ready to download (I already did), OR
- push this repo to a GitHub repo (I cannot push directly, but I can give exact commands), OR
- generate an even more accurate version with optional YOLO and small model training instructions (slower to deploy).

Tell me which next step you want.
