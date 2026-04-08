from __future__ import annotations

from typing import Dict


class Inventory:
    def __init__(self, initial: Dict[str, int] | None = None) -> None:
        # Estrutura obrigatoria: dict
        defaults = {
            "madeira": 0,
            "metal": 0,
            "comida": 0,
            "pano": 0,
            "erva": 0,
            "kit_medico": 0,
            "lanca": 1,
            "machado": 0,
            "espada": 0,
        }
        self.inventory: Dict[str, int] = defaults
        if initial:
            self.inventory.update(initial)

    def add_item(self, item: str, amount: int = 1) -> None:
        if amount <= 0:
            return
        self.inventory[item] = self.inventory.get(item, 0) + amount

    def remove_item(self, item: str, amount: int = 1) -> bool:
        if amount <= 0:
            return True
        if self.inventory.get(item, 0) < amount:
            return False
        self.inventory[item] -= amount
        return True

    def get_quantity(self, item: str) -> int:
        return self.inventory.get(item, 0)

    def has_items(self, required: Dict[str, int]) -> bool:
        for item, amount in required.items():
            if self.get_quantity(item) < amount:
                return False
        return True

    def to_dict(self) -> Dict[str, int]:
        return dict(self.inventory)
