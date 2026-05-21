from __future__ import annotations

import json
import sys
from typing import Any, Dict, Tuple

from inventory import Inventory
from player import Player

WEB_SAVE_KEY = "rua_morta_savegame"


def _web_storage() -> object | None:
    if sys.platform != "emscripten":
        return None
    try:
        import platform

        return platform.window.localStorage
    except (AttributeError, ImportError):
        return None


def save_game(
    file_path: str,
    player: Player,
    inventory: Inventory,
    game_time: float,
    quick_slots: list[str] | None = None,
) -> None:
    data: Dict[str, Any] = {
        "player_health": player.player_health,
        "player_hunger": player.player_hunger,
        "player_position": list(player.player_position),
        "inventory": inventory.to_dict(),
        "game_time": game_time,
        "current_weapon": player.current_weapon,
    }
    if quick_slots is not None:
        data["quick_slots"] = list(quick_slots)
    storage = _web_storage()
    if storage is not None:
        storage.setItem(WEB_SAVE_KEY, json.dumps(data))
        return

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_game(file_path: str) -> Dict[str, Any] | None:
    storage = _web_storage()
    if storage is not None:
        raw_data = storage.getItem(WEB_SAVE_KEY)
        if not raw_data:
            return None
        data = json.loads(str(raw_data))
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return None

    if "player_position" in data:
        data["player_position"] = tuple(data["player_position"])

    return data


def save_exists(file_path: str) -> bool:
    storage = _web_storage()
    if storage is not None:
        return bool(storage.getItem(WEB_SAVE_KEY))
    from pathlib import Path

    return Path(file_path).exists()
