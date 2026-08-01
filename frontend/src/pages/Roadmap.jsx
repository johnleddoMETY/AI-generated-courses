import { useLocation, useNavigate } from "react-router-dom";

const STORAGE_KEY = "ai_generated_courses_assessment";

function Roadmap() {
  const navigate = useNavigate();
  const location = useLocation();

  let weakAreas = location.state?.weakAreas || [];
  let strongAreas = location.state?.strongAreas || [];

  if (weakAreas.length === 0 && strongAreas.length === 0) {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        weakAreas = parsed?.results?.weakAreas || [];
        strongAreas = parsed?.results?.strongAreas || [];
      } catch {
        weakAreas = [];
        strongAreas = [];
      }
    }
  }

  const lessonLibrary = {
    IAM: [
      "IAM users, groups, roles, and policies",
      "Temporary credentials and role-based access",
      "Least privilege access design",
    ],
    S3: [
      "Buckets, objects, and storage classes",
      "Static website hosting",
      "Bucket policies and permissions",
    ],
    EC2: [
      "Launching and managing virtual servers",
      "Security groups and key pairs",
      "Choosing EC2 instance types",
    ],
    Security: [
      "AWS KMS basics",
      "Encryption at rest vs in transit",
      "Key management and rotation",
    ],
    Networking: [
      "Security groups vs network ACLs",
      "Inbound and outbound traffic control",
      "VPC basics and subnet concepts",
    ],
    Storage: [
      "Object storage fundamentals",
      "S3 use cases",
      "When to choose storage services",
    ],
  };

  const defaultRoadmap = [
    "Review the assessment concepts",
    "Study the weak areas identified in your score",
    "Practice scenario-based questions",
  ];

  const roadmapTopics =
    weakAreas.length > 0
      ? weakAreas.flatMap((area) => {
          const lessons = lessonLibrary[area] || [`Intro to ${area}`];
          return lessons.map((lesson) => ({
            concept: area,
            title: lesson,
          }));
        })
      : defaultRoadmap.map((item) => ({
          concept: "General",
          title: item,
        }));

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "50px auto",
        padding: "30px",
        fontFamily: "Arial, sans-serif",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "10px", color: "#0f172a" }}>
        Personalized Learning Roadmap
      </h1>

      <p style={{ color: "#475569", marginTop: 0 }}>
        Strong areas: {strongAreas.length > 0 ? strongAreas.join(", ") : "None"}
      </p>

      <div
        style={{
          marginTop: "24px",
          display: "grid",
          gap: "16px",
        }}
      >
        {roadmapTopics.map((topic, index) => (
          <div
            key={`${topic.concept}-${index}`}
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
                <h3 style={{ margin: 0, color: "#0f172a" }}>{topic.title}</h3>
                <p style={{ margin: "6px 0 0", color: "#475569" }}>
                  Concept: {topic.concept}
                </p>
              </div>

              <button
                onClick={() => navigate("/lesson", { state: { topic } })}
                style={{
                  padding: "10px 16px",
                  borderRadius: "10px",
                  border: "none",
                  background: "#2563eb",
                  color: "white",
                  cursor: "pointer",
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