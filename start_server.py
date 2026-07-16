"""Wrapper that patches os.getcwd/Path.cwd before Streamlit starts."""
import os
import sys
import pathlib

DASHBOARD_DIR = "/Users/martawrzosek/Desktop/Claude/Meta Ads/dashboard"

# Patch os.getcwd so Streamlit startup doesn't explode in sandboxed envs
_orig_getcwd = os.getcwd
def _safe_getcwd():
    try:
        return _orig_getcwd()
    except OSError:
        return DASHBOARD_DIR
os.getcwd = _safe_getcwd

# Patch pathlib.Path.cwd() (used by streamlit.config)
_orig_path_cwd = pathlib.Path.cwd.__func__ if hasattr(pathlib.Path.cwd, "__func__") else None

@classmethod  # type: ignore
def _safe_path_cwd(cls):
    try:
        if _orig_path_cwd:
            return _orig_path_cwd(cls)
        return pathlib.Path(os.getcwd())
    except OSError:
        return pathlib.Path(DASHBOARD_DIR)

pathlib.Path.cwd = _safe_path_cwd  # type: ignore

# Also patch os.path.abspath (called on the script path)
_orig_abspath = os.path.abspath
def _safe_abspath(p):
    if os.path.isabs(p):
        return p
    try:
        return _orig_abspath(p)
    except OSError:
        return os.path.join(DASHBOARD_DIR, p)
os.path.abspath = _safe_abspath

# Run Streamlit
sys.argv = [
    "streamlit", "run",
    os.path.join(DASHBOARD_DIR, "app.py"),
    "--server.port=8501",
    "--server.headless=true",
    "--browser.gatherUsageStats=false",
]

from streamlit.web.cli import main
main(prog_name="streamlit")
