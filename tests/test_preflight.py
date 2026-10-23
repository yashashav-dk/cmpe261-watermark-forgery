import pytest
from wmforge.preflight import run


def test_preflight_rejects_occupied_directory_without_touching_evidence(tmp_path):
    path = tmp_path / "preflight.json"
    path.write_bytes(b'{"passed":true}')
    checkpoint = tmp_path / "checkpoints"
    checkpoint.mkdir()
    (checkpoint / "TR.pt").write_bytes(b"optimizer-evidence")
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    with pytest.raises(FileExistsError):
        run(tmp_path, "unused")
    assert before == {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
