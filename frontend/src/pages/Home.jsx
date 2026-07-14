import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateLearningPath } from "../services/api";

function Home() {
  const navigate = useNavigate();

  const [certification, setCertification] = useState("");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!certification || !topic) {
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

      // Navigate to Assessment page
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
        maxWidth: "700px",
        margin: "60px auto",
        padding: "30px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1>AI Generated Courses</h1>

      <p>
        Generate a personalized learning roadmap powered by Artificial
        Intelligence.
      </p>

      <div style={{ marginTop: "30px" }}>
        <label>
          <strong>Certification</strong>
        </label>

        <input
          type="text"
          placeholder="AWS Solutions Architect"
          value={certification}
          onChange={(e) => setCertification(e.target.value)}
          style={{
            width: "100%",
            padding: "12px",
            marginTop: "8px",
            marginBottom: "20px",
            borderRadius: "6px",
            border: "1px solid #ccc",
          }}
        />

        <label>
          <strong>Topic</strong>
        </label>

        <input
          type="text"
          placeholder="Cloud Architecture"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          style={{
            width: "100%",
            padding: "12px",
            marginTop: "8px",
            marginBottom: "30px",
            borderRadius: "6px",
            border: "1px solid #ccc",
          }}
        />

        <button
          onClick={handleGenerate}
          disabled={loading}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            cursor: "pointer",
            border: "none",
            borderRadius: "6px",
            backgroundColor: "#2563eb",
            color: "white",
          }}
        >
          {loading ? "Generating..." : "Generate Learning Path"}
        </button>
      </div>
    </div>
  );
}

export default Home;