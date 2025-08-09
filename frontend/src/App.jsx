
import React from "react";
import "./index.css";

export default function App() {
  const [file, setFile] = React.useState(null);
  const [uploading, setUploading] = React.useState(false);
  const [progress, setProgress] = React.useState(0);
  const [moves, setMoves] = React.useState([]);
  const [pgnUrl, setPgnUrl] = React.useState(null);
  const [sid, setSid] = React.useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return alert("Choisis une vidéo");
    setUploading(true);
    const form = new FormData();
    form.append("video", file);
    const resp = await fetch("/api/upload", { method: "POST", body: form });
    const data = await resp.json();
    setSid(data.session_id);
    // SSE connect
    const es = new EventSource(`/api/progress/${data.session_id}`);
    es.onmessage = async (ev) => {
      try {
        const st = JSON.parse(ev.data);
        setProgress(st.progress || 0);
        if (st.status === "done") {
          es.close();
          setUploading(false);
          // fetch result
          const r = await fetch(`/api/result/${data.session_id}`);
          const j = await r.json();
          setMoves(j.moves || []);
          // make downloadable blob for pgn
          const blob = new Blob([j.pgn || ""], { type: "text/plain" });
          const url = URL.createObjectURL(blob);
          setPgnUrl(url);
        }
      } catch(e) {}
    };
    es.onerror = () => { setUploading(false); es.close(); }
  }

  return (
    <div style={{ maxWidth: 820, margin: 20, fontFamily: "Arial, sans-serif" }}>
      <h1>Chess Video Analyzer — Auto CPU</h1>
      <p>Uploade ta vidéo, laisse l'analyse se faire et télécharge le PGN.</p>
      <form onSubmit={handleSubmit}>
        <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files[0])} />
        <div style={{ marginTop: 10 }}>
          <button disabled={uploading} type="submit">Analyser</button>
        </div>
      </form>
      {uploading && (
        <div style={{ marginTop: 10 }}>
          <div style={{ width: "100%", background: "#eee", height: 12, borderRadius: 6, overflow: "hidden" }}>
            <div style={{ width: `${progress}%`, height: "100%", background: "#4caf50" }} />
          </div>
          <p>Progress: {progress}%</p>
        </div>
      )}
      <section style={{ marginTop: 20 }}>
        <h3>Coups détectés</h3>
        {moves.length === 0 ? <p>Aucun coup détecté (encore)</p> : (
          <ol>
            {moves.map((m,i)=>(<li key={i}>{m}</li>))}
          </ol>
        )}
        {pgnUrl && <a download="game.pgn" href={pgnUrl}>Télécharger PGN</a>}
      </section>
    </div>
  );
}
