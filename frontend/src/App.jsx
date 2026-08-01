import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Assessment from "./pages/Assessment";
import Results from "./pages/Results";
import Roadmap from "./pages/Roadmap";
import Lesson from "./pages/Lesson";

function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: "100vh", background: "#f8fafc", color: "#111827" }}>
        <Navbar />

        <main style={{ paddingBottom: "40px" }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/assessment" element={<Assessment />} />
            <Route path="/results" element={<Results />} />
            <Route path="/roadmap" element={<Roadmap />} />
            <Route path="/lesson" element={<Lesson />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;