import { useNavigate } from "react-router-dom";

function Roadmap() {
  const navigate = useNavigate();

  const roadmap = [
    {
      title: "Identity and Access Management",
      completed: false,
    },
    {
      title: "Encryption Fundamentals",
      completed: false,
    },
    {
      title: "AWS KMS",
      completed: false,
    },
  ];

  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "50px auto",
        padding: "30px",
      }}
    >
      <h1>Your Personalized Roadmap</h1>

      {roadmap.map((lesson, index) => (
        <div
          key={index}
          style={{
            padding: "15px",
            border: "1px solid #ddd",
            marginBottom: "15px",
            borderRadius: "8px",
          }}
        >
          <h3>{lesson.title}</h3>

          <button
            onClick={() => navigate("/lesson")}
          >
            Start Lesson
          </button>
        </div>
      ))}
    </div>
  );
}

export default Roadmap;