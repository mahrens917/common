#!/usr/bin/env python3
"""Categorize silent exception violations into actionable groups."""

import sys
from pathlib import Path

# Add ci_shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ci_shared"))

from ci_tools.scripts.policy_collectors_ast import collect_silent_handlers

# Expected failure exceptions - these are domain-specific errors that are handled gracefully
EXPECTED_FAILURES = {
    'InsufficientDataError',
    'GPSurfaceNotAvailableError',
    'SurfaceEvaluationError',
    'VisualizationGenerationError',
    'PricePathComputationError',
    'ProgressNotificationError',
    'PatternCompilationError',
    'LDMNotInstalledError',
    'DataValidationError',
    'ParsingError',
    'ValidationError',
    'DateTimeCorruptionError',
    'FileNotFoundError',
}

# Redis/network errors - these are expected transient failures
REDIS_NETWORK_ERRORS = {
    'REDIS_ERRORS',
    'REDIS_SETUP_ERRORS',
    'REDIS_DATA_ERRORS',
    'DATA_ACCESS_ERRORS',
    'SERIALIZATION_ERRORS',
    'JSON_ERRORS',
    'RedisFatalError',
    'RedisRetryError',
    'ConnectionError',
    'TimeoutError',
    'WebSocketException',
}

# Trading/API errors - domain specific expected failures
TRADING_ERRORS = {
    'TRADING_OPERATION_ERRORS',
    'TRADING_ERRORS',
    'ALERT_FAILURE_ERRORS',
    'ALERT_DELIVERY_ERRORS',
    'MONITOR_ENFORCEMENT_ERRORS',
}

# System resource errors - can be expected (e.g., process not found)
SYSTEM_ERRORS = {
    'OSError',
    'IOError',
    'ImportError',
    'PSUTIL_ERRORS',
}

# Programming errors - these should ALWAYS re-raise or fail-fast
PROGRAMMING_ERRORS = {
    'ValueError',
    'TypeError',
    'AttributeError',
    'KeyError',
    'IndexError',
    'RuntimeError',
    'UnicodeDecodeError',
    'OverflowError',
    'ArithmeticError',
}

def categorize_exception_type(exc_type_str: str) -> str:
    """Categorize an exception type string."""
    # Check for combined exception tuples
    for expected in EXPECTED_FAILURES:
        if expected in exc_type_str:
            return 'EXPECTED_FAILURE'

    for redis in REDIS_NETWORK_ERRORS:
        if redis in exc_type_str:
            return 'REDIS_NETWORK'

    for trading in TRADING_ERRORS:
        if trading in exc_type_str:
            return 'TRADING_EXPECTED'

    for system in SYSTEM_ERRORS:
        if system in exc_type_str:
            return 'SYSTEM_ERROR'

    # Check if it's a mix of programming errors
    for prog in PROGRAMMING_ERRORS:
        if prog in exc_type_str:
            # If mixed with system errors, it's ambiguous
            for system in SYSTEM_ERRORS:
                if system in exc_type_str:
                    return 'MIXED_ERRORS'
            return 'PROGRAMMING_ERROR'

    return 'UNKNOWN'

def main():
    """Categorize all violations."""
    violations = collect_silent_handlers()

    # Parse exception types from the detailed file
    import ast
    from ci_tools.scripts.policy_context import ROOT

    def get_exception_type(file_path: str, lineno: int) -> str:
        """Extract the exception type(s) being caught."""
        path = ROOT / file_path
        try:
            with open(path) as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception:
            return "unknown"

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.lineno == lineno:
                        if not handler.type:
                            return "bare-except"
                        if isinstance(handler.type, ast.Name):
                            return handler.type.id
                        if isinstance(handler.type, ast.Tuple):
                            return "(" + ", ".join(
                                elt.id if isinstance(elt, ast.Name) else "unknown"
                                for elt in handler.type.elts
                            ) + ")"
        return "unknown"

    # Categorize all violations
    categorized = {
        'EXPECTED_FAILURE': [],
        'REDIS_NETWORK': [],
        'TRADING_EXPECTED': [],
        'SYSTEM_ERROR': [],
        'PROGRAMMING_ERROR': [],
        'MIXED_ERRORS': [],
        'UNKNOWN': [],
    }

    for path, lineno, reason in violations:
        exc_type = get_exception_type(path, lineno)
        category = categorize_exception_type(exc_type)
        categorized[category].append((path, lineno, exc_type, reason))

    print("=" * 80)
    print("VIOLATION CATEGORIZATION")
    print("=" * 80)
    print()

    for category, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{category}: {len(items)} violations")
        print("-" * 80)

        # Group by reason within category
        by_reason = {}
        for path, lineno, exc_type, reason in items:
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append((path, lineno, exc_type))

        for reason, reason_items in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {reason}: {len(reason_items)}")

            # Show a few examples
            for path, lineno, exc_type in reason_items[:2]:
                print(f"    {path}:{lineno} ({exc_type})")

    # Detailed recommendations
    print("\n\n" + "=" * 80)
    print("RECOMMENDED FIXES BY CATEGORY")
    print("=" * 80)

    print("\n1. EXPECTED_FAILURE ({} violations):".format(len(categorized['EXPECTED_FAILURE'])))
    print("   Action: Add logger.debug() or logger.warning() + return None")
    print("   Rationale: These are domain-specific expected failures")

    print("\n2. REDIS_NETWORK ({} violations):".format(len(categorized['REDIS_NETWORK'])))
    print("   Action: Add logger.warning() for transient errors")
    print("   Rationale: Network/Redis failures are expected, need visibility")

    print("\n3. TRADING_EXPECTED ({} violations):".format(len(categorized['TRADING_EXPECTED'])))
    print("   Action: Add logger.warning() or logger.error() depending on severity")
    print("   Rationale: Trading failures need logging for monitoring")

    print("\n4. SYSTEM_ERROR ({} violations):".format(len(categorized['SYSTEM_ERROR'])))
    print("   Action: Review case-by-case - some may be expected (FileNotFoundError)")
    print("   Rationale: Context matters - file not found may be expected")

    print("\n5. PROGRAMMING_ERROR ({} violations):".format(len(categorized['PROGRAMMING_ERROR'])))
    print("   Action: Add logger.exception() + re-raise OR fail-fast")
    print("   Rationale: These indicate bugs that should not be silently suppressed")

    print("\n6. MIXED_ERRORS ({} violations):".format(len(categorized['MIXED_ERRORS'])))
    print("   Action: Split exception handlers to handle each type appropriately")
    print("   Rationale: Different exception types need different handling")

    print("\n7. UNKNOWN ({} violations):".format(len(categorized['UNKNOWN'])))
    print("   Action: Review manually")
    print("   Rationale: Need to determine expected vs unexpected")

    # Export detailed breakdown
    with open('/Users/mahrens917/projects/common/violations_by_category.txt', 'w') as f:
        for category, items in sorted(categorized.items()):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"{category}: {len(items)} violations\n")
            f.write(f"{'=' * 80}\n\n")

            for path, lineno, exc_type, reason in sorted(items):
                f.write(f"{path}:{lineno}\n")
                f.write(f"  Exception: {exc_type}\n")
                f.write(f"  Reason: {reason}\n\n")

    print(f"\n\nDetailed breakdown written to: /Users/mahrens917/projects/common/violations_by_category.txt")

if __name__ == "__main__":
    main()
