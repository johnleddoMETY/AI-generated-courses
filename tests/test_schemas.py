from datetime import date, datetime, timezone

from llm_engine.schemas import (
    Assessment,
    DomainScore,
    ExamDomain,
    GradedAssessment,
    KnowledgeGap,
    Question,
    QuestionOption,
    QuestionResult,
    Roadmap,
    RoadmapItem,
    SkippedDomain,
    StudyWeek,
    Syllabus,
    UserAnswer,
)

_NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)


def _syllabus() -> Syllabus:
    return Syllabus(
        syllabus_id="7b0d4a4e-0000-4000-8000-000000000001",
        topic="Cloud Architecture",
        certification="AWS Solutions Architect Associate SAA-C03",
        exam_code="SAA-C03",
        domains=[
            ExamDomain(
                domain_id="design-secure-architectures",
                name="Design Secure Architectures",
                weight_percent=30.0,
                key_topics=["IAM", "network boundaries"],
            )
        ],
        source_note="Official SAA-C03 blueprint.",
        created_at=_NOW,
    )


def _assessment(syllabus: Syllabus) -> Assessment:
    return Assessment(
        assessment_id="7b0d4a4e-0000-4000-8000-000000000002",
        syllabus_id=syllabus.syllabus_id,
        topic=syllabus.topic,
        certification=syllabus.certification,
        domains=syllabus.domains,
        questions=[
            Question(
                question_id="7b0d4a4e-0000-4000-8000-000000000003",
                domain_id="design-secure-architectures",
                difficulty="medium",
                stem="Which design most restricts administrative access?",
                options=[
                    QuestionOption(option_id="A", text="IAM roles with MFA"),
                    QuestionOption(option_id="B", text="Shared root credentials"),
                    QuestionOption(option_id="C", text="Disable CloudTrail"),
                    QuestionOption(option_id="D", text="Open security groups"),
                ],
                correct_option_id="A",
                explanation="IAM roles with MFA minimize standing privilege; the rest weaken security.",
            )
        ],
        num_questions=1,
        created_at=_NOW,
    )


def test_all_domain_models_round_trip_json() -> None:
    syllabus = _syllabus()
    assessment = _assessment(syllabus)

    graded = GradedAssessment(
        assessment_id=assessment.assessment_id,
        overall_score_percent=100.0,
        question_results=[
            QuestionResult(
                question_id=assessment.questions[0].question_id,
                domain_id="design-secure-architectures",
                correct=True,
                selected_option_id="A",
                correct_option_id="A",
                explanation=assessment.questions[0].explanation,
            )
        ],
        domain_scores=[
            DomainScore(
                domain_id="design-secure-architectures",
                domain_name="Design Secure Architectures",
                weight_percent=30.0,
                questions_total=1,
                questions_correct=1,
                score_percent=100.0,
                proficiency="proficient",
            )
        ],
        gaps=[
            KnowledgeGap(
                domain_id="design-secure-architectures",
                gap_summary="Confuses SCP deny semantics with IAM permission boundaries.",
                severity="minor",
                evidence_question_ids=[assessment.questions[0].question_id],
            )
        ],
        diagnostic_summary="Strong secure-architecture baseline.",
        strengths_summary="Correctly applies least-privilege access design.",
        graded_at=_NOW,
    )

    roadmap = Roadmap(
        roadmap_id="7b0d4a4e-0000-4000-8000-000000000004",
        assessment_id=assessment.assessment_id,
        syllabus_id=syllabus.syllabus_id,
        topic=syllabus.topic,
        certification=syllabus.certification,
        exam_date=date(2026, 9, 15),
        items=[
            RoadmapItem(
                item_id="7b0d4a4e-0000-4000-8000-000000000005",
                domain_id="design-secure-architectures",
                title="IAM permission boundaries deep dive",
                objective="Distinguish SCPs from permission boundaries in multi-account setups.",
                subtopics=["SCP evaluation logic", "Permission boundary use cases"],
                why_included="You missed the SCP-vs-boundary question; this closes that specific gap.",
                priority=1,
                estimated_hours=2.5,
                prerequisites=[],
            )
        ],
        skipped_domains=[
            SkippedDomain(
                domain_id="design-secure-architectures",
                reason="Scored proficient; reduced to one light review item.",
            )
        ],
        total_estimated_hours=2.5,
        weekly_plan=[
            StudyWeek(
                week_number=1,
                focus="Close the IAM boundary gap, then review.",
                item_ids=["7b0d4a4e-0000-4000-8000-000000000005"],
                estimated_hours=2.5,
            )
        ],
        guidance_summary="Short, targeted plan; most domains already proficient.",
        created_at=_NOW,
    )

    user_answer = UserAnswer(question_id=assessment.questions[0].question_id, selected_option_id=None)

    for instance in (syllabus, assessment, graded, roadmap, user_answer):
        restored = type(instance).model_validate_json(instance.model_dump_json())
        assert restored == instance


def test_roadmap_without_exam_date_round_trips() -> None:
    roadmap = Roadmap(
        roadmap_id="r-1",
        assessment_id="a-1",
        syllabus_id="s-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        exam_date=None,
        items=[],
        skipped_domains=[],
        total_estimated_hours=0.0,
        weekly_plan=None,
        guidance_summary="No items needed.",
        created_at=_NOW,
    )
    assert Roadmap.model_validate_json(roadmap.model_dump_json()) == roadmap
