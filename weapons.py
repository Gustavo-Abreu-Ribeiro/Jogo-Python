from __future__ import annotations

from typing import Dict, List


WEAPONS: Dict[str, Dict[str, float | int | str | tuple[int, int, int]]] = {
    "maos": {"family": "melee", "damage": 8, "range": 28, "cooldown": 0.45, "ammo": 0},
    "taco": {"family": "melee", "damage": 20, "range": 50, "cooldown": 0.5, "ammo": 0},
    "pistola": {
        "family": "pistola",
        "damage": 38,
        "range": 460,
        "cooldown": 0.35,
        "ammo": 1,
        "ammo_item": "balas",
        "pellets": 1,
        "spread": 0,
        "hit_width": 4,
        "visible_rounds": 6,
        "projectile_color": (255, 224, 120),
    },
    "pistola_incendiaria": {
        "family": "pistola",
        "damage": 30,
        "range": 430,
        "cooldown": 0.42,
        "ammo": 1,
        "ammo_item": "balas_incendiarias",
        "pellets": 1,
        "spread": 0,
        "hit_width": 5,
        "visible_rounds": 6,
        "projectile_color": (255, 112, 72),
        "effect": "fire",
        "splash_radius": 54,
        "splash_damage": 12,
    },
    "pistola_perfurante": {
        "family": "pistola",
        "damage": 34,
        "range": 520,
        "cooldown": 0.48,
        "ammo": 1,
        "ammo_item": "balas_perfurantes",
        "pellets": 1,
        "spread": 0,
        "hit_width": 3,
        "visible_rounds": 6,
        "projectile_color": (105, 190, 255),
        "effect": "pierce",
        "pierce": 2,
    },
    "escopeta": {
        "family": "escopeta",
        "damage": 80,
        "range": 260,
        "cooldown": 0.85,
        "ammo": 1,
        "ammo_item": "cartuchos",
        "pellets": 5,
        "spread": 22,
        "hit_width": 10,
        "visible_rounds": 4,
        "projectile_color": (255, 224, 120),
    },
    "escopeta_incendiaria": {
        "family": "escopeta",
        "damage": 58,
        "range": 235,
        "cooldown": 1.0,
        "ammo": 1,
        "ammo_item": "cartuchos_incendiarios",
        "pellets": 4,
        "spread": 28,
        "hit_width": 11,
        "visible_rounds": 4,
        "projectile_color": (255, 92, 66),
        "effect": "fire",
        "splash_radius": 46,
        "splash_damage": 10,
    },
}

WEAPON_FAMILIES: Dict[str, List[str]] = {
    "pistola": ["pistola", "pistola_incendiaria", "pistola_perfurante"],
    "escopeta": ["escopeta", "escopeta_incendiaria"],
}

WEAPON_ITEMS = {"maos", "taco", *WEAPON_FAMILIES["pistola"], *WEAPON_FAMILIES["escopeta"]}
