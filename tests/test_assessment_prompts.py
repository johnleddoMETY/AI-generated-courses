from llm_engine.prompts.assessment_prompts import build_assessment_user_prompt


def test_user_prompt_includes_type_allocation_block() -> None:
    prompt = build_assessment_user_prompt(
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        domains_block="- domain-a: Domain A (100% of exam) — key topics: t",
        allocation_block="- domain-a: 4 question(s)",
        type_allocation_block="- single_answer: 3 question(s)\n- multi_answer: 1 question(s)",
        num_questions=4,
        exam_date_line="",
    )
    assert "single_answer: 3 question(s)" in prompt
    assert "multi_answer: 1 question(s)" in prompt
    assert "fill_in_blank" in prompt  # documented in the expected-output section
    assert "full_text" in prompt
