#!/usr/bin/env python3
"""Get shadow-verify failure."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--jq", ".check_runs[] | select(.name == \"shadow-verify\") | {id, conclusion}"],
    capture_output=True, text=True, cwd=IDP
)
c = json.loads(r2.stdout.strip())
print(f"id={c['id']} conclusion={c['conclusion']}")

r3 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/check-runs/{c['id']}/annotations"],
    capture_output=True, text=True, cwd=IDP
)
anns = json.loads(r3.stdout)
for a in anns[:5]:
    print(f"[{a.get('annotation_level')}] {a.get('path','')}:{a.get('start_line','')}")
    print(f"  {a.get('message','')[:300]}")
