"""The committed Colab notebook must match what scripts/build_notebook.py generates."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _builder():
    spec = importlib.util.spec_from_file_location("build_notebook", ROOT / "scripts/build_notebook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_notebook_is_up_to_date():
    assert (ROOT / "colab/bridge.ipynb").read_text() == _builder().build(), (
        "colab/bridge.ipynb is stale: run `uv run python scripts/build_notebook.py`"
    )


def test_notebook_code_cells_compile():
    nb = json.loads(_builder().build())
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        # drop IPython-only lines (!shell, %%magic) before compiling as plain Python
        lines = [l for l in cell["source"] if not l.lstrip().startswith(("!", "%"))]
        compile("".join(lines), "<cell>", "exec")


def test_all_notebooks_are_valid_and_compile():
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        nb = json.loads(path.read_text())
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                assert cell["outputs"] == [], f"{path.name}: commit notebooks without outputs"
                lines = [l for l in cell["source"] if not l.lstrip().startswith(("!", "%"))]
                compile("".join(lines), f"{path.name}", "exec")
