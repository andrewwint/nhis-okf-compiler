"""Command-line interface: fetch, compile, verify, query.

    python -m nhis_okf fetch      # download the NHIS 2023 public-use file
    python -m nhis_okf compile    # verify concepts and emit the OKF bundle
    python -m nhis_okf verify     # run execution-grounded verification, print verdicts
    python -m nhis_okf query "how many adults with diabetes take insulin?"
"""

from __future__ import annotations

import argparse
import sys

from . import analysis, concepts as concepts_mod, verify as verify_mod, trends as trends_mod, registry
from .compiler import compile_bundle, check_conformance, OKF_DIR

# Columns the diabetes slice needs (keeps the 29MB load fast).
SLICE_COLUMNS = [
    "DIBEV_A", "DIBINS_A", "DIBPILL_A", "DIBAGETC_A", "PREDIB_A", "GESDIB_A",
    "WTFA_A", "PSTRAT", "PPSU",
]


def _load_df():
    return analysis.load_microdata(columns=SLICE_COLUMNS)


def cmd_fetch(_args) -> int:
    for year in sorted(registry.YEAR_FILES):
        path = trends_mod.fetch_year(year)
        print(f"microdata ready ({year}): {path}")
    return 0


def cmd_trends(_args) -> int:
    results = trends_mod.verify_all_trends()
    caught = 0
    for r in results:
        line = f"[{r.verdict:5}] {r.concept_id}  correct={r.correct}"
        print(line)
        for d in r.diagnosis:
            print(f"    - {d}")
        if r.caught:
            caught += 1
            print("    ^ caught by EXECUTION (the lint passed)")
    print(f"\n{caught} cross-year defect(s) caught by execution-grounded verification.")
    real_failures = [
        r for r in results if r.verdict == trends_mod.FAIL and not r.seeded_defect
    ]
    return 1 if real_failures else 0


def cmd_verify(_args) -> int:
    df = _load_df()
    results = verify_mod.verify_all(df, concepts_mod.load_all())
    caught = 0
    for r in results:
        head = f"[{r.verdict:11}] {r.concept_id}"
        if r.claimed_pct is not None:
            head += f"  claimed={r.claimed_pct}%  correct={r.correct_pct}%  Δ={r.delta_pp}pp"
        print(head)
        for d in r.diagnosis:
            print(f"    - {d}")
        if r.caught:
            caught += 1
            print("    ^ caught by EXECUTION (the lint passed)")
    print(f"\n{caught} defect(s) caught by execution-grounded verification.")
    # Non-zero exit if a non-seeded concept failed (a real regression).
    real_failures = [
        r for r in results if r.verdict == verify_mod.FAIL and not r.seeded_defect
    ]
    return 1 if real_failures else 0


def cmd_compile(_args) -> int:
    df = _load_df()
    report = compile_bundle(df)
    print(f"written to .okf/variables/: {report.written}")
    print(f"quarantined (failed verification): {report.quarantined}")
    if report.trend_results:
        print(f"trends written: {report.trend_written}")
        print(f"trends quarantined: {report.trend_quarantined}")
    print(f"audit log: .okf/log.md")
    if not report.ok:
        print("WARNING: compile invariant violated (a seeded defect passed or a sound "
              "concept failed).", file=sys.stderr)
        return 1
    return 0


def cmd_conformance(_args) -> int:
    ok, issues = check_conformance(OKF_DIR)
    if ok:
        print("OKF v0.1 conformance: PASS")
        return 0
    print("OKF v0.1 conformance: FAIL")
    for i in issues:
        print(f"    - {i}")
    return 1


def cmd_query(args) -> int:
    from .chat import answer

    ans = answer(args.question)
    print(f"[{ans.mode}] {ans.text}")
    if ans.citations:
        print(f"\ncitations: {', '.join(ans.citations)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nhis", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="download the NHIS 2023 public-use file")
    sub.add_parser("compile", help="verify concepts and emit the OKF bundle")
    sub.add_parser("verify", help="run execution-grounded verification")
    sub.add_parser("conformance", help="check the bundle against the OKF v0.1 spec")
    sub.add_parser("trends", help="verify cross-year trends (the 2019 redesign-rename catch)")
    q = sub.add_parser("query", help="ask a question grounded in the verified bundle")
    q.add_argument("question")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {
        "fetch": cmd_fetch,
        "compile": cmd_compile,
        "verify": cmd_verify,
        "conformance": cmd_conformance,
        "trends": cmd_trends,
        "query": cmd_query,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
