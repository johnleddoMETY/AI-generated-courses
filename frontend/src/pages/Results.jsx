import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { createRoadmap } from "../services/api";

const STORAGE_KEY = "ai_generated_courses_session";

function loadSession(locationState) {
  if (locationState?.graded) return locationState;

  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (!saved) return null;

  try {
    return JSON.parse(saved);
  } catch {
    return null;
  }
}

const proficiencyColor = {
  weak: "#dc2626",
  developing: "#d97706",
  proficient: "#16a34a",
};

function Results() {
  const navigate = useNavigate();
  const location = useLocation();

  const session = useMemo(() => loadSession(location.state), [location.state]);
  const graded = session?.graded;

  const [generatingRoadmap, setGeneratingRoadmap] = useState(false);
  const [error, setError] = useState("");

  if (!graded) {
    return (
      <div
        style={{
          maxWidth: "700px",
          margin: "60px auto",
          textAlign: "center",
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
    overall_score_percent: overallScore,
    domain_scores: domainScores,
    gaps,
    diagnostic_summary: diagnosticSummary,
    strengths_summary: strengthsSummary,
  } = graded;

  const goToRoadmap = async () => {
    setError("");
    setGeneratingRoadmap(true);

    try {
      const { data: roadmap } = await createRoadmap(session.assessmentId, {
        examDate: session.examDate,
      });

      const nextSession = { ...session, roadmap };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));

      navigate("/roadmap", { state: nextSession });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || err.message || "Something went wrong building the roadmap."
      );
    } finally {
      setGeneratingRoadmap(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "980px",
        margin: "50px auto",
        padding: "30px",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "10px", color: "#0f172a" }}>Assessment Results</h1>
      <p style={{ color: "#475569", marginTop: 0 }}>
        Score is weighted by each exam domain's weight, then graded server-side.
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
        <h2 style={{ marginTop: 0, color: "#ffffff" }}>Overall Score</h2>
        <h1 style={{ fontSize: "64px", margin: "6px 0", lineHeight: 1 }}>
          {overallScore.toFixed(1)}%
        </h1>
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
          <h2 style={{ marginTop: 0, color: "#0f172a" }}>Strengths</h2>
          <p style={{ color: "#334155", lineHeight: 1.6 }}>{strengthsSummary}</p>
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
          <h2 style={{ marginTop: 0, color: "#0f172a" }}>Diagnosis</h2>
          <p style={{ color: "#334155", lineHeight: 1.6 }}>{diagnosticSummary}</p>
        </div>
      </div>

      <h2 style={{ marginTop: "40px", color: "#0f172a" }}>Domain Scores</h2>

      {domainScores.map((domain) => (
        <div
          key={domain.domain_id}
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
            <h3 style={{ margin: 0, color: "#0f172a" }}>
              {domain.domain_name}{" "}
              <span style={{ color: "#94a3b8", fontWeight: 400, fontSize: "14px" }}>
                (weight {domain.weight_percent}%)
              </span>
            </h3>
            <span
              style={{
                color: "#ffffff",
                background: proficiencyColor[domain.proficiency] || "#64748b",
                borderRadius: "999px",
                padding: "4px 12px",
                fontSize: "12px",
                fontWeight: 700,
                textTransform: "capitalize",
              }}
            >
              {domain.proficiency}
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
                width: `${domain.score_percent}%`,
                background: domain.score_percent >= 70 ? "#16a34a" : "#2563eb",
                height: "100%",
              }}
            />
          </div>

          <p style={{ margin: "10px 0 0", color: "#475569" }}>
            {domain.questions_correct} / {domain.questions_total} correct — {domain.score_percent}%
          </p>
        </div>
      ))}

      {gaps.length > 0 && (
        <>
          <h2 style={{ marginTop: "40px", color: "#0f172a" }}>Knowledge Gaps</h2>
          {gaps.map((gap, index) => (
            <div
              key={`${gap.domain_id}-${index}`}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "12px",
                background: "#ffffff",
                boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <strong style={{ color: "#0f172a" }}>{gap.domain_id}</strong>
                <span
                  style={{
                    color: gap.severity === "critical" ? "#b91c1c" : "#92400e",
                    fontWeight: 700,
                    textTransform: "capitalize",
                  }}
                >
                  {gap.severity}
                </span>
              </div>
              <p style={{ color: "#334155", margin: "8px 0 0" }}>{gap.gap_summary}</p>
            </div>
          ))}
        </>
      )}

      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

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
          disabled={generatingRoadmap}
          style={{
            padding: "12px 20px",
            borderRadius: "10px",
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: generatingRoadmap ? "not-allowed" : "pointer",
            fontWeight: 700,
          }}
        >
          {generatingRoadmap ? "Building Roadmap..." : "View Learning Roadmap"}
        </button>
      </div>
    </div>
  );
}

export default Results;