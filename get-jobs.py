#!/usr/bin/env python3
"""Get workflow failure details."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

# Get run IDs
for wf_name in ["mutation-nightly.yml", "mutation-pr-gate.yml"]:
    print(f"\n{'='*60}")
    print(f"WORKFLOW: {wf_name}")
    r = subprocess.run(
        ["gh", "api", f"/repos/chidionyema/idp/actions/workflows/{wf_name}/runs",
         "--paginate", "--jq", ".workflow_runs[0] | {id, run_number, status, conclusion, head_sha}"],
        capture_output=True, text=True, cwd=IDP
    )
    try:
        run = json.loads(r.stdout)
        if not run:
            print("  No runs"); continue
        print(f"  ID={run['id']}  status={run['status']}  conclusion={run['conclusion']}")
        print(f"  SHA: {run.get('head_sha','')[:8]}")

        # Get jobs via direct API
        r2 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/actions/runs/{run['id']}/jobs"],
            capture_output=True, text=True, cwd=IDP
        )
        data = json.loads(r2.stdout)
        jobs = data.get("jobs", [])
        print(f"  Jobs: {len(jobs)}")
        for j in jobs:
            print(f"    {j['name']}  {j.get('conclusion') or j.get('status')}")
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  stdout: {r.stdout[:300]}")
        print(f"  stderr: {r.stderr[:200]}")
