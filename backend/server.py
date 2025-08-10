from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI()

# CORS pour autoriser le frontend à appeler le backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# On sert le frontend compilé depuis /frontend/build
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")

@app.post("/analyze/")
async def analyze_video(file: UploadFile = File(...)):
    """
    Endpoint d'analyse vidéo.
    (Ici c'est juste un exemple qui renvoie un PGN fictif)
    """
    pgn_path = "game.pgn"
    with open(pgn_path, "w") as f:
        f.write("[Event \"Example\"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6")
    return FileResponse(pgn_path, filename="game.pgn")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
