import os

import pytest

from llm_engine import Assessment, UserAnswer, run_full_pipeline


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="live LLM smoke test is opt-in (set RUN_LIVE_LLM_TESTS=1)",
)
def test_live_full_pipeline_smoke() -> None:
    def answer_provider(assessment: Assessment) -> list[UserAnswer]:
        return [
            UserAnswer(
                question_id=question.question_id,
                selected_option_id=question.options[0].option_id,
            )
            for question in assessment.questions
        ]

    syllabus, assessment, graded, roadmap = run_full_pipeline(
        "Cloud Architecture",
        "AWS Solutions Architect Associate SAA-C03",
        answer_provider,
        num_questions=4,
    )

    assert syllabus.domains
    assert len(assessment.questions) == 4
    assert len(graded.question_results) == 4
    assert roadmap.items or roadmap.skipped_domains
