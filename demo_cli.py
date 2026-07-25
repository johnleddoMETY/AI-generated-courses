#!/usr/bin/env python3
"""Terminal demo for the llm_engine pipeline.

Runs syllabus -> assessment -> (interactive or random answers) -> grading
-> roadmap with rich progress and result views. --json-out dumps every
artifact as pretty JSON — the example payloads for the backend teammate.

Usage:
    python demo_cli.py --topic "Cloud Architecture" \
        --certification "AWS Solutions Architect Associate SAA-C03" \
        --exam-date 2026-09-15 --num-questions 12
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from llm_engine import (
    Assessment,
    Course,
    GradedAssessment,
    LLMEngineError,
    Question,
    Roadmap,
    Syllabus,
    UserAnswer,
    generate_assessment,
    generate_course,
    generate_roadmap,
    generate_syllabus,
    grade_assessment,
)
from llm_engine.config import get_task_settings

console = Console()

_PROFICIENCY_STYLES = {"weak": "red", "developing": "yellow", "proficient": "green"}
_SEVERITY_STYLES = {"minor": "yellow", "moderate": "dark_orange", "critical": "red"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the llm_engine pipeline end to end.")
    parser.add_argument("--topic", required=True, help='Study topic, e.g. "Cloud Architecture"')
    parser.add_argument(
        "--certification",
        required=True,
        help='Certification name, e.g. "AWS Solutions Architect Associate SAA-C03"',
    )
    parser.add_argument(
        "--exam-date",
        type=date.fromisoformat,
        default=None,
        help="Exam date (YYYY-MM-DD); enables the weekly plan",
    )
    parser.add_argument("--num-questions", type=int, default=12, help="Assessment length")
    parser.add_argument(
        "--random-answers",
        action="store_true",
        help="Answer randomly instead of interactively (non-interactive runs)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory to dump syllabus/assessment/graded/roadmap JSON artifacts",
    )
    return parser.parse_args()


def check_api_key() -> None:
    """Explain exactly which env var to set before burning a failed call."""
    model = get_task_settings("syllabus").model
    provider = model.split("/", 1)[0]
    expected_var = {"openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}.get(provider)
    if expected_var and not os.getenv(expected_var):
        console.print(
            Panel(
                f"Model [bold]{model}[/bold] needs [bold]{expected_var}[/bold], "
                f"which is not set.\n\n"
                f"Copy .env.example to .env and set {expected_var}=<your key>.",
                title="Missing API key",
                border_style="red",
            )
        )
        sys.exit(1)


def collect_answers(assessment: Assessment, random_answers: bool) -> list[UserAnswer]:
    """Interactive one-question-at-a-time answering, or random selection."""
    if random_answers:
        return [_random_answer(question) for question in assessment.questions]

    answers: list[UserAnswer] = []
    for number, question in enumerate(assessment.questions, start=1):
        console.print()
        console.print(
            Panel(
                question.stem,
                title=f"Question {number}/{len(assessment.questions)} "
                f"[dim]({question.domain_id} · {question.difficulty} · {question.question_type})[/dim]",
            )
        )
        if question.question_type in ("single_answer", "multi_answer"):
            for option in question.options:
                console.print(f"  [bold]{option.option_id}[/bold]) {option.text}")
            if question.question_type == "single_answer":
                choice = Prompt.ask("Answer", choices=["A", "B", "C", "D", "S"], show_choices=True)
                answers.append(
                    UserAnswer(
                        question_id=question.question_id,
                        selected_option_id=None if choice == "S" else choice,  # type: ignore[arg-type]
                    )
                )
            else:
                raw = Prompt.ask("Answer(s), e.g. 'A,C', or 'S' to skip")
                selected = None if raw.strip().upper() == "S" else [c.strip().upper() for c in raw.split(",") if c.strip()]
                answers.append(
                    UserAnswer(question_id=question.question_id, selected_option_ids=selected)  # type: ignore[arg-type]
                )
        else:
            text = Prompt.ask("Answer (blank to skip)", default="")
            answers.append(
                UserAnswer(question_id=question.question_id, text_answer=text or None)
            )
    return answers


def _random_answer(question: Question) -> UserAnswer:
    if question.question_type == "single_answer":
        return UserAnswer(question_id=question.question_id, selected_option_id=random.choice(["A", "B", "C", "D"]))
    if question.question_type == "multi_answer":
        k = random.randint(1, len(question.options))
        picks = random.sample(["A", "B", "C", "D"], k=k)
        return UserAnswer(question_id=question.question_id, selected_option_ids=picks)  # type: ignore[arg-type]
    placeholder = random.choice(["Not sure.", "Something related to this topic."])
    return UserAnswer(question_id=question.question_id, text_answer=placeholder)


def show_syllabus(syllabus: Syllabus) -> None:
    table = Table(title=f"Syllabus — {syllabus.certification}"
                  + (f" ({syllabus.exam_code})" if syllabus.exam_code else ""))
    table.add_column("Domain")
    table.add_column("Weight", justify="right")
    table.add_column("Key topics")
    for domain in syllabus.domains:
        table.add_row(domain.name, f"{domain.weight_percent:.0f}%", ", ".join(domain.key_topics))
    console.print(table)
    console.print(f"[dim]Source: {syllabus.source_note}[/dim]")


def show_results(graded: GradedAssessment) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold]{graded.overall_score_percent}%[/bold] overall (weighted by exam domain weight)",
            title="Results",
        )
    )
    table = Table(title="Per-domain scores")
    table.add_column("Domain")
    table.add_column("Weight", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Correct", justify="right")
    table.add_column("Proficiency")
    for score in graded.domain_scores:
        style = _PROFICIENCY_STYLES[score.proficiency]
        table.add_row(
            score.domain_name,
            f"{score.weight_percent:.0f}%",
            f"{score.score_percent}%",
            f"{score.questions_correct}/{score.questions_total}",
            f"[{style}]{score.proficiency}[/{style}]",
        )
    console.print(table)

    skipped = [
        r
        for r in graded.question_results
        if r.selected_option_id is None
        and not r.selected_option_ids
        and not r.text_answer
    ]
    if skipped:
        console.print(f"[dim]{len(skipped)} question(s) skipped (counted incorrect).[/dim]")

    if graded.gaps:
        console.print("\n[bold]Knowledge gaps[/bold]")
        for gap in graded.gaps:
            style = _SEVERITY_STYLES[gap.severity]
            evidence = ", ".join(gap.evidence_question_ids) or "no linked questions"
            console.print(f"  [{style}]● {gap.severity}[/{style}] [{gap.domain_id}] "
                          f"{gap.gap_summary} [dim](evidence: {evidence})[/dim]")

    console.print(f"\n[bold]Diagnosis:[/bold] {graded.diagnostic_summary}")
    console.print(f"[bold]Strengths:[/bold] {graded.strengths_summary}")


def show_roadmap(roadmap: Roadmap) -> None:
    console.print()
    if roadmap.skipped_domains:
        lines = "\n".join(
            f"[green]✓ skipped[/green] [bold]{skipped.domain_id}[/bold] — {skipped.reason}"
            for skipped in roadmap.skipped_domains
        )
        console.print(Panel(lines, title="Already known — not re-taught", border_style="green"))

    table = Table(title=f"Study roadmap ({roadmap.total_estimated_hours:.1f}h total)")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Domain")
    table.add_column("Hours", justify="right")
    table.add_column("Why included")
    for item in roadmap.items:
        table.add_row(
            str(item.priority),
            item.title,
            item.domain_id,
            f"{item.estimated_hours:.1f}",
            item.why_included,
        )
    console.print(table)

    if roadmap.weekly_plan:
        items_by_id = {item.item_id: item for item in roadmap.items}
        week_table = Table(title=f"Weekly plan (exam {roadmap.exam_date})")
        week_table.add_column("Week", justify="right")
        week_table.add_column("Focus")
        week_table.add_column("Items")
        week_table.add_column("Hours", justify="right")
        for week in roadmap.weekly_plan:
            titles = ", ".join(
                items_by_id[item_id].title for item_id in week.item_ids if item_id in items_by_id
            )
            week_table.add_row(str(week.week_number), week.focus, titles, f"{week.estimated_hours:.1f}")
        console.print(week_table)

    console.print(f"\n[bold]Guidance:[/bold] {roadmap.guidance_summary}")


def show_course(course: Course) -> None:
    console.print()
    table = Table(title=f"Course — {len(course.lessons)} lesson(s), "
                        f"{course.total_estimated_hours:.1f}h total")
    table.add_column("#", justify="right")
    table.add_column("Lesson")
    table.add_column("Sections", justify="right")
    table.add_column("Examples", justify="right")
    table.add_column("Practice Qs", justify="right")
    for number, lesson in enumerate(course.lessons, start=1):
        table.add_row(
            str(number),
            lesson.title,
            str(len(lesson.sections)),
            str(len(lesson.examples)),
            str(len(lesson.practice_questions)),
        )
    console.print(table)


def dump_artifacts(
    directory: Path,
    syllabus: Syllabus,
    assessment: Assessment,
    graded: GradedAssessment,
    roadmap: Roadmap,
    course: Course,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "syllabus.json": syllabus,
        "assessment.json": assessment,
        "graded_assessment.json": graded,
        "roadmap.json": roadmap,
        "course.json": course,
    }
    for filename, model in artifacts.items():
        (directory / filename).write_text(model.model_dump_json(indent=2))
    console.print(f"[dim]Artifacts written to {directory}/[/dim]")


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(levelname)s %(name)s: %(message)s",
    )
    args = parse_args()
    check_api_key()

    try:
        with console.status("[bold]Stage 1/5 — generating syllabus...[/bold]"):
            syllabus = generate_syllabus(args.topic, args.certification)
        show_syllabus(syllabus)

        with console.status("[bold]Stage 2/5 — generating assessment...[/bold]"):
            assessment = generate_assessment(
                syllabus, num_questions=args.num_questions, exam_date=args.exam_date
            )

        answers = collect_answers(assessment, args.random_answers)

        with console.status("[bold]Stage 3/5 — grading...[/bold]"):
            graded = grade_assessment(assessment, answers)
        show_results(graded)

        with console.status("[bold]Stage 4/5 — generating roadmap...[/bold]"):
            roadmap = generate_roadmap(syllabus, graded, exam_date=args.exam_date)
        show_roadmap(roadmap)

        with console.status("[bold]Stage 5/5 — generating course...[/bold]"):
            course = generate_course(roadmap)
        show_course(course)
    except LLMEngineError as exc:
        console.print(Panel(str(exc), title="Pipeline failed", border_style="red"))
        sys.exit(1)

    if args.json_out:
        dump_artifacts(args.json_out, syllabus, assessment, graded, roadmap, course)


if __name__ == "__main__":
    main()
