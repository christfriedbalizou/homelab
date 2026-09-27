#!/usr/bin/env python3
"""Review a ruleset locally; --apply explicitly writes it to GitHub."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--apply", action="store_true")
parser.add_argument("--repo", default="christfriedbalizou/homelab")
args = parser.parse_args()
path = Path(__file__).resolve().parents[1] / ".github/rulesets/main.json"
payload = json.loads(path.read_text())
if not args.apply:
    print(json.dumps(payload, indent=2))
else:
    endpoint = f"repos/{args.repo}/rulesets"
    pages = json.loads(subprocess.check_output(["gh", "api", "--paginate", "--slurp", endpoint]))
    existing = [rule for page in pages for rule in page]
    match = next((r for r in existing if r["name"] == payload["name"]), None)
    if match:
        endpoint += f"/{match['id']}"
    subprocess.run(["gh", "api", "--method", "PUT" if match else "POST", endpoint,
                    "--input", str(path)], check=True)
