#!/usr/bin/env python3
"""Get workflow failure reasons."""
import subprocess
import json

IDP = "/Users/roseonyema/Documents/code/idp"

for wf_name in ["mutation-nightly.yml", "mutation-pr-gate.yml"]:
    print(f"\n{'='*50}")
    print(f"WORKFLOW: {wf_name}")
    r = subprocess.run(
        ["gh", "api", f"/repos/chidionyema/idp/actions/workflows/{wf_name}/runs",
         "--paginate", "--jq", ".workflow_runs[0]"],
        capture_output=True, text=True, cwd=IDP
    )
    try:
        run = json.loads(r.stdout)
        if not run:
            print("  No runs")
            continue
        print(f"  Run #{run['run_number']} at {run['created_at']}  status={run['status']}  conclusion={run['conclusion']}")
        run_id = run["id"]

        # Get jobs
        r2 = subprocess.run(
            ["gh", "api", f"/repos/chidionyema/idp/actions/runs/{run_id}/jobs",
             "--jq", ".jobs[] | {name, conclusion, status, id}"],
            capture_output=True, text=True, cwd=IDP
        )
        jobs = [json.loads(l) for l in r2.stdout.strip().split('\n') if l.strip()]
        for j in jobs:
            print(f"  Job: {j['name']}  {j['conclusion'] or j['status']}")

        # Get annotations for failures
        for j in jobs:
            if j.get('conclusion') not in ('success', None):
                r3 = subprocess.run(
                    ["gh", "api", f"/repos/chidionyema/idp/check-runs/{j['id']}/annotations"],
                    capture_output=True, text=True, cwd=IDP
                )
                try:
                    anns = json.loads(r3.stdout)
                    for a in anns[:3]:
                        print(f"  [{a.get('annotation_level')}] {a.get('path','?')}:{a.get('start_line','?')}  {a.get('message','')[:150]}")
                except:
                    pass
    except Exception as e:
        print(f"  Error: {e}  stdout: {r.stdout[:200]}")
