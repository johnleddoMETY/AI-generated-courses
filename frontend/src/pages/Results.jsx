import { useNavigate } from "react-router-dom";

function Results() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "50px auto",
        padding: "30px",
        fontFamily: "Arial",
      }}
    >
      <h1>Assessment Complete 🎉</h1>

      <h2>Score: 82%</h2>

      <h3>Strong Areas</h3>

      <ul>
        <li>Networking</li>
        <li>Storage</li>
      </ul>

      <h3>Needs Improvement</h3>

      <ul>
        <li>IAM</li>
        <li>KMS</li>
        <li>Encryption</li>
      </ul>

      <button
        onClick={() => navigate("/roadmap")}
        style={{
          marginTop: "30px",
          padding: "12px 20px",
          cursor: "pointer",
        }}
      >
        View Learning Roadmap
      </button>
    </div>
  );
}

export default Results;