#!/usr/bin/env python3
"""Check mutation-pr-gate failure."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get the workflow ID for mutation-pr-gate
r = subprocess.run(
    ["gh", "api", "/repos/chidionyema/idp/actions/workflows",
     "--jq", ".workflows[] | select(.name == \"mutation-pr-gate\") | {id, name, path}"],
    capture_output=True, text=True, cwd=IDP
)
try:
    wf = json.loads(r.stdout)
    print(f"Workflow: {wf}")
except:
    print(f"Workflow lookup failed: {r.stderr[:200]}")
    # Try listing all workflows
    r2 = subprocess.run(
        ["gh", "api", "/repos/chidionyema/idp/actions/workflows",
         "--jq", ".workflows[].name"],
        capture_output=True, text=True, cwd=IDP
    )
    print(f"All workflows: {r2.stdout[:500]}")
    exit(1)

wf_id = wf["id"]

# Get runs for this workflow on feat/pobr
r3 = subprocess.run(
    ["gh", "api", f"/repos/chidionyema/idp/actions/workflows/{wf_id}/runs?branch=feat/pobr&per_page=1",
     "--jq", ".workflow_runs[0] | {id, head_sha, conclusion, status}"],
    capture_output=True, text=True, cwd=IDP
)
try:
    run = json.loads(r3.stdout)
    print(f"Latest run: {run}")
    if run:
        run_id = run["id"]
        # Get jobs
        r4 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/actions/runs/{run_id}/jobs",
             "--jq", ".jobs[] | {name, conclusion, status}"],
            capture_output=True, text=True, cwd=IDP
        )
        jobs = json.loads(r4.stdout)
        for j in jobs:
            print(f"  {j}")
except Exception as e:
    print(f"Error: {e}")
    print(r3.stderr[:300])
