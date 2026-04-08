from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from inventory import Inventory
from player import Player


def save_game(file_path: str, player: Player, inventory: Inventory, game_time: float) -> None:
    data: Dict[str, Any] = {
        "player_health": player.player_health,
        "player_hunger": player.player_hunger,
        "player_position": list(player.player_position),
        "inventory": inventory.to_dict(),
        "game_time": game_time,
        "current_weapon": player.current_weapon,
    }
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_game(file_path: str) -> Dict[str, Any] | None:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return None

    if "player_position" in data:
        data["player_position"] = tuple(data["player_position"])

    return data
