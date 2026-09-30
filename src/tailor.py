import json

import anthropic

from . import print_usage
from .schema import RESUME_SCHEMA

SYSTEM_PROMPT_TEMPLATE = """\
You are a resume tailoring expert. You receive a base resume as JSON and a job \
description. Return a tailored version of the resume in the exact same JSON schema.

Rules:
- NEVER invent facts, metrics, skills, or experience that are not in the base resume.
- Reword bullets to actively mirror JD keywords and language where truthful \
(e.g. if the JD says "production-ready code", "data pipelines", "CI/CD", \
"configurable compliance checks", use those phrases when the base content supports it).
- Use the JD's exact wording for skills and tools the base resume already supports, \
including both the spelled-out and acronym forms where natural (e.g. "Continuous \
Integration/Continuous Delivery (CI/CD)"), so ATS keyword matching succeeds.
- Start every bullet with a strong past-tense action verb (present tense for current \
roles), state what was done, how, and the outcome. Keep any metric exactly as given in \
the base resume; do not add, round up, or estimate numbers.
- Where the base resume supports it, make the most JD-relevant accomplishment the first \
bullet of each entry, and mirror the seniority and scope language of the JD (ownership, \
collaboration, scale) only as far as the base facts justify.
- The candidate is applying for new-grad / entry-level roles. Keep the graduation date \
prominent, treat internships and team projects as real professional experience, and \
favor bullets showing ownership, shipped results, and measurable outcomes over \
task lists. Do not add years of experience or seniority claims.
- Within a bullet, lead with the outcome or metric when the base bullet has one.
- Reorder bullets within each entry to lead with the most JD-relevant ones.
- The base resume is a master list and may hold many more skills and projects than \
fit on a page. Order skills categories and the items within each by JD relevance, \
most relevant first, and drop categories or items with no relevance to the JD. Keep \
every category to roughly one line (about 90 characters including the label); the \
renderer will trim any overflow from the end, so the least relevant items must be last. \
{infer_skills_rule}\
Apply the same check to coursework: \
drop the least relevant courses rather than leave 1-2 orphan words on a wrapped line.
- Maintain reverse chronological order for experience and education entries. \
Do not reorder entries themselves, only bullets within an entry and items within a skill category.
- The summary field must be rewritten to match the JD. Open with the JD's role title if \
it fits the candidate's real background, then work in as many of the JD's key terms \
(technologies, domains, responsibilities) as the base resume truthfully supports, using \
the JD's exact phrasing. Repeating skills that appear elsewhere is fine here, since \
keyword match is the goal. Keep it to 2-3 lines (approximately 30-45 words), with no \
filler adjectives. Never include a term the base resume does not support.
- Do not use em dashes (use hyphens instead). En dashes in date ranges are fine.
- Keep all dates, company names, institution names, degrees, and locations unchanged.
- Keep the type field unchanged for education entries (degree or certification).
- Keep exactly the 2 projects most relevant to the JD (judged by technology overlap, \
domain, and impact) and drop all others, keeping their original wording apart from \
JD-keyword rewording. You may drop irrelevant bullets, but do not fabricate replacements.
- Avoid leaving short trailing text (1-3 words) at the end of a bullet. Either \
tighten the wording to pull trailing words up, or expand slightly to fill the line.\
"""

INFER_SKILLS_RULE = (
    "You may add a JD keyword to a skills category ONLY if it is an umbrella term, "
    "synonym, or direct implication of a skill already listed "
    "(e.g. \"containerization\" from \"Docker\", \"relational databases\" from "
    "\"PostgreSQL\", \"microservices\" from \"FastAPI\"). "
    "Never add a specific tool, library, or technology the candidate has not used. "
)

NO_INFER_RULE = "Never add items that are not in the base resume. "


def tailor_resume(
    base: dict,
    jd_text: str,
    company: str,
    role: str,
    client: anthropic.Anthropic,
    model: str,
    infer_skills: bool = False,
) -> dict:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        infer_skills_rule=INFER_SKILLS_RULE if infer_skills else NO_INFER_RULE,
    )

    if infer_skills:
        print("  [infer-skills] enabled: umbrella/synonym skill terms may be added")

    user_prompt = (
        f"Company: {company}\nRole: {role}\n\n"
        f"Job Description:\n{jd_text}\n\n"
        f"Base Resume JSON:\n{json.dumps(base, indent=2, ensure_ascii=False)}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": RESUME_SCHEMA,
            }
        },
    )

    print_usage(response, "tailor")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def run(
    base_json_path: str,
    jd_path: str,
    company: str,
    role: str,
    client: anthropic.Anthropic,
    model: str,
    infer_skills: bool = False,
) -> dict:
    base = json.loads(open(base_json_path).read())
    jd_text = open(jd_path).read()

    print(f"Tailoring resume for {role} at {company}...")
    tailored = tailor_resume(base, jd_text, company, role, client, model, infer_skills)
    print("Tailoring complete.")
    return tailored
