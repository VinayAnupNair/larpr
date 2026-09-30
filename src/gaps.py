import json

import anthropic

from . import print_usage

GAP_SCHEMA = {
    "type": "object",
    "properties": {
        "matched": {"type": "array", "items": {"type": "string"}},
        "on_resume_but_underplayed": {"type": "array", "items": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
        "new_grad_fit": {"type": "string"},
        "verdict": {"type": "string"},
    },
    "required": ["matched", "on_resume_but_underplayed", "missing", "new_grad_fit", "verdict"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You compare a job description to a candidate's base resume JSON and report honestly.
- matched: JD requirements clearly supported by the resume.
- on_resume_but_underplayed: requirements the resume supports only weakly or buried \
(name the entry so the candidate can surface it).
- missing: requirements with no support. Do not soften these. Suggest, in the same \
string, one concrete real way to close the gap (small project, course, certification).
- new_grad_fit: one or two sentences on whether the role is truly entry-level/new-grad \
(flag required years of experience, work authorization, or clearance requirements).
- verdict: one sentence, apply / apply with referral / skip, and why.
Never suggest claiming skills the candidate does not have."""


def run(base_json_path: str, jd_path: str, client: anthropic.Anthropic, model: str) -> dict:
    base = open(base_json_path).read()
    jd = open(jd_path).read()
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Job Description:\n{jd}\n\nBase Resume JSON:\n{base}"}],
        output_config={"format": {"type": "json_schema", "schema": GAP_SCHEMA}},
    )
    print_usage(response, "gaps")
    report = json.loads(next(b.text for b in response.content if b.type == "text"))

    for key, title in (
        ("matched", "Matched"),
        ("on_resume_but_underplayed", "On your resume but underplayed"),
        ("missing", "Missing (and how to close it)"),
    ):
        print(f"\n{title}:")
        for item in report[key] or ["(none)"]:
            print(f"  - {item}")
    print(f"\nNew-grad fit: {report['new_grad_fit']}")
    print(f"Verdict: {report['verdict']}")
    return report
