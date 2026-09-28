#!/usr/bin/env python3
"""Get full log for specific failing jobs."""
import subprocess
import json
import zipfile
import io

IDP = "/Users/roseonyema/Documents/code/idp"

# Get SHA
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

# Get failing check runs with their job IDs
r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--jq", ".check_runs[] | select(.conclusion == \"failure\") | {name, conclusion, id}"],
    capture_output=True, text=True, cwd=IDP
)
lines = [l for l in r2.stdout.strip().split('\n') if l]
print(f"Failing checks: {len(lines)}")

for line in lines:
    try:
        c = json.loads(line)
        print(f"\n{'='*60}")
        print(f"CHECK: {c['name']} (id={c['id']})")

        # Get annotations
        r3 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/check-runs/{c['id']}/annotations",
             "--jq", ".[] | \"[\\(.annotation_level)] \\(.message) -- \\(.path):\\(.line)\""],
            capture_output=True, text=True, cwd=IDP
        )
        if r3.stdout.strip():
            print("Annotations:")
            for l in r3.stdout.strip().split('\n')[:5]:
                print(f"  {l[:200]}")
        else:
            print("  No annotations")

        # Download logs directly
        r4 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/actions/jobs/{c['id']}/logs"],
            capture_output=True, cwd=IDP, timeout=15
        )
        if r4.status_code == 200 and r4.content[:2] == b'PK':
            try:
                z = zipfile.ZipFile(io.BytesIO(r4.content))
                for name in z.namelist():
                    content = z.read(name).decode('utf-8', errors='replace')
                    lines = content.split('\n')
                    print(f"\n  Log ({name}):")
                    # Find error lines
                    for i, line in enumerate(lines):
                        if any(x in line.lower() for x in ['error', 'fail', 'exception', 'traceback', 'exit code']):
                            start = max(0, i-1)
                            end = min(len(lines), i+2)
                            for l in lines[start:end]:
                                print(f"    {l[:200]}")
            except Exception as e:
                print(f"  Zip error: {e}")
        else:
            print(f"  No zip logs (status={r4.status_code})")
    except Exception as e:
        print(f"Error: {e}")
