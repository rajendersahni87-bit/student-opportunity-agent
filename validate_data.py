"""Validates data/opportunities.json against the schema and sanity-checks it with the matching engine."""

import json
import sys
from datetime import date, datetime
from pathlib import Path

from engine.matcher import evaluate_opportunities

DATA_FILE = Path(__file__).resolve().parent / "data" / "opportunities.json"
REQUIRED_FIELDS = [
    "id", "title", "organization", "type", "description",
    "skills", "eligible_branches", "eligible_years", "min_cgpa",
    "location", "deadline", "application_url",
]
ALLOWED_TYPES = {"Internship", "Hackathon", "Coding Competition", "Scholarship", "Fellowship"}


def validate(data, today=None):
    """Returns (errors, warnings). Collects every problem instead of stopping at the first."""
    today = today or date.today()
    errors, warnings, seen_ids = [], [], set()
    for idx, item in enumerate(data):
        label = f"#{idx} {item.get('title') or item.get('id')}"
        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{label}: missing '{field}'")
        if item.get("id") in seen_ids:
            errors.append(f"{label}: duplicate id '{item.get('id')}'")
        seen_ids.add(item.get("id"))
        if item.get("type") not in ALLOWED_TYPES:
            errors.append(f"{label}: unknown type '{item.get('type')}'")
        cg = item.get("min_cgpa")
        if not isinstance(cg, (int, float)) or not 0 <= cg <= 10:
            errors.append(f"{label}: min_cgpa must be a number between 0 and 10")
        if not str(item.get("application_url", "")).lower().startswith(("https://", "http://")):
            errors.append(f"{label}: application_url must be http(s)")
        for field in ("skills", "eligible_branches", "eligible_years"):
            if not isinstance(item.get(field), list) or not item.get(field):
                errors.append(f"{label}: '{field}' must be a non-empty list")
        try:
            if datetime.strptime(item.get("deadline", ""), "%Y-%m-%d").date() < today:
                warnings.append(f"{label}: deadline {item['deadline']} already passed")
        except ValueError:
            errors.append(f"{label}: deadline must be YYYY-MM-DD")
    return errors, warnings


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    print(f"Total opportunities: {len(data)}")

    errors, warnings = validate(data)
    types_count = {}
    for item in data:
        types_count[item.get("type")] = types_count.get(item.get("type"), 0) + 1
    print("Categories count:", json.dumps(types_count, indent=2))
    print("Sample/Demo entries count:", sum(1 for i in data if i.get("is_demo")))
    for w in warnings:
        print("WARNING:", w)
    if errors:
        print(f"\n{len(errors)} ERROR(S):")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    sample_student = {
        "name": "Aarav", "year": "3rd Year", "branch": "Computer Science", "cgpa": 8.5,
        "skills": ["Python", "Data Structures", "Algorithms", "C++"],
        "interests": ["Software Engineering", "Competitive Programming"],
        "preferred_types": ["Internship", "Coding Competition"], "preferred_mode": "Hybrid",
    }
    results = evaluate_opportunities(sample_student, data)
    print(f"Evaluated {len(results)} items successfully.")
    for label, res in zip(("Top match", "Second match"), results[:2]):
        print(f"{label}: {res['title']} ({res['match_score']}/100) - Eligible: {res['is_eligible']}")


if __name__ == "__main__":
    main()
