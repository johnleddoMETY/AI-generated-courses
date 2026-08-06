import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { createAssessment, createSyllabus } from "../services/api";

const STORAGE_KEY = "ai_generated_courses_session";

function Home() {
  const navigate = useNavigate();

  const [certification, setCertification] = useState("");
  const [topic, setTopic] = useState("");
  const [examDate, setExamDate] = useState("");
  const [numQuestions, setNumQuestions] = useState(12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!certification.trim() || !topic.trim()) {
      setError("Please fill in all fields.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const syllabusRes = await createSyllabus({ certification, topic });
      const syllabus = syllabusRes.data;

      const assessmentRes = await createAssessment(syllabus.syllabus_id, {
        numQuestions: Number(numQuestions) || 12,
        examDate: examDate || null,
      });
      const assessment = assessmentRes.data;

      const session = {
        syllabus,
        assessmentId: assessment.assessment_id,
        questions: assessment.questions,
        domains: assessment.domains,
        examDate: examDate || null,
      };

      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));

      navigate("/assessment", { state: session });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Something went wrong while generating your assessment."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "760px",
        margin: "56px auto",
        padding: "28px",
        color: "#111827",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "18px",
          padding: "32px",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <h1 style={{ marginTop: 0, color: "#0f172a", fontSize: "40px" }}>
          AI Generated Courses
        </h1>

        <p style={{ color: "#334155", fontSize: "16px", lineHeight: 1.7 }}>
          Generate a personalized learning roadmap powered by artificial
          intelligence.
        </p>

        <div style={{ marginTop: "28px" }}>
          <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>
            Certification
          </label>

          <input
            type="text"
            placeholder="AWS Solutions Architect Associate SAA-C03"
            value={certification}
            onChange={(e) => setCertification(e.target.value)}
            style={{
              width: "100%",
              padding: "14px",
              marginTop: "10px",
              marginBottom: "22px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#111827",
              outline: "none",
            }}
          />

          <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>
            Topic
          </label>

          <input
            type="text"
            placeholder="Cloud Architecture"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            style={{
              width: "100%",
              padding: "14px",
              marginTop: "10px",
              marginBottom: "22px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#111827",
              outline: "none",
            }}
          />

          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 200px" }}>
              <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>
                Exam date (optional)
              </label>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                style={{
                  width: "100%",
                  padding: "14px",
                  marginTop: "10px",
                  marginBottom: "28px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#111827",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ flex: "1 1 200px" }}>
              <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>
                Number of questions
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={numQuestions}
                onChange={(e) => setNumQuestions(e.target.value)}
                style={{
                  width: "100%",
                  padding: "14px",
                  marginTop: "10px",
                  marginBottom: "28px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#111827",
                  outline: "none",
                }}
              />
            </div>
          </div>

          {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "14px 22px",
              fontSize: "16px",
              cursor: loading ? "not-allowed" : "pointer",
              border: "none",
              borderRadius: "10px",
              backgroundColor: "#2563eb",
              color: "white",
              fontWeight: 700,
            }}
          >
            {loading ? "Generating..." : "Generate Learning Path"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Home;