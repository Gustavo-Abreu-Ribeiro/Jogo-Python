from __future__ import annotations

from typing import Dict, List, Tuple

from inventory import Inventory


class CraftingSystem:

    crafting_recipes: Dict[str, Dict[str, object]] = {
        "lanca": {"cost": {"madeira": 4, "metal": 2}, "station": "bancada"},
        "machado": {"cost": {"madeira": 3, "metal": 2}, "station": "bancada"},
        "espada": {"cost": {"metal": 4, "pano": 1}, "station": "bancada"},
        "kit_medico": {"cost": {"pano": 2, "erva": 2}, "station": "fogueira"},
    }

    def craft(self, item_name: str, inventory: Inventory, nearby_station: str | None) -> Tuple[bool, str]:
        if item_name not in self.crafting_recipes:
            return False, "Receita inexistente."

        recipe = self.crafting_recipes[item_name]
        recipe_cost = recipe["cost"]
        required_station = recipe["station"]

        if nearby_station != required_station:
            return False, f"Precisa estar perto de: {required_station}."

        if not inventory.has_items(recipe_cost):
            return False, "Recursos insuficientes."

        for item, amount in recipe_cost.items():
            inventory.remove_item(item, amount)

        inventory.add_item(item_name, 1)
        return True, f"Criado: {item_name}."

    def get_recipe_names(self) -> List[str]:
        return list(self.crafting_recipes.keys())

    def get_recipe(self, item_name: str) -> Dict[str, object] | None:
        return self.crafting_recipes.get(item_name)
