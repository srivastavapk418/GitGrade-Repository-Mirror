
import { useState } from "react";

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);

  const analyzeRepo = async () => {
    const res = await fetch("http://localhost:8000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: url }),
    });
    const data = await res.json();
    setResult(data);
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>GitGrade – Repository Mirror</h1>
      <input
        placeholder="Paste GitHub Repository URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        style={{ width: "60%", padding: 8 }}
      />
      <br /><br />
      <button onClick={analyzeRepo}>Analyze Repository</button>

      {result && (
        <div style={{ marginTop: 20 }}>
          <h2>Score: {result.score} / 100 ({result.level})</h2>
          <p>{result.summary}</p>
          <h3>Personalized Roadmap</h3>
          <ul>
            {result.roadmap.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
