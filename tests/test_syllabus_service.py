from datetime import timezone

import pytest

from llm_engine.schemas import LLMExamDomain, QuestionTypeWeight, SyllabusLLMResponse
from llm_engine.services.syllabus import generate_syllabus


def test_generate_syllabus_assigns_ids_and_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_structured_completion(*args: object, **kwargs: object) -> SyllabusLLMResponse:
        assert kwargs["task"] == "syllabus"
        return SyllabusLLMResponse(
            exam_code="SAA-C03",
            domains=[
                LLMExamDomain(
                    name="Design Secure Architectures",
                    weight_percent=30.0,
                    key_topics=["IAM", "KMS"],
                ),
                LLMExamDomain(
                    name="Design Secure Architectures",  # duplicate name -> deduped slug
                    weight_percent=70.0,
                    key_topics=["VPC"],
                ),
            ],
            question_type_mix=[
                QuestionTypeWeight(question_type="single_answer", weight_percent=80.0),
                QuestionTypeWeight(question_type="multi_answer", weight_percent=20.0),
            ],
            source_note="Official blueprint.",
        )

    monkeypatch.setattr(
        "llm_engine.services.syllabus.structured_completion", fake_structured_completion
    )

    syllabus = generate_syllabus("Cloud Architecture", "AWS SAA-C03")

    assert len(syllabus.syllabus_id) == 36  # UUID4 string
    assert syllabus.topic == "Cloud Architecture"
    assert syllabus.certification == "AWS SAA-C03"
    assert syllabus.exam_code == "SAA-C03"
    assert [d.domain_id for d in syllabus.domains] == [
        "design-secure-architectures",
        "design-secure-architectures-2",
    ]
    assert syllabus.domains[0].weight_percent == 30.0
    assert syllabus.source_note == "Official blueprint."
    assert syllabus.created_at.tzinfo == timezone.utc
    assert [(w.question_type, w.weight_percent) for w in syllabus.question_type_mix] == [
        ("single_answer", 80.0),
        ("multi_answer", 20.0),
    ]


def test_generate_syllabus_warns_on_bad_type_mix_total(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fake_structured_completion(*args: object, **kwargs: object) -> SyllabusLLMResponse:
        return SyllabusLLMResponse(
            exam_code=None,
            domains=[LLMExamDomain(name="Domain", weight_percent=100.0, key_topics=["t"])],
            question_type_mix=[QuestionTypeWeight(question_type="single_answer", weight_percent=40.0)],
            source_note="Generic breakdown.",
        )

    monkeypatch.setattr(
        "llm_engine.services.syllabus.structured_completion", fake_structured_completion
    )

    with caplog.at_level("WARNING"):
        generate_syllabus("Cloud Architecture", "Fictional Cert")

    assert "question_type_mix" in caplog.text
