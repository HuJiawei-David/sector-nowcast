import json

from nowcast import rawstore


def test_snapshot_roundtrip_and_gzip(tmp_path, monkeypatch):
    monkeypatch.setattr(rawstore, "RAW_DIR", tmp_path)
    small = rawstore.save_snapshot("src", "a.json", b'{"x": 1}', {"url": "u"})
    big_bytes = b"x" * (rawstore.GZIP_THRESHOLD_BYTES + 1)
    big = rawstore.save_snapshot("src", "b.txt", big_bytes, {"url": "v"})
    assert small.suffix == ".json" and big.suffix == ".gz"
    assert rawstore.read_snapshot(big) == big_bytes
    meta = json.loads((big.parent / "b.txt.request.json").read_text())
    assert meta["url"] == "v" and meta["bytes_uncompressed"] == len(big_bytes)
