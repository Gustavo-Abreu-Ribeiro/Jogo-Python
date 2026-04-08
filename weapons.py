from __future__ import annotations

from typing import Dict


WEAPONS: Dict[str, Dict[str, float | int]] = {
    "lanca": {"damage": 24, "range": 65, "cooldown": 0.6},
    "machado": {"damage": 18, "range": 45, "cooldown": 0.4},
    "espada": {"damage": 30, "range": 55, "cooldown": 0.7},
}
