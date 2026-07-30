#!/usr/bin/env python3
"""Verify a fresh full-test report and audit isolated distribution artifacts."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

try:
    from .source_fingerprint import source_tree_fingerprint
except ImportError:  # direct script execution
    from source_fingerprint import source_tree_fingerprint



def fingerprint(project: Path) -> str:
    return source_tree_fingerprint(project)

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project",default=".")
    parser.add_argument("--test-report",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--previous-wheel")
    args=parser.parse_args()
    project=Path(args.project).resolve(); test_path=(project/args.test_report).resolve()
    test=json.loads(test_path.read_text(encoding="utf-8"))
    current=fingerprint(project)
    if not test.get("passed") or test.get("source_tree_sha256") != current:
        raise SystemExit("full test report is missing, failed, or stale; run make test first")
    command=[sys.executable,"scripts/verify_dist.py","--project","."]
    if args.previous_wheel: command += ["--previous-wheel",args.previous_wheel]
    completed=subprocess.run(command,cwd=project,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(completed.stdout,end="" if completed.stdout.endswith("\n") else "\n")
    payload={"passed":completed.returncode==0,"schema":"fresh-tests-plus-isolated-dist-v1","source_tree_sha256":current,"test_report":str(test_path),"test_shard_count":test.get("shard_count"),"test_file_count":test.get("test_file_count"),"distribution_command":command,"distribution_returncode":completed.returncode,"distribution_stdout_tail":completed.stdout.splitlines()[-12:]}
    report=Path(args.report).resolve(); report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    raise SystemExit(0 if payload["passed"] else 1)
if __name__=="__main__": main()
