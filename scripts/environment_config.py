"""Load the service's stdlib schema without requiring installed application dependencies."""

import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "src/settings/environment.py"
_spec = importlib.util.spec_from_file_location("goalstats_environment_schema", _path)
assert _spec is not None and _spec.loader is not None
schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schema)
