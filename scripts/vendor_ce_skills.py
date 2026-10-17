#!/usr/bin/env python3
"""Vendor Compound Engineering skills into opencode's skill loader, repo-locally.

CE's upstream SKILL.md files use Claude Code conventions opencode rejects:
`name: ce:plan` (colon, and it does not match the folder name `ce-plan`) and
Claude-only frontmatter keys (`argument-hint`, `disable-model-invocation`).
opencode silently drops such skills, so we rewrite them on the way in.

Source: .ce/plugin (pinned tag, see .ce/plugin/PINNED_TAG)
Output: .opencode/skills/<name>/SKILL.md  (opencode's default project skill dir)

Usage:
    python3 scripts/vendor_ce_skills.py           # (re)generate .opencode/skills/
    python3 scripts/vendor_ce_skills.py --check   # fail if output drifted from source

Requires a `.ce/plugin` checkout, which is gitignored. In a fresh clone this
script cannot run and `--check` fails: the vendored output is committed, but its
source is not, so the committed skills are not reproducible from a clone alone.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".ce" / "plugin" / "plugins" / "compound-engineering" / "skills"
OUT = ROOT / ".opencode" / "skills"

# Curated: the compound-engineering loop plus the skills that help on this
# project. Deliberately omitted, and why:
#   lfg, slfg                  - push/PR automation; this repo must not push
#   git-worktree, resolve-*    - create branches; same reason
#   proof, deploy-docs         - publish over the network
#   rclone, gemini-imagegen, feature-video, frontend-design, agent-browser,
#   test-browser, test-xcode, dspy-ruby, dhh-rails-style, every-style-editor,
#   andrew-kane-gem-writer, orchestrating-swarms, generate_command,
#   agent-native-*, report-bug, reproduce-bug, heal-skill,
#   *-beta                     - Rails/browser/image domains this repo has none of
#   changelog                  - no merges to main in this engagement
# Add a line here to widen the surface; re-run and restart opencode.
SKILLS = [
    "ce-brainstorm",
    "ce-ideate",
    "ce-plan",
    "ce-work",
    "ce-review",
    "ce-compound",
    "ce-compound-refresh",
    "setup",
    "deepen-plan",
    "document-review",
    "compound-docs",
    "create-agent-skill",
    "create-agent-skills",
    "file-todos",
    "triage",
]

# Claude-only frontmatter. opencode's skill schema takes name, description,
# license, compatibility, metadata; anything else risks being rejected.
DROP_KEYS = ("argument-hint", "disable-model-invocation")


def convert(text: str) -> str:
    lines = text.split("\n")
    if lines[0].strip() != "---":
        raise SystemExit("no frontmatter")
    end = lines.index("---", 1)
    head, body = lines[1:end], lines[end:]
    out = []
    for line in head:
        key = line.split(":", 1)[0]
        if key in DROP_KEYS:
            continue
        if key == "name":
            # ce:plan -> ce-plan, matching the folder name opencode requires
            line = "name: " + line.split(":", 1)[1].strip().replace(":", "-")
        out.append(line)
    return "\n".join(["---"] + out + body)


def main() -> int:
    check = "--check" in sys.argv
    if not SRC.is_dir():
        raise SystemExit(
            f"missing {SRC} - see the Compound Engineering section of README.md"
        )
    drift = []
    for name in SKILLS:
        src = SRC / name / "SKILL.md"
        if not src.is_file():
            raise SystemExit(f"missing upstream skill: {src}")
        dst = OUT / name / "SKILL.md"
        want = convert(src.read_text())
        if check:
            got = dst.read_text() if dst.is_file() else ""
            if got != want:
                drift.append(name)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(want)
    if check:
        if drift:
            print("vendored skills drifted from source: " + ", ".join(drift))
            print("run: python3 scripts/vendor_ce_skills.py")
            return 1
        print(f"{len(SKILLS)} vendored skills match source")
        return 0
    print(f"vendored {len(SKILLS)} skills into {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())