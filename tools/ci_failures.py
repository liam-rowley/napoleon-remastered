#!/usr/bin/env python3
"""Build docs/CI_FAILURES.md: one row per failed gates.yml run attempt, with its class and the guard that answers it (J42).

purpose: list every failed `gates.yml` run attempt in a time window (reruns included: a rerun that passed hides its failed first attempt from `gh run list`), with the failed job and step and the first error line from its log, and render the committed failure table; the class and guard of each row come from CLASSES below, so a new failure is classed here, not in the generated file
usage: python3 tools/ci_failures.py --since 2026-10-29T00:00:00Z --until <utc> [--cache <json>] [--out docs/CI_FAILURES.md]   (--cache reuses a fetch; needs `gh` signed in)
when: by hand, when CI failures are reviewed (J42 built the first table); not part of any gate (it reads GitHub)
not-a-verb: a one-off report generator over the GitHub API; the table it writes is the record
"""
import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Classes (docs/CI_FAILURES.md "Classes"); each row of the table gets one.
BRANCH, CI_ONLY, FLAKY, WORKFLOW = "branch bug", "CI-only test", "flaky", "workflow"

# The guard this job (J42) adds for each kind of failure; a branch bug needs none: CI did its job.
GUARDS = {
    "branch": "none: branch bug, CI did its job",
    "smoke": "local route: `build.sh --docker smoke`, run by `tests/test_proxy_host.py` after `all` (J42)",
    "harness-host": "local route: `tests/test_harness_host.py` runs `Run-HostTests.ps1` under Windows PowerShell 5.1 (J42)",
    "policy": "local route named in `wsc jobs next` and `docs/REVIEW.md`: `python3 tools/pr_policy.py` (J42)",
    "heartbeat": "race fix: the watcher writes its first heartbeat before its first housekeeping pass, unit guard `static: the watcher "
                 "writes its first heartbeat...`; a failed start prints the watcher log (J42)",
    "rollback": "same race as the heartbeat (the revert waits for the old watcher's first heartbeat): fixed with it (J42)",
    "hashes": "race fix: `Hash-OrAbsent` reads each file once, unit guard `static: integration helpers never hash a file after a "
              "separate Test-Path` (J42)",
    "hang": "race fix in J19 (`hang.txt` before and after `Kill-Game`, unit guard `static: Handle-Hang ...`)",
    "auto-restore-log": "race fix in the J2 review (wait for the log lines, never read the log once)",
    "core_pin": "workflow fix: the pinned-tag fetch in `gates.yml` job `gates` (J41 review); the core's shallow-tag check is "
                "warscape-core's (open question in jobs/J42/report.md)",
    "console": "local route: `tests/test_proxy_host.py` runs the proxy host tests in `wsc gates` (J41)",
    "gzip": "fixed in the J7 review (`.tsv.gz` bytes no longer depend on the zlib build); the failure comment and `wsc jobs` "
            "listing tell the next session (J42)",
    "posix": "fixed in the J39 review (the test's root is POSIX on every host); the failure comment and `wsc jobs` listing tell the "
             "next session (J42)",
}

# run id (or "run/attempt") -> (class, guard key, note). Classed by reading the log and the commit that followed.
_J3 = (40840800818, 40843620267, 40844850374, 40846875148, 40847306677, 40847750402, 40848350112, 40849018927, 40850562639,
       40851273817, 40853702111, 40855770006, 40858709890)
_J15_SMOKE = (40946469799, 40946733041, 40947109181, 40951863309, 40952524994, 40956446776, 40956451648)
CLASSES = {
    **{f"{r}:auto-restore": (FLAKY, "auto-restore-log", "test read the log once before the watcher wrote the line") for r in (40832855493, 40832860145)},
    **{f"{r}:proxy": (CI_ONLY, "smoke", "wine smoke: minidump=2 default left nothing for the unhandled filter (build.sh step 4)") for r in _J3},
    **{f"{r}:proxy": (CI_ONLY, "smoke", "wine smoke still expected 0 engine sites after J15 added the first") for r in _J15_SMOKE},
    **{f"{r}:heartbeat": (FLAKY, "heartbeat", "watcher start: no heartbeat in 40 s, before any case ran")
       for r in ("40864853540/1", "40864853540/2", 40907834477, 40909011779, 40909021399, 40951863309, 40953862308)},
    **{f"{r}:hang": (FLAKY, "hang", "asserted hang.txt before the watcher wrote it") for r in (40878131007, 40889835620)},
    "40898971722:auto-restore": (FLAKY, "hashes", "Hashes: Test-Path saw dxvk.conf, the watcher deleted it before the hash"),
    "40956451648:rollback": (FLAKY, "rollback", "revert timed out at 150 s, then the next two cases timed out behind it"),
    **{f"{r}:policy": (BRANCH, "policy", "the branch changed files its kind may not") for r in
       (40867399646, 40895788310, 40896966222, 40903417452, 40903777547, 40931691218)},
    **{f"{r}:gates": (CI_ONLY, "gzip", "committed .tsv.gz bytes differ between the PC's zlib-ng and CI's zlib")
       for r in (40913488050, 40913736156, 40914454620, 40916071314, 40916121386)},
    **{f"{r}:gates": (CI_ONLY, "posix", "Windows path in a test: Path('C:\\\\repo').as_posix() differs on Linux")
       for r in (40926693022, 40927224019, 40927617902)},
    "40931548409:gates": (BRANCH, "branch", "the queue failed `wsc jobs check`"),
    **{f"{r}:proxy": (CI_ONLY, "console", "test_console lint failure; no local gate ran the C++ host tests yet") for r in (40953826497, 40953862308)},
    **{f"{r}:gates": (WORKFLOW, "core_pin", "warscape-core cut v0.3.0; the depth-1 submodule fetch lacked the pinned tag (runs cancelled by the next push)")
       for r in (40962228864, 40962483519, 40962535611)},
}


def gh(*args):
    for wait in (2, 4, 8, 0):  # a TLS handshake timeout is common over a few hundred calls: retry it, never a 4xx
        out = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode == 0 or "timeout" not in out.stderr.lower() or not wait:
            break
        time.sleep(wait)
    if out.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


# Most telling first: a harness case name, a unittest or C++ test failure, a smoke or policy refusal, then any failure word.
ERROR_PATTERNS = [r"^FAILED: ", r"^FAIL: test_", r"^FAIL \S+\.cpp:\d+", r"^build\.sh smoke: ", r"REFUSED", r"^FAIL  ",
                  r"AssertionError", r"\b(core_pin|untagged commit)\b", r"FullyQualifiedErrorId : timed out",
                  r"\b(timed out|Timeout|exceeded)\b", r"^FAIL "]


def first_error(log):
    """The most telling failure line of a job log, without the runner's timestamp; the runner's own exit line only if nothing else."""
    lines = [re.sub(r"^\S+Z ", "", ln).strip() for ln in log.splitlines()]
    for pat in ERROR_PATTERNS:
        hit = next((ln for ln in lines if re.search(pat, ln)), None)
        if hit:
            return re.sub(r"/home/runner/work/[^/]+/[^/]+/", "", hit)[:200]
    return next((ln[len("##[error]"):] for ln in lines if ln.startswith("##[error]")), "")[:200]


def fetch(since, until):
    runs = json.loads(gh("run", "list", "-w", "gates.yml", "-L", "300", "--json",
                         "databaseId,event,headBranch,headSha,conclusion,createdAt,attempt"))
    runs = [r for r in runs if since <= r["createdAt"] <= until]
    passed = {}  # sha -> set of job names that passed in some run of that commit
    rows = []
    for r in sorted(runs, key=lambda r: r["createdAt"]):
        for n in range(1, r["attempt"] + 1):
            # a cancelled run can hold a failed job (the newer push cancelled it after the job failed: PR #55's core_pin runs)
            if n == r["attempt"] and r["conclusion"] not in ("failure", "cancelled"):
                continue
            att = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{r['databaseId']}/attempts/{n}"))
            if att["conclusion"] not in ("failure", "cancelled"):
                continue
            jobs = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{r['databaseId']}/attempts/{n}/jobs"))["jobs"]
            for j in jobs:
                if j["conclusion"] not in ("failure", "timed_out"):
                    continue
                step = next((s["name"] for s in j["steps"] if s["conclusion"] in ("failure", "timed_out")), "")
                try:
                    log = gh("api", f"repos/{{owner}}/{{repo}}/actions/jobs/{j['id']}/logs")
                except SystemExit:
                    log = ""
                if r["headSha"] not in passed:
                    passed[r["headSha"]] = set()
                    for o in runs:
                        if o["headSha"] == r["headSha"]:
                            oj = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{o['databaseId']}/jobs"))["jobs"]
                            passed[r["headSha"]] |= {x["name"] for x in oj if x["conclusion"] == "success"}
                rows.append({"run": r["databaseId"], "attempt": n, "event": r["event"], "branch": r["headBranch"],
                             "sha": r["headSha"][:8], "created": r["createdAt"], "run_conclusion": att["conclusion"],
                             "job": j["name"], "step": step, "error": first_error(log),
                             "passed_elsewhere": j["name"] in passed[r["headSha"]]})
    return rows


def tag(row):
    """The CLASSES key suffix: the harness case that failed (one job, several races), else the job name."""
    if row["job"] == "harness-windows":
        for t, rx in (("heartbeat", r"heartbeat"), ("auto-restore", r"auto-restore"), ("hang", r"hang watchdog"),
                      ("rollback", r"update rollback")):
            if re.search(rx, row["error"]):
                return t
    return row["job"]


def classify(row):
    for key in (f"{row['run']}/{row['attempt']}:{tag(row)}", f"{row['run']}:{tag(row)}"):
        if key in CLASSES:
            return CLASSES[key]
    return ("unclassed", "", "")


def render(rows, since, until):
    out = ["# CI failures", "",
           f"Every failed `gates.yml` run attempt from {since} to {until}, one row per failed job. Generated by "
           "`tools/ci_failures.py` (classes live there, in `CLASSES`); do not edit the table by hand.", "",
           "## Classes", "",
           f"- **{BRANCH}**: the commit was wrong; CI did its job.",
           f"- **{CI_ONLY}**: the branch broke a check it had no way to run before pushing.",
           f"- **{FLAKY}**: the same commit passed in another run.",
           f"- **{WORKFLOW}**: CI itself was wrong (pins, fetch depth, concurrency, runner).", "",
           "## Summary", "", "| class | rows | guard |", "|---|---|---|"]
    classed = [(r, *classify(r)) for r in rows]
    counts = Counter(c for _, c, _, _ in classed)
    guards = {}
    for _, c, g, _ in classed:
        guards.setdefault(c, [])
        if GUARDS.get(g, g) not in guards[c]:
            guards[c].append(GUARDS.get(g, g))
    for c in (BRANCH, CI_ONLY, FLAKY, WORKFLOW, "unclassed"):
        if counts[c]:
            out.append(f"| {c} | {counts[c]} | {'<br>'.join(guards[c])} |")
    out += ["", "Every failure, whatever its class, now also comments on its pull request and is listed by `wsc jobs next|review|view` "
            "(J42), so a red check on an open pull request is told, not found.", "",
            "## Failures", "",
            "| run | event | branch | commit | job | step | first error line | class | guard | note |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r, c, g, note in classed:
        run = f"{r['run']}" + (f" (attempt {r['attempt']})" if r["attempt"] > 1 else "")
        err = r["error"].replace("|", "\\|").replace("`", "'")
        out.append(f"| {run} | {r['event']} | {r['branch']} | {r['sha']} | {r['job']} | {r['step']} | `{err}` | {c} | "
                   f"{GUARDS.get(g, g)} | {note} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--cache", help="json file: read it if it exists, else fetch and write it")
    ap.add_argument("--out", default=str(ROOT / "docs" / "CI_FAILURES.md"))
    a = ap.parse_args()
    cache = Path(a.cache) if a.cache else None
    if cache and cache.exists():
        rows = json.loads(cache.read_text(encoding="utf-8"))
    else:
        rows = fetch(a.since, a.until)
        if cache:
            cache.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    Path(a.out).write_text(render(rows, a.since, a.until), encoding="utf-8", newline="\n")
    unclassed = [r for r in rows if classify(r)[0] == "unclassed"]
    print(f"{len(rows)} failed jobs, {len(unclassed)} unclassed -> {a.out}")
    for r in unclassed:
        print(f"  {r['run']}/{r['attempt']} {r['branch']} {r['sha']} {r['job']} | {r['step']} | {r['error']}")
    return 1 if unclassed else 0


if __name__ == "__main__":
    sys.exit(main())
