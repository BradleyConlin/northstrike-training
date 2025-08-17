import hashlib
import pathlib

PLAN = pathlib.Path("simulation/missions/v1.0/waypoints_demo.plan")
SUMF = PLAN.with_suffix(PLAN.suffix + ".sha256")


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def test_plan_checksum_matches_fixture():
    assert PLAN.exists(), "plan file is missing"
    assert SUMF.exists(), "checksum file is missing (run plan_demo to regenerate)"
    want = SUMF.read_text().strip().split()[0]
    got = _sha256_bytes(PLAN.read_bytes())
    assert got == want, f"SHA256 changed: expected {want}, got {got}"
