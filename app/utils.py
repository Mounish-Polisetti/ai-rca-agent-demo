"""
app/utils.py
-------------
Shared utility functions used across the RCA pipeline.
"""

import os
import json
from datetime import datetime, timezone


def load_dotenv_manual():
    """
    Load .env file into os.environ manually.
    Works without the python-dotenv package as a fallback.
    Called at startup of both rca_service.py and metrics_exporter.py.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            # Don't overwrite vars already set in environment
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def save_report(report_text: str, output_dir: str) -> str:
    """
    Save the RCA report to a Markdown file.

    Args:
        report_text: The Markdown report text from Gemini.
        output_dir:  Directory to save the report in.

    Returns:
        Full path to the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts       = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"rca_report_{ts}.md"
    filepath = os.path.join(output_dir, filename)

    # Also write to the fixed name so it's easy to find
    fixed_path = os.path.join(output_dir, "rca_report.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    with open(fixed_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"[Utils] ✓ Report saved → {filepath}")
    print(f"[Utils] ✓ Report saved → {fixed_path} (latest)")
    return filepath


def pretty_json(data: dict) -> str:
    """Return a nicely indented JSON string for logging."""
    return json.dumps(data, indent=2, default=str)
