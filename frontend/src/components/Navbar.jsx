import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "15px 30px",
        background: "#1e293b",
        color: "white",
      }}
    >
      <h2>AI Generated Courses</h2>

      <div style={{ display: "flex", gap: "20px" }}>
        <Link to="/" style={{ color: "white" }}>
          Home
        </Link>

        <Link to="/assessment" style={{ color: "white" }}>
          Assessment
        </Link>

        <Link to="/roadmap" style={{ color: "white" }}>
          Roadmap
        </Link>
      </div>
    </nav>
  );
}

export default Navbar;