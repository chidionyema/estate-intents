#!/usr/bin/env python3
"""Get shadow-verify job logs."""
import subprocess
import json
import zipfile
import io

IDP = "/Users/roseonyema/Documents/code/idp"

r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/pulls/4731", "--jq", ".head.sha"],
    capture_output=True, text=True, cwd=IDP
)
sha = r.stdout.strip()

r2 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/commits/{sha}/check-runs",
     "--jq", ".check_runs[] | select(.name == \"shadow-verify\") | .id"],
    capture_output=True, text=True, cwd=IDP
)
job_id = r2.stdout.strip()
print(f"Job ID: {job_id}")

# Get logs
# Try gh run view --log
r3 = subprocess.run(
    ["gh", "run", "view", job_id, "--log"],
    capture_output=True, text=True, cwd=IDP, timeout=15
)
if r3.returncode == 0 and r3.stdout:
    lines = r3.stdout.split('\n')
    for i, line in enumerate(lines):
        if any(x in line.lower() for x in ['error', 'fail', 'exit code', 'not found', 'k3d', 'docker', 'cannot']):
            for j in range(max(0, i-1), min(len(lines), i+3)):
                if lines[j].strip():
                    print(f"  {j+1}: {lines[j][:200]}")
            print()
else:
    print(f"gh run view failed: {r3.stderr[:200]}")
    # Try direct API with raw output
    import urllib.request
    import os
    token = os.environ.get('GH_TOKEN', '')
    if not token:
        # Try gh auth token
        r4 = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
        token = r4.stdout.strip()
    if token:
        req = urllib.request.Request(
            f'https://api.github.com/repos/chidionyema/idp/actions/jobs/{job_id}/logs',
            headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            if data[:2] == b'PK':
                z = zipfile.ZipFile(io.BytesIO(data))
                for fname in sorted(z.namelist()):
                    content = z.read(fname).decode('utf-8', errors='replace')
                    lines2 = content.split('\n')
                    for i, line in enumerate(lines2):
                        if any(x in line.lower() for x in ['error', 'fail', 'exit code', 'not found', 'k3d', 'docker', 'cannot']):
                            for j in range(max(0, i-1), min(len(lines2), i+3)):
                                if lines2[j].strip():
                                    print(f"  {j+1}: {lines2[j][:200]}")
                            print()
            else:
                print(f"Not a zip: {data[:200]}")
        except Exception as e:
            print(f"urlopen error: {e}")
    else:
        print("No GH token available")
