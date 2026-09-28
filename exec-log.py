#!/usr/bin/env python3
"""Get executes-gate failure details."""
import subprocess
import zipfile
import io
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get the failing executes-gate check
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--jq", ".check_runs[] | select(.name == \"executes-gate\" and .conclusion == \"failure\") | {name, conclusion, id}"],
    capture_output=True, text=True, cwd=IDP
)
checks = [json.loads(l) for l in r2.stdout.strip().split('\n') if l.strip()]
if not checks:
    print("No executes-gate failure found")
    exit(0)

c = checks[0]
print(f"Check: {c['name']} id={c['id']}")

# Get annotations
r3 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/check-runs/{c['id']}/annotations"],
    capture_output=True, text=True, cwd=IDP
)
anns = json.loads(r3.stdout) if r3.stdout.strip() else []
print(f"Annotations ({len(anns)}):")
for a in anns[:5]:
    print(f"  [{a.get('annotation_level')}] {a.get('path','')}:{a.get('start_line','')}")
    print(f"    {a.get('message','')[:300]}")

# Download and read logs
r4 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/actions/jobs/{c['id']}/logs"],
    capture_output=True, cwd=IDP, timeout=15
)
if r4.returncode == 0 and r4.stdout[:2] == b'PK':
    z = zipfile.ZipFile(io.BytesIO(r4.stdout))
    for fname in sorted(z.namelist()):
        content = z.read(fname).decode('utf-8', errors='replace')
        lines = content.split('\n')
        # Look for error lines
        errors = [(i, l) for i, l in enumerate(lines)
                  if any(x in l.lower() for x in ['error', 'fail', 'exception', 'exit code', 'not executable'])]
        if errors:
            print(f"\n  File: {fname}")
            for i, l in errors[:10]:
                # Print context
                for j in range(max(0, i-1), min(len(lines), i+2)):
                    print(f"    {j+1}: {lines[j][:200]}")
                print()
