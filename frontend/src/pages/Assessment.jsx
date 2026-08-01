import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const STORAGE_KEY = "ai_generated_courses_assessment";

function shuffleArray(array) {
  const copied = [...array];
  for (let i = copied.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copied[i], copied[j]] = [copied[j], copied[i]];
  }
  return copied;
}

function getKnowledgePoints(isCorrect, confidenceLevel) {
  if (isCorrect) {
    if (confidenceLevel === "High") return 3;
    if (confidenceLevel === "Medium") return 2;
    return 1;
  }

  if (confidenceLevel === "High") return -2;
  if (confidenceLevel === "Medium") return -1;
  return 0;
}

function getMasteryPoints(isCorrect, confidenceLevel) {
  if (!isCorrect) return 0;
  if (confidenceLevel === "High") return 3;
  if (confidenceLevel === "Medium") return 2;
  return 0;
}

function Assessment() {
  const navigate = useNavigate();

  const questions = useMemo(
    () => [
      {
        id: 1,
        concept: "IAM",
        difficulty: "medium",
        question:
          "A company wants employees to access AWS resources temporarily without long-term passwords. What should they use?",
        options: ["IAM role", "Security group", "S3 bucket policy", "CloudWatch alarm"],
        correctAnswer: "IAM role",
      },
      {
        id: 2,
        concept: "IAM",
        difficulty: "easy",
        question:
          "A team wants to apply the same permissions to 20 users at once. What should they use?",
        options: ["IAM group", "EC2 instance profile", "S3 lifecycle rule", "NACL"],
        correctAnswer: "IAM group",
      },
      {
        id: 3,
        concept: "S3",
        difficulty: "easy",
        question:
          "A team needs to store and retrieve a large number of photos on AWS. Which service is the best fit?",
        options: ["Amazon S3", "Amazon EC2", "Amazon RDS", "AWS Lambda"],
        correctAnswer: "Amazon S3",
      },
      {
        id: 4,
        concept: "S3",
        difficulty: "medium",
        question:
          "Which AWS service is commonly used to host static website files such as HTML, CSS, and images?",
        options: ["Amazon S3", "Amazon EC2", "AWS Step Functions", "Amazon ECS"],
        correctAnswer: "Amazon S3",
      },
      {
        id: 5,
        concept: "EC2",
        difficulty: "medium",
        question:
          "A developer needs a virtual server to run a custom application 24/7. Which AWS service should they choose?",
        options: ["Amazon EC2", "Amazon CloudFront", "Amazon S3", "AWS IAM"],
        correctAnswer: "Amazon EC2",
      },
      {
        id: 6,
        concept: "EC2",
        difficulty: "hard",
        question:
          "A team needs operating-system-level control, custom software installation, and persistent compute for an app. Which service is the best fit?",
        options: ["Amazon EC2", "Amazon S3", "AWS KMS", "Amazon Route 53"],
        correctAnswer: "Amazon EC2",
      },
      {
        id: 7,
        concept: "Security",
        difficulty: "hard",
        question:
          "A company must encrypt data at rest with a key that it can manage and rotate in AWS. Which service should they use?",
        options: ["AWS KMS", "Amazon Route 53", "Amazon SNS", "AWS Budgets"],
        correctAnswer: "AWS KMS",
      },
      {
        id: 8,
        concept: "Security",
        difficulty: "medium",
        question:
          "A web application needs protection against common malicious HTTP requests like SQL injection and XSS. Which AWS service should be used?",
        options: ["AWS WAF", "Amazon EBS", "AWS CloudTrail", "Amazon SQS"],
        correctAnswer: "AWS WAF",
      },
      {
        id: 9,
        concept: "Networking",
        difficulty: "medium",
        question:
          "An application needs to allow only inbound HTTP and HTTPS traffic to a group of instances. What should be configured?",
        options: ["Security group", "IAM policy", "S3 lifecycle rule", "CloudTrail trail"],
        correctAnswer: "Security group",
      },
      {
        id: 10,
        concept: "Networking",
        difficulty: "easy",
        question:
          "Which AWS feature creates an isolated virtual network for your resources?",
        options: ["VPC", "CloudWatch", "Lambda", "IAM"],
        correctAnswer: "VPC",
      },
    ],
    []
  );

  const questionsWithShuffledOptions = useMemo(() => {
    return questions.map((question) => ({
      ...question,
      shuffledOptions: shuffleArray(question.options),
    }));
  }, [questions]);

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [confidence, setConfidence] = useState({});
  const [explanations, setExplanations] = useState({});

  const question = questionsWithShuffledOptions[currentQuestion];
  const selectedAnswer = answers[question.id] || "";
  const selectedConfidence = confidence[question.id] || "";
  const selectedExplanation = explanations[question.id] || "";

  const handleAnswerSelect = (option) => {
    setAnswers((prev) => ({
      ...prev,
      [question.id]: option,
    }));
  };

  const handleConfidenceSelect = (level) => {
    setConfidence((prev) => ({
      ...prev,
      [question.id]: level,
    }));
  };

  const handleExplanationChange = (value) => {
    setExplanations((prev) => ({
      ...prev,
      [question.id]: value,
    }));
  };

  const nextQuestion = () => {
    if (currentQuestion < questionsWithShuffledOptions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
    }
  };

  const calculateResults = () => {
    const conceptStats = {};
    let knowledgePoints = 0;
    let masteryPoints = 0;
    let totalCorrect = 0;
    let likelyGuessCount = 0;
    let overconfidentWrongCount = 0;
    let uncertainWrongCount = 0;

    questionsWithShuffledOptions.forEach((q) => {
      const selected = answers[q.id];
      const confidenceLevel = confidence[q.id] || "Low";
      const isCorrect = selected === q.correctAnswer;

      const questionKnowledgePoints = getKnowledgePoints(isCorrect, confidenceLevel);
      const questionMasteryPoints = getMasteryPoints(isCorrect, confidenceLevel);

      knowledgePoints += questionKnowledgePoints;
      masteryPoints += questionMasteryPoints;

      if (!conceptStats[q.concept]) {
        conceptStats[q.concept] = {
          total: 0,
          correct: 0,
          masteryPoints: 0,
          knowledgePoints: 0,
          lowConfidenceCorrect: 0,
          mediumHighConfidenceCorrect: 0,
          likelyGuessQuestions: [],
          overconfidentWrongQuestions: [],
          missedQuestions: [],
          confidenceSum: 0,
        };
      }

      const confidenceValue =
        confidenceLevel === "High" ? 3 : confidenceLevel === "Medium" ? 2 : 1;

      conceptStats[q.concept].total += 1;
      conceptStats[q.concept].knowledgePoints += questionKnowledgePoints;
      conceptStats[q.concept].masteryPoints += questionMasteryPoints;
      conceptStats[q.concept].confidenceSum += confidenceValue;

      if (isCorrect) {
        totalCorrect += 1;
        if (confidenceLevel === "Low") {
          likelyGuessCount += 1;
          conceptStats[q.concept].lowConfidenceCorrect += 1;
          conceptStats[q.concept].likelyGuessQuestions.push(q.question);
        } else {
          conceptStats[q.concept].mediumHighConfidenceCorrect += 1;
        }
      } else {
        conceptStats[q.concept].missedQuestions.push(q.question);
        if (confidenceLevel === "High") {
          overconfidentWrongCount += 1;
          conceptStats[q.concept].overconfidentWrongQuestions.push(q.question);
        } else {
          uncertainWrongCount += 1;
        }
      }

      if (isCorrect) {
        conceptStats[q.concept].correct += 1;
      }
    });

    const totalQuestions = questionsWithShuffledOptions.length;
    const maxKnowledgePoints = totalQuestions * 3;
    const minKnowledgePoints = totalQuestions * -2;
    const maxMasteryPoints = totalQuestions * 3;

    const knowledgeScore = Math.max(
      0,
      Math.min(
        100,
        Math.round(
          ((knowledgePoints - minKnowledgePoints) /
            (maxKnowledgePoints - minKnowledgePoints)) *
            100
        )
      )
    );

    const masteryScore = Math.max(
      0,
      Math.min(100, Math.round((masteryPoints / maxMasteryPoints) * 100))
    );

    const accuracyScore = Math.round((totalCorrect / totalQuestions) * 100);

    const strongAreas = [];
    const weakAreas = [];

    Object.entries(conceptStats).forEach(([concept, stats]) => {
      const masteryPercent = Math.round((stats.masteryPoints / (stats.total * 3)) * 100);
      const confidenceQuality =
        stats.correct > 0
          ? stats.mediumHighConfidenceCorrect / stats.correct
          : 0;

      const isStrong =
        stats.total >= 2 &&
        masteryPercent >= 70 &&
        confidenceQuality >= 0.7 &&
        stats.lowConfidenceCorrect === 0;

      if (isStrong) {
        strongAreas.push(concept);
      } else {
        weakAreas.push(concept);
      }

      stats.masteryPercent = masteryPercent;
      stats.confidenceQuality = Math.round(confidenceQuality * 100);
      stats.averageConfidence = Number(
        (stats.confidenceSum / stats.total).toFixed(1)
      );
    });

    return {
      knowledgeScore,
      masteryScore,
      accuracyScore,
      knowledgePoints,
      masteryPoints,
      maxKnowledgePoints,
      minKnowledgePoints,
      strongAreas,
      weakAreas,
      conceptStats,
      likelyGuessCount,
      overconfidentWrongCount,
      uncertainWrongCount,
      answers,
      confidence,
      explanations,
    };
  };

  const submitAssessment = () => {
    const results = calculateResults();

    const payload = {
      answers,
      confidence,
      explanations,
      results,
    };

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));

    navigate("/results", {
      state: payload,
    });
  };

  const isCurrentQuestionHard = question.difficulty === "hard";

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "40px auto",
        padding: "30px",
        color: "#111827",
      }}
    >
      <h1 style={{ marginBottom: "8px", color: "#0f172a" }}>Assessment</h1>
      <p style={{ marginTop: 0, color: "#475569" }}>
        Question {currentQuestion + 1} of {questionsWithShuffledOptions.length}
      </p>

      <div
        style={{
          height: "10px",
          background: "#e2e8f0",
          borderRadius: "999px",
          overflow: "hidden",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            width: `${
              ((currentQuestion + 1) / questionsWithShuffledOptions.length) * 100
            }%`,
            height: "100%",
            background: "#2563eb",
            transition: "width 0.25s ease",
          }}
        />
      </div>

      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
          padding: "24px",
          background: "#ffffff",
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            marginBottom: "14px",
          }}
        >
          <span
            style={{
              display: "inline-block",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "#dbeafe",
              color: "#1d4ed8",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            Concept: {question.concept}
          </span>

          <span
            style={{
              display: "inline-block",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "#e2e8f0",
              color: "#334155",
              fontSize: "12px",
              fontWeight: 700,
              textTransform: "capitalize",
            }}
          >
            Difficulty: {question.difficulty}
          </span>
        </div>

        <h2 style={{ marginTop: 0, color: "#0f172a" }}>{question.question}</h2>

        <div style={{ marginTop: "20px" }}>
          {question.shuffledOptions.map((option) => (
            <label
              key={option}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "12px 14px",
                marginBottom: "12px",
                border: "1px solid #cbd5e1",
                borderRadius: "12px",
                cursor: "pointer",
                background: selectedAnswer === option ? "#eff6ff" : "#ffffff",
                color: "#111827",
              }}
            >
              <input
                type="radio"
                name={`question-${question.id}`}
                value={option}
                checked={selectedAnswer === option}
                onChange={() => handleAnswerSelect(option)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>

        <div style={{ marginTop: "24px" }}>
          <p style={{ marginBottom: "10px", fontWeight: 700, color: "#0f172a" }}>
            How confident are you in this answer?
          </p>

          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
            }}
          >
            {["Low", "Medium", "High"].map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => handleConfidenceSelect(level)}
                style={{
                  padding: "10px 14px",
                  borderRadius: "999px",
                  border:
                    selectedConfidence === level
                      ? "2px solid #2563eb"
                      : "1px solid #cbd5e1",
                  background: selectedConfidence === level ? "#dbeafe" : "#ffffff",
                  color: "#0f172a",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {isCurrentQuestionHard && (
          <div style={{ marginTop: "24px" }}>
            <p style={{ marginBottom: "8px", fontWeight: 700, color: "#0f172a" }}>
              One-line explanation
            </p>
            <textarea
              value={selectedExplanation}
              onChange={(e) => handleExplanationChange(e.target.value)}
              placeholder="Write why you chose this answer..."
              rows={4}
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "12px",
                border: "1px solid #cbd5e1",
                resize: "vertical",
                fontFamily: "inherit",
                background: "#ffffff",
                color: "#111827",
                outline: "none",
              }}
            />
          </div>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "12px",
            marginTop: "30px",
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            onClick={previousQuestion}
            disabled={currentQuestion === 0}
            style={{
              padding: "12px 18px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: currentQuestion === 0 ? "#e2e8f0" : "#ffffff",
              color: "#0f172a",
              cursor: currentQuestion === 0 ? "not-allowed" : "pointer",
              fontWeight: 700,
            }}
          >
            Previous
          </button>

          {currentQuestion === questionsWithShuffledOptions.length - 1 ? (
            <button
              type="button"
              onClick={submitAssessment}
              style={{
                padding: "12px 18px",
                borderRadius: "10px",
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              Submit Assessment
            </button>
          ) : (
            <button
              type="button"
              onClick={nextQuestion}
              style={{
                padding: "12px 18px",
                borderRadius: "10px",
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              Next
            </button>
          )}
        </div>
      </div>

      <div
        style={{
          marginTop: "18px",
          color: "#475569",
          fontSize: "14px",
          lineHeight: 1.6,
        }}
      >
        This assessment separates confidence-based mastery from lucky guesses.
        Low-confidence correct answers contribute very little to mastery, so a
        guess will not be treated as real understanding.
      </div>
    </div>
  );
}

export default Assessment;