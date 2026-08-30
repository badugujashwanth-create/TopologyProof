"""Map changed Git diff lines to candidate Python symbols."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import PurePosixPath

from backend.app.config import Settings
from backend.app.ingestion.git_client import GitClient
from backend.app.schemas.repository import ChangedSymbol, DiffArtifact, RepositorySnapshot

DIFF_SECTION_PREFIX = "diff --git "
NEW_PATH_PREFIX = "+++ b/"
HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class ChangedSymbolDetector:
    """Detect definitions and assignment targets touched in candidate Python blobs."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Bind source-read limits for candidate Git-object inspection."""
        self._settings = settings or Settings()
        self._diagnostics: tuple[str, ...] = ()

    @property
    def diagnostics(self) -> tuple[str, ...]:
        """Return safe non-fatal diagnostics from the latest detection pass."""
        return self._diagnostics

    def detect(
        self, snapshot: RepositorySnapshot, diff: DiffArtifact
    ) -> tuple[ChangedSymbol, ...]:
        """Return candidate symbols intersecting actual added or modified lines."""
        client = GitClient(snapshot.repository_root, self._settings)
        changed_lines_by_path = _changed_candidate_lines(diff.patch)
        diagnostics: list[str] = []
        symbols: list[ChangedSymbol] = []
        for changed_path in diff.changed_paths:
            path = changed_path.path
            if path.suffix != ".py" or changed_path.change_type == "D":
                continue
            source = client.read_blob(snapshot.candidate_commit, path)
            try:
                module = ast.parse(source, filename=path.as_posix())
            except SyntaxError as error:
                line_number = error.lineno or 1
                diagnostics.append(f"python_syntax_error:{path.as_posix()}:{line_number}")
                continue
            changed_lines = changed_lines_by_path.get(path, frozenset())
            symbols.extend(_symbols_for_module(path, snapshot.candidate_commit, module, changed_lines))
        self._diagnostics = tuple(diagnostics)
        return tuple(
            sorted(
                symbols,
                key=lambda symbol: (
                    symbol.path.as_posix(),
                    symbol.new_line_start or 0,
                    symbol.kind,
                    symbol.name,
                ),
            )
        )


def _changed_candidate_lines(patch: str) -> dict[PurePosixPath, frozenset[int]]:
    """Extract exact candidate line numbers introduced by each file diff."""
    changed_lines: dict[PurePosixPath, set[int]] = {}
    current_path: PurePosixPath | None = None
    old_line = 0
    new_line = 0
    in_hunk = False
    for line in patch.splitlines():
        if line.startswith(DIFF_SECTION_PREFIX):
            current_path = None
            in_hunk = False
            continue
        if line.startswith(NEW_PATH_PREFIX):
            current_path = PurePosixPath(line.removeprefix(NEW_PATH_PREFIX))
            changed_lines.setdefault(current_path, set())
            continue
        hunk_match = HUNK_PATTERN.match(line)
        if hunk_match is not None:
            new_line = int(hunk_match.group(1))
            old_line = _old_hunk_start(line)
            in_hunk = True
            continue
        if not in_hunk or current_path is None or not line:
            continue
        marker = line[0]
        if marker == "+":
            changed_lines[current_path].add(new_line)
            new_line += 1
        elif marker == "-":
            old_line += 1
        elif marker == " ":
            old_line += 1
            new_line += 1
        elif marker == "\\":
            continue
    return {path: frozenset(lines) for path, lines in changed_lines.items()}


def _old_hunk_start(header: str) -> int:
    """Read the old-side start line from a validated unified hunk header."""
    old_range = header.split(" ", maxsplit=2)[1]
    return int(old_range.removeprefix("-").split(",", maxsplit=1)[0])


def _symbols_for_module(
    path: PurePosixPath,
    candidate_commit: str,
    module: ast.Module,
    changed_lines: frozenset[int],
) -> tuple[ChangedSymbol, ...]:
    """Create typed symbols whose source spans contain candidate changed lines."""
    symbols: list[ChangedSymbol] = []
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = _definition_start_line(node)
            end_line = node.end_lineno or node.lineno
            if _span_intersects(start_line, end_line, changed_lines):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                symbols.append(
                    ChangedSymbol(
                        path=path,
                        kind=kind,
                        name=node.name,
                        candidate_commit=candidate_commit,
                        new_line_start=start_line,
                        new_line_end=end_line,
                    )
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            start_line = node.lineno
            end_line = node.end_lineno or node.lineno
            if not _span_intersects(start_line, end_line, changed_lines):
                continue
            for name in _assignment_names(node):
                symbols.append(
                    ChangedSymbol(
                        path=path,
                        kind="variable",
                        name=name,
                        candidate_commit=candidate_commit,
                        new_line_start=start_line,
                        new_line_end=end_line,
                    )
                )
    return tuple(symbols)


def _definition_start_line(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> int:
    """Include decorator lines in a changed definition's candidate span."""
    decorator_lines = [decorator.lineno for decorator in node.decorator_list]
    return min([node.lineno, *decorator_lines])


def _span_intersects(start_line: int, end_line: int, changed_lines: frozenset[int]) -> bool:
    """Return whether a source span contains at least one changed candidate line."""
    return any(start_line <= line <= end_line for line in changed_lines)


def _assignment_names(
    node: ast.Assign | ast.AnnAssign | ast.AugAssign | ast.NamedExpr,
) -> tuple[str, ...]:
    """Extract stable name targets from one Python assignment node."""
    if isinstance(node, ast.Assign):
        targets: Iterable[ast.expr] = node.targets
    else:
        targets = (node.target,)
    names: list[str] = []
    for target in targets:
        names.extend(_target_names(target))
    return tuple(dict.fromkeys(names))


def _target_names(target: ast.expr) -> tuple[str, ...]:
    """Recursively collect plain names from tuple or list assignment targets."""
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(name for element in target.elts for name in _target_names(element))
    return ()
