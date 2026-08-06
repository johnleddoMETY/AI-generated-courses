import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { createCourse } from "../services/api";

const STORAGE_KEY = "ai_generated_courses_session";

function loadSession(locationState) {
  if (locationState?.roadmap) return locationState;

  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (!saved) return null;

  try {
    return JSON.parse(saved);
  } catch {
    return null;
  }
}

function Roadmap() {
  const navigate = useNavigate();
  const location = useLocation();

  const session = useMemo(() => loadSession(location.state), [location.state]);
  const roadmap = session?.roadmap;

  const [generatingCourse, setGeneratingCourse] = useState(false);
  const [error, setError] = useState("");

  if (!roadmap) {
    return (
      <div style={{ maxWidth: "700px", margin: "60px auto", textAlign: "center", color: "#111827" }}>
        <h1 style={{ color: "#0f172a" }}>No Roadmap Found</h1>
        <p style={{ color: "#475569" }}>View your results first to build a roadmap.</p>
        <button
          onClick={() => navigate("/results")}
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
          Back to Results
        </button>
      </div>
    );
  }

  const course = session?.course;

  const handleGenerateCourse = async () => {
    setError("");
    setGeneratingCourse(true);

    try {
      const { data: generatedCourse } = await createCourse(roadmap.roadmap_id);
      const nextSession = { ...session, course: generatedCourse };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
      navigate("/roadmap", { state: nextSession, replace: true });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || err.message || "Something went wrong generating the course."
      );
    } finally {
      setGeneratingCourse(false);
    }
  };

  const startLesson = (item) => {
    const lesson = course?.lessons?.find((l) => l.item_id === item.item_id);
    navigate("/lesson", {
      state: {
        ...session,
        item,
        lesson: lesson || null,
      },
    });
  };

  return (
    <div style={{ maxWidth: "900px", margin: "50px auto", padding: "30px", color: "#111827" }}>
      <h1 style={{ marginBottom: "10px", color: "#0f172a" }}>
        Personalized Learning Roadmap
      </h1>

      <p style={{ color: "#475569", marginTop: 0 }}>{roadmap.guidance_summary}</p>
      <p style={{ color: "#475569", marginTop: 0 }}>
        Total estimated study time: {roadmap.total_estimated_hours} hours
      </p>

      {roadmap.skipped_domains.length > 0 && (
        <p style={{ color: "#475569", marginTop: 0 }}>
          Skipped (already proficient):{" "}
          {roadmap.skipped_domains.map((d) => d.domain_id).join(", ")}
        </p>
      )}

      {!course && (
        <div
          style={{
            marginTop: "16px",
            padding: "16px",
            borderRadius: "12px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
          }}
        >
          <p style={{ margin: "0 0 12px", color: "#1e3a8a" }}>
            Generate lesson content for every item below (one LLM call per item — this can take a
            while).
          </p>
          <button
            onClick={handleGenerateCourse}
            disabled={generatingCourse}
            style={{
              padding: "12px 18px",
              borderRadius: "10px",
              border: "none",
              background: "#2563eb",
              color: "white",
              cursor: generatingCourse ? "not-allowed" : "pointer",
              fontWeight: 700,
            }}
          >
            {generatingCourse ? "Generating course..." : "Generate Full Course"}
          </button>
        </div>
      )}

      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

      <div style={{ marginTop: "24px", display: "grid", gap: "16px" }}>
        {roadmap.items.map((item) => (
          <div
            key={item.item_id}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: "14px",
              padding: "18px",
              background: "#ffffff",
              boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "12px",
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <div>
                <h3 style={{ margin: 0, color: "#0f172a" }}>
                  {item.priority}. {item.title}
                </h3>
                <p style={{ margin: "6px 0 0", color: "#475569" }}>{item.objective}</p>
                <p style={{ margin: "6px 0 0", color: "#94a3b8", fontSize: "13px" }}>
                  {item.estimated_hours}h · {item.subtopics.join(", ")}
                </p>
              </div>

              <button
                onClick={() => startLesson(item)}
                disabled={!course}
                title={!course ? "Generate the course first" : undefined}
                style={{
                  padding: "10px 16px",
                  borderRadius: "10px",
                  border: "none",
                  background: course ? "#2563eb" : "#94a3b8",
                  color: "white",
                  cursor: course ? "pointer" : "not-allowed",
                  fontWeight: 700,
                }}
              >
                Start Lesson
              </button>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "30px" }}>
        <button
          onClick={() => navigate("/results")}
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
          Back to Results
        </button>
      </div>
    </div>
  );
}

export default Roadmap;