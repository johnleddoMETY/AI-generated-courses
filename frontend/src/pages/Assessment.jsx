import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Assessment() {
  const questions = [
    {
      id: 1,
      question: "What does IAM stand for?",
      options: [
        "Identity and Access Management",
        "Internet Access Module",
        "Internal Account Manager",
        "Identity Authorization Model",
      ],
    },
    {
      id: 2,
      question: "Which AWS service is used for object storage?",
      options: ["EC2", "Lambda", "S3", "RDS"],
    },
    {
      id: 3,
      question: "Which service manages virtual servers?",
      options: ["S3", "EC2", "IAM", "CloudFront"],
    },
  ];

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});

  const question = questions[currentQuestion];

  const handleSelect = (option) => {
    setAnswers({
      ...answers,
      [question.id]: option,
    });
  };

  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const submitAssessment = () => {
    console.log(answers);

    navigate("/results");
  };

  const navigate = useNavigate();

  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "40px auto",
        padding: "30px",
        fontFamily: "Arial",
      }}
    >
      <h1>Assessment</h1>

      <p>
        Question {currentQuestion + 1} of {questions.length}
      </p>

      <div
        style={{
          height: "10px",
          background: "#ddd",
          borderRadius: "10px",
          overflow: "hidden",
          marginBottom: "30px",
        }}
      >
        <div
          style={{
            width: `${
              ((currentQuestion + 1) / questions.length) * 100
            }%`,
            height: "100%",
            background: "#2563eb",
          }}
        />
      </div>

      <h2>{question.question}</h2>

      <div style={{ marginTop: "25px" }}>
        {question.options.map((option) => (
          <div
            key={option}
            style={{
              marginBottom: "15px",
            }}
          >
            <label>
              <input
                type="radio"
                name={`question-${question.id}`}
                value={option}
                checked={answers[question.id] === option}
                onChange={() => handleSelect(option)}
              />

              <span style={{ marginLeft: "10px" }}>{option}</span>
            </label>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: "40px",
        }}
      >
        <button
          onClick={previousQuestion}
          disabled={currentQuestion === 0}
        >
          Previous
        </button>

        {currentQuestion === questions.length - 1 ? (
          <button onClick={submitAssessment}>
            Submit Assessment
          </button>
        ) : (
          <button onClick={nextQuestion}>
            Next
          </button>
        )}
      </div>
    </div>
  );
}

export default Assessment;