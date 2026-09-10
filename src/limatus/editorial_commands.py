from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .editorial_diagnosis_schema import validate_diagnosis
from .editorial_markup import render_annotated_markus, render_annotated_xml
from .editorial_scan import scan_draft
from .editorial_options_schema import validate_decisions
from .sdk import record_decision
from .editorial_rewrite_options import generate_rewrite_options
from .editorial_style import load_style_profile
from .editorial_apply import apply_patch, render_diff
from .editorial_compare import compare_candidates, compare_regression
from .editorial_compare_schema import validate_compare_report
from .editorial_verifier import verify_revision
from .editorial_standfirst import check_standfirst
from ._util import DEFAULT_EDITORIAL_REWRITE_MODEL


def _run_scan_command(flags: list[str], *, prog: str) -> None:
    parser = argparse.ArgumentParser(prog=prog)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--draft", help="Path to the draft file (read-only).")
    input_group.add_argument("--text", help="Draft text to scan without reading a file.")
    parser.add_argument("--profile", required=True, help="Path to the style profile YAML.")
    parser.add_argument(
        "--surface",
        default="",
        help="Named surface (e.g. marketing, legal) whose rules.bySurface override applies, if any.",
    )
    parser.add_argument("--output", default="", help="Optional path to write diagnostic JSON.")
    parser.add_argument(
        "--markup-out",
        default="",
        help="Optional path to write Markus-annotated Markdown (editorial-finding directives).",
    )
    parser.add_argument(
        "--xml-out",
        default="",
        help="Optional path to write editorial annotation XML.",
    )
    parser.add_argument(
        "--require-judge",
        action="store_true",
        help="Fail when a configured judge cannot run (missing OPENAI_API_KEY or API error).",
    )
    args = parser.parse_args(flags)

    profile_path = Path(args.profile).resolve()
    if args.draft:
        draft_path = Path(args.draft).resolve()
        if not draft_path.is_file():
            raise ValueError(f"Draft file not found: {draft_path}")
        draft_text = draft_path.read_text(encoding="utf-8")
    else:
        draft_text = args.text

    style_profile = load_style_profile(profile_path)
    diagnosis = scan_draft(
        draft_text,
        style_profile=style_profile,
        surface=args.surface or None,
        require_judge=args.require_judge,
    )
    rendered = json.dumps(diagnosis, indent=2) + "\n"

    if args.markup_out:
        markup_path = Path(args.markup_out).resolve()
        markup_path.write_text(render_annotated_markus(draft_text, diagnosis), encoding="utf-8")

    if args.xml_out:
        xml_path = Path(args.xml_out).resolve()
        xml_path.write_text(render_annotated_xml(draft_text, diagnosis), encoding="utf-8")

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(rendered, encoding="utf-8")
        return

    sys.stdout.write(rendered)


def editorial_scan(flags: list[str]) -> None:
    _run_scan_command(flags, prog="limatus scan")


def editorial_diagnose(flags: list[str]) -> None:
    _run_scan_command(flags, prog="limatus diagnose")


def editorial_decide(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus decide")
    parser.add_argument("--finding-id", required=True, help="Stable finding id from scan JSON.")
    parser.add_argument(
        "--decision",
        required=True,
        help="Steering decision: skip, rewrite, delete, keep, or add.",
    )
    parser.add_argument("--note", default="", help="Optional note for the decision record.")
    parser.add_argument(
        "--decisions",
        required=True,
        help="Path to decisions JSON list (created as [] when missing).",
    )
    args = parser.parse_args(flags)

    decisions_path = Path(args.decisions).resolve()
    if decisions_path.is_file():
        decisions_payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        if not isinstance(decisions_payload, list):
            raise ValueError("Decisions JSON must be a list.")
    else:
        decisions_payload = []

    updated = record_decision(
        decisions_payload,
        args.finding_id,
        args.decision,
        note=args.note,
    )
    rendered = json.dumps(updated, indent=2) + "\n"
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    decisions_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)


def editorial_options(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus options")
    parser.add_argument("--draft", required=True, help="Path to the draft file (read-only).")
    parser.add_argument("--profile", required=True, help="Path to the style profile YAML.")
    parser.add_argument("--diagnosis", required=True, help="Path to validated diagnostic JSON.")
    parser.add_argument("--decisions", required=True, help="Path to steering decisions JSON.")
    parser.add_argument("--output", default="", help="Optional path to write options JSON.")
    parser.add_argument("--model", default=DEFAULT_EDITORIAL_REWRITE_MODEL, help="OpenAI model id.")
    parser.add_argument(
        "--skill",
        required=True,
        help="Path to editorial rewrite skill YAML.",
    )
    args = parser.parse_args(flags)

    draft_path = Path(args.draft).resolve()
    if not draft_path.is_file():
        raise ValueError(f"Draft file not found: {draft_path}")
    draft_text = draft_path.read_text(encoding="utf-8")

    diagnosis_path = Path(args.diagnosis).resolve()
    decisions_path = Path(args.decisions).resolve()
    diagnosis_payload = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    decisions_payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    if not isinstance(decisions_payload, list):
        raise ValueError("Decisions JSON must be a list.")

    style_profile = load_style_profile(Path(args.profile).resolve())
    validate_diagnosis(diagnosis_payload)
    validate_decisions(decisions_payload)

    options = generate_rewrite_options(
        draft_text,
        style_profile=style_profile,
        diagnosis=diagnosis_payload,
        decisions=decisions_payload,
        model=args.model,
        skill_path=args.skill,
    )
    rendered = json.dumps(options, indent=2) + "\n"

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(rendered, encoding="utf-8")
        return

    sys.stdout.write(rendered)


def editorial_apply(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus apply")
    parser.add_argument("--original", required=True, help="Original draft path; never modified.")
    parser.add_argument("--working-copy", required=True, help="Explicit working-copy path to modify.")
    parser.add_argument("--options", required=True, help="Validated options JSON path.")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--option-id", required=True, help="Explicit selected option id.")
    parser.add_argument("--anchor", required=True, help="Exact text expected at the patch span.")
    parser.add_argument("--delete", action="store_true", help="Confirm the selected option is a deletion.")
    parser.add_argument("--change-log", default="", help="Path for machine-readable change log JSON.")
    args = parser.parse_args(flags)
    options = json.loads(Path(args.options).read_text(encoding="utf-8"))
    log = apply_patch(
        original_path=args.original,
        working_copy_path=args.working_copy,
        options=options,
        finding_id=args.finding_id,
        option_id=args.option_id,
        anchor=args.anchor,
        delete=args.delete,
        change_log_path=args.change_log or None,
    )
    sys.stdout.write(json.dumps(log, indent=2) + "\n")


def editorial_diff(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus diff")
    parser.add_argument("--original", required=True)
    parser.add_argument("--working-copy", required=True)
    parser.add_argument("--output", default="", help="Optional path for the unified diff.")
    args = parser.parse_args(flags)
    rendered = render_diff(args.original, args.working_copy)
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def editorial_compare(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus compare")
    parser.add_argument("--profile", required=True, help="Path to the style profile YAML or JSON.")
    parser.add_argument("--baseline", default="", help="Baseline draft path (read-only).")
    parser.add_argument("--candidate", action="append", default=[], help="Candidate draft path (read-only); repeat for each.")
    parser.add_argument(
        "--candidate-id",
        action="append",
        default=[],
        help="Optional id for each --candidate (same order).",
    )
    parser.add_argument("--original", default="", help="Regression mode: original draft path (read-only).")
    parser.add_argument(
        "--working-copy",
        default="",
        help="Regression mode: working copy path (read-only).",
    )
    parser.add_argument(
        "--surface",
        default="",
        help="Named surface override from the profile, if any.",
    )
    parser.add_argument("--output", default="", help="Optional path for compare JSON.")
    args = parser.parse_args(flags)

    regression = bool(args.original or args.working_copy)
    rank = bool(args.baseline or args.candidate)
    if regression and rank:
        raise ValueError("Use either regression (--original/--working-copy) or rank (--baseline/--candidate) flags.")
    if not regression and not rank:
        raise ValueError("Provide regression paths or a baseline with candidates.")

    style_profile = load_style_profile(Path(args.profile).resolve())
    surface = args.surface or None

    if regression:
        if not args.original or not args.working_copy:
            raise ValueError("Regression compare requires both --original and --working-copy.")
        original_path = Path(args.original).resolve()
        working_path = Path(args.working_copy).resolve()
        if not original_path.is_file() or not working_path.is_file():
            raise ValueError("Both --original and --working-copy must point to files.")
        result = compare_regression(
            original_path.read_text(encoding="utf-8"),
            working_path.read_text(encoding="utf-8"),
            style_profile=style_profile,
            surface=surface,
        )
    else:
        baseline_path = Path(args.baseline).resolve()
        if not baseline_path.is_file():
            raise ValueError(f"Baseline file not found: {baseline_path}")
        if len(args.candidate) < 2:
            raise ValueError("Rank compare requires at least two --candidate paths.")
        candidate_paths = [Path(path).resolve() for path in args.candidate]
        for path in candidate_paths:
            if not path.is_file():
                raise ValueError(f"Candidate file not found: {path}")
        ids = list(args.candidate_id)
        candidates: list[dict[str, str]] = []
        for index, path in enumerate(candidate_paths):
            candidate_id = ids[index] if index < len(ids) else path.stem
            candidates.append(
                {
                    "id": candidate_id,
                    "text": path.read_text(encoding="utf-8"),
                }
            )
        result = compare_candidates(
            baseline_path.read_text(encoding="utf-8"),
            candidates,
            style_profile=style_profile,
            surface=surface,
            mode="rank",
        )

    validate_compare_report(result)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def editorial_verify(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus verify")
    parser.add_argument("--original", required=True, help="Original draft path; read-only.")
    parser.add_argument("--working-copy", required=True, help="Explicitly applied working draft path; read-only.")
    parser.add_argument("--profile", required=True, help="Path to the style profile YAML or JSON.")
    parser.add_argument("--threshold", type=float, default=0.05, help="Required normalized net improvement (default: 0.05).")
    parser.add_argument("--output", default="", help="Optional path for verification JSON.")
    args = parser.parse_args(flags)
    original_path = Path(args.original).resolve()
    working_path = Path(args.working_copy).resolve()
    if not original_path.is_file() or not working_path.is_file():
        raise ValueError("Both --original and --working-copy must point to files.")
    result = verify_revision(
        original_path.read_text(encoding="utf-8"),
        working_path.read_text(encoding="utf-8"),
        style_profile=load_style_profile(Path(args.profile).resolve()),
        threshold=args.threshold,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def editorial_standfirst(flags: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="limatus standfirst")
    parser.add_argument("--text", required=True, help="Candidate standfirst text to check.")
    parser.add_argument("--profile", required=True, help="Path to a style profile with 'standfirst' rules.")
    parser.add_argument("--body", default="", help="Optional path to the article body, for the proper-noun check.")
    parser.add_argument("--description", default="", help="Optional description field, for the overlap check.")
    parser.add_argument("--output", default="", help="Optional path to write findings JSON.")
    args = parser.parse_args(flags)

    style_profile = load_style_profile(Path(args.profile).resolve())
    body_text = ""
    if args.body:
        body_path = Path(args.body).resolve()
        if not body_path.is_file():
            raise ValueError(f"Body file not found: {body_path}")
        body_text = body_path.read_text(encoding="utf-8")

    result = check_standfirst(
        args.text,
        style_profile=style_profile,
        body_text=body_text,
        description=args.description,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
