"""Build bounded, provenance-preserving context from candidate Git blobs."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import PurePosixPath

from backend.app.config import Settings
from backend.app.context.python_graph import Definition, PythonGraph
from backend.app.errors import TopologyProofError
from backend.app.ingestion.git_client import GitClient
from backend.app.schemas.analysis import ContextItem
from backend.app.schemas.repository import (
    AnalysisRequest,
    ChangedSymbol,
    DiffArtifact,
    RepositorySnapshot,
)

MAX_CONTEXT_EXCERPT_LINES = 80
SECRET_PATH_PARTS = frozenset({".env", "credentials", "credential", "secrets", "secret", "id_rsa"})
SECRET_PATH_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx"})


class ContextBuilder:
    """Select only bounded, directly relevant candidate source excerpts."""

    def __init__(self, settings: Settings) -> None:
        """Bind safe Git reads and configured context-file capacity."""
        self._settings = settings

    def build(
        self,
        request: AnalysisRequest,
        snapshot: RepositorySnapshot,
        diff: DiffArtifact,
        symbols: tuple[ChangedSymbol, ...],
    ) -> tuple[ContextItem, ...]:
        """Build deterministic candidate-blob context for a resolved patch."""
        del request
        paths = _candidate_python_paths(diff, symbols)
        client = GitClient(snapshot.repository_root, self._settings)
        sources = self._read_sources(client, snapshot.candidate_commit, paths)
        graph = PythonGraph.build(sources)
        expanded = self._expand_direct_imports(graph, paths)
        if len(sources) < self._settings.max_context_files:
            additional_paths = tuple(path for path in expanded if path not in sources)
            sources.update(self._read_sources(client, snapshot.candidate_commit, additional_paths))
            graph = PythonGraph.build(sources)
        return self._select_items(graph, snapshot.candidate_commit, symbols)

    @staticmethod
    def items_from_source(
        *, path: PurePosixPath, commit: str, source: str, selection_reason: str
    ) -> tuple[ContextItem, ...]:
        """Build deterministic test-only context from an already bounded source string."""
        graph = PythonGraph.build({path: source})
        return tuple(
            _context_item(f"CTX-{index:03d}", path, commit, source, definition, selection_reason)
            for index, definition in enumerate(graph.definitions_for(path), start=1)
        )

    def _read_sources(
        self, client: GitClient, commit: str, paths: Iterable[PurePosixPath]
    ) -> dict[PurePosixPath, str]:
        """Read only safe candidate Python text blobs within the file budget."""
        sources: dict[PurePosixPath, str] = {}
        for path in paths:
            if len(sources) >= self._settings.max_context_files or _is_secret_prone(path):
                continue
            try:
                source = client.read_blob(commit, path)
                ast.parse(source, filename=path.as_posix())
            except (SyntaxError, TopologyProofError):
                continue
            sources[path] = source
        return sources

    @staticmethod
    def _expand_direct_imports(
        graph: PythonGraph, paths: tuple[PurePosixPath, ...]
    ) -> tuple[PurePosixPath, ...]:
        """Add only direct local import targets while retaining deterministic order."""
        expanded = list(paths)
        for path in graph.paths:
            for module_name in graph.direct_import_modules(path):
                import_path = PurePosixPath(*module_name.split(".")).with_suffix(".py")
                if import_path not in expanded and not _is_secret_prone(import_path):
                    expanded.append(import_path)
        return tuple(expanded)

    @staticmethod
    def _select_items(
        graph: PythonGraph, commit: str, symbols: tuple[ChangedSymbol, ...]
    ) -> tuple[ContextItem, ...]:
        """Prioritize changed symbols, state users, and one-hop direct callees."""
        candidates: list[tuple[PurePosixPath, Definition, str]] = []
        selected: set[tuple[PurePosixPath, int, int]] = set()
        for symbol in symbols:
            if symbol.path not in graph.paths:
                continue
            for definition in graph.definitions_for(symbol.path):
                if definition.name == symbol.name:
                    _append_candidate(candidates, selected, symbol.path, definition, "changed_symbol")
                    if definition.kind == "variable":
                        for function in graph.functions_using(symbol.path, definition.name):
                            _append_candidate(candidates, selected, symbol.path, function, "state_reference")
        for path in graph.paths:
            for definition in graph.definitions_for(path):
                if definition.kind == "variable" and _is_mutable_definition(definition):
                    _append_candidate(candidates, selected, path, definition, "module_state")
        for path, definition, _ in tuple(candidates):
            if definition.kind != "function":
                continue
            for call in graph.direct_called_names(definition):
                called_name = call.rsplit(".", maxsplit=1)[-1]
                for target_path in graph.paths:
                    for target in graph.definitions_for(target_path):
                        if target.kind == "function" and target.name == called_name:
                            _append_candidate(candidates, selected, target_path, target, "one_hop_callee")
        return tuple(
            _context_item(f"CTX-{index:03d}", path, commit, graph.module(path).source, definition, reason)
            for index, (path, definition, reason) in enumerate(candidates, start=1)
        )


def _candidate_python_paths(diff: DiffArtifact, symbols: tuple[ChangedSymbol, ...]) -> tuple[PurePosixPath, ...]:
    """Order changed-symbol paths ahead of changed Python files without duplicates."""
    paths: list[PurePosixPath] = []
    for path in (symbol.path for symbol in symbols):
        if path.suffix == ".py" and path not in paths and not _is_secret_prone(path):
            paths.append(path)
    for changed_path in diff.changed_paths:
        if changed_path.change_type != "D" and changed_path.path.suffix == ".py" and changed_path.path not in paths and not _is_secret_prone(changed_path.path):
            paths.append(changed_path.path)
    return tuple(paths)


def _append_candidate(
    candidates: list[tuple[PurePosixPath, Definition, str]], selected: set[tuple[PurePosixPath, int, int]],
    path: PurePosixPath, definition: Definition, reason: str,
) -> None:
    """Append one source span once while retaining the first deterministic priority."""
    key = (path, definition.line, definition.line_end)
    if key not in selected:
        selected.add(key)
        candidates.append((path, definition, reason))


def _context_item(
    context_id: str, path: PurePosixPath, commit: str, source: str,
    definition: Definition, selection_reason: str,
) -> ContextItem:
    """Build one source-backed context item with an explicitly bounded excerpt."""
    lines = source.splitlines()
    end_line = min(definition.line_end, definition.line + MAX_CONTEXT_EXCERPT_LINES - 1)
    return ContextItem(
        context_id=context_id, path=path, commit=commit, line=definition.line, line_end=end_line,
        excerpt="\n".join(lines[definition.line - 1 : end_line]), symbol=definition.name,
        selection_reason=selection_reason, provenance="candidate_git_blob",
    )


def _is_mutable_definition(definition: Definition) -> bool:
    """Return whether a top-level assignment initializes a supported collection."""
    value = definition.node.value if isinstance(definition.node, (ast.Assign, ast.AnnAssign)) else None
    return _mutable_collection_kind(value) is not None


def _mutable_collection_kind(value: ast.expr | None) -> str | None:
    """Classify supported set, dict, and list initialization expressions."""
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(value, (ast.List, ast.ListComp)):
        return "list"
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in {"set", "dict", "list"}:
        return value.func.id
    return None


def _is_secret_prone(path: PurePosixPath) -> bool:
    """Reject secret-bearing filename patterns before source content is read."""
    parts = {part.casefold() for part in path.parts}
    filename = path.name.casefold()
    return bool(parts & SECRET_PATH_PARTS) or filename.startswith(".env") or path.suffix.casefold() in SECRET_PATH_SUFFIXES
