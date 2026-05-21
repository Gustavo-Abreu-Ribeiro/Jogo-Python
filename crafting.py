from __future__ import annotations

from typing import Dict, List, Tuple

from inventory import Inventory


class CraftingSystem:

    crafting_recipes: Dict[str, Dict[str, object]] = {
        "taco": {"cost": {"madeira": 3}},
        "balas": {"cost": {"metal": 1, "polvora": 1}, "amount": 6},
        "cartuchos": {"cost": {"metal": 2, "polvora": 1}, "amount": 3, "unlock_any": ["escopeta", "escopeta_incendiaria"]},
        "balas_incendiarias": {
            "cost": {"balas": 4, "polvora": 1},
            "amount": 4,
            "unlock": "pistola_incendiaria",
        },
        "balas_perfurantes": {
            "cost": {"balas": 4, "metal": 2},
            "amount": 4,
            "unlock": "pistola_perfurante",
        },
        "cartuchos_incendiarios": {
            "cost": {"cartuchos": 2, "polvora": 1},
            "amount": 2,
            "unlock": "escopeta_incendiaria",
        },
        "kit_medico": {"cost": {"pano": 2, "erva": 2}},
    }

    def is_recipe_unlocked(self, item_name: str, inventory: Inventory | None = None) -> bool:
        recipe = self.crafting_recipes.get(item_name)
        if recipe is None:
            return False
        if inventory is None:
            return "unlock" not in recipe and "unlock_any" not in recipe

        unlock = recipe.get("unlock")
        if isinstance(unlock, str) and inventory.get_quantity(unlock) <= 0:
            return False

        unlock_any = recipe.get("unlock_any")
        if isinstance(unlock_any, list) and not any(inventory.get_quantity(str(item)) > 0 for item in unlock_any):
            return False

        return True

    def craft(self, item_name: str, inventory: Inventory) -> Tuple[bool, str]:
        if item_name not in self.crafting_recipes:
            return False, "Receita inexistente."
        if not self.is_recipe_unlocked(item_name, inventory):
            return False, "Receita ainda bloqueada."

        recipe = self.crafting_recipes[item_name]
        recipe_cost = recipe["cost"]

        if not inventory.has_items(recipe_cost):
            return False, "Recursos insuficientes."

        for item, amount in recipe_cost.items():
            inventory.remove_item(item, amount)

        amount = int(recipe.get("amount", 1))
        inventory.add_item(item_name, amount)
        suffix = f" x{amount}" if amount > 1 else ""
        return True, f"Criado: {item_name}{suffix}."

    def get_recipe_names(self, inventory: Inventory | None = None) -> List[str]:
        return [name for name in self.crafting_recipes if self.is_recipe_unlocked(name, inventory)]

    def get_recipe(self, item_name: str) -> Dict[str, object] | None:
        return self.crafting_recipes.get(item_name)
