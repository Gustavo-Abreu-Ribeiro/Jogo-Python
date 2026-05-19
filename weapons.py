from __future__ import annotations

from typing import Dict


WEAPONS: Dict[str, Dict[str, float | int]] = {
    "maos": {"damage": 8, "range": 28, "cooldown": 0.45, "ammo": 0},
    "taco": {"damage": 20, "range": 50, "cooldown": 0.5, "ammo": 0},
    "pistola": {"damage": 38, "range": 460, "cooldown": 0.35, "ammo": 1, "pellets": 1, "spread": 0, "hit_width": 4},
    "escopeta": {"damage": 80, "range": 260, "cooldown": 0.85, "ammo": 2, "pellets": 5, "spread": 22, "hit_width": 10},
}
