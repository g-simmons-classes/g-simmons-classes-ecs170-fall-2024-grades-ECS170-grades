import argparse
from datetime import datetime
import sys
from typing import Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
import yaml


@dataclass
class PenaltyResult:
    days_late: int
    penalty: float


@dataclass
class AssignmentScore:
    name: str
    original_score: float
    adjusted_score: float
    days_late: int


def calculate_late_penalty(
    submitted_at: str, due_date: str, rate: float, max_penalty: float
) -> PenaltyResult:
    """Calculate late penalty based on submission date."""
    if not submitted_at or not due_date:
        print(
            f"Warning: Missing date - submitted: {submitted_at}, due: {due_date}",
            file=sys.stderr,
        )
        return PenaltyResult(0, 0)

    submitted = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    days_late = max(0, (submitted - due).days)
    penalty = min(max_penalty, rate * days_late)

    return PenaltyResult(days_late, penalty)


def process_assignment_category(
    category_name: str,
    scores: Dict,
    due_dates: Dict,
    weight: float,
    late_penalty_rate: float,
    late_penalty_max: float,
    drops: int = 0,
) -> tuple[float, Table]:
    """Process a category of assignments (quizzes, homework, or reflections)."""
    assignments = []
    for name, assignment in scores.items():
        penalty = calculate_late_penalty(
            assignment["submitted_at"],
            due_dates.get(name, ""),
            late_penalty_rate,
            late_penalty_max,
        )
        adjusted_score = assignment["score"] * (1 - penalty.penalty)
        assignments.append(
            AssignmentScore(
                name, assignment["score"], adjusted_score, penalty.days_late
            )
        )

    if drops > 0:
        assignments.sort(key=lambda x: x.adjusted_score, reverse=True)
        assignments = assignments[:-drops]

    avg_score = sum(a.adjusted_score for a in assignments) / len(assignments)
    weighted_score = avg_score * weight

    # Create table for this category
    table = Table(show_header=True, header_style="bold")
    table.add_column(f"{category_name.title()}")
    table.add_column("Original Score")
    table.add_column("Days Late")
    table.add_column("Adjusted Score")

    for assignment in assignments:
        table.add_row(
            assignment.name,
            f"{assignment.original_score:.2f}",
            str(assignment.days_late),
            f"{assignment.adjusted_score:.2f}",
        )

    return weighted_score, table


def calculate_grade(grades: Dict[str, Any], policy: Dict[str, Any]) -> None:
    """Calculate final grade and print a terminal report."""
    if not grades or "scores" not in grades:
        raise ValueError("Invalid grades data")

    console = Console()
    total_score = 0
    warning_messages = []

    # Print header
    console.print(
        f"\n[bold cyan]Grade Report for {grades.get('name', 'N/A')} (ID: {grades.get('id', 'N/A')})[/bold cyan]\n"
    )

    # Project calculation
    if grades["scores"].get("project") and policy["weights"].get("project"):
        project_penalty = calculate_late_penalty(
            grades["scores"]["project"]["submitted_at"],
            policy["due_dates"].get("project", ""),
            policy["late_penalty"]["rate"],
            policy["late_penalty"]["max_penalty"],
        )

        project_score = (
            grades["scores"]["project"]["score"]
            * (1 - project_penalty.penalty)
            * policy["weights"]["project"]
        )
        total_score += project_score

        console.print("[bold]Project Score:[/bold]")
        console.print(f"Original Score: {grades['scores']['project']['score']:.2f}")
        console.print(f"Days Late: {project_penalty.days_late}")
        console.print(f"Weight: {policy['weights']['project']:.2f}")
        console.print(f"Contribution to Final Grade: {project_score:.2f}\n")
    else:
        warning_messages.append("Missing project data")

    # Quiz calculations
    if grades["scores"].get("quizzes") and policy["weights"].get("quizzes"):
        quiz_score, quiz_table = process_assignment_category(
            "quizzes",
            grades["scores"]["quizzes"],
            policy["due_dates"]["quizzes"],
            policy["weights"]["quizzes"],
            policy["late_penalty"]["rate"],
            policy["late_penalty"]["max_penalty"],
            policy.get("quiz_drops", 0),
        )
        total_score += quiz_score
        console.print("[bold]Quiz Scores:[/bold]")
        console.print(quiz_table)
        console.print(f"Quiz Weight: {policy['weights']['quizzes']:.2f}")
        console.print(f"Contribution to Final Grade: {quiz_score:.2f}\n")
    else:
        warning_messages.append("Missing quizzes data")

    # Homework calculations
    if grades["scores"].get("homework") and policy["weights"].get("homework"):
        homework_score, homework_table = process_assignment_category(
            "homework",
            grades["scores"]["homework"],
            policy["due_dates"]["homework"],
            policy["weights"]["homework"],
            policy["late_penalty"]["rate"],
            policy["late_penalty"]["max_penalty"],
        )
        total_score += homework_score
        console.print("[bold]Homework Scores:[/bold]")
        console.print(homework_table)
        console.print(f"Homework Weight: {policy['weights']['homework']:.2f}")
        console.print(f"Contribution to Final Grade: {homework_score:.2f}\n")
    else:
        warning_messages.append("Missing homework data")

    # Reflections calculations
    if grades["scores"].get("reflections") and policy["weights"].get("reflections"):
        reflection_score, reflection_table = process_assignment_category(
            "reflections",
            grades["scores"]["reflections"],
            policy["due_dates"]["reflections"],
            policy["weights"]["reflections"],
            policy["late_penalty"]["rate"],
            policy["late_penalty"]["max_penalty"],
        )
        total_score += reflection_score
        console.print("[bold]Reflection Scores:[/bold]")
        console.print(reflection_table)
        console.print(f"Reflection Weight: {policy['weights']['reflections']:.2f}")
        console.print(f"Contribution to Final Grade: {reflection_score:.2f}\n")
    else:
        warning_messages.append("Missing reflections data")

    # Calculate final grade
    letter_grade = "F"
    if policy.get("grade_scale"):
        for grade, min_score in sorted(
            policy["grade_scale"].items(), key=lambda x: x[1], reverse=True
        ):
            if total_score >= min_score:
                letter_grade = grade
                break

    # Print final results
    console.print("[bold green]Final Grade Summary:[/bold green]")
    console.print(f"Final Score: {total_score:.2f}%")
    console.print(f"Letter Grade: {letter_grade}\n")

    # Print policy details
    console.print("[bold]Grading Policy Details:[/bold]")
    console.print(
        f"Late Penalty Rate: {policy['late_penalty']['rate']*100:.1f}% per day"
    )
    console.print(
        f"Maximum Late Penalty: {policy['late_penalty']['max_penalty']*100:.1f}%"
    )
    console.print(f"Number of Quiz Drops: {policy.get('quiz_drops', 'N/A')}\n")

    # Print warnings if any
    if warning_messages:
        console.print("[bold red]Warnings:[/bold red]")
        for msg in warning_messages:
            console.print(f"- {msg}")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate final grades based on submission times and scores"
    )
    parser.add_argument("grades_file", help="YAML file containing student grades")
    parser.add_argument("policy_file", help="YAML file containing grading policy")
    args = parser.parse_args()

    try:
        with open(args.grades_file, "r") as f:
            grades = yaml.safe_load(f)
        with open(args.policy_file, "r") as f:
            policy = yaml.safe_load(f)

        calculate_grade(grades, policy)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML format - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
