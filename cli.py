#!/usr/bin/env python3
import argparse
import json
import os
import sys

from dotenv import load_dotenv
import anthropic


def get_client_and_model():
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    client = anthropic.Anthropic(api_key=api_key)
    return client, model


def cmd_import(args):
    from src.importer import run
    client, model = get_client_and_model()
    run(args.pdf, args.output, client, model)


def cmd_tailor(args):
    from src.tailor import run as tailor_run
    from src.export import export_pdf

    warn_empty_links(args.base)
    client, model = get_client_and_model()
    tailored = tailor_run(args.base, args.jd, args.company, args.role, client, model, args.infer_skills)

    tailored_json_path = os.path.join(
        "output",
        f"van_{args.company.lower().replace(' ', '_')}_{args.role.lower().replace(' ', '_')}.json",
    )
    os.makedirs("output", exist_ok=True)
    with open(tailored_json_path, "w") as f:
        json.dump(tailored, f, indent=2, ensure_ascii=False)
    print(f"Saved tailored JSON to {tailored_json_path}")

    pdf_path = export_pdf(tailored, args.company, args.role, client, model)
    print(f"Done: {pdf_path}")


def cmd_gaps(args):
    from src.gaps import run as gaps_run
    client, model = get_client_and_model()
    gaps_run(args.base, args.jd, client, model)


def warn_empty_links(base_path):
    header = json.load(open(base_path)).get("header", {})
    for key in ("linkedin_url", "github_url"):
        if not header.get(key):
            print(f"Warning: header.{key} is empty in {base_path}; the PDF link will be dead.")


def main():
    parser = argparse.ArgumentParser(description="LaRPR - Resume tailoring CLI")
    subs = parser.add_subparsers(dest="command", required=True)

    p_import = subs.add_parser("import", help="Extract and structure base resume from PDF")
    p_import.add_argument("--pdf", default="data/base_resume.pdf", help="Path to resume PDF")
    p_import.add_argument("--output", default="data/base_resume.json", help="Output JSON path")
    p_import.set_defaults(func=cmd_import)

    p_tailor = subs.add_parser("tailor", help="Tailor resume to a job description")
    p_tailor.add_argument("--jd", required=True, help="Path to job description text file")
    p_tailor.add_argument("--company", required=True, help="Company name")
    p_tailor.add_argument("--role", required=True, help="Role title")
    p_tailor.add_argument("--base", default="data/base_resume.json", help="Base resume JSON")
    p_tailor.add_argument("--infer-skills", action="store_true",
                          help="Allow adding umbrella/synonym skill terms implied by existing skills")
    p_tailor.set_defaults(func=cmd_tailor)

    p_gaps = subs.add_parser("gaps", help="Report how well your resume covers a job description")
    p_gaps.add_argument("--jd", required=True, help="Path to job description text file")
    p_gaps.add_argument("--base", default="data/base_resume.json", help="Base resume JSON")
    p_gaps.set_defaults(func=cmd_gaps)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
