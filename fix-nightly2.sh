#!/usr/bin/env python3
"""Write fixed mutation-nightly.yml using separate step for Python."""
content = """# .github/workflows/mutation-nightly.yml
# Runs mutation testing on the full codebase at 3am UTC every day.
# 4 shards so each runner handles ~1/4 of the codebase.
name: mutation-nightly

on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:
    inputs:
      shard:
        description: "Shard to run (blank = all)"
        required: false
        default: ""

jobs:
  mutation:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install mutation tools
        run: |
          pip install -q mutmut
          cargo install cargo-mutants --locked 2>/dev/null || true

      - name: Install orchestrator
        run: |
          mkdir -p "$HOME/.estate/bin"
          cp bin/mutation-orchestrator "$HOME/.estate/bin/mutation-orchestrator"
          chmod +x "$HOME/.estate/bin/mutation-orchestrator"

      - name: Run shard
        env:
          SHARD: ${{ matrix.shard }}/4
        run: |
          python3 "$HOME/.estate/bin/mutation-orchestrator" \\
            --tier=full \\
            --shard="$SHARD" \\
            --cwd="$PWD"

      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: mutation-shard-${{ matrix.shard }}-report
          path: |
            mutmut_output/
            mutants.out/
            reports/
            mewt-report.json
          retention-days: 7

  mutation-summary:
    needs: mutation
    runs-on: ubuntu-latest
    if: always()
    steps:
      - uses: actions/checkout@v4

      - name: Download all reports
        uses: actions/download-artifact@v4
        with:
          pattern: mutation-shard-*-report
          merge-multiple: true

      - name: Write summarise script
        run: |
          printf '%s\\n' \
            'import json, os' \
            'ledger = os.path.expanduser("~/.estate/mutation-ledger.jsonl")' \
            'scores = []' \
            'if os.path.exists(ledger):' \
            '    for line in open(ledger):' \
            '        try:' \
            '            scores.append(json.loads(line))' \
            '        except json.JSONDecodeError:' \
            '            pass' \
            'if scores:' \
            '    print("## Mutation Testing Summary")' \
            '    print()' \
            '    print("| Tier | Score | Killed | Survived | Elapsed | Budget |")' \
            '    print("|------|-------|--------|----------|---------|--------|")' \
            '    for s in scores[-4:]:' \
            '        budget = "\\u2713" if s.get("budget_ok") else "\\u2717"' \
            '        print(f"| {s.get(\\"tier\\",\\"?\\")} | {s.get(\\"score\\",\\"?\\")}% | "' \
            '              f"{s.get(\\"killed\\",0)} | {s.get(\\"survived\\",0)} | "' \
            '              f"{s.get(\\"elapsed_s\\",0)}s | {budget} |")' \
            > /tmp/summarise.py

      - name: Summarise
        run: python3 /tmp/summarise.py
"""

import os
path = "/Users/roseonyema/Documents/code/idp/.github/workflows/mutation-nightly.yml"
with open(path, "w") as f:
    f.write(content)
print(f"Written {os.path.getsize(path)} bytes")
