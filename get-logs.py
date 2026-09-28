#!/usr/bin/env python3
"""Get job logs from failing runs."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get the latest run for PR 4731
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()
print(f"PR HEAD: {sha}")

# Get check runs for this SHA
r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--jq", ".check_runs[] | select(.conclusion != \"success\" and .conclusion != \"skipped\") | {name, conclusion, html_url, id}"],
    capture_output=True, text=True, cwd=IDP
)
try:
    checks = json.loads(r2.stdout)
    if not checks:
        print("No failing checks found")
        exit(0)
    print(f"\nFailing checks ({len(checks)}):")
    for c in checks:
        print(f"  {c['name']} ({c['conclusion']})")
except:
    print(f"Parse error: {r2.stdout[:200]}")
    print(f"stderr: {r2.stderr[:200]}")
