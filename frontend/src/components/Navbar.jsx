import { Link, useNavigate } from "react-router-dom";

const STORAGE_KEY = "ai_generated_courses_assessment";

function Navbar() {
  const navigate = useNavigate();

  const handleStartOver = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    navigate("/");
  };

  const linkStyle = {
    color: "#ffffff",
    textDecoration: "none",
    fontWeight: 600,
  };

  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 28px",
        background: "#0f172a",
        color: "#ffffff",
        flexWrap: "wrap",
        gap: "14px",
        borderBottom: "1px solid #1e293b",
      }}
    >
      <h2 style={{ margin: 0, color: "#ffffff" }}>AI Generated Courses</h2>

      <div
        style={{
          display: "flex",
          gap: "18px",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <Link to="/" style={linkStyle}>
          Home
        </Link>

        <Link to="/assessment" style={linkStyle}>
          Assessment
        </Link>

        <Link to="/results" style={linkStyle}>
          Results
        </Link>

        <Link to="/roadmap" style={linkStyle}>
          Roadmap
        </Link>

        <Link to="/lesson" style={linkStyle}>
          Lesson
        </Link>

        <button
          type="button"
          onClick={handleStartOver}
          style={{
            padding: "10px 14px",
            borderRadius: "10px",
            border: "1px solid #334155",
            background: "#2563eb",
            color: "#ffffff",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Start Over
        </button>
      </div>
    </nav>
  );
}

export default Navbar;