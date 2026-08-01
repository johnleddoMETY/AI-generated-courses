import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateLearningPath } from "../services/api";

function Home() {
  const navigate = useNavigate();

  const [certification, setCertification] = useState("");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!certification.trim() || !topic.trim()) {
      alert("Please fill in all fields.");
      return;
    }

    setLoading(true);

    try {
      const response = await generateLearningPath({
        certification,
        topic,
      });

      console.log("Backend Response:", response.data);
      navigate("/assessment");
    } catch (error) {
      console.error(error);
      alert("Something went wrong.");
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
            placeholder="AWS Solutions Architect"
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
              marginBottom: "28px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#111827",
              outline: "none",
            }}
          />

          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "14px 22px",
              fontSize: "16px",
              cursor: "pointer",
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