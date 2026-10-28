"""Codebase indexing with :mod:`ast`.

Parses a Python codebase and extracts a structured index: modules, classes,
functions / methods, their signatures and docstrings, plus a dependency
graph of imports *between local modules*. This index is the retrieval
corpus used for context-window management — instead of stuffing a whole
repository into a prompt, we retrieve the few symbols that matter.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Symbol:
    """A class, function, or method extracted from a module."""

    name: str
    qualname: str
    kind: str  # "class" | "function" | "method"
    module: str
    signature: str
    docstring: str = ""
    lineno: int = 0

    def describe(self) -> str:
        """One-block textual description used in prompts / retrieval."""
        doc = f'    """{self.docstring}"""\n' if self.docstring else ""
        return f"# {self.kind}: {self.qualname} (in {self.module})\n{self.signature}\n{doc}"


@dataclass
class ModuleInfo:
    """A parsed Python module."""

    name: str
    path: str
    docstring: str = ""
    imports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class CodebaseIndex:
    """The full index of a codebase."""

    root: str
    modules: dict[str, ModuleInfo] = field(default_factory=dict)
    dependency_graph: dict[str, set[str]] = field(default_factory=dict)

    @property
    def symbols(self) -> list[Symbol]:
        """All symbols across all modules, in module order."""
        out: list[Symbol] = []
        for module in self.modules.values():
            out.extend(module.symbols)
        return out

    def get_symbol(self, qualname: str) -> Symbol | None:
        """Return a symbol by qualified name, or ``None``."""
        for symbol in self.symbols:
            if symbol.qualname == qualname:
                return symbol
        return None

    def dependents_of(self, module: str) -> set[str]:
        """Modules that (locally) import ``module``."""
        return {m for m, deps in self.dependency_graph.items() if module in deps}


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args}){returns}:"


def _class_signature(node: ast.ClassDef) -> str:
    bases = ", ".join(ast.unparse(b) for b in node.bases)
    return f"class {node.name}({bases}):" if bases else f"class {node.name}:"


def _collect_symbols(tree: ast.Module, module: str) -> list[Symbol]:
    symbols: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                Symbol(node.name, f"{module}.{node.name}", "function", module,
                       _signature(node), ast.get_docstring(node) or "", node.lineno)
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                Symbol(node.name, f"{module}.{node.name}", "class", module,
                       _class_signature(node), ast.get_docstring(node) or "", node.lineno)
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        Symbol(child.name, f"{module}.{node.name}.{child.name}",
                               "method", module, _signature(child),
                               ast.get_docstring(child) or "", child.lineno)
                    )
    return symbols


def _collect_imports(tree: ast.Module) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join(parts) if parts else root.name


def index_codebase(root: str | Path) -> CodebaseIndex:
    """Index every ``*.py`` file under ``root`` and build the dep graph.

    Args:
        root: Directory containing the codebase to parse.

    Returns:
        A :class:`CodebaseIndex` with modules, symbols, and a dependency
        graph whose edges only point at *local* modules (imports of
        third-party / stdlib packages are recorded on the module but do
        not become graph edges).
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise NotADirectoryError(f"Codebase root is not a directory: {root_path}")

    files = sorted(root_path.rglob("*.py"))
    names = {_module_name(f, root_path) for f in files}

    index = CodebaseIndex(root=str(root_path))
    for file in files:
        name = _module_name(file, root_path)
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except SyntaxError:
            continue  # An unparseable file cannot be indexed; skip, don't crash.
        module = ModuleInfo(
            name=name,
            path=str(file),
            docstring=ast.get_docstring(tree) or "",
            imports=_collect_imports(tree),
            symbols=_collect_symbols(tree, name),
        )
        index.modules[name] = module
        local_deps: set[str] = set()
        for imported in module.imports:
            for local in names:
                # Exact / absolute match, or a relative import such as
                # ``from .calculator import add`` (recorded as "calculator")
                # resolving to ``sample_pkg.calculator``.
                if imported == local or imported.startswith(local + ".") \
                        or local.endswith("." + imported):
                    if local != name:
                        local_deps.add(local)
        index.dependency_graph[name] = local_deps
    return index
