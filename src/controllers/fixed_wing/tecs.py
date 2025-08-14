from __future__ import annotations

from typing import Dict


class TECS:
    """Tiny placeholder for TECS controller interface."""

    def step(self, state: Dict, refs: Dict) -> Dict:
        """Return placeholder pitch/throttle commands."""
        return {"pitch": 0.0, "throttle": 0.5}
