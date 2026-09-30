RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "header": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "linkedin": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "github": {"type": "string"},
                "github_url": {"type": "string"},
                "website": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "summary": {"type": "string"},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "location": {"type": "string"},
                    "degree": {"type": "string"},
                    "date": {"type": "string"},
                    "type": {"type": "string"},
                    "coursework": {"type": "string"},
                    "details": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["institution", "date"],
                "additionalProperties": False,
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["category", "items"],
                "additionalProperties": False,
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "role": {"type": "string"},
                    "date": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["company", "role", "date", "bullets"],
                "additionalProperties": False,
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "technologies": {"type": "string"},
                    "date": {"type": "string"},
                    "url": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "bullets"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["header", "education", "skills", "experience", "projects"],
    "additionalProperties": False,
}

TOOL_DEFINITION = {
    "name": "structure_resume",
    "description": (
        "Structure extracted resume text into a standardized JSON format. "
        "Set type to 'degree' for academic degrees and 'certification' for certifications. "
        "Split project names from award/subtitle text into separate name and subtitle fields. "
        "Put coursework in the coursework field, not in details. "
        "Include location for header, education, and experience entries. "
        "Include linkedin_url and github_url if URLs are present."
    ),
    "strict": True,
    "input_schema": RESUME_SCHEMA,
}
