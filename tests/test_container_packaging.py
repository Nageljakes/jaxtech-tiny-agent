from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_container_includes_versioned_capability_catalog() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert "COPY catalog ./catalog" in dockerfile
    assert (ROOT / "catalog" / "capabilities.v1.json").is_file()
