import sys
from pathlib import Path

import pytest

from cibmangotree import __main__


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific startup path")
def test_noop_entry_point_outside_repository(monkeypatch, tmp_path):
    """The installed entry point must not rely on the repository root."""
    repository_root = Path(__file__).resolve().parents[2]
    import_paths = [
        path for path in sys.path if Path(path or ".").resolve() != repository_root
    ]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", import_paths)
    monkeypatch.setattr(sys, "argv", ["cibmt", "--noop"])
    monkeypatch.delitem(sys.modules, "src", raising=False)
    monkeypatch.delitem(sys.modules, "src.cibmangotree", raising=False)

    with pytest.raises(SystemExit) as exit_info:
        __main__.main()

    assert exit_info.value.code == 0
