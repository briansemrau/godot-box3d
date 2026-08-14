"""Audit Box3D API coverage — what's bound, what's skipped, what's missing."""

import argparse
import re
import sys
from pathlib import Path

import yaml

from parser import parse_headers
from utils import load_type_map


def load_existing_bindings(root: str) -> set:
    """Find existing binding stubs by scanning src/ for method declarations."""
    bound = set()
    src = Path(root) / "src"

    for f in src.rglob("*.hpp"):
        text = f.read_text()
        # Match: static ReturnType methodName(
        for m in re.finditer(r'static\s+\w+.*?\b(\w+)\s*\(', text):
            name = m.group(1)
            if name in ("_bind_methods", "Box3DAPI"):
                continue
            bound.add(name)

    return bound


def audit(root: str) -> dict:
    """Run the audit and return results.

    Classification is delegated to :func:`classification.classify_function`
    so the audit can never disagree with the stub generator about what is
    generatable and what is skipped.
    """
    from classification import SKIP, classify_function, prepare_type_map

    data = parse_headers(root)
    type_map = load_type_map(root)
    prepare_type_map(type_map, data)
    bound = load_existing_bindings(root)

    domains = {}
    missing = []
    skipped = []  # (name, reason, configured)
    implicit = []  # (name, reason) — skipped for structural reasons w/o config
    array_functions = []

    for func in data["functions"]:
        verdict = classify_function(func, data, type_map)
        domain = verdict.domain
        domains.setdefault(domain, {"total": 0, "bound": 0, "skipped": 0, "missing": 0})
        domains[domain]["total"] += 1

        if verdict.decision == SKIP:
            domains[domain]["skipped"] += 1
            skipped.append((func.name, verdict.reason, verdict.configured))
            if not verdict.configured:
                implicit.append((func.name, verdict.reason))
        else:
            godot_name = verdict.godot_name
            if godot_name in bound or func.name in bound:
                domains[domain]["bound"] += 1
            else:
                domains[domain]["missing"] += 1
                missing.append((func.name, godot_name, domain))

        if verdict.array_params:
            array_functions.append((func, verdict.array_params))

    return {
        "domains": domains,
        "missing": missing,
        "skipped": skipped,
        "implicit": implicit,
        "array_functions": array_functions,
        "total_functions": len(data["functions"]),
        "total_structs": len(data["structs"]),
        "total_enums": len(data["enums"]),
    }


def print_report(results: dict):
    from parser import ArrayDirection

    domains = results["domains"]
    total_covered = sum(d["bound"] for d in domains.values())
    total_skipped = sum(d["skipped"] for d in domains.values())
    total_missing = sum(d["missing"] for d in domains.values())

    print(f"\nBox3D API Audit")
    print(f"{'=' * 50}")
    print(f"Functions: {results['total_functions']} total, {results['total_structs']} structs, {results['total_enums']} enums")
    print(f"Bound: {total_covered} | Skipped: {total_skipped} | Missing: {total_missing}")
    print()

    # Domain breakdown
    print("Domain Coverage")
    print("-" * 40)
    for domain in sorted(domains.keys()):
        d = domains[domain]
        if d["total"] == 0:
            continue
        bar = "█" * d["bound"] + "░" * (d["total"] - d["bound"])
        print(f"  {domain:12s} {d['bound']:3d}/{d['total']:3d}  {bar}")

    # Array params
    if results["array_functions"]:
        print(f"\nArray Params ({len(results['array_functions'])} functions):")
        for func, detected in results["array_functions"]:
            for param_name, info in detected.items():
                dir_str = info.direction.name.lower()
                count_fn = info.count_function if info.count_function else "MISSING"
                marker = "" if info.count_function or info.direction != ArrayDirection.OUTPUT else " ⚠"
                print(f"  {func.name}: {param_name} → {dir_str} array[{info.config_source}], count_fn={count_fn}{marker}")

    # Missing functions
    if results["missing"]:
        print(f"\nMissing ({len(results['missing'])} functions not bound, not skipped):")
        by_domain = {}
        for b3_name, godot_name, domain in results["missing"]:
            by_domain.setdefault(domain, []).append((b3_name, godot_name))

        for domain in sorted(by_domain.keys()):
            funcs = by_domain[domain]
            print(f"  [{domain}]")
            for b3_name, godot_name in sorted(funcs, key=lambda x: x[1]):
                print(f"    {b3_name:45s} → {godot_name}")

    # Skipped
    if results["skipped"]:
        print(f"\nSkipped ({len(results['skipped'])} functions):")
        for name, reason, configured in sorted(results["skipped"]):
            marker = "" if configured else " [IMPLICIT]"
            print(f"    {name:45s} {reason}{marker}")

    # Implicit skips — structural skips without an explicit config entry.
    # These are surfaced so a human can decide whether to support or configure.
    if results["implicit"]:
        print(f"\nImplicit Skips ({len(results['implicit'])} — no config entry, needs attention):")
        for name, reason in sorted(results["implicit"]):
            print(f"    {name:45s} {reason}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Audit Box3D API coverage")
    parser.add_argument("root", nargs="?", default=".", help="Project root directory")
    args = parser.parse_args()

    results = audit(args.root)
    print_report(results)

    # Exit with error if there are missing functions
    if results["missing"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
