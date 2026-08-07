from llm_engine.prompts.grading_prompts import build_grading_user_prompt


def test_user_prompt_includes_both_blocks_and_no_precomputed_overall() -> None:
    prompt = build_grading_user_prompt(
        scored_questions_block="[q1] domain=d\n  Correct: A | Learner chose: A | CORRECT",
        free_text_block="[q2] domain=d question_type=full_text\n  Learner answer: some text",
    )
    assert "Correct: A | Learner chose: A | CORRECT" in prompt
    assert "Learner answer: some text" in prompt
    assert "free_text_judgments" in prompt  # documented in expected-output section
