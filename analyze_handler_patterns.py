#!/usr/bin/env python3
"""Analyze handler patterns to understand what actions are being taken."""

import ast
import sys
from pathlib import Path
from collections import defaultdict

# Add ci_shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ci_shared"))

from ci_tools.scripts.policy_collectors_ast import collect_silent_handlers
from ci_tools.scripts.policy_context import ROOT, is_logging_call

def analyze_handler(file_path: str, lineno: int):
    """Analyze what a handler does."""
    path = ROOT / file_path
    try:
        with open(path) as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.lineno == lineno:
                    analysis = {
                        'has_logging': False,
                        'logging_level': None,
                        'has_return': False,
                        'return_value': None,
                        'has_continue': False,
                        'has_break': False,
                        'has_pass': False,
                        'has_assignment': False,
                        'other_operations': [],
                    }

                    for stmt in handler.body:
                        # Check for logging
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            func = stmt.value.func
                            if isinstance(func, ast.Attribute):
                                if func.attr in ('debug', 'info', 'warning', 'error', 'exception'):
                                    analysis['has_logging'] = True
                                    analysis['logging_level'] = func.attr
                                elif isinstance(func.value, ast.Name) and func.value.id == 'logger':
                                    analysis['has_logging'] = True
                                    analysis['logging_level'] = func.attr

                        # Check for return
                        if isinstance(stmt, ast.Return):
                            analysis['has_return'] = True
                            if stmt.value is None:
                                analysis['return_value'] = 'None'
                            elif isinstance(stmt.value, ast.Constant):
                                analysis['return_value'] = repr(stmt.value.value)
                            elif isinstance(stmt.value, (ast.Dict, ast.List, ast.Tuple)):
                                analysis['return_value'] = 'empty_collection'
                            else:
                                analysis['return_value'] = 'computed'

                        # Check for control flow
                        if isinstance(stmt, ast.Continue):
                            analysis['has_continue'] = True
                        if isinstance(stmt, ast.Break):
                            analysis['has_break'] = True
                        if isinstance(stmt, ast.Pass):
                            analysis['has_pass'] = True

                        # Check for assignment
                        if isinstance(stmt, ast.Assign):
                            analysis['has_assignment'] = True

                        # Other operations
                        if isinstance(stmt, (ast.If, ast.For, ast.While)):
                            analysis['other_operations'].append('control_flow')

                    return analysis
    return None

def main():
    """Analyze all violation patterns."""
    violations = collect_silent_handlers()

    print("=" * 80)
    print("HANDLER PATTERN ANALYSIS")
    print("=" * 80)

    # Categorize by pattern
    patterns = defaultdict(list)

    for path, lineno, reason in violations:
        analysis = analyze_handler(path, lineno)
        if analysis is None:
            patterns['ERROR_ANALYZING'].append((path, lineno, reason))
            continue

        # Determine pattern
        if analysis['has_pass']:
            pattern = 'COMPLETELY_SILENT_PASS'
        elif analysis['has_continue'] and not analysis['has_logging']:
            pattern = 'SILENT_CONTINUE'
        elif analysis['has_break'] and not analysis['has_logging']:
            pattern = 'SILENT_BREAK'
        elif analysis['has_return'] and not analysis['has_logging']:
            pattern = f"SILENT_RETURN_{analysis['return_value']}"
        elif analysis['has_logging'] and not analysis['has_return'] and not analysis['has_continue'] and not analysis['has_break']:
            pattern = f"LOGS_{analysis['logging_level']}_NO_RERAISE"
        elif analysis['has_logging'] and analysis['has_return']:
            pattern = f"LOGS_{analysis['logging_level']}_RETURNS_{analysis['return_value']}"
        elif analysis['has_logging'] and analysis['has_continue']:
            pattern = f"LOGS_{analysis['logging_level']}_CONTINUES"
        elif analysis['has_logging'] and analysis['has_break']:
            pattern = f"LOGS_{analysis['logging_level']}_BREAKS"
        elif analysis['has_assignment'] and not analysis['has_logging']:
            pattern = 'SILENT_ASSIGNMENT'
        else:
            pattern = 'OTHER_PATTERN'

        patterns[pattern].append((path, lineno, reason))

    # Print summary
    print("\nPattern Summary:")
    print("-" * 80)
    for pattern, items in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{pattern}: {len(items)}")

    # Detailed breakdown
    print("\n\n" + "=" * 80)
    print("DETAILED PATTERN BREAKDOWN")
    print("=" * 80)

    for pattern, items in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{pattern}: {len(items)} occurrences")
        print("-" * 80)

        # Show examples
        for path, lineno, reason in items[:5]:
            print(f"  {path}:{lineno}")
            print(f"    Reason: {reason}")

    # Export to file
    with open('/Users/mahrens917/projects/common/handler_patterns.txt', 'w') as f:
        for pattern, items in sorted(patterns.items()):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"{pattern}: {len(items)}\n")
            f.write(f"{'=' * 80}\n\n")
            for path, lineno, reason in sorted(items):
                f.write(f"{path}:{lineno} - {reason}\n")

    print(f"\n\nFull pattern breakdown written to: /Users/mahrens917/projects/common/handler_patterns.txt")

    # Now let's categorize by fix strategy
    print("\n\n" + "=" * 80)
    print("FIX STRATEGY RECOMMENDATIONS")
    print("=" * 80)

    fix_strategies = {
        'IMMEDIATE_FAIL_FAST': [],
        'ADD_LOGGING_DEBUG': [],
        'ADD_LOGGING_WARNING': [],
        'ADD_LOGGING_ERROR_RERAISE': [],
        'REFACTOR_SPLIT_HANDLERS': [],
        'MANUAL_REVIEW': [],
    }

    for pattern, items in patterns.items():
        if pattern == 'COMPLETELY_SILENT_PASS':
            # Completely silent - needs logging at minimum
            fix_strategies['ADD_LOGGING_DEBUG'].extend(items)
        elif pattern in ('SILENT_CONTINUE', 'SILENT_BREAK', 'SILENT_ASSIGNMENT'):
            # Silent control flow - needs logging
            fix_strategies['ADD_LOGGING_WARNING'].extend(items)
        elif pattern.startswith('SILENT_RETURN_'):
            # Silent return - could be error or expected
            fix_strategies['MANUAL_REVIEW'].extend(items)
        elif pattern.startswith('LOGS_debug_'):
            # Already logs at debug - check if should re-raise
            fix_strategies['MANUAL_REVIEW'].extend(items)
        elif pattern.startswith('LOGS_exception_'):
            # Logs exception but doesn't re-raise - should re-raise
            fix_strategies['ADD_LOGGING_ERROR_RERAISE'].extend(items)
        elif pattern.startswith('LOGS_error_'):
            # Logs error - may need re-raise
            fix_strategies['ADD_LOGGING_ERROR_RERAISE'].extend(items)
        elif pattern.startswith('LOGS_warning_'):
            # Logs warning - probably expected failure
            fix_strategies['MANUAL_REVIEW'].extend(items)
        else:
            fix_strategies['MANUAL_REVIEW'].extend(items)

    for strategy, items in sorted(fix_strategies.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{strategy}: {len(items)}")
        if items:
            print(f"  Example: {items[0][0]}:{items[0][1]}")

if __name__ == "__main__":
    main()
