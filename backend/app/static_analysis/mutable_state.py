"""Detect module-level mutable collection facts without semantic verdicts."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable
from pathlib import PurePosixPath

from backend.app.config import Settings
from backend.app.schemas.analysis import ContextItem, StaticSignal
from backend.app.schemas.evidence import EvidenceLocation
from backend.app.schemas.repository import DiffArtifact, RepositorySnapshot

MUTATION_METHODS = frozenset({
    "add", "append", "clear", "discard", "extend", "pop", "remove", "setdefault", "update",
})
DURABLE_CALL_PREFIXES = ("charge", "create", "persist", "record", "save", "send", "write")


class MutableStateScanner:
    """Emit exact module-mutable facts while keeping signals distinct from findings."""

    def __init__(self, settings: Settings) -> None:
        """Accept shared configuration while preserving a deterministic scanner API."""
        self._settings = settings

    def scan(
        self, snapshot: RepositorySnapshot, diff: DiffArtifact, context: tuple[ContextItem, ...]
    ) -> tuple[StaticSignal, ...]:
        """Scan bounded context snippets for module-level mutable collection evidence."""
        del snapshot, diff
        signals: list[StaticSignal] = []
        for path, items in _group_context_by_path(context).items():
            source = _reconstruct_source(items)
            try:
                module = ast.parse(source, filename=path.as_posix())
            except SyntaxError:
                continue
            for assignment, name, kind in _module_mutable_assignments(module):
                evidence_item = _context_for_line(items, assignment.lineno)
                if evidence_item is None:
                    continue
                membership = _membership_tested(module, name)
                mutation = _mutation_observed(module, name)
                durable_call = _durable_call_observed(module)
                evidence = EvidenceLocation(
                    path=path,
                    line=assignment.lineno,
                    line_end=assignment.end_lineno or assignment.lineno,
                    symbol=name,
                    commit_id=evidence_item.commit,
                    excerpt=_line_excerpt(source, assignment.lineno, assignment.end_lineno),
                )
                signals.append(
                    StaticSignal(
                        signal_id=f"SIG-{len(signals) + 1:03d}",
                        kind="module_mutable_collection",
                        module=path,
                        symbol=name,
                        facts={
                            "collection_kind": kind,
                            "module_local": True,
                            "membership_tested": membership,
                            "mutation_observed": mutation,
                            "side_effect_call": durable_call,
                            "correctness_link": membership and mutation and durable_call is not None,
                        },
                        evidence=(evidence,),
                        related_context_ids=tuple(item.context_id for item in items),
                    )
                )
        return tuple(signals)


def _group_context_by_path(
    context: tuple[ContextItem, ...],
) -> dict[PurePosixPath, tuple[ContextItem, ...]]:
    """Group candidate excerpts by source path while preserving their input order."""
    grouped: defaultdict[PurePosixPath, list[ContextItem]] = defaultdict(list)
    for item in context:
        if not item.redacted:
            grouped[item.path].append(item)
    return {path: tuple(grouped[path]) for path in sorted(grouped, key=PurePosixPath.as_posix)}


def _reconstruct_source(items: tuple[ContextItem, ...]) -> str:
    """Restore absolute source line positions from bounded context excerpts."""
    lines = [""] * max(item.line_end for item in items)
    for item in items:
        for offset, line in enumerate(item.excerpt.splitlines()):
            index = item.line - 1 + offset
            if index < len(lines):
                lines[index] = line
    return "\n".join(lines) + "\n"


def _module_mutable_assignments(
    module: ast.Module,
) -> Iterable[tuple[ast.Assign | ast.AnnAssign, str, str]]:
    """Yield supported top-level mutable collection assignments and plain names."""
    for node in module.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        kind = _mutable_collection_kind(node.value)
        if kind is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        for target in targets:
            if isinstance(target, ast.Name):
                yield node, target.id, kind


def _mutable_collection_kind(value: ast.expr | None) -> str | None:
    """Classify the limited collection forms promised by Task 7."""
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(value, (ast.List, ast.ListComp)):
        return "list"
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in {"set", "dict", "list"}
    ):
        return value.func.id
    return None


def _membership_tested(module: ast.Module, name: str) -> bool:
    """Return whether a state symbol appears as the container of an in-test."""
    return any(
        isinstance(node, ast.Compare)
        and any(isinstance(operator, (ast.In, ast.NotIn)) for operator in node.ops)
        and any(isinstance(comparator, ast.Name) and comparator.id == name for comparator in node.comparators)
        for node in ast.walk(module)
    )


def _mutation_observed(module: ast.Module, name: str) -> bool:
    """Return whether a supported mutation method is called on the state symbol."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == name
        and node.func.attr in MUTATION_METHODS
        for node in ast.walk(module)
    )


def _durable_call_observed(module: ast.Module) -> str | None:
    """Return a direct durable-side-effect-style call name, if syntactically visible."""
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id.startswith(DURABLE_CALL_PREFIXES)
        ):
            return node.func.id
    return None


def _context_for_line(items: tuple[ContextItem, ...], line: int) -> ContextItem | None:
    """Find the context item that supplied a requested absolute source line."""
    return next((item for item in items if item.line <= line <= item.line_end), None)


def _line_excerpt(source: str, line: int, line_end: int | None) -> str:
    """Extract the exact nonblank source span backing a signal evidence record."""
    return "\n".join(source.splitlines()[line - 1 : line_end or line])
