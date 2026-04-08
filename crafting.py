from __future__ import annotations

from typing import Dict, List, Tuple

from inventory import Inventory


class CraftingSystem:
    # Estrutura obrigatoria: dict
    crafting_recipes: Dict[str, Dict[str, int]] = {
        "lanca": {"madeira": 5, "metal": 2},
        "machado": {"madeira": 3, "metal": 1},
        "espada": {"madeira": 2, "metal": 4},
    }

    def craft(self, item_name: str, inventory: Inventory) -> Tuple[bool, str]:
        if item_name not in self.crafting_recipes:
            return False, "Receita inexistente."

        recipe = self.crafting_recipes[item_name]
        if not inventory.has_items(recipe):
            return False, "Recursos insuficientes."

        for item, amount in recipe.items():
            inventory.remove_item(item, amount)

        inventory.add_item(item_name, 1)
        return True, f"Criado: {item_name}."

    def get_recipe_names(self) -> List[str]:
        return list(self.crafting_recipes.keys())

    def get_recipe(self, item_name: str) -> Dict[str, int] | None:
        return self.crafting_recipes.get(item_name)
