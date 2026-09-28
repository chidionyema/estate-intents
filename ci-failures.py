#!/usr/bin/env python3
"""Get failure reasons for PR 4731."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get failing runs
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731",
     "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()
print(f"HEAD SHA: {sha}")

# Get all check runs for this SHA
r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--paginate"],
    capture_output=True, text=True, cwd=IDP
)
checks = json.loads(r2.stdout)
print(f"\nFailing checks:")
for c in checks.get("check_runs", []):
    if c["conclusion"] != "success":
        print(f"\n  {c['name']}")
        print(f"  conclusion: {c['conclusion']}")
        print(f"  url: {c['html_url']}")
        # Get annotations
        r3 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/check-runs/{c['id']}/annotations",
             "--paginate"],
            capture_output=True, text=True, cwd=IDP
        )
        try:
            anns = json.loads(r3.stdout)
            for a in anns.get("annotations", [])[:3]:
                print(f"  {a.get('annotation_level')}: {a.get('message','')[:200]}")
        except:
            pass
