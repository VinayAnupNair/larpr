import json
import anthropic

from . import print_usage
from .render import render_html
from .schema import RESUME_SCHEMA

PAGE_HEIGHT_IN = 11.0
PAGE_WIDTH_IN = 8.5
MARGIN_IN = 0.5
PX_PER_IN = 96
PRINTABLE_WIDTH_PX = int((PAGE_WIDTH_IN - 2 * MARGIN_IN) * PX_PER_IN)
PRINTABLE_HEIGHT_PX = (PAGE_HEIGHT_IN - 2 * MARGIN_IN) * PX_PER_IN

SCALE_MIN = 0.70
SCALE_MAX = 1.30
TARGET_LOW = 0.985
TARGET_HIGH = 1.0
MAX_ITERATIONS = 20


def measure_content_height(page, html: str) -> float:
    page.set_content(html, wait_until="networkidle")
    return page.evaluate(
        "() => document.querySelector('.resume-content').getBoundingClientRect().height"
    )


def binary_search_scale(page, resume_data: dict) -> tuple[float, float]:
    lo, hi = SCALE_MIN, SCALE_MAX

    for i in range(MAX_ITERATIONS):
        mid = (lo + hi) / 2
        html = render_html(resume_data, scale=mid)
        height = measure_content_height(page, html)
        fill = height / PRINTABLE_HEIGHT_PX
        print(f"  [fit] iter={i+1}  scale={mid:.4f}  height={height:.0f}px  fill={fill*100:.1f}%")

        if fill < TARGET_LOW:
            lo = mid
        elif fill > TARGET_HIGH:
            hi = mid
        else:
            return mid, fill

    final_scale = (lo + hi) / 2
    final_html = render_html(resume_data, scale=final_scale)
    final_height = measure_content_height(page, final_html)
    final_fill = final_height / PRINTABLE_HEIGHT_PX
    print(f"  [fit] converged  scale={final_scale:.4f}  fill={final_fill*100:.1f}%")
    return final_scale, final_fill


def adjust_content_with_claude(
    resume_data: dict,
    fill_pct: float,
    client: anthropic.Anthropic,
    model: str,
) -> dict:
    if fill_pct > TARGET_HIGH:
        action = "shorten"
        detail = (
            f"The resume overflows the page by {(fill_pct - 1.0) * 100:.1f}%. "
            "Remove the least impactful bullets or tighten wording to fit. "
            "Do not remove entire sections or invent new content."
        )
    else:
        action = "expand"
        detail = (
            f"The resume only fills {fill_pct * 100:.1f}% of the page. "
            "Expand bullet points with more detail from the existing content. "
            "Do not invent new facts, metrics, or experience."
        )

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=(
            f"You are a resume editor. {action.capitalize()} the resume content "
            "to better fill exactly one page. Do not use em dashes. "
            "Avoid leaving short trailing text (1-3 words) at the end of bullets, "
            "skill rows, or the coursework line; either tighten wording to pull trailing "
            "words up, expand to fill the line, or drop the least relevant items. "
            "Return the adjusted resume in the exact same JSON schema."
        ),
        messages=[
            {
                "role": "user",
                "content": f"{detail}\n\nCurrent resume JSON:\n{json.dumps(resume_data, indent=2, ensure_ascii=False)}",
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": RESUME_SCHEMA,
            }
        },
    )

    print_usage(response, "fit-adjust")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def trim_skills_to_one_line(page, resume_data: dict) -> dict:
    """Drop trailing (least relevant) skill items until every skills row is one line."""
    skills = [dict(s, items=list(s["items"])) for s in resume_data.get("skills", [])]
    resume_data = dict(resume_data, skills=skills)

    for _ in range(100):
        page.set_content(render_html(resume_data), wait_until="networkidle")
        wrapped = page.evaluate(
            """() => [...document.querySelectorAll('.skills-row')].map(el => {
                const line = parseFloat(getComputedStyle(el).fontSize) * 1.5;
                return el.getBoundingClientRect().height > line;
            })"""
        )
        if not any(wrapped):
            break
        for skill, is_wrapped in zip(skills, wrapped):
            if is_wrapped and len(skill["items"]) > 1:
                dropped = skill["items"].pop()
                print(f"  [fit] skills row '{skill['category']}' wraps, dropped '{dropped}'")
    return resume_data


def fit_to_page(
    page,
    resume_data: dict,
    client: anthropic.Anthropic,
    model: str,
) -> tuple[dict, float, float]:
    resume_data = trim_skills_to_one_line(page, resume_data)
    scale, fill = binary_search_scale(page, resume_data)

    if fill < TARGET_LOW or fill > TARGET_HIGH:
        print(f"  Fill {fill*100:.1f}% outside target, asking Claude to adjust content...")
        resume_data = adjust_content_with_claude(resume_data, fill, client, model)
        scale, fill = binary_search_scale(page, resume_data)

    return resume_data, scale, fill
