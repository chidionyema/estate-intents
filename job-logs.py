#!/usr/bin/env python3
"""Get job logs for failing checks."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs"],
    capture_output=True, text=True, cwd=IDP
)
checks = json.loads(r2.stdout)

for c in checks.get("check_runs", []):
    if c["conclusion"] not in ("success", "skipped", None):
        print(f"\n{'='*60}")
        print(f"{c['name']} (id={c['id']})")
        r3 = subprocess.run(
            ["gh", "run", "view", str(c['id']), "--log"],
            capture_output=True, text=True, cwd=IDP, timeout=10
        )
        if r3.stdout:
            lines = r3.stdout.strip().split('\n')
            # Print last 30 lines looking for errors
            for line in lines[-30:]:
                print(f"  {line[:200]}")
        else:
            print(f"  No logs: {r3.stderr[:100]}")
