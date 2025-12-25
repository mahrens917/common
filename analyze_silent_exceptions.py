#!/usr/bin/env python3
"""Extract all silent exception handler violations with context."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Add ci_shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ci_shared"))

from ci_tools.scripts.policy_collectors_ast import collect_silent_handlers
from ci_tools.scripts.policy_context import ROOT

def get_exception_type(handler: ast.ExceptHandler) -> str:
    """Extract the exception type(s) being caught."""
    if not handler.type:
        return "bare-except"
    if isinstance(handler.type, ast.Name):
        return handler.type.id
    if isinstance(handler.type, ast.Tuple):
        return "(" + ", ".join(
            elt.id if isinstance(elt, ast.Name) else str(elt)
            for elt in handler.type.elts
        ) + ")"
    return "unknown"

def get_handler_code(file_path: str, lineno: int) -> Tuple[str, str, List[str]]:
    """Get the exception type and handler body code."""
    path = ROOT / file_path
    try:
        with open(path) as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        return "error", f"Failed to parse: {e}", []

    # Find the handler at this line
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.lineno == lineno:
                    exc_type = get_exception_type(handler)

                    # Get the source code for the handler body
                    lines = source.split('\n')
                    start_line = handler.lineno - 1
                    if handler.body:
                        end_line = handler.body[-1].end_lineno if handler.body[-1].end_lineno else handler.body[-1].lineno
                    else:
                        end_line = handler.lineno

                    handler_lines = lines[start_line:end_line]

                    # Get body statements
                    body_stmts = []
                    for stmt in handler.body:
                        stmt_class = stmt.__class__.__name__
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            # It's a call expression
                            body_stmts.append(f"Call({ast.unparse(stmt.value.func)})")
                        elif isinstance(stmt, ast.Return):
                            if stmt.value is None:
                                body_stmts.append("Return(None)")
                            else:
                                body_stmts.append(f"Return({ast.unparse(stmt.value)})")
                        else:
                            body_stmts.append(stmt_class)

                    return exc_type, '\n'.join(handler_lines), body_stmts

    return "not-found", "", []

def main():
    """Collect and analyze all silent exception handlers."""
    violations = collect_silent_handlers()

    print(f"Total violations: {len(violations)}\n")

    # Group by reason
    by_reason = {}
    for path, lineno, reason in violations:
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append((path, lineno))

    print("Violations by reason:")
    for reason, items in sorted(by_reason.items()):
        print(f"  {reason}: {len(items)}")

    print("\n" + "="*80 + "\n")

    # Group by file
    by_file = {}
    for path, lineno, reason in violations:
        if path not in by_file:
            by_file[path] = []
        by_file[path].append((lineno, reason))

    print(f"Violations across {len(by_file)} files\n")

    # Detailed analysis with exception types
    exc_type_stats = {}
    for path, lineno, reason in sorted(violations):
        exc_type, code, body_stmts = get_handler_code(path, lineno)
        key = (exc_type, reason)
        if key not in exc_type_stats:
            exc_type_stats[key] = []
        exc_type_stats[key].append((path, lineno, body_stmts))

    print("\n" + "="*80)
    print("EXCEPTION TYPE ANALYSIS")
    print("="*80 + "\n")

    for (exc_type, reason), items in sorted(exc_type_stats.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{exc_type} -> {reason}: {len(items)} occurrences")

        # Sample a few examples
        for path, lineno, body_stmts in items[:3]:
            print(f"  {path}:{lineno}")
            if body_stmts:
                print(f"    Body: {', '.join(body_stmts)}")

    # Export full data for further analysis
    with open('/Users/mahrens917/projects/common/silent_exceptions_detailed.txt', 'w') as f:
        for path, lineno, reason in sorted(violations):
            exc_type, code, body_stmts = get_handler_code(path, lineno)
            f.write(f"\n{'='*80}\n")
            f.write(f"File: {path}:{lineno}\n")
            f.write(f"Exception Type: {exc_type}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"Body Statements: {body_stmts}\n")
            f.write(f"Code:\n{code}\n")

    print(f"\n\nDetailed output written to: /Users/mahrens917/projects/common/silent_exceptions_detailed.txt")

if __name__ == "__main__":
    main()
