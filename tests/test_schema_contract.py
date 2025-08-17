import json
import pathlib

SCHEMA = pathlib.Path("datasets/schema_v1.json")


def test_schema_exists_and_has_expected_columns():
    assert SCHEMA.exists(), "datasets/schema_v1.json missing"
    schema = json.loads(SCHEMA.read_text())
    cols = [c["name"] for c in schema["columns"]]
    for required in [
        "t",
        "lat",
        "lon",
        "abs_alt_m",
        "rel_alt_m",
        "vn",
        "ve",
        "vd",
        "battery_pct",
        "in_air",
    ]:
        assert required in cols
