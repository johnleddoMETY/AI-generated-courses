"""Assessment prompts (V1).

Design intent: the model acts as a senior certification exam content
developer and psychometrician — the persona carries the MCQ craft
standards of real exam item writers. The per-domain question allocation
is computed in Python and stated in the prompt as a hard requirement, so
the model never does arithmetic. The user prompt restates the output
shape in words as belt-and-suspenders for the JSON-mode fallback, and a
retry suffix feeds post-validation errors back verbatim.
"""

ASSESSMENT_SYSTEM_V1 = """\
You are a senior certification exam content developer and psychometrician.
You write multiple-choice questions indistinguishable in craft from real
certification exam items.

MCQ craft rules — mandatory for every question:
- Exactly 4 options labeled A, B, C, D, with exactly ONE unambiguously
  correct answer.
- Distractors must be plausible: build each one from a common real
  misconception or mistake practitioners actually make. Never use obviously
  silly or throwaway options.
- Never use "all of the above" or "none of the above".
- The stem must pass the cover-the-options test: a knowledgeable candidate
  could answer it without seeing the options.
- For professional certifications, prefer scenario-based stems that place
  the candidate in a realistic job situation.
- The explanation must state why the correct answer is correct AND why each
  distractor is wrong.
- Every question's domain_id must be exactly one of the domain IDs provided.
- Follow the per-domain question allocation you are given exactly — it was
  computed from the official domain weights. Do not redistribute questions.
- Match the requested difficulty mix across the whole assessment.
"""

ASSESSMENT_USER_TEMPLATE_V1 = """\
## Syllabus

Topic: {topic}
Certification: {certification}

Domains — use these domain_id values exactly:
{domains_block}

## Question allocation (computed from official weights — follow exactly)

{allocation_block}
Total questions: {num_questions}
Difficulty mix across the whole assessment: roughly 30% easy, 50% medium, 20% hard.
{exam_date_block}
## Expected output

Return a JSON object with a single key "questions": a list of question
objects, each with domain_id (one of the IDs above), difficulty ("easy" |
"medium" | "hard"), stem (string), options (a list of exactly 4 objects,
each with option_id "A"/"B"/"C"/"D" and text), correct_option_id
("A"|"B"|"C"|"D"), and explanation (string).
"""

ASSESSMENT_RETRY_SUFFIX_V1 = """\

## Errors in your previous attempt

Your previous set of questions violated these requirements:
{errors_block}

Regenerate the complete set of questions, fixing every violation while
still following all rules above.
"""


def build_assessment_user_prompt(
    topic: str,
    certification: str,
    domains_block: str,
    allocation_block: str,
    num_questions: int,
    exam_date_line: str,
) -> str:
    """Render the assessment user prompt from pre-formatted data blocks."""
    exam_date_block = f"\n{exam_date_line}\n" if exam_date_line else "\n"
    return ASSESSMENT_USER_TEMPLATE_V1.format(
        topic=topic,
        certification=certification,
        domains_block=domains_block,
        allocation_block=allocation_block,
        num_questions=num_questions,
        exam_date_block=exam_date_block,
    )


def build_assessment_retry_suffix(errors: list[str]) -> str:
    """Render the retry suffix listing every post-validation error."""
    errors_block = "\n".join(f"- {error}" for error in errors)
    return ASSESSMENT_RETRY_SUFFIX_V1.format(errors_block=errors_block)
