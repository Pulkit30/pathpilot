"""Guards for the Vercel deployment config (Phase 6)."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _names(specs):
    return sorted(re.split(r"[<>=!~\[ ]", s.strip(), maxsplit=1)[0].lower() for s in specs)


def test_requirements_txt_matches_pyproject():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    lines = [l for l in (ROOT / "requirements.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert sorted(pyproject) == sorted(lines), "requirements.txt and pyproject.toml dependencies differ"


def test_dev_tools_not_deployed():
    deps = _names(tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"])
    assert not {"pytest", "uvicorn", "httpx"} & set(deps)


def test_vercel_entrypoint_and_function_key_agree():
    entry = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["vercel"]["entrypoint"]
    module, var = entry.split(":")
    assert var == "app"
    function_file = module.replace(".", "/") + ".py"
    assert (ROOT / function_file).exists()
    assert function_file in json.loads((ROOT / "vercel.json").read_text())["functions"]


def test_runtime_files_are_not_excluded():
    pattern = json.loads((ROOT / "vercel.json").read_text())["functions"]["backend/app/main.py"]["excludeFiles"]
    for needed in ["careers.json", "skills.json", "resources.json", "synonyms.json", "artifacts", "frontend/dist"]:
        assert needed not in pattern, f"{needed} is needed at runtime"
