from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from .render import render_html
from .fit import fit_to_page, PRINTABLE_WIDTH_PX


def export_pdf(
    resume_data: dict,
    company: str,
    role: str,
    client,
    model: str,
    output_dir: str = "output",
) -> str:
    slug_company = company.lower().replace(" ", "_")
    slug_role = role.lower().replace(" ", "_")
    filename = f"van_{slug_company}_{slug_role}.pdf"
    out_path = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": PRINTABLE_WIDTH_PX, "height": 2000})

        print("Fitting content to one page...")
        resume_data, scale, fill = fit_to_page(page, resume_data, client, model)

        html = render_html(resume_data, scale=scale)
        page.set_content(html, wait_until="networkidle")

        page.pdf(
            path=str(out_path),
            format="Letter",
            margin={
                "top": "0.5in",
                "bottom": "0.5in",
                "left": "0.5in",
                "right": "0.5in",
            },
            print_background=True,
        )
        browser.close()

    reader = PdfReader(str(out_path))
    num_pages = len(reader.pages)
    if num_pages != 1:
        out_path.unlink()
        raise RuntimeError(
            f"PDF was {num_pages} pages (expected 1). "
            f"Fill was {fill*100:.1f}%. Deleted {out_path}."
        )

    print(f"PDF is exactly 1 page.")
    print(f"Fill: {fill * 100:.1f}%")
    print(f"Saved to {out_path}")
    return str(out_path)
