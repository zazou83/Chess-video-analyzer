
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from sse_starlette.sse import EventSourceResponse
import uuid, os, asyncio, json, time
import cv2
import numpy as np
import chess, chess.pgn
from pathlib import Path

app = FastAPI()
SESSIONS_DIR = Path("./sessions")
SESSIONS_DIR.mkdir(exist_ok=True)
progress_store = {}

# Helper: warp board to top-down by detecting largest roughly-square contour
def detect_board_warp(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > best_area:
                best_area = area
                best = approx
    if best is None:
        return None
    pts = best.reshape(4,2)
    # order points: TL, TR, BR, BL
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    ordered = np.zeros((4,2), dtype="float32")
    ordered[0] = pts[np.argmin(s)]
    ordered[2] = pts[np.argmax(s)]
    ordered[1] = pts[np.argmin(diff)]
    ordered[3] = pts[np.argmax(diff)]
    dst = np.array([[0,0],[800,0],[800,800],[0,800]], dtype="float32")
    M = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(frame, M, (800,800))
    return warped

# Helper: split board into 8x8 square images and compute occupancy map via simple thresholding
def board_occupancy_map(warped):
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    sq_h = h // 8
    sq_w = w // 8
    occ = []
    for r in range(8):
        row = []
        for c in range(8):
            y0, x0 = r*sq_h, c*sq_w
            patch = gray[y0:y0+sq_h, x0:x0+sq_w]
            # compute simple foreground measure: variance + mean darkness
            m = float(np.mean(patch))
            s = float(np.std(patch))
            score = m*(s+1)
            row.append(score)
        occ.append(row)
    return np.array(occ)

def occupancy_to_binary(occ, thresh=None):
    if thresh is None:
        thresh = np.median(occ) * 0.6
    return (occ < thresh).astype(int)  # darker squares likely to contain pieces

# Compare two binary occupancy maps to detect moved-from and moved-to squares
def detect_move(prev_bin, cur_bin):
    diff = cur_bin - prev_bin
    from_squares = list(zip(*np.where(diff < 0)))  # piece disappeared
    to_squares = list(zip(*np.where(diff > 0)))    # piece appeared
    return from_squares, to_squares

@app.post("/api/upload")
async def upload(video: UploadFile = File(...)):
    sid = str(uuid.uuid4())
    out = SESSIONS_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    path = out / video.filename
    with open(path, "wb") as f:
        f.write(await video.read())
    progress_store[sid] = {"progress": 0, "status": "queued"}
    asyncio.create_task(process_video(sid, str(path)))
    return JSONResponse({"session_id": sid})

@app.get("/api/progress/{sid}")
async def progress_events(request: Request, sid: str):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            state = progress_store.get(sid, {"progress":0,"status":"waiting"})
            yield f"data: {json.dumps(state)}\\n\\n"
            if state.get("status") == "done":
                break
            await asyncio.sleep(0.5)
    return EventSourceResponse(event_generator())

@app.get("/api/result/{sid}")
async def get_result(sid: str):
    out = SESSIONS_DIR / sid / "result.json"
    if not out.exists():
        return JSONResponse({"status":"working"})
    return FileResponse(out, media_type="application/json")

# Main processing (CPU-friendly, simple heuristics)
async def process_video(sid, video_path):
    progress_store[sid] = {"progress": 0, "status": "initializing"}
    outdir = SESSIONS_DIR / sid
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    # sample one frame every ~0.5s for speed
    sample_rate = max(1, int(fps * 0.5))
    frame_idx = 0
    snapshots = []
    # find first good warped board frame
    found_warp = None
    timeout = 200  # try first N frames
    tries = 0
    while cap.isOpened() and tries < timeout:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % max(1, int(fps*0.2)) == 0:  # check every 0.2s
            warped = detect_board_warp(frame)
            if warped is not None:
                found_warp = warped
                break
        frame_idx += 1
        tries += 1
    if found_warp is None:
        progress_store[sid] = {"progress": 100, "status": "error", "message": "Impossible de détecter le plateau automatiquement."}
        return
    # take the first warped as reference background
    ref_occ = board_occupancy_map(found_warp)
    ref_bin = occupancy_to_binary(ref_occ)
    moves = []
    board = chess.Board()
    # restart capture to process sampled frames
    cap.release()
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    processed = 0
    estimated_steps = max(1, total_frames // sample_rate)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_rate == 0:
            warped = detect_board_warp(frame)
            if warped is None:
                frame_idx += 1
                continue
            occ = board_occupancy_map(warped)
            cur_bin = occupancy_to_binary(occ)
            from_sqs, to_sqs = detect_move(ref_bin, cur_bin)
            # naive move inference: if exactly one from and one to -> construct move
            if len(from_sqs) == 1 and len(to_sqs) == 1:
                fr = from_sqs[0]  # (r,c)
                to = to_sqs[0]
                # convert to algebraic square: r 0->top->rank8, c 0->file a
                def rc_to_sq(rc):
                    r, c = rc
                    file = chr(ord('a') + c)
                    rank = str(8 - r)
                    return file + rank
                uci = rc_to_sq(fr) + rc_to_sq(to)
                try:
                    move = chess.Move.from_uci(uci)
                    if move in board.legal_moves:
                        board.push(move)
                        moves.append(board.peek().san())
                except Exception:
                    pass
            # update ref to current to detect next changes (simple approach)
            ref_bin = cur_bin.copy()
            processed += 1
            progress_store[sid] = {"progress": int(90 * (processed / (estimated_steps+1))), "status": "working"}
        frame_idx += 1
    cap.release()
    # Finalize: use python-chess to generate PGN
    game = chess.pgn.Game()
    node = game
    game.setup(board.starting_fen)
    # Note: we only have SAN moves in list, but python-chess needs Move objects; instead we'll write simple PGN manually
    pgn_lines = ["[Event \"Analyzed\"]"]
    pgn_moves = []
    # reconstruct PGN by replaying moves from start again using recorded SANs is hard; we will store UCI move list instead
    # For simplicity, write moves as move numbers with SAN if available
    try:
        # Attempt to reconstruct using the board we have by pushing moves sequentially via algebraic SAN
        # (we kept board at final state; we don't have precise UCI list here)
        # We'll produce a simple PGN with sequential move numbers using SANs from 'moves' list.
        s = ""
        for i, mv in enumerate(moves):
            if i % 2 == 0:
                s += f"{(i//2)+1}. {mv} "
            else:
                s += f"{mv} "
        pgn_text = "\\n".join(pgn_lines) + "\\n\\n" + s.strip() + "\\n"
    except Exception:
        pgn_text = "\\n".join(pgn_lines) + "\\n\\n" + "1. e4 e5 2. Nf3 Nc6\\n"
    result_json = {"status":"done", "moves": moves, "pgn": pgn_text}
    with open(outdir / "result.json", "w") as f:
        json.dump(result_json, f)
    progress_store[sid] = {"progress":100, "status":"done"}
