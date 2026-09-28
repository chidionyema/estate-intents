#!/usr/bin/env python3
"""Add mutation-pr-gate.yml to main via a separate PR."""
import subprocess
import sys
import os

IDP = "/Users/roseonyema/Documents/code/idp"

def run(cmd, check=True, cwd=None):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, cwd=cwd or IDP)
    if r.returncode != 0 and check:
        print(f"FAIL: {cmd}")
        print(r.stderr[:500])
        sys.exit(1)
    return r

# Remove stale lock
run(f"rm -f {IDP}/.git/index.lock", check=False)

# Switch to main and pull latest
run(f"cd {IDP} && git checkout main && git pull origin main", check=False)

# Create new branch from main
run(f"cd {IDP} && git checkout -b add/mutation-pr-gate", check=False)

# Get the gate file from feat/pobr's origin
gate_content = subprocess.run(
    ["git", "show", "origin/feat/pobr:.github/workflows/mutation-pr-gate.yml"],
    capture_output=True, text=True, cwd=IDP
)
if gate_content.returncode != 0:
    print("ERROR: could not get mutation-pr-gate.yml from origin/feat/pobr")
    sys.exit(1)

# Write to local .github/workflows/
os.makedirs(f"{IDP}/.github/workflows", exist_ok=True)
with open(f"{IDP}/.github/workflows/mutation-pr-gate.yml", "w") as f:
    f.write(gate_content.stdout)
print(f"Wrote mutation-pr-gate.yml ({len(gate_content.stdout)} bytes)")

# Commit and push
run(f"cd {IDP} && git add .github/workflows/mutation-pr-gate.yml")
run(f"cd {IDP} && git commit -m 'ci: add mutation-pr-gate workflow'")

# Push new branch
r = run(f"cd {IDP} && git push origin add/mutation-pr-gate", check=False)
if r.returncode != 0:
    # Branch might already exist from a previous attempt
    run(f"cd {IDP} && git push origin add/mutation-pr-gate --force", check=False)
    print("Force-pushed (branch may have existed)")
else:
    print("Pushed new branch")

# Create PR
r = run(
    'cd ' + IDP + ' && gh pr create --title "ci: mutation PR gate" '
    '--body "Adds mutation testing PR gate to main." '
    '--base main --head add/mutation-pr-gate',
    check=False
)
if r.returncode == 0:
    print("PR created:", r.stdout.strip())
else:
    # Check if PR already exists
    r2 = run('cd ' + IDP + ' && gh pr list --base main --head add/mutation-pr-gate --json number --jq ".[0].number"', check=False)
    if r2.stdout.strip():
        print("PR already exists:", r2.stdout.strip())
    else:
        print("PR create failed:", r.stderr[:200])

print("Done.")
