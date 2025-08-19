# Northstrike – Compatibility Support Matrix

| Area | Min | Tested |
|---|---:|---:|
| Python | 3.10 | 3.10, 3.11 |
| OS | Ubuntu 22.04+ | Ubuntu-latest |
| OpenCV | 4.12 | 4.12 |
| NumPy | 1.26 | 2.2 |
| MLflow (optional) | 2.x+ | 3.3 |

Notes:
- CI runs a smoke test (imports + A* + CV) and a CLI smoke pytest.
- Heavy tests remain opt-in to keep CI fast.
