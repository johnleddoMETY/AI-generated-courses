import { useLocation, useNavigate } from "react-router-dom";

const STORAGE_KEY = "ai_generated_courses_assessment";

function Results() {
  const navigate = useNavigate();
  const location = useLocation();

  let results = location.state?.results;

  if (!results) {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        results = JSON.parse(saved)?.results;
      } catch {
        results = null;
      }
    }
  }

  if (!results) {
    return (
      <div
        style={{
          maxWidth: "700px",
          margin: "60px auto",
          textAlign: "center",
          fontFamily: "Arial, sans-serif",
          color: "#111827",
        }}
      >
        <h1 style={{ color: "#0f172a" }}>No Assessment Results Found</h1>
        <p style={{ color: "#475569" }}>Please complete the assessment first.</p>

        <button
          onClick={() => navigate("/")}
          style={{
            marginTop: "20px",
            padding: "12px 20px",
            borderRadius: "10px",
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Go Home
        </button>
      </div>
    );
  }

  const {
    knowledgeScore,
    masteryScore,
    accuracyScore,
    knowledgePoints,
    masteryPoints,
    maxKnowledgePoints,
    minKnowledgePoints,
    strongAreas,
    weakAreas,
    conceptStats,
    likelyGuessCount,
    overconfidentWrongCount,
    uncertainWrongCount,
  } = results;

  const goToRoadmap = () => {
    navigate("/roadmap", {
      state: {
        weakAreas,
        strongAreas,
        conceptStats,
        knowledgeScore,
        masteryScore,
        accuracyScore,
      },
    });
  };

  return (
    <div
      style={{
        maxWidth: "980px",
        margin: "50px auto",
        padding: "30px",
        fontFamily: "Arial, sans-serif",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "10px", color: "#0f172a" }}>
        Assessment Results
      </h1>
      <p style={{ color: "#475569", marginTop: 0 }}>
        Knowledge score gives partial credit for correct answers, while mastery
        score only trusts confident and consistent understanding.
      </p>

      <div
        style={{
          background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
          color: "white",
          padding: "28px",
          borderRadius: "16px",
          marginTop: "25px",
          boxShadow: "0 10px 28px rgba(37, 99, 235, 0.18)",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0, color: "#ffffff" }}>Knowledge Score</h2>
            <h1 style={{ fontSize: "64px", margin: "6px 0", lineHeight: 1 }}>
              {knowledgeScore}%
            </h1>
          </div>

          <div>
            <h2 style={{ marginTop: 0, color: "#ffffff" }}>Mastery Score</h2>
            <h1 style={{ fontSize: "64px", margin: "6px 0", lineHeight: 1 }}>
              {masteryScore}%
            </h1>
          </div>

          <div>
            <h2 style={{ marginTop: 0, color: "#ffffff" }}>Accuracy</h2>
            <h1 style={{ fontSize: "64px", margin: "6px 0", lineHeight: 1 }}>
              {accuracyScore}%
            </h1>
          </div>
        </div>

        <p style={{ marginBottom: 0, color: "#eff6ff", marginTop: "16px" }}>
          Knowledge points: {knowledgePoints} / {maxKnowledgePoints} | Minimum:
          {minKnowledgePoints}
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "18px",
          marginTop: "30px",
        }}
      >
        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "14px",
            padding: "20px",
            background: "#ffffff",
            boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
          }}
        >
          <h2 style={{ marginTop: 0, color: "#0f172a" }}>Strong Concepts</h2>
          {strongAreas.length === 0 ? (
            <p style={{ color: "#475569" }}>No strong concepts yet.</p>
          ) : (
            <ul style={{ color: "#111827" }}>
              {strongAreas.map((concept) => (
                <li key={concept}>✅ {concept}</li>
              ))}
            </ul>
          )}
        </div>

        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "14px",
            padding: "20px",
            background: "#ffffff",
            boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
          }}
        >
          <h2 style={{ marginTop: 0, color: "#0f172a" }}>
            Concepts To Improve
          </h2>
          {weakAreas.length === 0 ? (
            <p style={{ color: "#475569" }}>Excellent! No weak concepts detected.</p>
          ) : (
            <ul style={{ color: "#111827" }}>
              {weakAreas.map((concept) => (
                <li key={concept}>📘 {concept}</li>
              ))}
            </ul>
          )}
        </div>

        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "14px",
            padding: "20px",
            background: "#ffffff",
            boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
          }}
        >
          <h2 style={{ marginTop: 0, color: "#0f172a" }}>
            Guessing Indicators
          </h2>
          <ul style={{ color: "#111827" }}>
            <li>Likely correct guesses: {likelyGuessCount}</li>
            <li>Overconfident wrong answers: {overconfidentWrongCount}</li>
            <li>Uncertain wrong answers: {uncertainWrongCount}</li>
          </ul>
        </div>
      </div>

      <h2 style={{ marginTop: "40px", color: "#0f172a" }}>
        Concept Breakdown
      </h2>

      {Object.entries(conceptStats).map(([concept, stats]) => {
        const percent = Math.round((stats.correct / stats.total) * 100);

        return (
          <div
            key={concept}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: "12px",
              padding: "16px",
              marginBottom: "16px",
              background: "#ffffff",
              boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "12px",
                alignItems: "center",
                marginBottom: "10px",
                flexWrap: "wrap",
              }}
            >
              <h3 style={{ margin: 0, color: "#0f172a" }}>{concept}</h3>
              <span style={{ color: "#475569" }}>
                Correct: {stats.correct} / {stats.total}
              </span>
            </div>

            <div
              style={{
                height: "12px",
                background: "#e2e8f0",
                borderRadius: "999px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${percent}%`,
                  background: percent >= 70 ? "#16a34a" : "#2563eb",
                  height: "100%",
                }}
              />
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "10px",
                marginTop: "12px",
                color: "#475569",
              }}
            >
              <p style={{ margin: 0 }}>Mastery: {stats.masteryPercent}%</p>
              <p style={{ margin: 0 }}>
                Confidence quality: {stats.confidenceQuality}%
              </p>
              <p style={{ margin: 0 }}>
                Likely guesses: {stats.lowConfidenceCorrect}
              </p>
              <p style={{ margin: 0 }}>
                Concept points: {stats.masteryPoints} mastery /{" "}
                {stats.knowledgePoints} knowledge
              </p>
            </div>

            {stats.likelyGuessQuestions.length > 0 && (
              <div style={{ marginTop: "12px", color: "#7c2d12" }}>
                <strong>Possible guesses:</strong>
                <ul style={{ marginTop: "6px" }}>
                  {stats.likelyGuessQuestions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {stats.overconfidentWrongQuestions.length > 0 && (
              <div style={{ marginTop: "12px", color: "#991b1b" }}>
                <strong>Overconfident wrong answers:</strong>
                <ul style={{ marginTop: "6px" }}>
                  {stats.overconfidentWrongQuestions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}

      <div
        style={{
          marginTop: "40px",
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => navigate("/assessment")}
          style={{
            padding: "12px 20px",
            borderRadius: "10px",
            border: "1px solid #cbd5e1",
            background: "#ffffff",
            color: "#0f172a",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Retake Assessment
        </button>

        <button
          onClick={goToRoadmap}
          style={{
            padding: "12px 20px",
            borderRadius: "10px",
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          View Learning Roadmap
        </button>
      </div>
    </div>
  );
}

export default Results;