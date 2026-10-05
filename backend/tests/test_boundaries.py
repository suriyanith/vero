"""Architecture rules that must hold for the life of the project."""

import ast
from pathlib import Path

VERO_CORE = Path(__file__).resolve().parent.parent / "vero_core"


def iter_imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_vero_core_never_imports_django() -> None:
    offenders = {
        str(path.relative_to(VERO_CORE)): module
        for path in VERO_CORE.rglob("*.py")
        for module in iter_imported_modules(path)
        if module == "django" or module.startswith("django.")
    }
    assert not offenders, f"vero_core must stay framework-free, found: {offenders}"


def test_env_example_covers_settings_variables() -> None:
    """Every environment variable read in settings must appear in .env.example."""
    repo_root = VERO_CORE.parent.parent
    example = (repo_root / ".env.example").read_text()
    documented = {
        line.split("=")[0].strip()
        for line in example.splitlines()
        if "=" in line and not line.startswith("#")
    }

    settings_dir = VERO_CORE.parent / "config" / "settings"
    referenced = set()
    for path in settings_dir.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "env"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                referenced.add(node.args[0].value)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "env"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                referenced.add(node.args[0].value)

    missing = referenced - documented
    assert not missing, f".env.example is missing variables used in settings: {missing}"
