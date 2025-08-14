from __future__ import annotations

from typing import Any, Dict


class EKF:
    """Minimal EKF stub."""

    def step(self, meas: Dict[str, Any]) -> Dict[str, Any]:
        # Replace with real predict/update
        return {"state": [0.0, 0.0, 0.0], "cov": [[1.0, 0.0, 0.0]]}
