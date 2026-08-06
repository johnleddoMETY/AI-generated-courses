import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { gradeAssessment } from "../services/api";

const STORAGE_KEY = "ai_generated_courses_session";

function loadSession(locationState) {
  if (locationState?.assessmentId) return locationState;

  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (!saved) return null;

  try {
    return JSON.parse(saved);
  } catch {
    return null;
  }
}

function Assessment() {
  const navigate = useNavigate();
  const location = useLocation();

  const session = useMemo(() => loadSession(location.state), [location.state]);

  const domainNameById = useMemo(() => {
    const map = {};
    (session?.domains || []).forEach((domain) => {
      map[domain.domain_id] = domain.name;
    });
    return map;
  }, [session]);

  const questions = session?.questions || [];

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!session || questions.length === 0) {
    return (
      <div style={{ maxWidth: "700px", margin: "60px auto", textAlign: "center", color: "#111827" }}>
        <h1 style={{ color: "#0f172a" }}>No Assessment Found</h1>
        <p style={{ color: "#475569" }}>Generate a learning path first to get an assessment.</p>
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

  const question = questions[currentQuestion];
  const selectedOptionId = answers[question.question_id] ?? null;

  const handleAnswerSelect = (optionId) => {
    setAnswers((prev) => ({
      ...prev,
      [question.question_id]: optionId,
    }));
  };

  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
    }
  };

  const submitAssessment = async () => {
    setError("");
    setSubmitting(true);

    try {
      const payloadAnswers = questions.map((q) => ({
        question_id: q.question_id,
        selected_option_id: answers[q.question_id] ?? null,
      }));

      const { data: graded } = await gradeAssessment(session.assessmentId, payloadAnswers);

      const nextSession = { ...session, graded };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));

      navigate("/results", { state: nextSession });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || err.message || "Something went wrong while grading."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "40px auto",
        padding: "30px",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "8px", color: "#0f172a" }}>Assessment</h1>
      <p style={{ marginTop: 0, color: "#475569" }}>
        Question {currentQuestion + 1} of {questions.length}
      </p>

      <div
        style={{
          height: "10px",
          background: "#e2e8f0",
          borderRadius: "999px",
          overflow: "hidden",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            width: `${((currentQuestion + 1) / questions.length) * 100}%`,
            height: "100%",
            background: "#2563eb",
            transition: "width 0.25s ease",
          }}
        />
      </div>

      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
          padding: "24px",
          background: "#ffffff",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            marginBottom: "14px",
          }}
        >
          <span
            style={{
              display: "inline-block",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "#dbeafe",
              color: "#1d4ed8",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            Domain: {domainNameById[question.domain_id] || question.domain_id}
          </span>

          <span
            style={{
              display: "inline-block",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "#e2e8f0",
              color: "#334155",
              fontSize: "12px",
              fontWeight: 700,
              textTransform: "capitalize",
            }}
          >
            Difficulty: {question.difficulty}
          </span>
        </div>

        <h2 style={{ marginTop: 0, color: "#0f172a" }}>{question.stem}</h2>

        <div style={{ marginTop: "20px" }}>
          {question.options.map((option) => (
            <label
              key={option.option_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "12px 14px",
                marginBottom: "12px",
                border: "1px solid #cbd5e1",
                borderRadius: "12px",
                cursor: "pointer",
                background: selectedOptionId === option.option_id ? "#eff6ff" : "#ffffff",
                color: "#111827",
              }}
            >
              <input
                type="radio"
                name={`question-${question.question_id}`}
                value={option.option_id}
                checked={selectedOptionId === option.option_id}
                onChange={() => handleAnswerSelect(option.option_id)}
              />
              <span>{option.text}</span>
            </label>
          ))}
        </div>

        {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "12px",
            marginTop: "30px",
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            onClick={previousQuestion}
            disabled={currentQuestion === 0}
            style={{
              padding: "12px 18px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: currentQuestion === 0 ? "#e2e8f0" : "#ffffff",
              color: "#0f172a",
              cursor: currentQuestion === 0 ? "not-allowed" : "pointer",
              fontWeight: 700,
            }}
          >
            Previous
          </button>

          {currentQuestion === questions.length - 1 ? (
            <button
              type="button"
              onClick={submitAssessment}
              disabled={submitting}
              style={{
                padding: "12px 18px",
                borderRadius: "10px",
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: submitting ? "not-allowed" : "pointer",
                fontWeight: 700,
              }}
            >
              {submitting ? "Grading..." : "Submit Assessment"}
            </button>
          ) : (
            <button
              type="button"
              onClick={nextQuestion}
              style={{
                padding: "12px 18px",
                borderRadius: "10px",
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              Next
            </button>
          )}
        </div>
      </div>

      <div
        style={{
          marginTop: "18px",
          color: "#475569",
          fontSize: "14px",
          lineHeight: 1.6,
        }}
      >
        Skipped questions are graded as incorrect. Grading runs on the server —
        it recomputes scores from the stored assessment, never from anything
        the browser sends.
      </div>
    </div>
  );
}

export default Assessment;