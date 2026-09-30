# LaRPR

CLI tool that tailors your resume to a job description using the Anthropic API and exports a one-page PDF in Jake's Resume format.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill in your ANTHROPIC_API_KEY
```

## Usage

### 1. Import your base resume

Extracts text from `data/base_resume.pdf` and structures it into `data/base_resume.json` via Claude:

```bash
python cli.py import
```

Review and edit `data/base_resume.json` as needed — this is your source of truth.

### 2. Tailor to a job description

```bash
python cli.py tailor --jd jd.txt --company "Veridian Health Systems" --role "Software Engineer"
```

Outputs `output/van_veridian_health_systems_software_engineer.pdf`.
