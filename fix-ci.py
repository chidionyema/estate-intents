#!/usr/bin/env python3
"""Get annotations for failing CI jobs on PR 4731."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get SHA of PR 4731
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

# Get check runs
r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs"],
    capture_output=True, text=True, cwd=IDP
)
checks = json.loads(r2.stdout)

for c in checks.get("check_runs", []):
    if c["conclusion"] not in ("success", "skipped", None):
        print(f"\n{'='*60}")
        print(f"FAILING: {c['name']} ({c['conclusion']})")
        print(f"URL: {c['html_url']}")

        # Get annotations for this check run
        job_id = c["id"]
        r3 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/check-runs/{job_id}/annotations"],
            capture_output=True, text=True, cwd=IDP
        )
        try:
            anns = json.loads(r3.stdout)
            if anns:
                for a in anns[:5]:
                    print(f"  [{a.get('annotation_level','?')}] {a.get('message','(no message)')[:300]}")
            else:
                print("  No annotations")
                # Get log tail
                r4 = subprocess.run(
                    ["gh", "api", f"/repos/chidionyema/idp/actions/jobs/{job_id}/logs"],
                    capture_output=True, text=True, cwd=IDP, timeout=10
                )
                if r4.stdout:
                    lines = r4.stdout.strip().split('\n')
                    # Find errors
                    for line in lines[-100:]:
                        if any(x in line.lower() for x in ['error', 'fail', 'exception', 'traceback']):
                            print(f"  {line[:200]}")
        except Exception as e:
            print(f"  Parse error: {e}")
