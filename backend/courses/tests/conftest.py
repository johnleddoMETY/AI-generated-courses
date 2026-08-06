from datetime import datetime, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from llm_engine import (
    Assessment,
    Course,
    DomainScore,
    ExamDomain,
    FillInBlankQuestion,
    FullTextQuestion,
    GradedAssessment,
    Lesson,
    LessonExample,
    LessonPracticeQuestion,
    LessonSection,
    MultiAnswerQuestion,
    QuestionOption,
    QuestionResult,
    QuestionTypeWeight,
    Roadmap,
    RoadmapItem,
    SingleAnswerQuestion,
    SkippedDomain,
    Syllabus,
)
from rest_framework.test import APIClient

# Mirrors tests/conftest.py at the repo root — keeps backend tests isolated
# from the developer's real .env / exported LLM_* vars too.
_LLM_ENV_VARS = [
    "LLM_MODEL_DEFAULT",
    "LLM_MODEL_SYLLABUS",
    "LLM_MODEL_ASSESSMENT",
    "LLM_MODEL_GRADING",
    "LLM_MODEL_ROADMAP",
    "LLM_FALLBACK_MODELS",
    "LLM_TEMPERATURE_SYLLABUS",
    "LLM_TEMPERATURE_ASSESSMENT",
    "LLM_TEMPERATURE_GRADING",
    "LLM_TEMPERATURE_ROADMAP",
    "LLM_TIMEOUT_SECONDS",
    "LLM_NUM_RETRIES",
    "PROFICIENCY_WEAK_BELOW",
    "PROFICIENCY_PROFICIENT_AT",
]


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# Real Supabase projects sign session tokens with an asymmetric key (ES256)
# verified via a JWKS endpoint. Tests mint their own keypair and monkeypatch
# the JWKS lookup so auth verification works offline, without a live
# Supabase project or network access.
_TEST_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()


class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _FakeJWKSClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(_TEST_PUBLIC_KEY)


@pytest.fixture(autouse=True)
def _patch_jwks_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("courses.authentication._get_jwks_client", lambda: _FakeJWKSClient())


# Matches every test fixture's Syllabus.owner_id below, so api_client (and
# anything it creates) is treated as the same authenticated user.
TEST_USER_ID = "test-user-id"
OTHER_USER_ID = "other-user-id"


def _make_token(sub: str = TEST_USER_ID, email: str = "test@example.com") -> str:
    return jwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated", "role": "authenticated"},
        _TEST_PRIVATE_KEY,
        algorithm="ES256",
    )


@pytest.fixture
def api_client() -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_token()}")
    return client


@pytest.fixture
def other_user_client() -> APIClient:
    """A different authenticated user — for cross-user isolation tests."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_token(sub=OTHER_USER_ID, email='other@example.com')}")
    return client


@pytest.fixture
def anonymous_client() -> APIClient:
    return APIClient()


@pytest.fixture
def sample_syllabus() -> Syllabus:
    return Syllabus(
        syllabus_id="11111111-1111-1111-1111-111111111111",
        topic="Cloud Architecture",
        certification="AWS Solutions Architect Associate SAA-C03",
        exam_code="SAA-C03",
        domains=[
            ExamDomain(
                domain_id="design-resilient-architectures",
                name="Design Resilient Architectures",
                weight_percent=60.0,
                key_topics=["High availability", "Disaster recovery"],
            ),
            ExamDomain(
                domain_id="design-secure-architectures",
                name="Design Secure Architectures",
                weight_percent=40.0,
                key_topics=["IAM", "KMS"],
            ),
        ],
        question_type_mix=[
            QuestionTypeWeight(question_type="single_answer", weight_percent=80.0),
            QuestionTypeWeight(question_type="multi_answer", weight_percent=20.0),
        ],
        source_note="Based on the official SAA-C03 exam guide.",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_assessment(sample_syllabus: Syllabus) -> Assessment:
    return Assessment(
        assessment_id="22222222-2222-2222-2222-222222222222",
        syllabus_id=sample_syllabus.syllabus_id,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        domains=sample_syllabus.domains,
        questions=[
            SingleAnswerQuestion(
                question_id="33333333-3333-3333-3333-333333333333",
                domain_id="design-resilient-architectures",
                difficulty="easy",
                stem="Which AWS service distributes traffic across Availability Zones?",
                options=[
                    QuestionOption(option_id="A", text="Elastic Load Balancing"),
                    QuestionOption(option_id="B", text="Amazon S3"),
                    QuestionOption(option_id="C", text="Amazon RDS"),
                    QuestionOption(option_id="D", text="AWS Lambda"),
                ],
                correct_option_id="A",
                explanation="ELB distributes traffic across healthy targets in multiple AZs.",
            ),
        ],
        num_questions=1,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_assessment_all_types(sample_syllabus: Syllabus) -> Assessment:
    """One question of each type — for exercising answer-key stripping and
    answer submission across single_answer, multi_answer, fill_in_blank,
    and full_text."""
    return Assessment(
        assessment_id="88888888-8888-8888-8888-888888888888",
        syllabus_id=sample_syllabus.syllabus_id,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        domains=sample_syllabus.domains,
        questions=[
            SingleAnswerQuestion(
                question_id="q-single",
                domain_id="design-resilient-architectures",
                difficulty="easy",
                stem="Which AWS service distributes traffic across Availability Zones?",
                options=[
                    QuestionOption(option_id="A", text="Elastic Load Balancing"),
                    QuestionOption(option_id="B", text="Amazon S3"),
                    QuestionOption(option_id="C", text="Amazon RDS"),
                    QuestionOption(option_id="D", text="AWS Lambda"),
                ],
                correct_option_id="A",
                explanation="ELB distributes traffic across healthy targets in multiple AZs.",
            ),
            MultiAnswerQuestion(
                question_id="q-multi",
                domain_id="design-resilient-architectures",
                difficulty="medium",
                stem="Which of these are AWS compute services? (select all that apply)",
                options=[
                    QuestionOption(option_id="A", text="EC2"),
                    QuestionOption(option_id="B", text="Lambda"),
                    QuestionOption(option_id="C", text="S3"),
                    QuestionOption(option_id="D", text="RDS"),
                ],
                correct_option_ids=["A", "B"],
                explanation="EC2 and Lambda are compute services; S3 and RDS are not.",
            ),
            FillInBlankQuestion(
                question_id="q-fill",
                domain_id="design-secure-architectures",
                difficulty="easy",
                stem="AWS's identity and access management service is abbreviated ___.",
                accepted_answers=["IAM"],
                explanation="IAM stands for Identity and Access Management.",
            ),
            FullTextQuestion(
                question_id="q-text",
                domain_id="design-secure-architectures",
                difficulty="hard",
                stem="Describe the principle of least privilege.",
                rubric="Full credit requires mentioning minimal necessary permissions and reducing blast radius.",
                explanation="Least privilege limits access to only what's needed for a task.",
            ),
        ],
        num_questions=4,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_graded_assessment(sample_assessment: Assessment) -> GradedAssessment:
    return GradedAssessment(
        assessment_id=sample_assessment.assessment_id,
        overall_score_percent=100.0,
        question_results=[
            QuestionResult(
                question_id="33333333-3333-3333-3333-333333333333",
                domain_id="design-resilient-architectures",
                question_type="single_answer",
                correct=True,
                score_percent=100.0,
                selected_option_id="A",
                correct_option_id="A",
                explanation="ELB distributes traffic across healthy targets in multiple AZs.",
            )
        ],
        domain_scores=[
            DomainScore(
                domain_id="design-resilient-architectures",
                domain_name="Design Resilient Architectures",
                weight_percent=60.0,
                questions_total=1,
                questions_correct=1,
                score_percent=100.0,
                proficiency="proficient",
            )
        ],
        gaps=[],
        diagnostic_summary="Strong grasp of resilient architecture concepts.",
        strengths_summary="Correctly identified load balancing for high availability.",
        graded_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_roadmap(sample_assessment: Assessment, sample_syllabus: Syllabus) -> Roadmap:
    return Roadmap(
        roadmap_id="44444444-4444-4444-4444-444444444444",
        assessment_id=sample_assessment.assessment_id,
        syllabus_id=sample_syllabus.syllabus_id,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        exam_date=None,
        items=[
            RoadmapItem(
                item_id="55555555-5555-5555-5555-555555555555",
                domain_id="design-secure-architectures",
                title="AWS IAM Fundamentals",
                objective="Understand IAM roles, policies, and permissions.",
                subtopics=["IAM policies", "Roles vs. users"],
                why_included="Moderate gap in security domain.",
                priority=1,
                estimated_hours=2.0,
                prerequisites=[],
            )
        ],
        skipped_domains=[
            SkippedDomain(
                domain_id="design-resilient-architectures",
                reason="Scored 100% — proficient; not re-taught.",
            )
        ],
        total_estimated_hours=2.0,
        weekly_plan=None,
        guidance_summary="Focus on security fundamentals.",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_course(sample_roadmap: Roadmap) -> Course:
    return Course(
        course_id="66666666-6666-6666-6666-666666666666",
        roadmap_id=sample_roadmap.roadmap_id,
        topic=sample_roadmap.topic,
        certification=sample_roadmap.certification,
        lessons=[
            Lesson(
                lesson_id="77777777-7777-7777-7777-777777777777",
                item_id=sample_roadmap.items[0].item_id,
                title="AWS IAM Fundamentals",
                sections=[
                    LessonSection(
                        heading="What is IAM?",
                        body_markdown="IAM lets you manage access to AWS services and resources.",
                    )
                ],
                examples=[
                    LessonExample(
                        scenario="A team needs read-only access to an S3 bucket.",
                        walkthrough="Create an IAM policy granting s3:GetObject and attach it to a group.",
                    )
                ],
                practice_questions=[
                    LessonPracticeQuestion(
                        question="What AWS service manages user permissions?",
                        answer="IAM",
                        explanation="IAM (Identity and Access Management) controls who can do what.",
                    )
                ],
                summary="IAM governs authentication and authorization in AWS.",
                created_at=datetime.now(timezone.utc),
            )
        ],
        total_estimated_hours=2.0,
        created_at=datetime.now(timezone.utc),
    )
