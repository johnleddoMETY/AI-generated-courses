import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { regenerateLesson } from "../services/api";

const STORAGE_KEY = "ai_generated_courses_session";

function Lesson() {
  const navigate = useNavigate();
  const location = useLocation();

  const session = location.state || JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
  const item = location.state?.item;
  const [lesson, setLesson] = useState(location.state?.lesson || null);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState("");

  if (!session || !item) {
    return (
      <div style={{ maxWidth: "700px", margin: "60px auto", textAlign: "center", color: "#111827" }}>
        <h1 style={{ color: "#0f172a" }}>No Lesson Selected</h1>
        <p style={{ color: "#475569" }}>Pick a lesson from your roadmap.</p>
        <button
          onClick={() => navigate("/roadmap")}
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
          Back to Roadmap
        </button>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div style={{ maxWidth: "700px", margin: "60px auto", textAlign: "center", color: "#111827" }}>
        <h1 style={{ color: "#0f172a" }}>Lesson Not Generated Yet</h1>
        <p style={{ color: "#475569" }}>
          Go back to the roadmap and generate the course first.
        </p>
        <button
          onClick={() => navigate("/roadmap")}
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
          Back to Roadmap
        </button>
      </div>
    );
  }

  const handleRegenerate = async () => {
    setError("");
    setRegenerating(true);

    try {
      const { data: newLesson } = await regenerateLesson(session.course.course_id, item.item_id);
      setLesson(newLesson);

      const lessons = session.course.lessons.map((l) =>
        l.item_id === item.item_id ? newLesson : l
      );
      const nextSession = { ...session, course: { ...session.course, lessons } };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || err.message || "Something went wrong regenerating the lesson."
      );
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "50px auto",
        padding: "30px",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "8px", color: "#0f172a" }}>{lesson.title}</h1>
      <p style={{ color: "#475569", marginTop: 0 }}>Domain: {item.domain_id}</p>

      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: "14px",
          padding: "24px",
          background: "#ffffff",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        {lesson.sections.map((section, index) => (
          <div key={index} style={{ marginBottom: "20px" }}>
            <h2 style={{ marginTop: 0, color: "#0f172a" }}>{section.heading}</h2>
            <p style={{ color: "#111827", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
              {section.body_markdown}
            </p>
          </div>
        ))}

        {lesson.examples.length > 0 && (
          <div style={{ marginTop: "24px" }}>
            <h2 style={{ color: "#0f172a" }}>Worked Examples</h2>
            {lesson.examples.map((example, index) => (
              <div
                key={index}
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  padding: "14px",
                  marginBottom: "12px",
                }}
              >
                <p style={{ margin: 0, fontWeight: 700, color: "#0f172a" }}>{example.scenario}</p>
                <p style={{ margin: "8px 0 0", color: "#334155", whiteSpace: "pre-wrap" }}>
                  {example.walkthrough}
                </p>
              </div>
            ))}
          </div>
        )}

        {lesson.practice_questions.length > 0 && (
          <div style={{ marginTop: "24px" }}>
            <h2 style={{ color: "#0f172a" }}>Practice Questions</h2>
            {lesson.practice_questions.map((pq, index) => (
              <div
                key={index}
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  padding: "14px",
                  marginBottom: "12px",
                }}
              >
                <p style={{ margin: 0, fontWeight: 700, color: "#0f172a" }}>{pq.question}</p>
                <p style={{ margin: "8px 0 0", color: "#166534" }}>
                  <strong>Answer:</strong> {pq.answer}
                </p>
                <p style={{ margin: "4px 0 0", color: "#334155" }}>{pq.explanation}</p>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: "24px" }}>
          <h2 style={{ color: "#0f172a" }}>Summary</h2>
          <p style={{ color: "#334155", lineHeight: 1.7 }}>{lesson.summary}</p>
        </div>
      </div>

      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

      <div
        style={{
          marginTop: "24px",
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => navigate("/roadmap", { state: session })}
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
          Back to Roadmap
        </button>

        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          style={{
            padding: "12px 20px",
            borderRadius: "10px",
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: regenerating ? "not-allowed" : "pointer",
            fontWeight: 700,
          }}
        >
          {regenerating ? "Regenerating..." : "Regenerate Lesson"}
        </button>
      </div>
    </div>
  );
}

export default Lesson;