#!/usr/bin/env python3
"""Compare benchmark results between runs to detect performance regressions."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Threshold for performance regression (10%)
REGRESSION_THRESHOLD = 0.1


def load_benchmark(filepath: str) -> Dict:
    """Load benchmark results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_benchmarks(baseline: Dict, current: Dict) -> List[Tuple[str, float, float, float]]:
    """Compare benchmark results and identify regressions.
    
    Returns list of (test_name, baseline_time, current_time, percentage_change)
    """
    regressions = []
    
    baseline_tests = {b['name']: b for b in baseline.get('benchmarks', [])}
    current_tests = {b['name']: b for b in current.get('benchmarks', [])}
    
    for test_name, current_test in current_tests.items():
        if test_name in baseline_tests:
            baseline_test = baseline_tests[test_name]
            
            # Extract mean times
            baseline_time = baseline_test['stats']['mean']
            current_time = current_test['stats']['mean']
            
            # Calculate percentage change
            if baseline_time > 0:
                change = (current_time - baseline_time) / baseline_time
                
                regressions.append((test_name, baseline_time, current_time, change))
    
    return regressions


def print_results(regressions: List[Tuple[str, float, float, float]]) -> bool:
    """Print comparison results and return True if regressions found."""
    has_regressions = False
    
    print("# Performance Comparison Report\n")
    print("| Test | Baseline (s) | Current (s) | Change (%) |")
    print("|------|--------------|-------------|------------|")
    
    for test_name, baseline, current, change in sorted(regressions, key=lambda x: x[3], reverse=True):
        change_pct = change * 100
        
        # Mark regressions
        if change > REGRESSION_THRESHOLD:
            has_regressions = True
            status = "🔴"
        elif change < -REGRESSION_THRESHOLD:
            status = "🟢"  # Performance improvement
        else:
            status = "🟡"  # Minor change
            
        print(f"| {status} {test_name} | {baseline:.4f} | {current:.4f} | {change_pct:+.1f}% |")
    
    if has_regressions:
        print("\n⚠️  **Performance regressions detected!**")
        print(f"Tests with >{REGRESSION_THRESHOLD*100:.0f}% slowdown need attention.")
    else:
        print("\n✅ No significant performance regressions detected.")
    
    return has_regressions


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: compare_benchmarks.py <baseline.json> <current.json>")
        sys.exit(1)
    
    baseline_file = sys.argv[1]
    current_file = sys.argv[2]
    
    try:
        baseline = load_benchmark(baseline_file)
        current = load_benchmark(current_file)
    except Exception as e:
        print(f"Error loading benchmark files: {e}")
        sys.exit(1)
    
    regressions = compare_benchmarks(baseline, current)
    has_regressions = print_results(regressions)
    
    # Exit with error if regressions found
    sys.exit(1 if has_regressions else 0)


if __name__ == "__main__":
    main()