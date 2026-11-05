import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_jsonl(path):
    records = []
    warnings = []

    if not path.exists():
        return records, warnings

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                warnings.append(
                    f"{path.name}, line {line_number}: {exc}"
                )
                continue

            if not isinstance(record, dict):
                warnings.append(
                    f"{path.name}, line {line_number}: "
                    "record is not a JSON object"
                )
                continue

            records.append(record)

    return records, warnings


def text(value):
    return "" if value is None else str(value)


def table_cell(value):
    return (
        text(value)
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def heading(value):
    return text(value).replace("\r", " ").replace("\n", " ")


def render_message(message):
    """Render known structured reviews; preserve other message text."""
    if not isinstance(message, str):
        return json.dumps(message, indent=2, ensure_ascii=False)

    cleaned = message.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return message.strip()

    if (
        not isinstance(parsed, dict)
        or "decision_on_original_artifact" not in parsed
    ):
        return message.strip()

    parts = [
        "Verdict on original artifact: "
        + text(parsed["decision_on_original_artifact"])
    ]

    evidence = parsed.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [evidence]

    if evidence:
        parts.append(
            "Evidence:\n"
            + "\n".join(f"- {text(item)}" for item in evidence)
        )

    response = parsed.get("response_to_peers")
    if response:
        parts.append("Response to peers:\n\n" + text(response))

    return "\n\n".join(parts)


def evidence_lines(value):
    if value is None:
        return ["- No evidence recorded."]

    if not isinstance(value, list):
        value = [value]

    return (
        [f"- {text(item)}" for item in value]
        if value
        else ["- No evidence recorded."]
    )


def record_key(record):
    return (
        text(record.get("experiment_id", "unknown")),
        text(record.get("artifact_id", "unknown")),
        text(record.get("repeat", "unknown")),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Create readable Markdown from experiment JSONL logs."
    )
    parser.add_argument(
        "results_dir",
        type=Path,
        help="Directory containing discussions.jsonl and final_reviews.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output Markdown filename",
    )
    args = parser.parse_args()

    folder = args.results_dir

    if not folder.is_dir():
        parser.error(f"Results directory does not exist: {folder}")

    output = args.output or folder / "readable_report.md"

    raw_paths = {
        (folder / name).resolve()
        for name in (
            "discussions.jsonl",
            "final_reviews.jsonl",
            "errors.jsonl",
            "discussion_turns.jsonl",
        )
    }

    if output.resolve() in raw_paths:
        parser.error("Output must not overwrite a raw log file.")

    discussions, warnings_d = load_jsonl(
        folder / "discussions.jsonl"
    )
    reviews, warnings_r = load_jsonl(
        folder / "final_reviews.jsonl"
    )
    errors, warnings_e = load_jsonl(folder / "errors.jsonl")

    if not discussions and not reviews and not errors:
        parser.error("No discussion, review, or error records found.")

    warnings = warnings_d + warnings_r + warnings_e

    discussion_groups = defaultdict(list)
    review_groups = defaultdict(list)

    for record in discussions:
        discussion_groups[record_key(record)].append(record)

    for record in reviews:
        review_groups[record_key(record)].append(record)

    keys = list(dict.fromkeys(
        list(discussion_groups) + list(review_groups)
    ))

    lines = [
        "# Code-review experiment report",
        "",
        f"Source directory: `{folder}`",
        "",
        f"- Completed discussion records: {len(discussions)}",
        f"- Final-review records: {len(reviews)}",
        f"- Error records: {len(errors)}",
        "",
        "This report preserves recorded messages. "
        "Reviewer claims and proposed tests are not independently "
        "verified by this formatter.",
        "",
    ]

    for experiment_id, artifact_id, repeat in keys:
        key = (experiment_id, artifact_id, repeat)
        group_discussions = discussion_groups[key]
        group_reviews = review_groups[key]

        example = (group_discussions + group_reviews)[0]

        lines.extend([
            "---",
            "",
            f"## {heading(artifact_id)} — repeat {heading(repeat)}",
            "",
            f"- Experiment: `{experiment_id}`",
            f"- Source task: `{example.get('source_task_id', example.get('task_id', 'unknown'))}`",
            f"- Scenario: `{example.get('scenario_id') or 'not recorded'}`",
            f"- Model: `{example.get('model', 'unknown')}`",
            "",
            "### Final verdicts",
            "",
        ])

        if group_reviews:
            lines.extend([
                "| Condition | Decision | Confidence | API success | Parse success |",
                "|---|---|---|---|---|",
            ])

            for review in group_reviews:
                values = [
                    review.get("condition"),
                    review.get("decision"),
                    review.get("confidence"),
                    review.get("api_success"),
                    review.get("parse_success"),
                ]
                lines.append(
                    "| "
                    + " | ".join(table_cell(v) for v in values)
                    + " |"
                )

            lines.append("")

            for review in group_reviews:
                lines.extend([
                    f"#### Final-review evidence: {heading(review.get('condition'))}",
                    "",
                    f"Run ID: `{review.get('run_id', 'not recorded')}`",
                    "",
                    *evidence_lines(review.get("evidence")),
                    "",
                ])

                if review.get("error"):
                    lines.extend([
                        "Recorded error:",
                        "",
                        text(review["error"]),
                        "",
                    ])

                if review.get("decision") in {"UNPARSEABLE", "ERROR"}:
                    lines.extend([
                        "Raw output:",
                        "",
                        render_message(review.get("raw_output", "")),
                        "",
                    ])
        else:
            lines.extend([
                "No final-review records saved for this artifact/repeat.",
                "",
            ])

        for discussion in group_discussions:
            condition = heading(discussion.get("condition", "unknown"))
            transcript = discussion.get("transcript", [])

            lines.extend([
                f"### Discussion: {condition}",
                "",
                f"Discussion ID: `{discussion.get('discussion_id', 'not recorded')}`",
                "",
            ])

            if not isinstance(transcript, list):
                lines.extend(["Invalid transcript structure.", ""])
                continue

            current_round = object()

            for turn in transcript:
                if not isinstance(turn, dict):
                    lines.extend(["Malformed turn record.", ""])
                    continue

                round_number = turn.get("round", "unknown")

                if round_number != current_round:
                    current_round = round_number
                    lines.extend([
                        f"#### Round {heading(round_number)}",
                        "",
                    ])

                speaker = heading(turn.get("speaker", "Unknown reviewer"))
                role_label = (
                    "ADVERSARIAL PARTICIPANT"
                    if turn.get("is_adversary")
                    else "HONEST PARTICIPANT"
                )

                lines.extend([
                    f"##### {speaker} — {role_label}",
                    "",
                    f"Status: {turn.get('status', 'not recorded')}",
                    "",
                    render_message(turn.get("message", "")),
                    "",
                ])

    if errors:
        lines.extend([
            "---",
            "",
            "## Interrupted discussions and errors",
            "",
            "These are incomplete records, not completed review outcomes.",
            "",
        ])

        for index, error in enumerate(errors, start=1):
            lines.extend([
                f"### Error {index}",
                "",
                f"- Experiment: `{error.get('experiment_id', 'unknown')}`",
                f"- Discussion: `{error.get('discussion_id', 'not recorded')}`",
                f"- Stage: `{error.get('stage', 'unknown')}`",
                f"- Round: `{error.get('round', 'not recorded')}`",
                f"- Agent ID: `{error.get('agent_id', 'not recorded')}`",
                "",
                text(error.get("error", "No error message recorded.")),
                "",
            ])

            partial = error.get("partial_transcript", [])

            if isinstance(partial, list) and partial:
                lines.extend([
                    "#### Saved partial discussion",
                    "",
                ])

                for turn in partial:
                    if not isinstance(turn, dict):
                        continue

                    role_label = (
                        "ADVERSARIAL"
                        if turn.get("is_adversary")
                        else "HONEST"
                    )

                    lines.extend([
                        f"##### Round {heading(turn.get('round'))} — "
                        f"{heading(turn.get('speaker'))} — {role_label}",
                        "",
                        render_message(turn.get("message", "")),
                        "",
                    ])

    if warnings:
        lines.extend([
            "---",
            "",
            "## Log-reading warnings",
            "",
            *[f"- {warning}" for warning in warnings],
            "",
        ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report created: {output.resolve()}")
    print(
        f"Read {len(discussions)} discussions, "
        f"{len(reviews)} final reviews, and {len(errors)} errors."
    )

    if warnings:
        print(f"Warnings: {len(warnings)}; see the report.")


if __name__ == "__main__":
    main()