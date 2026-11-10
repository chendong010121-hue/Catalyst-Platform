"""Write the identity of this method candidate: what runs, and the digest over it.

An identity that names only one half cannot be reviewed, and an admission that names only
the Skill package cannot name M1 at all: this candidate's rule lives in a prompt paragraph
and a row check, and neither is a Skill file. So three things are bound here, and the
identity is the digest over exactly them:

* the **candidate commit and its tree** - which source this is;
* the **prompt paragraph digest** - the rule the model reads;
* the **check implementation digest** - the rule the code enforces.

The unchanged Skill package is reported beside them, explicitly as the half that cannot
identify M1 on its own.

    PYTHONUTF8=1 python scripts/m1_method_package.py
    PYTHONUTF8=1 python scripts/m1_method_package.py --write-spec <path/to/candidate.json>

Zero API. Writes `M1-METHOD-PACKAGE.json` at the repository root.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalyst_platform.semantic_acceptance import method_identity  # noqa: E402

CHECK_IMPLEMENTATION = "catalyst_platform/understand_semantic.py"
CARRIED = (
    "catalyst_platform/understand_semantic.py",
    "tests/test_semantic_duty_holder_source.py",
    "scripts/m1_offline_control.py",
)
PROMPT_MARKER = "prints its own holder before a colon"
PROMPT_END = "never hung on the nearest name."
RULES = {
    "duty_holder_names_another_group": "句子点名的群体与 subject 不是同一群体时，duty 降为未解析并写出那个名字",
    "duty_holder_not_declared": "既有规则：持有人在本次声明里找不到",
    "label_headings": "「服务」「管理+赋能」「管理赋能」是栏目标签，不是持有人；词表显式声明，不推广成「冒号前都是实体」",
}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _prompt_paragraph() -> str:
    text = (ROOT / CHECK_IMPLEMENTATION).read_text(encoding="utf-8")
    start = text.find(PROMPT_MARKER)
    if start < 0:
        raise SystemExit("prompt paragraph not found")
    start = text.rfind('"', 0, start) + 1
    end = text.find(PROMPT_END, start)
    if end < 0:
        raise SystemExit("prompt paragraph end not found")
    raw = text[start:end + len(PROMPT_END)]
    return "".join(piece for piece in raw.split('" ') if piece)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def identity_sha(commit: str, tree: str, prompt: str, check: str) -> str:
    """The one digest that names M1: which source, what the model reads, what the code enforces."""
    return _sha_bytes("\n".join([commit, tree, prompt, check]).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-spec", type=Path, default=None,
                        help="also write the binding spec the entry script reads")
    parser.add_argument("--out", type=Path, default=None,
                        help="where the package report goes; default: beside the spec, or stdout-less root")
    args = parser.parse_args()

    skill = method_identity({})
    paragraph = _prompt_paragraph()
    prompt_sha = _sha_bytes(paragraph.encode("utf-8"))
    check_sha = _sha_file(ROOT / CHECK_IMPLEMENTATION)
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    identity = identity_sha(commit, tree, prompt_sha, check_sha)
    files = [{"path": path, "sha256": _sha_file(ROOT / path)} for path in CARRIED]

    package = {
        "candidate": "M1 主体绑定以明确来源为准",
        "method_commit": commit,
        "method_tree": tree,
        "method_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "method_identity_sha256": identity,
        "identity_inputs": {
            "method_commit": commit,
            "method_tree": tree,
            "prompt_paragraph_sha256": prompt_sha,
            "check_implementation_sha256": check_sha,
        },
        "skill_package": {
            "package_sha256": skill["package_sha256"],
            "files": len(skill["files"]),
            "note": "Skill 文件未改；单独用这个摘要不能识别 M1，因为规则不在 Skill 文件里",
        },
        "carried_checks": {"files": files, "prompt_paragraph_chars": len(paragraph)},
        "rules": RULES,
        "what_it_does_not_include": [
            "模型与参数（未定）",
            "请求数与费用上限（未定）",
            "真实运行产生的卡片（未运行）",
        ],
    }
    # The report lives beside the binding spec, not inside the tree it identifies: a file
    # that records the commit it was written from cannot also be part of that commit
    # without the two disagreeing.
    out = args.out or (args.write_spec.parent / "M1-METHOD-PACKAGE.json" if args.write_spec
                       else ROOT.parent / "m1-method-package.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(package, ensure_ascii=False, indent=2) + "\n")

    if args.write_spec:
        spec = {
            "candidate_id": "m1-duty-holder",
            "root": str(ROOT),
            "method_commit": commit,
            "method_tree": tree,
            "method_identity_sha256": identity,
            "prompt_paragraph_sha256": prompt_sha,
            "check_implementation_sha256": check_sha,
            "skill_package_sha256": skill["package_sha256"],
            "note": ("入口以 --candidate-spec 显式选择本候选；路径、commit、tree、三个摘要任一不符即停止，"
                     "不回退 main。skill_package_sha256 只作记录，单独不能识别 M1。"),
        }
        args.write_spec.parent.mkdir(parents=True, exist_ok=True)
        with io.open(args.write_spec, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        print("wrote spec", args.write_spec)

    print(json.dumps({"commit": commit[:8], "tree": tree[:8], "identity": identity},
                     ensure_ascii=False, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
