"""
tests/synthetic_failures/simulator.py — Failure Simulator CLI & Engine (Unit 12).

Standalone CLI demo panel and automated test runner for the 9 synthetic failure scenarios.
Can run in:
  1. Automated batch mode: python -m tests.synthetic_failures.simulator --all
  2. Single scenario mode: python -m tests.synthetic_failures.simulator --scenario wrong_weight
  3. Interactive console menu: python -m tests.synthetic_failures.simulator
  4. Web demo panel: python -m tests.synthetic_failures.simulator --web
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Optional

# Ensure workspace root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from tests.synthetic_failures.scenarios import SCENARIOS, SyntheticScenario
from tests.synthetic_failures.generator import ensure_fixtures, get_scenario_email
from agents.orchestrator import run_single_email
from shared.schemas import SubmissionEntry

# ANSI color styling
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def run_scenario(scenario_id: str, fixtures_dir: Optional[Path] = None) -> dict:
    """Execute a single synthetic failure scenario through the live pipeline."""
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario ID: {scenario_id}")

    sc = SCENARIOS[scenario_id]
    fix_root = ensure_fixtures(fixtures_dir)
    email_data = get_scenario_email(scenario_id, fix_root)

    t0 = time.time()
    state = run_single_email(email_data, dataset_source=str(fix_root))
    latency = time.time() - t0

    entry: SubmissionEntry = state["submission_entry"]
    actual_status = entry.status
    actual_reason = entry.review_reason
    actual_defects = entry.defect_fields or []

    # Verification checks
    status_match = actual_status == sc.expected_status
    reason_match = actual_reason == sc.expected_review_reason
    defects_match = sorted(actual_defects) == sorted(sc.expected_defect_fields)
    passed = status_match and reason_match and defects_match

    # Extract field summary
    extractions_summary = {}
    for att_name, ext in state.get("extractions", {}).items():
        doc_tag = "BL" if "_BL" in att_name.upper() else "SI"
        extractions_summary[doc_tag] = {
            "status": ext.doc_status,
            "fields": {f.field_name: f.value for f in ext.fields if f.value is not None},
        }

    return {
        "scenario_id": scenario_id,
        "name": sc.name,
        "category": sc.category,
        "description": sc.description,
        "passed": passed,
        "latency_seconds": latency,
        "expected_status": sc.expected_status,
        "actual_status": actual_status,
        "expected_review_reason": sc.expected_review_reason,
        "actual_review_reason": actual_reason,
        "expected_defect_fields": sc.expected_defect_fields,
        "actual_defect_fields": actual_defects,
        "status_match": status_match,
        "reason_match": reason_match,
        "defects_match": defects_match,
        "extractions": extractions_summary,
        "timeline_events": [t.get("stage") for t in state.get("timeline_logs", [])],
        "email_id": email_data["email_id"],
    }


def print_scenario_detail(result: dict):
    """Print detailed audit card for a single scenario execution."""
    passed = result["passed"]
    badge = f"{GREEN}{BOLD}[ PASS ]{RESET}" if passed else f"{RED}{BOLD}[ FAIL ]{RESET}"

    print(f"\n{BOLD}{'=' * 76}{RESET}")
    print(f" {BOLD}SCENARIO:{RESET} {result['name']}  {badge}")
    print(f" {BOLD}Category:{RESET} {result['category']} | {BOLD}Latency:{RESET} {result['latency_seconds']:.2f}s")
    print(f" {BOLD}Details:{RESET}  {result['description']}")
    print(f"{'-' * 76}")

    # Status comparison
    st_color = GREEN if result["status_match"] else RED
    print(f"  Status:        Expected: {result['expected_status']:<14} Actual: {st_color}{result['actual_status']}{RESET}")

    # Review Reason comparison
    rr_color = GREEN if result["reason_match"] else RED
    exp_rr = str(result['expected_review_reason'])
    act_rr = str(result['actual_review_reason'])
    print(f"  Review Reason: Expected: {exp_rr:<14} Actual: {rr_color}{act_rr}{RESET}")

    # Defect fields comparison
    df_color = GREEN if result["defects_match"] else RED
    exp_df = str(result['expected_defect_fields'])
    act_df = str(result['actual_defect_fields'])
    print(f"  Defect Fields: Expected: {exp_df:<14} Actual: {df_color}{act_df}{RESET}")

    # Extracted fields overview
    if result.get("extractions"):
        print(f"{'-' * 76}")
        print(f"  {BOLD}Pipeline Extractions:{RESET}")
        for doc, info in result["extractions"].items():
            print(f"    * {BOLD}{doc}{RESET} (doc_status: {info['status']}):")
            for fn, fv in info["fields"].items():
                print(f"        {fn}: {fv}")

    print(f"{BOLD}{'=' * 76}{RESET}\n")


def run_all_scenarios(fixtures_dir: Optional[Path] = None, verbose: bool = True) -> list[dict]:
    """Execute all 9 scenarios sequentially and print formatted summary table."""
    fix_root = ensure_fixtures(fixtures_dir)

    print(f"\n{BOLD}{'=' * 82}{RESET}")
    print(f"  {BOLD}{CYAN}MANIFEST AI -- SYNTHETIC TEST & FAILURE SIMULATOR{RESET}")
    print(f"  Running 9 fault injection scenarios through live LangGraph pipeline...")
    print(f"{BOLD}{'=' * 82}{RESET}\n")

    results = []
    t_start = time.time()

    for idx, (sid, sc) in enumerate(SCENARIOS.items(), 1):
        if verbose:
            print(f"  [{idx}/9] Testing {sc.name}...", end="", flush=True)

        res = run_scenario(sid, fix_root)
        results.append(res)

        if verbose:
            tag = f"{GREEN}PASS{RESET}" if res["passed"] else f"{RED}FAIL{RESET}"
            print(f" [{tag}] ({res['latency_seconds']:.2f}s)")

    t_total = time.time() - t_start
    total_passed = sum(1 for r in results if r["passed"])

    # Summary Table
    print(f"\n{BOLD}+---+----------------------------------+-----------------+----------+----------+--------+{RESET}")
    print(f"{BOLD}| # | Scenario Name                    | Expected        | Actual   | Defects  | Verdict|{RESET}")
    print(f"{BOLD}+---+----------------------------------+-----------------+----------+----------+--------+{RESET}")

    for idx, r in enumerate(results, 1):
        v_str = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        exp = r["expected_status"] if not r["expected_review_reason"] else f"NEEDS_REV({r['expected_review_reason']})"
        act = r["actual_status"] if not r["actual_review_reason"] else f"NEEDS_REV({r['actual_review_reason']})"
        def_str = ",".join(r["actual_defect_fields"]) if r["actual_defect_fields"] else "-"
        print(f"| {idx:<1} | {r['name'][:32]:<32} | {exp[:15]:<15} | {act[:8]:<8} | {def_str[:8]:<8} | {v_str}   |")

    print(f"{BOLD}+---+----------------------------------+-----------------+----------+----------+--------+{RESET}")
    print(f"\n  {BOLD}Total Passed:{RESET} {total_passed}/{len(results)} ({total_passed/len(results)*100:.1f}%) | {BOLD}Total Time:{RESET} {t_total:.2f}s")
    print(f"{BOLD}{'=' * 82}{RESET}\n")

    return results


def interactive_menu():
    """Interactive terminal console for live demonstrations."""
    ensure_fixtures()
    sc_list = list(SCENARIOS.items())

    while True:
        print(f"\n{BOLD}{CYAN}+======================================================================+{RESET}")
        print(f"{BOLD}{CYAN}|         MANIFEST AI -- SYNTHETIC TEST & FAILURE SIMULATOR             |{RESET}")
        print(f"{BOLD}{CYAN}+======================================================================+{RESET}")
        print(f" Select a synthetic failure scenario to inject live:\n")

        for idx, (sid, sc) in enumerate(sc_list, 1):
            cat_tag = f"{YELLOW}[{sc.category}]{RESET}"
            print(f"   [{idx}] {sc.name:<38} {cat_tag}")

        print(f"\n   [A] Run All 9 Scenarios (Automated Test Suite)")
        print(f"   [W] Launch Web Demonstration Dashboard")
        print(f"   [Q] Quit")
        print(f"{'-' * 72}")

        choice = input(f"{BOLD} Choice [1-9, A, W, Q]: {RESET}").strip().upper()

        if choice == "Q":
            print("Exiting Failure Simulator.")
            break
        elif choice == "A":
            run_all_scenarios(verbose=True)
        elif choice == "W":
            start_web_server()
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(sc_list):
            sid, sc = sc_list[int(choice) - 1]
            print(f"\n{CYAN}Executing scenario: {sc.name}...{RESET}")
            res = run_scenario(sid)
            print_scenario_detail(res)
        else:
            print(f"{RED}Invalid selection. Please choose 1-9, A, W, or Q.{RESET}")


def start_web_server(port: int = 8085):
    """Launch the standalone FastAPI web panel for visual pitch recording."""
    import uvicorn
    from tests.synthetic_failures.web_panel import app

    print(f"\n{BOLD}{GREEN}Starting Manifest AI Failure Simulator Web Dashboard on http://localhost:{port}{RESET}")
    print(f"Press Ctrl+C to stop.\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="Manifest AI Synthetic Failure Simulator (Unit 12)")
    parser.add_argument("--all", action="store_true", help="Run all 9 failure scenarios and display summary table")
    parser.add_argument("--scenario", type=str, choices=list(SCENARIOS.keys()), help="Run a specific scenario by ID")
    parser.add_argument("--web", action="store_true", help="Start the interactive web demo panel")
    parser.add_argument("--port", type=int, default=8085, help="Port for the web demo panel (default: 8085)")
    args = parser.parse_args()

    if args.web:
        start_web_server(port=args.port)
    elif args.all:
        results = run_all_scenarios(verbose=True)
        all_passed = all(r["passed"] for r in results)
        sys.exit(0 if all_passed else 1)
    elif args.scenario:
        res = run_scenario(args.scenario)
        print_scenario_detail(res)
        sys.exit(0 if res["passed"] else 1)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
