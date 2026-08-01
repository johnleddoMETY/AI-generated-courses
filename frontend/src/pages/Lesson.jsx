import { useLocation, useNavigate } from "react-router-dom";

const STORAGE_KEY = "ai_generated_courses_assessment";

function Lesson() {
  const navigate = useNavigate();
  const location = useLocation();

  let topic = location.state?.topic;

  if (!topic) {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const weakArea = parsed?.results?.weakAreas?.[0];
        topic = weakArea
          ? {
              concept: weakArea,
              title: `Intro to ${weakArea}`,
            }
          : {
              concept: "General",
              title: "Learning Topic",
            };
      } catch {
        topic = {
          concept: "General",
          title: "Learning Topic",
        };
      }
    } else {
      topic = {
        concept: "General",
        title: "Learning Topic",
      };
    }
  }

  const lessonContent = {
    IAM: [
      "IAM users represent individual identities in AWS.",
      "Groups let you manage permissions for multiple users at once.",
      "Roles provide temporary access without long-term credentials.",
      "Policies define what actions are allowed or denied.",
    ],
    S3: [
      "Amazon S3 is object storage used for storing files and data.",
      "It is commonly used for backups, static websites, and media storage.",
      "Permissions can be controlled with bucket policies and ACLs.",
    ],
    EC2: [
      "Amazon EC2 provides virtual servers in the cloud.",
      "You choose instance types based on CPU, memory, and performance needs.",
      "Security groups and key pairs are important for access control.",
    ],
    Security: [
      "AWS KMS helps manage encryption keys.",
      "Encryption at rest protects stored data.",
      "Encryption in transit protects data while it moves across networks.",
    ],
    Networking: [
      "Security groups control instance-level traffic.",
      "VPCs help isolate your AWS network.",
      "Subnets organize resources within a VPC.",
    ],
    Storage: [
      "Object storage is good for files, images, and backups.",
      "Choose the right storage class based on access frequency.",
      "S3 is a common AWS storage service for many use cases.",
    ],
  };

  const bullets = lessonContent[topic.concept] || [
    `Introductory notes for ${topic.concept}.`,
    "Review the key terminology and use cases.",
    "Practice scenario-based questions after reading.",
  ];

  const markComplete = () => {
    alert("Lesson marked complete!");
    navigate("/roadmap");
  };

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
      <h1 style={{ marginBottom: "8px", color: "#0f172a" }}>{topic.title}</h1>
      <p style={{ color: "#475569", marginTop: 0 }}>Concept: {topic.concept}</p>

      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: "14px",
          padding: "24px",
          background: "#ffffff",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <h2 style={{ marginTop: 0, color: "#0f172a" }}>Lesson Notes</h2>

        <ul style={{ lineHeight: 1.8, color: "#111827" }}>
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div
        style={{
          marginTop: "24px",
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => navigate("/roadmap")}
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
          Back to Roadmap
        </button>

        <button
          onClick={markComplete}
          style={{
            padding: "12px 20px",
            borderRadius: "10px",
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Mark Lesson Complete
        </button>
      </div>
    </div>
  );
}

export default Lesson;