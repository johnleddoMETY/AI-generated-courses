import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

function Login() {
  const { signInWithPassword, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mode, setMode] = useState("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);

    try {
      const { error: authError } =
        mode === "sign-in"
          ? await signInWithPassword(email, password)
          : await signUp(email, password);

      if (authError) {
        setError(authError.message);
        return;
      }

      if (mode === "sign-up") {
        setNotice("Account created. Check your email to confirm, then sign in.");
        setMode("sign-in");
        return;
      }

      navigate(from, { replace: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "420px", margin: "80px auto", padding: "28px", color: "#111827" }}>
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "18px",
          padding: "32px",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <h1 style={{ marginTop: 0, color: "#0f172a", fontSize: "28px" }}>
          {mode === "sign-in" ? "Sign in" : "Create an account"}
        </h1>

        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              width: "100%",
              padding: "12px",
              marginTop: "8px",
              marginBottom: "18px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#111827",
              outline: "none",
            }}
          />

          <label style={{ display: "block", fontWeight: 700, color: "#111827" }}>Password</label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              width: "100%",
              padding: "12px",
              marginTop: "8px",
              marginBottom: "20px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#111827",
              outline: "none",
            }}
          />

          {error && <p style={{ color: "#b91c1c", marginTop: 0 }}>{error}</p>}
          {notice && <p style={{ color: "#166534", marginTop: 0 }}>{notice}</p>}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "14px",
              fontSize: "16px",
              cursor: "pointer",
              border: "none",
              borderRadius: "10px",
              backgroundColor: "#2563eb",
              color: "white",
              fontWeight: 700,
            }}
          >
            {loading ? "Please wait..." : mode === "sign-in" ? "Sign in" : "Sign up"}
          </button>
        </form>

        <p style={{ marginTop: "18px", color: "#475569" }}>
          {mode === "sign-in" ? "Need an account?" : "Already have an account?"}{" "}
          <button
            type="button"
            onClick={() => {
              setError("");
              setNotice("");
              setMode(mode === "sign-in" ? "sign-up" : "sign-in");
            }}
            style={{
              border: "none",
              background: "none",
              color: "#2563eb",
              fontWeight: 700,
              cursor: "pointer",
              padding: 0,
            }}
          >
            {mode === "sign-in" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}

export default Login;