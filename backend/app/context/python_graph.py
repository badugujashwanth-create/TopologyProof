"""Small bounded AST index used by deterministic context selection."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True, slots=True)
class Definition:
    """Describe one source-level definition or assignment target."""

    name: str
    kind: str
    line: int
    line_end: int
    node: ast.AST


@dataclass(frozen=True, slots=True)
class PythonModule:
    """Retain one parsed candidate Python source blob and its definitions."""

    path: PurePosixPath
    source: str
    tree: ast.Module
    definitions: tuple[Definition, ...]


class PythonGraph:
    """Index only direct AST relationships needed by Task 7 context selection."""

    def __init__(self, modules: Mapping[PurePosixPath, PythonModule]) -> None:
        """Store immutable parsed module records keyed by repository path."""
        self._modules = dict(modules)

    @classmethod
    def build(cls, items: Mapping[PurePosixPath, str]) -> PythonGraph:
        """Parse the supplied bounded candidate sources into a small graph."""
        modules: dict[PurePosixPath, PythonModule] = {}
        for path, source in items.items():
            tree = ast.parse(source, filename=path.as_posix())
            modules[path] = PythonModule(path, source, tree, _definitions(tree))
        return cls(modules)

    @property
    def paths(self) -> tuple[PurePosixPath, ...]:
        """Return deterministic repository paths represented by this graph."""
        return tuple(sorted(self._modules, key=PurePosixPath.as_posix))

    def module(self, path: PurePosixPath) -> PythonModule:
        """Return one parsed candidate module by its canonical repository path."""
        return self._modules[path]

    def definitions_for(self, path: PurePosixPath) -> tuple[Definition, ...]:
        """Return source definitions in their original lexical order."""
        return self._modules[path].definitions

    def direct_import_modules(self, path: PurePosixPath) -> tuple[str, ...]:
        """Return direct absolute import module names from one candidate module."""
        names: list[str] = []
        for node in self._modules[path].tree.body:
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
        return tuple(dict.fromkeys(names))

    def functions_using(self, path: PurePosixPath, name: str) -> tuple[Definition, ...]:
        """Return functions whose bodies reference a requested state name."""
        return tuple(
            definition
            for definition in self.definitions_for(path)
            if definition.kind == "function"
            and any(isinstance(node, ast.Name) and node.id == name for node in ast.walk(definition.node))
        )

    def direct_called_names(self, definition: Definition) -> tuple[str, ...]:
        """Return direct call names made within one function definition."""
        names: list[str] = []
        for node in ast.walk(definition.node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                names.append(node.func.id)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
            ):
                names.append(f"{node.func.value.id}.{node.func.attr}")
        return tuple(dict.fromkeys(names))


def _definitions(tree: ast.Module) -> tuple[Definition, ...]:
    """Collect top-level assignments and definitions without whole-program traversal."""
    definitions: list[Definition] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(Definition(node.name, "function", node.lineno, node.end_lineno or node.lineno, node))
        elif isinstance(node, ast.ClassDef):
            definitions.append(Definition(node.name, "class", node.lineno, node.end_lineno or node.lineno, node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for name in _assignment_names(node):
                definitions.append(Definition(name, "variable", node.lineno, node.end_lineno or node.lineno, node))
    return tuple(definitions)


def _assignment_names(node: ast.Assign | ast.AnnAssign) -> tuple[str, ...]:
    """Extract plain assignment names from a top-level assignment."""
    targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
    return tuple(target.id for target in targets if isinstance(target, ast.Name))
