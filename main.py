from __future__ import annotations

import asyncio
import json
from pathlib import Path
import random
import sys
from typing import Dict, List, Tuple

import pygame
try:
    from pygame._sdl2 import controller as sdl_controller
except (ImportError, pygame.error):
    sdl_controller = None

from crafting import CraftingSystem
from inventory import Inventory
from map_loader import TiledMap
from player import Player
from save_system import load_game, save_exists, save_game
from weapons import WEAPONS, WEAPON_FAMILIES, WEAPON_ITEMS
from zombie import Zombie


WIDTH, HEIGHT = 960, 540
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
WORLD_WIDTH, WORLD_HEIGHT = 2200, 1400
PROJECT_ROOT = Path(__file__).resolve().parent
IS_WEB = sys.platform == "emscripten"
LOCAL_MAP_ROOT = PROJECT_ROOT / "maps"
MAP_ROOT = LOCAL_MAP_ROOT if LOCAL_MAP_ROOT.exists() else PROJECT_ROOT.parent
MAP_SEQUENCE = [
    MAP_ROOT / "Mapa 1.1.tmj",
]
INTERIOR_MAP_PATHS = [
    MAP_ROOT / "interior 1.1.tmj",
    MAP_ROOT / "Interior 1.tmj",
]
TILED_MAP_PATH = MAP_SEQUENCE[0]
SAVE_GAME_PATH = PROJECT_ROOT / "savegame.json"
SETTINGS_PATH = PROJECT_ROOT / "settings.json"
MUSIC_ROOT = PROJECT_ROOT / "musics"
TITLE_MUSIC_PATH = MUSIC_ROOT / "Menu_Music.mp3"
GAME_MUSIC_PATH = MUSIC_ROOT / "Loop_Music.mp3"
GAME_MUSIC_GAIN = 3.0
GAME_MUSIC_LAYER_COUNT = 2
SFX_ROOT = MUSIC_ROOT / "Sound Effects"
SFX_GAIN = 1.25
WEB_SETTINGS_KEY = "rua_morta_settings"
TILED_MAP_SCALE = 2
BG_COLOR = (24, 29, 31)
SEARCH_RANGE = 50
DOOR_RANGE = 74
EXIT_RANGE = 64
START_CLEAR_RADIUS = 170
ZOMBIE_AVOIDANCE_ANGLES = (0, 25, -25, 50, -50, 85, -85, 125, -125, 180)
ZOMBIE_SEPARATION_STRENGTH = 58.0
ZOMBIE_SEPARATION_ITERATIONS = 2
BOTTOM_WORLD_PADDING = 118
GAMEPAD_A = 0
GAMEPAD_B = 1
GAMEPAD_X = 2
GAMEPAD_Y = 3
GAMEPAD_BACK = 4
GAMEPAD_GUIDE = 5
GAMEPAD_START = 6
GAMEPAD_L3 = 7
GAMEPAD_R3 = 8
GAMEPAD_L1 = 9
GAMEPAD_R1 = 10
GAMEPAD_DPAD_UP = 11
GAMEPAD_DPAD_DOWN = 12
GAMEPAD_DPAD_LEFT = 13
GAMEPAD_DPAD_RIGHT = 14
GAMEPAD_AXIS_LEFT_X = 0
GAMEPAD_AXIS_LEFT_Y = 1
GAMEPAD_AXIS_RIGHT_X = 2
GAMEPAD_AXIS_RIGHT_Y = 3
GAMEPAD_AXIS_L2 = 4
GAMEPAD_AXIS_R2 = 5
RAW_GAMEPAD_BACK = 8
RAW_GAMEPAD_START = 9
RAW_GAMEPAD_L3 = 10
RAW_GAMEPAD_R3 = 11
RAW_GAMEPAD_DPAD_UP = 12
RAW_GAMEPAD_DPAD_DOWN = 13
RAW_GAMEPAD_DPAD_LEFT = 14
RAW_GAMEPAD_DPAD_RIGHT = 15
RAW_GAMEPAD_GUIDE = 16
RAW_GAMEPAD_TOUCHPAD = 17
GAMEPAD_RESCAN_INTERVAL_MS = 600
GAMEPAD_DISCONNECT_GRACE_MS = 1400

SFX_FILES = {
    "craft_success": "craft_success.wav",
    "door_locked": "door_locked.wav",
    "door_open": "door_open.wav",
    "eat": "eat.wav",
    "gun_empty": "gun_empty_click.wav",
    "pistol": "gun_pistol_shot.wav",
    "shotgun": "gun_shotgun_shot.wav",
    "heal": "heal.wav",
    "hit_flesh": "hit_flesh.wav",
    "inventory_move": "inventory_move_item.wav",
    "melee": "melee_punch.wav",
    "objective": "objective_update.wav",
    "pickup_ammo": "pickup_ammo.wav",
    "pickup_item": "pickup_item.wav",
    "player_damage": "player_damage.wav",
    "search_car": "search_car.wav",
    "search_tree": "search_tree.wav",
    "ui_confirm": "ui_click_confirm.wav",
    "ui_denied": "ui_denied.wav",
    "ui_close": "ui_menu_close.wav",
    "ui_move": "ui_menu_move.wav",
    "ui_open": "ui_menu_open.wav",
    "zombie_alert": "zombie_alert.wav",
    "zombie_big_attack": "zombie_big_attack.wav",
    "zombie_death": "zombie_death.wav",
    "zombie_normal_attack": "zombie_normal_attack.wav",
    "zombie_small_dash": "zombie_small_dash.wav",
}


def _web_audio_path(path: Path) -> Path:
    if IS_WEB:
        return path.with_suffix(".ogg")
    ogg_path = path.with_suffix(".ogg")
    return path if path.exists() or not ogg_path.exists() else ogg_path


def _web_local_storage() -> object | None:
    if not IS_WEB:
        return None
    try:
        import platform

        return platform.window.localStorage
    except (AttributeError, ImportError):
        return None


PALETTE = {
    "bg_deep": (18, 24, 27),
    "ground_a": (49, 62, 58),
    "ground_b": (56, 71, 66),
    "border": (86, 102, 94),
    "panel": (14, 18, 21),
    "panel_edge": (84, 96, 101),
    "text": (233, 233, 224),
    "text_soft": (188, 193, 186),
    "accent": (214, 188, 121),
    "danger": (195, 87, 79),
}

NODE_TYPES: Dict[str, Dict[str, object]] = {
    "caixote": {
        "label": "Caixote",
        "color": (155, 111, 69),
        "loot": ["metal", "pano", "comida", "balas"],
        "drops": (2, 4),
        "ambush": 0.15,
    },
    "arvore": {
        "label": "Arvore",
        "color": (92, 149, 96),
        "loot": ["madeira", "madeira", "madeira", "pano"],
        "drops": (2, 4),
        "ambush": 0.05,
    },
    "sucata": {
        "label": "Monte de Sucata",
        "color": (116, 126, 129),
        "loot": ["metal", "metal", "pano", "polvora", "balas", "balas"],
        "drops": (2, 4),
        "ambush": 0.25,
    },
    "despensa": {
        "label": "Despensa",
        "color": (174, 108, 89),
        "loot": ["comida", "comida", "pano", "erva", "kit_medico", "balas", "balas"],
        "drops": (2, 3),
        "ambush": 0.1,
    },
    "erva": {
        "label": "Ervas",
        "color": (92, 149, 96),
        "loot": ["erva", "erva", "comida"],
        "drops": (2, 3),
        "ambush": 0.05,
    },
    "natureza": {
        "label": "Natureza",
        "color": (92, 149, 96),
        "loot": ["madeira", "madeira", "erva", "pano"],
        "drops": (0, 2),
        "ambush": 0.05,
    },
    "carro": {
        "label": "Carro abandonado",
        "color": (120, 132, 138),
        "loot": [
            "metal",
            "metal",
            "balas",
            "balas",
            "balas",
            "pistola",
            "pistola_perfurante",
            "polvora",
            "comida",
        ],
        "drops": (0, 4),
        "ambush": 0.18,
    },
    "edificio": {
        "label": "Predio abandonado",
        "color": (155, 142, 91),
        "loot": [
            "pano",
            "balas",
            "cartuchos",
            "polvora",
            "pistola",
            "pistola_incendiaria",
            "escopeta",
            "escopeta_incendiaria",
            "kit_medico",
        ],
        "drops": (2, 5),
        "ambush": 0.22,
    },
}

OBJECT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "objects"
SHOT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "Shot"
UI_SPRITE_ROOT = PROJECT_ROOT / "UIMENU"
_RAW_SPRITE_CACHE: Dict[str, pygame.Surface] = {}
_SCALED_SPRITE_CACHE: Dict[Tuple[str, float], pygame.Surface] = {}
_COMPOSITE_SPRITE_CACHE: Dict[Tuple[str, str, str, str, float], pygame.Surface] = {}
_UI_SPRITE_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_SHOT_IMPACT_CACHE: List[List[pygame.Surface]] | None = None

INVENTORY_ITEM_ORDER = [
    "madeira",
    "metal",
    "pano",
    "erva",
    "polvora",
    "balas",
    "balas_incendiarias",
    "balas_perfurantes",
    "cartuchos",
    "cartuchos_incendiarios",
    "comida",
    "kit_medico",
    "taco",
    "pistola",
    "pistola_incendiaria",
    "pistola_perfurante",
    "escopeta",
    "escopeta_incendiaria",
]
ITEM_LABELS = {
    "madeira": "MAD",
    "metal": "MET",
    "pano": "PAN",
    "erva": "ERV",
    "polvora": "POL",
    "balas": "BAL",
    "balas_incendiarias": "BFI",
    "balas_perfurantes": "BPE",
    "cartuchos": "CAR",
    "cartuchos_incendiarios": "CFI",
    "comida": "COM",
    "kit_medico": "KIT",
    "maos": "MAO",
    "taco": "TAC",
    "pistola": "PIS",
    "pistola_incendiaria": "PIF",
    "pistola_perfurante": "PPE",
    "escopeta": "ESC",
    "escopeta_incendiaria": "ESF",
}
ITEM_ICONS = {
    "madeira": "Icon_Wooden-wall.png",
    "metal": "Icon_Rock.png",
    "pano": "Icon_Bandage.png",
    "erva": "Icon_Bandage.png",
    "polvora": "Icon_Bullet-crate_Red.png",
    "balas": "Icon_Bullet-box_Red.png",
    "balas_incendiarias": "Icon_Bullet-box_Green.png",
    "balas_perfurantes": "Icon_Bullet-box_Blue.png",
    "cartuchos": "Icon_Bullet-crate_Red.png",
    "cartuchos_incendiarios": "Icon_Bullet-crate_Green.png",
    "taco": "Icon_Bat.png",
    "pistola": "Icon_Pistol.png",
    "pistola_incendiaria": "Icon_Pistol.png",
    "pistola_perfurante": "Icon_Pistol.png",
    "escopeta": "Icon_Shotgun.png",
    "escopeta_incendiaria": "Icon_Shotgun.png",
    "comida": "Icon_Canned-food.png",
    "kit_medico": "Icon_First-Aid-Kit_Red.png",
}
CONSUMABLE_ITEMS = {"comida", "kit_medico"}
AMMO_LOOT_RANGES = {
    "balas": (3, 8),
    "balas_incendiarias": (2, 4),
    "balas_perfurantes": (2, 4),
    "cartuchos": (1, 3),
    "cartuchos_incendiarios": (1, 2),
}
ITEM_TINTS = {
    "pistola_incendiaria": (255, 132, 86),
    "pistola_perfurante": (100, 185, 255),
    "escopeta_incendiaria": (255, 102, 76),
    "balas_incendiarias": (255, 132, 86),
    "balas_perfurantes": (100, 185, 255),
    "cartuchos_incendiarios": (255, 132, 86),
}

ZOMBIE_VARIANTS: Dict[str, Dict[str, float | int]] = {
    "axe": {"weight": 7, "speed": 1.0, "health": 1.0, "radius": 12},
    "small": {"weight": 4, "speed": 1.68, "health": 0.72, "radius": 10},
    "big": {"weight": 3, "speed": 0.66, "health": 1.95, "radius": 18},
}

DECOR_VARIANTS: Dict[str, List[Dict[str, object]]] = {
    "tree": [
        {"path": "Nature/Green/Tree_5_Big_Green.png", "scale": 2.35},
        {"path": "Nature/Green/Tree_3_Normal_Green.png", "scale": 2.15},
        {"path": "Nature/Dark-Green/Tree_1_Spruce_Dark-Green.png", "scale": 2.2},
        {"path": "Nature/Dark-Green/Tree_9_Small-oak_Dark-Green.png", "scale": 2.0},
    ],
    "bush": [
        {"path": "Nature/Green/Bush_1_Green.png", "scale": 2.3},
        {"path": "Nature/Green/Bush_2_Green.png", "scale": 2.2},
        {"path": "Nature/Dark-Green/Bush_1_Dark-Green.png", "scale": 2.25},
        {"path": "Nature/Dark-Green/Bush_2_Dark-Green.png", "scale": 2.15},
    ],
    "rock": [
        {"path": "Nature/Flowers_Mashrooms_Other-nature-stuff/Rocks/Rock_4.png", "scale": 2.0},
        {"path": "Nature/Flowers_Mashrooms_Other-nature-stuff/Rocks/Rock_6.png", "scale": 1.9},
        {"path": "Nature/Dark-Green/Rocks/Rock-grass_Dark-Green.png", "scale": 2.0},
    ],
    "vehicle": [
        {"path": "Vehicles/Rust/Car_3_Rust_Van/Car_3_Rust_Blue_Van.png", "scale": 2.0},
        {"path": "Vehicles/Rust/Car_6_Rust_Scrap/Car_6_Rust_Blue_Scrap.png", "scale": 2.2},
        {"path": "Vehicles/Rust/Car_4_Rust/Car_4_Rust_Orange.png", "scale": 2.0},
    ],
    "container": [
        {"path": "Container/Container_7_Red_Horizontal.png", "scale": 1.95},
        {"path": "Container/Container_3_Gray_Horizontal.png", "scale": 1.95},
        {"path": "Container/Container_1_Gray_Vertical.png", "scale": 1.55},
    ],
    "street_light": [
        {"path": "Street-Light_3_Down.png", "scale": 2.0},
        {"path": "Street-Light_6_Down_Overgrown_Green.png", "scale": 2.0},
    ],
}

DECOR_DRAW_STYLE: Dict[str, Dict[str, float]] = {
    "tree": {"shadow_w": 0.36, "shadow_h": 0.1, "ground_offset": 10},
    "bush": {"shadow_w": 0.58, "shadow_h": 0.16, "ground_offset": 7},
    "rock": {"shadow_w": 0.54, "shadow_h": 0.15, "ground_offset": 5},
    "vehicle": {"shadow_w": 0.72, "shadow_h": 0.13, "ground_offset": 8},
    "container": {"shadow_w": 0.74, "shadow_h": 0.12, "ground_offset": 8},
    "street_light": {"shadow_w": 0.34, "shadow_h": 0.08, "ground_offset": 6},
    "building": {"shadow_w": 0.78, "shadow_h": 0.12, "ground_offset": 10},
}

BUILDING_VARIANTS: List[Dict[str, object]] = [
    {
        "entrance": "Buildings/Enterance_Green.png",
        "awning": "Buildings/Awning_orange_3.png",
        "window": "Windows/Window_16_Beige.png",
        "poster": "Buildings/layered-posters_1_For-ground-and-walls.png",
        "scale": 2.45,
    },
    {
        "entrance": "Buildings/Enterance_Dark-Green.png",
        "awning": "Buildings/Awning_blue_4.png",
        "window": "Windows/Window_19_gray.png",
        "poster": "Buildings/layered-posters_2_For-ground-and-walls.png",
        "scale": 2.4,
    },
    {
        "entrance": "Buildings/Enterance_Bleak-Yellow.png",
        "awning": "Buildings/Awning_orange_2.png",
        "window": "Windows/Window_18_Boarded-up_Beige.png",
        "poster": "Buildings/layered-posters_1_For-ground-and-walls.png",
        "scale": 2.4,
    },
]

NODE_SPRITES: Dict[str, List[Dict[str, object]]] = {
    "caixote": [
        {"path": "Cardboard_1.png", "scale": 2.7},
        {"path": "Cardboard_2.png", "scale": 2.55},
    ],
    "arvore": [
        {"path": "Nature/Green/Tree_5_Big_Green.png", "scale": 1.7},
        {"path": "Nature/Green/Tree_3_Normal_Green.png", "scale": 1.6},
        {"path": "Nature/Dark-Green/Tree_1_Spruce_Dark-Green.png", "scale": 1.65},
    ],
    "sucata": [
        {"path": "Barrel_rust_blue_1.png", "scale": 2.2},
        {"path": "Barrel_rust_red_1.png", "scale": 2.2},
        {"path": "Vehicles/Rust/Car_6_Rust_Scrap/Car_6_Rust_Blue_Scrap.png", "scale": 1.7},
    ],
    "despensa": [
        {"path": "Shopping-cart.png", "scale": 2.4},
        {"path": "Garbage-Bin_1.png", "scale": 1.7},
        {"path": "Garbage-Bin_2.png", "scale": 1.85},
    ],
    "erva": [
        {"path": "Nature/Green/Bush_1_Green.png", "scale": 2.0},
        {"path": "Nature/Green/Grass_4_Green.png", "scale": 2.1},
        {"path": "Nature/Dark-Green/Bush_2_Dark-Green.png", "scale": 1.95},
    ],
    "natureza": [
        {"path": "Nature/Green/Bush_1_Green.png", "scale": 2.0},
        {"path": "Nature/Green/Grass_4_Green.png", "scale": 2.1},
        {"path": "Nature/Dark-Green/Bush_2_Dark-Green.png", "scale": 1.95},
    ],
    "carro": [
        {"path": "Vehicles/Rust/Car_3_Rust_Van/Car_3_Rust_Blue_Van.png", "scale": 1.7},
        {"path": "Vehicles/Rust/Car_6_Rust_Scrap/Car_6_Rust_Blue_Scrap.png", "scale": 1.75},
        {"path": "Vehicles/Rust/Car_4_Rust/Car_4_Rust_Orange.png", "scale": 1.7},
    ],
    "edificio": [
        {"path": "Buildings/Enterance_Green.png", "scale": 2.8},
        {"path": "Buildings/Enterance_Dark-Green.png", "scale": 2.8},
        {"path": "Buildings/Enterance_Bleak-Yellow.png", "scale": 2.8},
    ],
}


def _load_raw_sprite(relative_path: str) -> pygame.Surface:
    cached = _RAW_SPRITE_CACHE.get(relative_path)
    if cached is not None:
        return cached

    sprite = pygame.image.load(str(OBJECT_SPRITE_ROOT / relative_path)).convert_alpha()
    _RAW_SPRITE_CACHE[relative_path] = sprite
    return sprite


def _load_scaled_sprite(relative_path: str, scale: float = 1.0) -> pygame.Surface:
    normalized_scale = round(scale, 2)
    cache_key = (relative_path, normalized_scale)
    cached = _SCALED_SPRITE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    sprite = _load_raw_sprite(relative_path)
    width = max(1, int(round(sprite.get_width() * normalized_scale)))
    height = max(1, int(round(sprite.get_height() * normalized_scale)))
    if (width, height) != sprite.get_size():
        sprite = pygame.transform.scale(sprite, (width, height))
    _SCALED_SPRITE_CACHE[cache_key] = sprite
    return sprite


def _load_ui_sprite(file_name: str, scale: int = 1) -> pygame.Surface:
    scale = max(1, int(scale))
    cache_key = (file_name, scale)
    cached = _UI_SPRITE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    sprite = pygame.image.load(str(UI_SPRITE_ROOT / file_name)).convert_alpha()
    if scale != 1:
        sprite = pygame.transform.scale(sprite, (sprite.get_width() * scale, sprite.get_height() * scale))
    _UI_SPRITE_CACHE[cache_key] = sprite
    return sprite


def _build_facade_sprite(
    entrance_path: str,
    awning_path: str,
    window_path: str,
    poster_path: str,
    scale: float,
) -> pygame.Surface:
    normalized_scale = round(scale, 2)
    cache_key = (entrance_path, awning_path, window_path, poster_path, normalized_scale)
    cached = _COMPOSITE_SPRITE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    entrance = _load_raw_sprite(entrance_path)
    awning = _load_raw_sprite(awning_path)
    window = _load_raw_sprite(window_path)
    poster = _load_raw_sprite(poster_path)

    width = max(awning.get_width() + 20, entrance.get_width() + (window.get_width() * 2) + 22)
    height = awning.get_height() + entrance.get_height() + 18
    facade = pygame.Surface((width, height), pygame.SRCALPHA)

    awning_x = (width - awning.get_width()) // 2
    body_y = awning.get_height() - 3
    entrance_x = (width - entrance.get_width()) // 2
    window_y = body_y + 9

    facade.blit(awning, (awning_x, 0))
    facade.blit(window, (entrance_x - window.get_width() - 6, window_y))
    facade.blit(window, (entrance_x + entrance.get_width() + 6, window_y))
    facade.blit(entrance, (entrance_x, body_y + 4))
    facade.blit(poster, (6, body_y + 14))

    if normalized_scale != 1.0:
        facade = pygame.transform.scale(
            facade,
            (
                max(1, int(round(facade.get_width() * normalized_scale))),
                max(1, int(round(facade.get_height() * normalized_scale))),
            ),
        )
    _COMPOSITE_SPRITE_CACHE[cache_key] = facade
    return facade


def _make_shadow(size: Tuple[int, int], alpha: int = 110) -> pygame.Surface:
    shadow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (18, 22, 24, alpha), shadow.get_rect())
    return shadow


def _dim_sprite(sprite: pygame.Surface) -> pygame.Surface:
    dimmed = sprite.copy()
    dimmed.fill((125, 125, 125, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return dimmed


def _tint_sprite(sprite: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    tinted = sprite.copy()
    overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, 0))
    tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return tinted


def _load_shot_impact_frames() -> List[pygame.Surface]:
    global _SHOT_IMPACT_CACHE
    if _SHOT_IMPACT_CACHE is not None:
        return random.choice(_SHOT_IMPACT_CACHE)

    frame_count = 3
    variants: List[List[pygame.Surface]] = []
    for spritesheet_path in [SHOT_SPRITE_ROOT / "shot_1-Sheet3.png", SHOT_SPRITE_ROOT / "shot_2-Sheet3.png"]:
        sheet = pygame.image.load(str(spritesheet_path)).convert_alpha()
        frame_width = sheet.get_width() // frame_count
        frame_height = sheet.get_height()
        frames: List[pygame.Surface] = []
        for frame_index in range(frame_count):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(frame_index * frame_width, 0, frame_width, frame_height))
            frames.append(pygame.transform.scale(frame, (frame_width * 3, frame_height * 3)))
        variants.append(frames)
    _SHOT_IMPACT_CACHE = variants
    return random.choice(_SHOT_IMPACT_CACHE)


class Decoration:
    def __init__(self, decor_type: str, position: Tuple[int, int], scale: float = 1.0) -> None:
        self.decor_type = decor_type
        self.position = pygame.Vector2(position)
        self.scale = scale
        self.sprite = self._create_sprite()
        style = DECOR_DRAW_STYLE[self.decor_type]
        self._ground_offset = int(style["ground_offset"] * self.scale)
        self._shadow = _make_shadow(
            (
                max(12, int(self.sprite.get_width() * style["shadow_w"])),
                max(6, int(self.sprite.get_height() * style["shadow_h"])),
            )
        )

    def _create_sprite(self) -> pygame.Surface:
        if self.decor_type == "building":
            variant = random.choice(BUILDING_VARIANTS)
            return _build_facade_sprite(
                str(variant["entrance"]),
                str(variant["awning"]),
                str(variant["window"]),
                str(variant["poster"]),
                float(variant["scale"]) * self.scale,
            )

        variant = random.choice(DECOR_VARIANTS[self.decor_type])
        return _load_scaled_sprite(str(variant["path"]), float(variant["scale"]) * self.scale)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = self.position - camera_offset
        sprite_rect = self.sprite.get_rect(
            midbottom=(round(draw_pos.x), round(draw_pos.y + self._ground_offset))
        )
        shadow_rect = self._shadow.get_rect(center=(sprite_rect.centerx + 3, sprite_rect.bottom - 4))
        surface.blit(self._shadow, shadow_rect)
        surface.blit(self.sprite, sprite_rect)


class SearchNode:
    def __init__(
        self,
        node_type: str,
        position: Tuple[int, int],
        draw_sprite: bool = True,
        radius: int | None = None,
    ) -> None:
        self.node_type = node_type
        self.position = pygame.Vector2(position)
        self.draw_sprite = draw_sprite
        self._sprite: pygame.Surface | None = None
        self._searched_sprite: pygame.Surface | None = None
        if self.draw_sprite:
            variant = random.choice(NODE_SPRITES[self.node_type])
            self._sprite = _load_scaled_sprite(str(variant["path"]), float(variant["scale"]))
            self._searched_sprite = _dim_sprite(self._sprite)
            self.radius = max(18, int(max(self._sprite.get_width(), self._sprite.get_height()) * 0.42))
        else:
            self.radius = radius or SEARCH_RANGE
        self.searched = False

    def search(self) -> Tuple[Dict[str, int], int]:
        node_data = NODE_TYPES[self.node_type]
        min_drops, max_drops = node_data["drops"]
        loot_items = node_data["loot"]
        drop_count = random.randint(min_drops, max_drops)

        rewards: Dict[str, int] = {}
        for _ in range(drop_count):
            item = random.choice(loot_items)
            amount_range = AMMO_LOOT_RANGES.get(item)
            amount = random.randint(*amount_range) if amount_range is not None else 1
            rewards[item] = rewards.get(item, 0) + amount

        ambush_count = 0
        if random.random() < float(node_data["ambush"]):
            ambush_count = random.randint(1, 2)

        self.searched = True
        return rewards, ambush_count

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        if not self.draw_sprite or self._sprite is None or self._searched_sprite is None:
            return

        draw_pos = self.position - camera_offset
        sprite = self._searched_sprite if self.searched else self._sprite
        sprite_rect = sprite.get_rect(midbottom=(round(draw_pos.x), round(draw_pos.y + 8)))
        shadow = _make_shadow(
            (
                max(10, int(sprite_rect.width * 0.62)),
                max(5, int(sprite_rect.height * 0.18)),
            ),
            alpha=105,
        )
        shadow_rect = shadow.get_rect(center=(sprite_rect.centerx + 2, sprite_rect.bottom - 3))
        surface.blit(shadow, shadow_rect)
        surface.blit(sprite, sprite_rect)


class MapTrigger:
    def __init__(self, trigger_type: str, position: Tuple[int, int], radius: int) -> None:
        self.trigger_type = trigger_type
        self.position = pygame.Vector2(position)
        self.radius = radius


class ShotImpact:
    def __init__(
        self,
        position: Tuple[float, float] | pygame.Vector2,
        origin: Tuple[float, float] | pygame.Vector2 | None = None,
        color: Tuple[int, int, int] = (255, 224, 120),
    ) -> None:
        self.position = pygame.Vector2(position)
        self.origin = pygame.Vector2(origin) if origin is not None else self.position.copy()
        self.color = color
        self.animation_time = 0.0
        self.frames = _load_shot_impact_frames()
        self.fps = 18.0
        self.duration = 0.22

    def update(self, dt: float) -> None:
        self.animation_time += dt * self.fps

    def is_finished(self) -> bool:
        return self.animation_time >= len(self.frames) and self.animation_time / self.fps >= self.duration

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        age = self.animation_time / self.fps
        progress = max(0.0, min(1.0, age / self.duration))
        alpha = max(0, int(210 * (1.0 - progress)))
        start = self.origin - camera_offset
        end = self.position - camera_offset
        bullet_pos = start.lerp(end, progress)
        if alpha > 0 and start.distance_to(end) > 2:
            trail = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
            pygame.draw.line(trail, (*self.color, alpha), start, end, 2)
            glow = tuple(min(255, component + 35) for component in self.color)
            pygame.draw.circle(trail, (*glow, min(255, alpha + 35)), bullet_pos, 3)
            surface.blit(trail, (0, 0))

        frame_index = min(int(self.animation_time), len(self.frames) - 1)
        sprite = self.frames[frame_index]
        surface.blit(sprite, sprite.get_rect(center=(round(end.x), round(end.y))))


class FloatingPopup:
    def __init__(
        self,
        position: Tuple[float, float] | pygame.Vector2,
        icon_name: str | None = None,
        amount: int = 0,
        label: str = "",
        color: Tuple[int, int, int] = PALETTE["text"],
    ) -> None:
        self.position = pygame.Vector2(position)
        self.icon_name = icon_name
        self.amount = amount
        self.label = label
        self.color = color
        self.age = 0.0
        self.duration = 1.15

    def update(self, dt: float) -> None:
        self.age += dt

    def is_finished(self) -> bool:
        return self.age >= self.duration

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2, font: pygame.font.Font) -> None:
        progress = max(0.0, min(1.0, self.age / self.duration))
        alpha = max(0, min(255, int(255 * (1.0 - progress))))
        center = self.position - camera_offset + pygame.Vector2(0, -28 - (34 * progress))

        pieces: List[pygame.Surface] = []
        if self.icon_name is not None:
            icon = _load_ui_sprite(self.icon_name, 2).copy()
            icon.set_alpha(alpha)
            pieces.append(icon)

        text = self.label
        if self.amount > 0:
            text = f"+{self.amount}"
        if text:
            text_surface = font.render(text, True, self.color)
            text_surface.set_alpha(alpha)
            pieces.append(text_surface)

        if not pieces:
            return

        gap = 4 if len(pieces) > 1 else 0
        total_width = sum(piece.get_width() for piece in pieces) + gap * (len(pieces) - 1)
        x = center.x - (total_width / 2)
        for piece in pieces:
            rect = piece.get_rect(midleft=(round(x), round(center.y)))
            surface.blit(piece, rect)
            x += piece.get_width() + gap


class Game:
    def __init__(self) -> None:
        self._audio_enabled = True
        self._current_music: Path | None = None
        self._game_music_sound: pygame.mixer.Sound | None = None
        self._game_music_channels: List[pygame.mixer.Channel] = []
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except pygame.error:
            self._audio_enabled = False
        pygame.init()
        pygame.display.set_caption("Jogo de Sobrevivencia Zumbi")
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.menu_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 56, bold=True)

        self.game_time: float = 0.0
        self.difficulty_scale: float = 1.0
        self.spawn_rate: float = 1.0
        self.is_game_running: bool = True
        self._screen_state = "main_menu"
        self._menu_pressed_button: str | None = None
        self._menu_message = ""
        self._menu_message_timer = 0.0
        self._settings = self._load_settings()
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._has_started_game = False
        self._controller: object | None = None
        self._gamepad: object | None = None
        self._gamepad_backend: str | None = None
        self._gamepad_last_seen_ms = 0
        self._gamepad_next_scan_ms = 0
        self._gamepad_missing_since_ms: int | None = None
        self._gamepad_buttons_down: set[int] = set()
        self._gamepad_attack_down = False
        self._gamepad_menu_axis_y_down = False
        self._gamepad_menu_axis_x_down = False
        self._right_stick_axes: Tuple[int, int] | None = None
        self._gamepad_aim_vector = pygame.Vector2()
        self._show_gamepad_debug = False
        self._menu_selected_index = 0

        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.crafting = CraftingSystem()

        self.zombies: List[Zombie] = []
        self.shot_impacts: List[ShotImpact] = []
        self._floating_popups: List[FloatingPopup] = []
        self.nodes: List[SearchNode] = []
        self.decorations: List[Decoration] = []
        self.doors: List[MapTrigger] = []
        self.exits: List[MapTrigger] = []
        self.tile_map: TiledMap | None = None
        self.collision_rects: List[pygame.Rect] = []

        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._transition_cooldown = 0.0
        self._camera = pygame.Vector2()

        self._recipe_names = self.crafting.get_recipe_names(self.inventory)
        self._selected_recipe_index = 0
        self._base_position = pygame.Vector2(WORLD_WIDTH * 0.48, WORLD_HEIGHT * 0.52)
        self._current_map_index = 0
        self._current_map_path = self._first_existing_path(MAP_SEQUENCE, TILED_MAP_PATH)
        self._inside_interior = False
        self._return_map_path: Path | None = None
        self._return_map_index = 0
        self._return_position: pygame.Vector2 | None = None
        self._interior_exit: MapTrigger | None = None
        self._show_inventory = False
        self._show_crafting = False
        self._quick_slots = ["maos", "taco", "pistola", "escopeta", "comida", "kit_medico"]
        self._selected_quick_slot = 0

        self._load_sfx()
        self._reset_game()
        self._play_title_music()

    @staticmethod
    def _first_existing_path(paths: List[Path], fallback: Path) -> Path:
        for path in paths:
            if path.exists():
                return path
        return fallback

    def _load_settings(self) -> Dict[str, int]:
        default_settings = {"master": 80, "music": 70, "sfx": 80}
        storage = _web_local_storage()
        if storage is not None:
            raw_settings = storage.getItem(WEB_SETTINGS_KEY)
            if not raw_settings:
                return default_settings
            try:
                raw_settings = json.loads(str(raw_settings))
            except json.JSONDecodeError:
                return default_settings
        else:
            if not SETTINGS_PATH.exists():
                return default_settings
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
                    raw_settings = json.load(file)
            except (OSError, json.JSONDecodeError):
                return default_settings

        settings = default_settings.copy()
        for key in settings:
            try:
                settings[key] = max(0, min(100, int(raw_settings.get(key, settings[key]))))
            except (TypeError, ValueError):
                pass
        return settings

    def _save_settings(self) -> None:
        storage = _web_local_storage()
        if storage is not None:
            storage.setItem(WEB_SETTINGS_KEY, json.dumps(self._settings))
            self._apply_audio_settings()
            return

        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
                json.dump(self._settings, file, indent=2)
        except OSError:
            self._set_menu_message("Nao foi possivel salvar configuracoes.")
        self._apply_audio_settings()

    def _music_volume(self, music_path: Path | None = None) -> float:
        master = self._settings.get("master", 100) / 100
        music = self._settings.get("music", 100) / 100
        gain = GAME_MUSIC_GAIN if music_path == GAME_MUSIC_PATH else 1.0
        return max(0.0, min(1.0, master * music * gain))

    def _sfx_volume(self) -> float:
        master = self._settings.get("master", 100) / 100
        sfx = self._settings.get("sfx", 100) / 100
        return max(0.0, min(1.0, master * sfx * SFX_GAIN))

    def _apply_audio_settings(self) -> None:
        if not self._audio_enabled:
            return
        if pygame.mixer.get_init() is None:
            return
        try:
            pygame.mixer.music.set_volume(self._music_volume(self._current_music))
            for channel in self._game_music_channels:
                channel.set_volume(self._music_volume(GAME_MUSIC_PATH))
            for sound in self._sounds.values():
                sound.set_volume(self._sfx_volume())
        except pygame.error:
            self._audio_enabled = False

    def _load_sfx(self) -> None:
        if not self._audio_enabled or pygame.mixer.get_init() is None:
            return
        for sound_name, file_name in SFX_FILES.items():
            sound_path = _web_audio_path(SFX_ROOT / file_name)
            if not sound_path.exists():
                continue
            try:
                sound = pygame.mixer.Sound(str(sound_path))
                sound.set_volume(self._sfx_volume())
                self._sounds[sound_name] = sound
            except pygame.error:
                continue

    def _play_sfx(self, sound_name: str) -> None:
        sound = self._sounds.get(sound_name)
        if sound is None:
            return
        sound.set_volume(self._sfx_volume())
        sound.play()

    def _play_music(self, music_path: Path) -> None:
        if not self._audio_enabled or self._current_music == music_path:
            return
        resolved_music_path = _web_audio_path(music_path)
        if not resolved_music_path.exists():
            self._set_menu_message(f"Musica nao encontrada: {resolved_music_path.name}")
            return
        if music_path == GAME_MUSIC_PATH:
            self._play_boosted_game_music()
            return
        if pygame.mixer.get_init() is None:
            self._set_menu_message("Audio do pygame indisponivel.")
            return

        try:
            self._stop_boosted_game_music()
            pygame.mixer.music.load(str(resolved_music_path))
            pygame.mixer.music.set_volume(self._music_volume(music_path))
            pygame.mixer.music.play(-1)
        except pygame.error:
            self._audio_enabled = False
            self._set_menu_message(f"Musica nao suportada: {music_path.name}")
            return

        self._current_music = music_path

    def _play_boosted_game_music(self) -> None:
        if pygame.mixer.get_init() is None:
            self._set_menu_message("Audio do pygame indisponivel.")
            return
        try:
            game_music_path = _web_audio_path(GAME_MUSIC_PATH)
            if not game_music_path.exists():
                self._set_menu_message(f"Musica nao encontrada: {game_music_path.name}")
                return
            if self._game_music_sound is None:
                self._game_music_sound = pygame.mixer.Sound(str(game_music_path))
            pygame.mixer.music.stop()
            self._stop_boosted_game_music()
            self._game_music_channels = [
                channel
                for channel in (
                    self._game_music_sound.play(loops=-1)
                    for _ in range(GAME_MUSIC_LAYER_COUNT)
                )
                if channel is not None
            ]
            for channel in self._game_music_channels:
                channel.set_volume(self._music_volume(GAME_MUSIC_PATH))
        except pygame.error:
            self._audio_enabled = False
            self._set_menu_message(f"Musica nao suportada: {GAME_MUSIC_PATH.name}")
            return

        self._current_music = GAME_MUSIC_PATH

    def _stop_boosted_game_music(self) -> None:
        for channel in self._game_music_channels:
            channel.stop()
        self._game_music_channels = []

    def _play_title_music(self) -> None:
        self._play_music(TITLE_MUSIC_PATH)

    def _play_game_music(self) -> None:
        self._play_music(GAME_MUSIC_PATH)

    def _reset_game(self) -> None:
        self.game_time = 0.0
        self.difficulty_scale = 1.0
        self.spawn_rate = 1.0
        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.zombies = []
        self.shot_impacts = []
        self._floating_popups = []
        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._transition_cooldown = 0.0
        self._camera = pygame.Vector2()
        self._current_map_index = 0
        self._current_map_path = self._first_existing_path(MAP_SEQUENCE, TILED_MAP_PATH)
        self._inside_interior = False
        self._return_map_path = None
        self._return_map_index = 0
        self._return_position = None
        self._show_inventory = False
        self._show_crafting = False
        self._selected_quick_slot = 0
        self._menu_selected_index = 0
        self._gamepad_aim_vector = pygame.Vector2()

        self._generate_world()
        self.player.set_position(tuple(self._base_position))
        self.inventory.add_item("comida", 2)

    def _clear_world_content(self) -> None:
        self.nodes.clear()
        self.zombies.clear()
        self.shot_impacts.clear()
        self._floating_popups.clear()
        self.decorations.clear()
        self.doors.clear()
        self.exits.clear()
        self.collision_rects.clear()
        self.tile_map = None
        self._interior_exit = None

    def _generate_world(self) -> None:
        self._clear_world_content()
        self._inside_interior = False

        if self._load_tiled_world(self._current_map_path, inside_interior=False):
            return

        node_pool = [
            "arvore",
            "arvore",
            "arvore",
            "caixote",
            "caixote",
            "sucata",
            "sucata",
            "despensa",
            "despensa",
            "erva",
            "erva",
            "carro",
            "edificio",
        ]
        for _ in range(28):
            self.nodes.append(SearchNode(random.choice(node_pool), self._random_world_position()))

        self._populate_decorations()

        for _ in range(6):
            self._spawn_zombie()

    def _load_tiled_world(self, map_path: Path, inside_interior: bool = False) -> bool:
        if not map_path.exists():
            return False

        global WORLD_WIDTH, WORLD_HEIGHT
        self.tile_map = TiledMap(map_path, scale=TILED_MAP_SCALE)
        self._current_map_path = map_path
        self._inside_interior = inside_interior
        WORLD_WIDTH = self.tile_map.world_width
        WORLD_HEIGHT = self.tile_map.world_height
        self.collision_rects = list(self.tile_map.collision_rects)
        self._base_position = self._find_open_position_near(self._default_spawn_target(inside_interior))

        for spawn in self.tile_map.search_nodes:
            interaction_position = self._find_open_position_near(spawn.position)
            if not inside_interior and interaction_position.distance_to(self._base_position) < 80:
                continue
            node_type = "edificio" if inside_interior and spawn.node_type == "despensa" else spawn.node_type
            self.nodes.append(
                SearchNode(
                    node_type,
                    tuple(interaction_position),
                    draw_sprite=spawn.draw_sprite,
                    radius=spawn.radius,
                )
            )

        if not inside_interior:
            for trigger in self.tile_map.door_triggers:
                self.doors.append(MapTrigger(trigger.trigger_type, trigger.position, max(DOOR_RANGE, trigger.radius)))
            for trigger in self.tile_map.exit_triggers:
                self.exits.append(MapTrigger(trigger.trigger_type, trigger.position, max(EXIT_RANGE, trigger.radius)))
            for _ in range(2):
                self._spawn_zombie()
        else:
            self._interior_exit = MapTrigger(
                "interior_exit",
                tuple(self._find_open_position_near((WORLD_WIDTH * 0.5, WORLD_HEIGHT - self.tile_map.render_tile_height))),
                DOOR_RANGE,
            )

        self._set_message("Interior carregado." if inside_interior else "Mapa do Tiled carregado.")
        return True

    def _default_spawn_target(self, inside_interior: bool) -> Tuple[float, float]:
        if inside_interior:
            return (WORLD_WIDTH * 0.5, WORLD_HEIGHT - 72)
        return (WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.5)

    def _switch_to_tiled_map(
        self,
        map_path: Path,
        inside_interior: bool,
        spawn_position: Tuple[float, float] | pygame.Vector2 | None = None,
        map_index: int | None = None,
    ) -> bool:
        self._clear_world_content()
        if map_index is not None:
            self._current_map_index = map_index
        if not self._load_tiled_world(map_path, inside_interior=inside_interior):
            self._set_message("Mapa nao encontrado.")
            return False

        target = pygame.Vector2(spawn_position) if spawn_position is not None else pygame.Vector2(
            self._default_spawn_target(inside_interior)
        )
        spawn = self._find_open_position_near(target)
        self.player.set_position(tuple(spawn))
        self._transition_cooldown = 0.8
        return True

    def _enter_random_interior(self, door: MapTrigger) -> None:
        interior_paths = [path for path in INTERIOR_MAP_PATHS if path.exists()]
        if not interior_paths:
            self._play_sfx("door_locked")
            self._set_message("Nenhum interior configurado.")
            return

        self._return_map_path = self._current_map_path
        self._return_map_index = self._current_map_index
        self._return_position = self._find_open_position_near(door.position + pygame.Vector2(0, 78))
        interior_path = random.choice(interior_paths)
        if self._switch_to_tiled_map(interior_path, inside_interior=True):
            self._play_sfx("door_open")
            self._set_message("Voce entrou no predio.")

    def _leave_interior(self) -> None:
        if self._return_map_path is None or self._return_position is None:
            self._play_sfx("door_locked")
            self._set_message("Saida sem destino.")
            return

        return_path = self._return_map_path
        return_index = self._return_map_index
        return_position = self._return_position.copy()
        if self._switch_to_tiled_map(
            return_path,
            inside_interior=False,
            spawn_position=return_position,
            map_index=return_index,
        ):
            self._return_map_path = None
            self._return_position = None
            self._play_sfx("door_open")
            self._set_message("Voce saiu do predio.")

    def _use_map_exit(self, trigger: MapTrigger) -> None:
        available_maps = [path for path in MAP_SEQUENCE if path.exists()]
        if not available_maps:
            self._play_sfx("ui_denied")
            self._set_message("Nenhum mapa configurado.")
            return

        old_world_height = max(1, WORLD_HEIGHT)
        player_y_ratio = pygame.Vector2(self.player.player_position).y / old_world_height
        going_right = trigger.position.x > WORLD_WIDTH * 0.5
        next_index = (self._current_map_index + 1) % len(available_maps)
        next_path = available_maps[next_index]

        self._clear_world_content()
        self._current_map_index = next_index
        if not self._load_tiled_world(next_path, inside_interior=False):
            self._set_message("Mapa nao encontrado.")
            return

        spawn_margin = max(56, self.player.radius * 3)
        spawn_x = spawn_margin if going_right else WORLD_WIDTH - spawn_margin
        spawn_y = max(spawn_margin, min(WORLD_HEIGHT - spawn_margin, player_y_ratio * WORLD_HEIGHT))
        spawn = self._find_open_position_near((spawn_x, spawn_y))
        self.player.set_position(tuple(spawn))
        self._transition_cooldown = 0.9
        self._play_sfx("objective")
        self._set_message("Voce continuou pela rua.")

    def _populate_decorations(self) -> None:
        decor_plan = [
            ("tree", 20, 130, START_CLEAR_RADIUS + 120, (0.95, 1.0, 1.08, 1.16)),
            ("bush", 16, 110, START_CLEAR_RADIUS + 90, (0.9, 1.0, 1.08)),
            ("rock", 10, 100, START_CLEAR_RADIUS + 85, (0.9, 1.0, 1.1)),
            ("vehicle", 7, 180, START_CLEAR_RADIUS + 150, (0.95, 1.0, 1.05)),
            ("container", 5, 180, START_CLEAR_RADIUS + 160, (0.95, 1.0)),
            ("building", 5, 220, START_CLEAR_RADIUS + 200, (0.95, 1.0, 1.05)),
            ("street_light", 8, 120, START_CLEAR_RADIUS + 100, (1.0, 1.1)),
        ]

        for decor_type, count, margin, safe_distance, scale_choices in decor_plan:
            placed = 0
            attempts = 0
            while placed < count and attempts < count * 16:
                decor_pos = self._random_world_position(margin)
                attempts += 1
                if pygame.Vector2(decor_pos).distance_to(self._base_position) <= safe_distance:
                    continue
                self.decorations.append(Decoration(decor_type, decor_pos, random.choice(scale_choices)))
                placed += 1

    def _random_world_position(self, margin: int = 120) -> Tuple[int, int]:
        margin = min(margin, max(10, WORLD_WIDTH // 4), max(10, WORLD_HEIGHT // 4))
        for _ in range(80):
            position = (
                random.randint(margin, max(margin, WORLD_WIDTH - margin)),
                random.randint(margin, max(margin, WORLD_HEIGHT - margin)),
            )
            if not self._is_position_blocked(position, 22):
                return position
        return (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)

    def _is_position_blocked(self, position: Tuple[float, float] | pygame.Vector2, radius: int) -> bool:
        point = pygame.Vector2(position)
        if point.x < radius or point.y < radius or point.x > WORLD_WIDTH - radius or point.y > WORLD_HEIGHT - radius:
            return True

        test_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        test_rect.center = (round(point.x), round(point.y))
        return any(test_rect.colliderect(rect) for rect in self.collision_rects)

    def _find_open_position_near(self, target: Tuple[float, float] | pygame.Vector2) -> pygame.Vector2:
        target = pygame.Vector2(target)
        target.x = max(24, min(WORLD_WIDTH - 24, target.x))
        target.y = max(24, min(WORLD_HEIGHT - 24, target.y))
        if not self._is_position_blocked(target, self.player.radius):
            return target

        for radius in range(32, max(WORLD_WIDTH, WORLD_HEIGHT), 32):
            for angle in range(0, 360, 30):
                candidate = target + pygame.Vector2(radius, 0).rotate(angle)
                candidate.x = max(24, min(WORLD_WIDTH - 24, candidate.x))
                candidate.y = max(24, min(WORLD_HEIGHT - 24, candidate.y))
                if not self._is_position_blocked(candidate, self.player.radius):
                    return candidate

        return pygame.Vector2(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)

    def _is_gamepad_live(self, gamepad: object | None) -> bool:
        if gamepad is None:
            return False
        try:
            if hasattr(gamepad, "get_attached") and not gamepad.get_attached():
                return False
            if hasattr(gamepad, "get_numaxes"):
                gamepad.get_numaxes()
            if hasattr(gamepad, "get_numbuttons"):
                gamepad.get_numbuttons()
            return True
        except pygame.error:
            return False

    def _remember_gamepad(self, gamepad: object, backend: str) -> object:
        self._gamepad = gamepad
        self._controller = gamepad if backend == "sdl" else None
        self._gamepad_backend = backend
        self._gamepad_last_seen_ms = pygame.time.get_ticks()
        self._gamepad_missing_since_ms = None
        return gamepad

    def _clear_gamepad(self) -> None:
        self._controller = None
        self._gamepad = None
        self._gamepad_backend = None
        self._gamepad_buttons_down.clear()
        self._gamepad_attack_down = False
        self._gamepad_aim_vector = pygame.Vector2()

    def _scan_sdl_gamepad(self) -> object | None:
        if IS_WEB or sdl_controller is None:
            return None
        try:
            if not sdl_controller.get_init():
                sdl_controller.init()
            for index in range(sdl_controller.get_count()):
                if sdl_controller.is_controller(index):
                    return sdl_controller.Controller(index)
        except pygame.error:
            return None
        return None

    def _scan_raw_gamepad(self) -> object | None:
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            if pygame.joystick.get_count() <= 0:
                return None
            gamepad = pygame.joystick.Joystick(0)
            if hasattr(gamepad, "get_init") and not gamepad.get_init():
                gamepad.init()
            if not self._is_gamepad_live(gamepad):
                return None
            if self._gamepad_axis_count(gamepad) > 0 or self._gamepad_button_count(gamepad) > 0:
                return gamepad
        except pygame.error:
            return None
        return None

    def _get_gamepad(self) -> object | None:
        now = pygame.time.get_ticks()
        if self._is_gamepad_live(self._gamepad):
            self._gamepad_last_seen_ms = now
            self._gamepad_missing_since_ms = None
            return self._gamepad

        if self._gamepad is not None:
            if self._gamepad_missing_since_ms is None:
                self._gamepad_missing_since_ms = now
            if now - self._gamepad_missing_since_ms < GAMEPAD_DISCONNECT_GRACE_MS:
                return self._gamepad
            self._clear_gamepad()

        if now < self._gamepad_next_scan_ms:
            return None
        self._gamepad_next_scan_ms = now + GAMEPAD_RESCAN_INTERVAL_MS

        if self._gamepad_backend in (None, "sdl"):
            gamepad = self._scan_sdl_gamepad()
            if gamepad is not None:
                return self._remember_gamepad(gamepad, "sdl")

        gamepad = self._scan_raw_gamepad()
        if gamepad is not None:
            return self._remember_gamepad(gamepad, "raw")
        return None

    @staticmethod
    def _deadzone_axis(value: float, deadzone: float = 0.18) -> float:
        if abs(value) > 1.0:
            value = max(-1.0, min(1.0, value / 32767.0))
        return 0.0 if abs(value) < deadzone else value

    def _gamepad_axis(self, gamepad: object, axis: int) -> float:
        try:
            if hasattr(gamepad, "get_numaxes") and axis >= gamepad.get_numaxes():
                return 0.0
            return self._deadzone_axis(float(gamepad.get_axis(axis)))
        except (AttributeError, pygame.error):
            return 0.0

    def _gamepad_axis_count(self, gamepad: object) -> int:
        if hasattr(gamepad, "get_numaxes"):
            try:
                return int(gamepad.get_numaxes())
            except pygame.error:
                return 0
        return 6

    def _gamepad_button_count(self, gamepad: object) -> int:
        if hasattr(gamepad, "get_numbuttons"):
            try:
                return int(gamepad.get_numbuttons())
            except pygame.error:
                return 0
        return 18

    def _uses_sdl_gamepad_mapping(self, gamepad: object) -> bool:
        return self._controller is not None and gamepad is self._controller

    def _gamepad_button_map(self, gamepad: object) -> Dict[str, set[int]]:
        if self._uses_sdl_gamepad_mapping(gamepad):
            return {
                "back": {GAMEPAD_BACK},
                "start": {GAMEPAD_START},
                "guide": {GAMEPAD_GUIDE, 15, RAW_GAMEPAD_TOUCHPAD},
                "l3": {GAMEPAD_L3},
                "r3": {GAMEPAD_R3},
                "l1": {GAMEPAD_L1},
                "r1": {GAMEPAD_R1},
                "dpad_up": {GAMEPAD_DPAD_UP},
                "dpad_down": {GAMEPAD_DPAD_DOWN},
                "dpad_left": {GAMEPAD_DPAD_LEFT},
                "dpad_right": {GAMEPAD_DPAD_RIGHT},
            }

        return {
            "back": {RAW_GAMEPAD_BACK},
            "start": {RAW_GAMEPAD_START},
            "guide": {RAW_GAMEPAD_GUIDE, RAW_GAMEPAD_TOUCHPAD},
            "l3": {RAW_GAMEPAD_L3},
            "r3": {RAW_GAMEPAD_R3},
            "l1": {4},
            "r1": {5},
            "dpad_up": {RAW_GAMEPAD_DPAD_UP},
            "dpad_down": {RAW_GAMEPAD_DPAD_DOWN},
            "dpad_left": {RAW_GAMEPAD_DPAD_LEFT},
            "dpad_right": {RAW_GAMEPAD_DPAD_RIGHT},
        }

    @staticmethod
    def _has_any_button(buttons: set[int], candidates: set[int]) -> bool:
        return bool(buttons.intersection(candidates))

    def _gamepad_right_stick(self, gamepad: object, left: pygame.Vector2) -> pygame.Vector2:
        axis_count = self._gamepad_axis_count(gamepad)
        candidates: List[Tuple[Tuple[int, int], pygame.Vector2]] = []
        for pair in ((2, 3), (3, 4), (2, 4), (4, 5)):
            x_axis, y_axis = pair
            if x_axis >= axis_count or y_axis >= axis_count:
                continue
            vector = pygame.Vector2(self._gamepad_axis(gamepad, x_axis), self._gamepad_axis(gamepad, y_axis))
            candidates.append((pair, vector))

        if self._right_stick_axes is not None:
            for pair, vector in candidates:
                if pair == self._right_stick_axes:
                    if vector.length_squared() > 0.01:
                        return vector
                    break

        best_pair: Tuple[int, int] | None = None
        best_vector = pygame.Vector2()
        best_score = 0.0
        for pair, vector in candidates:
            score = vector.length_squared()
            if pair == (4, 5) and vector.y > 0:
                score *= 0.2
            if left.length_squared() > 0.04 and abs(vector.x - left.x) < 0.03 and abs(vector.y - left.y) < 0.03:
                score *= 0.25
            if score > best_score:
                best_score = score
                best_pair = pair
                best_vector = vector

        if best_pair is not None and best_score > 0.04:
            self._right_stick_axes = best_pair
        return best_vector

    def _poll_gamepad_buttons(self, gamepad: object) -> set[int]:
        buttons: set[int] = set()
        try:
            button_count = self._gamepad_button_count(gamepad)
            for index in range(button_count):
                try:
                    if gamepad.get_button(index):
                        buttons.add(index)
                except pygame.error:
                    continue
        except (AttributeError, pygame.error):
            return set()
        return buttons

    def _apply_gamepad_input(
        self,
        direction: pygame.Vector2,
        running: bool,
        craft_pressed: bool,
        search_pressed: bool,
        attack_pressed: bool,
        heal_pressed: bool,
    ) -> Tuple[pygame.Vector2, bool, bool, bool, bool, bool]:
        gamepad = self._get_gamepad()
        if gamepad is None:
            self._gamepad_buttons_down.clear()
            self._gamepad_attack_down = False
            return direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed

        buttons = self._poll_gamepad_buttons(gamepad)
        pressed = buttons - self._gamepad_buttons_down
        button_map = self._gamepad_button_map(gamepad)

        left = pygame.Vector2(self._gamepad_axis(gamepad, 0), self._gamepad_axis(gamepad, 1))
        if left.length_squared() > 0.01:
            direction = left.normalize() if left.length_squared() > 1.0 else left

        right = self._gamepad_right_stick(gamepad, left)
        if right.length_squared() > 0.04:
            self._gamepad_aim_vector = right.normalize()
        elif right.length_squared() <= 0.01:
            self._gamepad_aim_vector = pygame.Vector2()

        if self._has_any_button(pressed, button_map["guide"]):
            self._show_gamepad_debug = not self._show_gamepad_debug

        running = running or self._has_any_button(buttons, button_map["l3"])
        search_pressed = search_pressed or GAMEPAD_A in pressed
        heal_pressed = heal_pressed or GAMEPAD_Y in pressed
        if GAMEPAD_X in pressed:
            self._show_crafting = not self._show_crafting
            self._play_sfx("ui_open" if self._show_crafting else "ui_close")
            if self._show_crafting:
                self._show_inventory = False
        if self._has_any_button(pressed, button_map["r3"]):
            self._show_inventory = not self._show_inventory
            self._play_sfx("ui_open" if self._show_inventory else "ui_close")
            if self._show_inventory:
                self._show_crafting = False
        if self._has_any_button(pressed, button_map["back"]) or self._has_any_button(pressed, button_map["start"]):
            if self._show_inventory:
                self._show_inventory = False
            elif self._show_crafting:
                self._show_crafting = False
            else:
                self._screen_state = "main_menu"
                self._play_title_music()
                self._play_sfx("ui_open")
        if self._has_any_button(pressed, button_map["l1"]):
            self._cycle_quick_slot(-1)
        if self._has_any_button(pressed, button_map["r1"]):
            self._cycle_quick_slot(1)
        if self._has_any_button(pressed, button_map["dpad_left"]):
            self._cycle_quick_slot(-1)
        if self._has_any_button(pressed, button_map["dpad_right"]):
            self._cycle_quick_slot(1)

        trigger_attack = self._gamepad_axis(gamepad, GAMEPAD_AXIS_R2) > 0.45
        if not self._uses_sdl_gamepad_mapping(gamepad):
            trigger_attack = trigger_attack or 7 in buttons
        if trigger_attack and not self._gamepad_attack_down:
            attack_pressed = True

        self._gamepad_buttons_down = buttons
        self._gamepad_attack_down = trigger_attack
        return direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed

    def _spawn_zombie(self, near_position: Tuple[float, float] | pygame.Vector2 | None = None) -> None:
        if near_position is None:
            pos = pygame.Vector2(self._random_world_position())
            while pos.distance_to(pygame.Vector2(self.player.player_position)) < 260:
                pos = pygame.Vector2(self._random_world_position())
        else:
            base = pygame.Vector2(near_position)
            pos = self._find_open_position_near(base + pygame.Vector2(random.randint(-120, 120), random.randint(-120, 120)))

        variant_name = random.choices(
            list(ZOMBIE_VARIANTS.keys()),
            weights=[float(data["weight"]) for data in ZOMBIE_VARIANTS.values()],
            k=1,
        )[0]
        variant = ZOMBIE_VARIANTS[variant_name]
        base_speed = 55.0 + (self.difficulty_scale * 5.0)
        base_health = 24 + (self.difficulty_scale * 4.0)
        speed = base_speed * float(variant["speed"])
        health = int(base_health * float(variant["health"]))
        radius = int(variant["radius"])
        self.zombies.append(Zombie(pos, speed, health=health, radius=radius, zombie_type=variant_name))

    def _apply_loaded_state(self, data: Dict) -> None:
        self.player.player_health = int(data.get("player_health", 100))
        self.player.player_hunger = float(data.get("player_hunger", 100.0))
        position = data.get("player_position", tuple(self._base_position))
        self.player.set_position(position)
        self.inventory = Inventory(data.get("inventory", None))
        self.game_time = float(data.get("game_time", 0.0))
        loaded_weapon = data.get("current_weapon")
        if loaded_weapon in WEAPONS:
            self.player.current_weapon = loaded_weapon
        else:
            self.player.current_weapon = "maos"
        loaded_quick_slots = data.get("quick_slots")
        if isinstance(loaded_quick_slots, list) and len(loaded_quick_slots) == len(self._quick_slots):
            self._quick_slots = [
                str(item_name) if str(item_name) in ITEM_LABELS else fallback
                for item_name, fallback in zip(loaded_quick_slots, self._quick_slots)
            ]

    def process_input(self) -> Tuple[pygame.Vector2, bool, bool, bool, bool, bool]:
        direction = pygame.Vector2(0, 0)
        running = False
        craft_pressed = False
        search_pressed = False
        attack_pressed = False
        heal_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._show_inventory:
                        self._show_inventory = False
                    elif self._show_crafting:
                        self._show_crafting = False
                    else:
                        self._screen_state = "main_menu"
                        self._play_title_music()
                        self._play_sfx("ui_open")
                elif event.key == pygame.K_c:
                    if self._quick_slots[self._selected_quick_slot] in CONSUMABLE_ITEMS:
                        heal_pressed = True
                    else:
                        search_pressed = True
                elif event.key == pygame.K_b:
                    self._show_crafting = not self._show_crafting
                    self._play_sfx("ui_open" if self._show_crafting else "ui_close")
                    if self._show_crafting:
                        self._show_inventory = False
                elif event.key == pygame.K_TAB:
                    self._cycle_recipe()
                elif event.key == pygame.K_e:
                    search_pressed = True
                elif event.key == pygame.K_i:
                    self._show_inventory = not self._show_inventory
                    self._play_sfx("ui_open" if self._show_inventory else "ui_close")
                    if self._show_inventory:
                        self._show_crafting = False
                elif event.key == pygame.K_q:
                    heal_pressed = True
                elif event.key == pygame.K_1:
                    self._select_quick_slot(0)
                elif event.key == pygame.K_2:
                    self._select_quick_slot(1)
                elif event.key == pygame.K_3:
                    self._select_quick_slot(2)
                elif event.key == pygame.K_4:
                    self._select_quick_slot(3)
                elif event.key == pygame.K_5:
                    self._select_quick_slot(4)
                elif event.key == pygame.K_6:
                    self._select_quick_slot(5)
                elif event.key == pygame.K_SPACE:
                    attack_pressed = True
                elif event.key == pygame.K_F2:
                    self._show_gamepad_debug = not self._show_gamepad_debug
                elif event.key == pygame.K_F5:
                    save_game(str(SAVE_GAME_PATH), self.player, self.inventory, self.game_time, self._quick_slots)
                    self._play_sfx("objective")
                    self._set_message("Jogo salvo.")
                elif event.key == pygame.K_F9:
                    data = load_game(str(SAVE_GAME_PATH))
                    if data is None:
                        self._play_sfx("ui_denied")
                        self._set_message("Sem save encontrado.")
                    else:
                        self._apply_loaded_state(data)
                        self._play_sfx("objective")
                        self._set_message("Save carregado.")
            elif event.type == pygame.MOUSEWHEEL:
                self._cycle_quick_slot(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._window_to_screen(event.pos)
                if self._show_inventory:
                    if self._inventory_close_button_rect().collidepoint(mouse_pos):
                        self._show_inventory = False
                        self._play_sfx("ui_close")
                    else:
                        quick_slot_index = self._quick_slot_index_at(mouse_pos)
                        if quick_slot_index is not None:
                            self._selected_quick_slot = quick_slot_index
                            self._play_sfx("inventory_move")
                            continue

                        inventory_item = self._inventory_item_at(mouse_pos)
                        if inventory_item is not None:
                            self._assign_quick_slot_item(inventory_item)
                    continue
                if self._show_crafting:
                    self._handle_crafting_click(mouse_pos)
                    continue
                attack_pressed = True

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_s]:
            direction.y += 1
        if keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_d]:
            direction.x += 1
        running = running or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        return self._apply_gamepad_input(direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed)

    def process_menu_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._screen_state == "main_menu":
                        self.is_game_running = False
                    else:
                        self._play_sfx("ui_close")
                        self._screen_state = "main_menu"
                elif event.key == pygame.K_F2:
                    self._show_gamepad_debug = not self._show_gamepad_debug
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self._screen_state == "main_menu":
                    self._play_sfx("ui_confirm")
                    self._handle_main_menu_action("new_game")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._window_to_screen(event.pos)
                self._menu_pressed_button = None
                clicked_button = False
                if self._screen_state == "main_menu":
                    for action, _, rect in self._main_menu_button_rects():
                        if rect.collidepoint(mouse_pos):
                            clicked_button = True
                            self._menu_pressed_button = action
                            self._play_sfx("ui_confirm")
                            self._handle_main_menu_action(action)
                            break
                elif self._screen_state == "saves":
                    clicked_button = self._handle_saves_menu_click(mouse_pos)
                elif self._screen_state == "settings":
                    clicked_button = self._handle_settings_menu_click(mouse_pos)
                if not clicked_button:
                    self._play_sfx("ui_denied")
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._menu_pressed_button = None
        self._process_gamepad_menu_input()

    def _current_menu_actions(self) -> List[str]:
        if self._screen_state == "saves":
            return [action for action, _, _ in self._saves_menu_button_rects()]
        if self._screen_state == "settings":
            return ["master", "music", "sfx", "back"]
        return [action for action, _, _ in self._main_menu_button_rects()]

    def _clamp_menu_selection(self) -> None:
        actions = self._current_menu_actions()
        if not actions:
            self._menu_selected_index = 0
            return
        self._menu_selected_index %= len(actions)

    def _move_menu_selection(self, delta: int) -> None:
        actions = self._current_menu_actions()
        if not actions or delta == 0:
            return
        self._menu_selected_index = (self._menu_selected_index + delta) % len(actions)
        self._play_sfx("ui_move")

    def _activate_menu_selection(self) -> None:
        actions = self._current_menu_actions()
        if not actions:
            return
        action = actions[self._menu_selected_index % len(actions)]
        if self._screen_state == "main_menu":
            self._play_sfx("ui_confirm")
            self._handle_main_menu_action(action)
        elif self._screen_state == "saves":
            rects = {item_action: rect for item_action, _, rect in self._saves_menu_button_rects()}
            rect = rects.get(action)
            if rect is not None:
                self._handle_saves_menu_click(rect.center)
        elif self._screen_state == "settings":
            if action == "back":
                self._play_sfx("ui_close")
                self._screen_state = "main_menu"

    def _adjust_selected_setting(self, delta: int) -> None:
        actions = self._current_menu_actions()
        if not actions or self._screen_state != "settings":
            return
        action = actions[self._menu_selected_index % len(actions)]
        if action not in self._settings:
            return
        self._settings[action] = max(0, min(100, self._settings[action] + delta))
        self._save_settings()
        self._play_sfx("ui_move")

    def _process_gamepad_menu_input(self) -> None:
        gamepad = self._get_gamepad()
        if gamepad is None:
            self._gamepad_buttons_down.clear()
            return

        buttons = self._poll_gamepad_buttons(gamepad)
        pressed = buttons - self._gamepad_buttons_down
        button_map = self._gamepad_button_map(gamepad)
        y_axis = self._gamepad_axis(gamepad, GAMEPAD_AXIS_LEFT_Y)
        x_axis = self._gamepad_axis(gamepad, GAMEPAD_AXIS_LEFT_X)

        self._clamp_menu_selection()
        if self._has_any_button(pressed, button_map["dpad_up"]) or (y_axis < -0.55 and not self._gamepad_menu_axis_y_down):
            self._move_menu_selection(-1)
        elif self._has_any_button(pressed, button_map["dpad_down"]) or (y_axis > 0.55 and not self._gamepad_menu_axis_y_down):
            self._move_menu_selection(1)

        if self._screen_state == "settings":
            if self._has_any_button(pressed, button_map["dpad_left"]) or (x_axis < -0.55 and not self._gamepad_menu_axis_x_down):
                self._adjust_selected_setting(-5)
            elif self._has_any_button(pressed, button_map["dpad_right"]) or (x_axis > 0.55 and not self._gamepad_menu_axis_x_down):
                self._adjust_selected_setting(5)

        if self._has_any_button(pressed, button_map["guide"]):
            self._show_gamepad_debug = not self._show_gamepad_debug
        if GAMEPAD_A in pressed:
            self._activate_menu_selection()
        if (
            GAMEPAD_B in pressed
            or self._has_any_button(pressed, button_map["back"])
            or self._has_any_button(pressed, button_map["start"])
        ):
            if self._screen_state == "main_menu":
                if self._has_started_game and not self._game_over:
                    self._screen_state = "playing"
                    self._play_game_music()
                else:
                    self.is_game_running = False
            else:
                self._screen_state = "main_menu"
                self._menu_selected_index = 0
                self._play_sfx("ui_close")

        self._gamepad_menu_axis_y_down = abs(y_axis) > 0.55
        self._gamepad_menu_axis_x_down = abs(x_axis) > 0.55
        self._gamepad_buttons_down = buttons

    def _handle_main_menu_action(self, action: str) -> None:
        if action == "new_game":
            self._reset_game()
            self._has_started_game = True
            self._screen_state = "playing"
            self._play_game_music()
            self._set_message("Novo jogo iniciado.")
        elif action == "continue_game":
            if self._has_started_game and not self._game_over:
                self._screen_state = "playing"
                self._play_game_music()
            else:
                self._load_saved_game()
        elif action == "saves":
            self._play_sfx("ui_open")
            self._screen_state = "saves"
        elif action == "settings":
            self._play_sfx("ui_open")
            self._screen_state = "settings"
        elif action == "quit":
            self.is_game_running = False

    def _load_saved_game(self) -> bool:
        data = load_game(str(SAVE_GAME_PATH))
        if data is None:
            self._play_sfx("ui_denied")
            self._set_menu_message("Nenhum save encontrado.")
            return False

        self._reset_game()
        self._apply_loaded_state(data)
        self._has_started_game = True
        self._screen_state = "playing"
        self._play_game_music()
        self._play_sfx("objective")
        self._set_message("Save carregado.")
        return True

    def _set_menu_message(self, text: str) -> None:
        self._menu_message = text
        self._menu_message_timer = 3.0

    def _main_menu_button_rects(self) -> List[Tuple[str, str, pygame.Rect]]:
        specs = [
            ("new_game", "Play"),
            ("continue_game", "Load"),
            ("saves", "Save"),
            ("settings", "Settings"),
            ("quit", "Quit"),
        ]
        button = _load_ui_sprite("Play_Not-Pressed.png", 3)
        gap = 11
        total_height = len(specs) * button.get_height() + (len(specs) - 1) * gap
        start_y = (HEIGHT - total_height) // 2
        rects: List[Tuple[str, str, pygame.Rect]] = []
        for index, (action, sprite_base) in enumerate(specs):
            rect = button.get_rect(center=(WIDTH // 2, start_y + index * (button.get_height() + gap) + button.get_height() // 2))
            rects.append((action, sprite_base, rect))
        return rects

    def _blank_menu_button_rect(self, center: Tuple[int, int], scale: int = 3) -> pygame.Rect:
        button = _load_ui_sprite("Blank_Not-Pressed.png", scale)
        return button.get_rect(center=center)

    def _saves_menu_button_rects(self) -> List[Tuple[str, str, pygame.Rect]]:
        button_y = 336
        buttons = [("load", "CARREGAR", self._blank_menu_button_rect((WIDTH // 2, button_y)))]
        if self._has_started_game:
            buttons.append(("save_current", "SALVAR", self._blank_menu_button_rect((WIDTH // 2, button_y + 70))))
            buttons.append(("back", "VOLTAR", self._blank_menu_button_rect((WIDTH // 2, button_y + 140))))
        else:
            buttons.append(("back", "VOLTAR", self._blank_menu_button_rect((WIDTH // 2, button_y + 70))))
        return buttons

    def _settings_slider_rects(self) -> List[Tuple[str, str, pygame.Rect]]:
        rows = [("master", "MASTER"), ("music", "MUSICA"), ("sfx", "SFX")]
        rects: List[Tuple[str, str, pygame.Rect]] = []
        for index, (key, label) in enumerate(rows):
            rects.append((key, label, pygame.Rect(WIDTH // 2 - 120, 246 + index * 58, 240, 14)))
        return rects

    def _settings_back_button_rect(self) -> pygame.Rect:
        return self._blank_menu_button_rect((WIDTH // 2, 452))

    def _handle_saves_menu_click(self, mouse_pos: Tuple[int, int]) -> bool:
        for action, _, rect in self._saves_menu_button_rects():
            if not rect.collidepoint(mouse_pos):
                continue
            if action == "load":
                if save_exists(str(SAVE_GAME_PATH)):
                    self._play_sfx("ui_confirm")
                    self._load_saved_game()
                else:
                    self._play_sfx("ui_denied")
                    self._set_menu_message("Nenhum save encontrado.")
            elif action == "save_current":
                save_game(str(SAVE_GAME_PATH), self.player, self.inventory, self.game_time, self._quick_slots)
                self._play_sfx("objective")
                self._set_menu_message("Jogo salvo no Slot 1.")
            elif action == "back":
                self._play_sfx("ui_close")
                self._screen_state = "main_menu"
            return True
        return False

    def _handle_settings_menu_click(self, mouse_pos: Tuple[int, int]) -> bool:
        if self._settings_back_button_rect().collidepoint(mouse_pos):
            self._play_sfx("ui_close")
            self._screen_state = "main_menu"
            return True

        for key, _, rect in self._settings_slider_rects():
            hit_area = rect.inflate(26, 24)
            if not hit_area.collidepoint(mouse_pos):
                continue
            ratio = (mouse_pos[0] - rect.left) / max(1, rect.width)
            self._settings[key] = max(0, min(100, int(round(ratio * 100))))
            self._save_settings()
            self._play_sfx("ui_move")
            return True
        return False

    def _update_difficulty(self, dt: float) -> None:
        self.game_time += dt
        self.difficulty_scale = 1.0 + (self.game_time / 150.0)
        self.spawn_rate = 1.0 + (self.game_time / 180.0)

    def _update_survival(self, dt: float) -> None:
        self.player.player_hunger = max(0.0, self.player.player_hunger - (0.75 * dt))
        if self.player.player_hunger <= 0:
            self._starvation_timer += dt
            if self._starvation_timer >= 1.4:
                self._starvation_timer = 0.0
                if self.player.take_damage(5):
                    self._play_sfx("player_damage")
                    self._set_message("Voce esta morrendo de fome!")
        else:
            self._starvation_timer = 0.0

    def _update_zombies(self, dt: float) -> None:
        world_rect = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
        for zombie in self.zombies:
            old_position = zombie.position.copy()
            zombie.update(self.player.player_position, dt, world_rect)
            if zombie.consume_attack_started():
                self._play_sfx(zombie.attack_sfx_name())
            self._resolve_zombie_obstacles(zombie, old_position, dt)
            if zombie.can_damage_player(self.player.player_position, self.player.radius):
                if self.player.take_damage(10):
                    self._play_sfx("player_damage")
                    self._set_message("Voce foi atingido!")
        self._separate_zombies(dt)
        self.zombies = [zombie for zombie in self.zombies if not zombie.is_dead()]

    def _update_shot_impacts(self, dt: float) -> None:
        for impact in self.shot_impacts:
            impact.update(dt)
        self.shot_impacts = [impact for impact in self.shot_impacts if not impact.is_finished()]

    def _update_spawns(self, dt: float) -> None:
        if self._inside_interior:
            return

        self._spawn_timer += dt
        max_zombies = 4 + int(self.game_time / 180.0)
        if self._spawn_timer >= max(20.0, 32.0 / self.spawn_rate) and len(self.zombies) < max_zombies:
            self._spawn_timer = 0.0
            unexplored_nodes = [node for node in self.nodes if not node.searched]
            if unexplored_nodes:
                target_node = random.choice(unexplored_nodes)
                self._spawn_zombie(target_node.position)
            else:
                self._spawn_zombie()

    def _find_nearest_node(self) -> SearchNode | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = float("inf")

        for node in self.nodes:
            if node.searched:
                continue
            distance = node.position.distance_to(player_pos)
            effective_range = max(SEARCH_RANGE, node.radius)
            if distance <= effective_range and distance <= closest_distance:
                closest_distance = distance
                closest = node

        return closest

    def _find_nearest_corpse(self) -> Zombie | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = SEARCH_RANGE

        for zombie in self.zombies:
            if not zombie.can_be_searched():
                continue
            distance = zombie.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = zombie

        return closest

    def _find_nearest_trigger(self, triggers: List[MapTrigger], max_distance: float) -> MapTrigger | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = float("inf")

        for trigger in triggers:
            distance = trigger.position.distance_to(player_pos)
            effective_distance = max(float(trigger.radius), max_distance)
            if distance <= effective_distance and distance <= closest_distance:
                closest_distance = distance
                closest = trigger

        return closest

    def _handle_map_transitions(self, interact_pressed: bool) -> bool:
        if self._transition_cooldown > 0:
            return False

        exit_trigger = self._find_nearest_trigger(self.exits, EXIT_RANGE)
        if exit_trigger is not None:
            self._use_map_exit(exit_trigger)
            return True

        if not interact_pressed:
            return False

        if self._inside_interior:
            if self._interior_exit is not None:
                distance = self._interior_exit.position.distance_to(pygame.Vector2(self.player.player_position))
                if distance <= self._interior_exit.radius:
                    self._leave_interior()
                    return True
            return False

        door = self._find_nearest_trigger(self.doors, DOOR_RANGE)
        if door is not None:
            self._enter_random_interior(door)
            return True

        return False

    def _handle_search(self, search_pressed: bool) -> None:
        if not search_pressed:
            return

        corpse = self._find_nearest_corpse()
        if corpse is not None:
            self.player.start_pickup_animation()
            self._play_sfx("pickup_ammo")
            corpse.corpse_searched = True
            rewards: Dict[str, int] = {}
            for _ in range(random.randint(1, 2)):
                item = random.choice(["pano", "balas", "balas", "polvora", "comida"])
                amount_range = AMMO_LOOT_RANGES.get(item)
                amount = random.randint(*amount_range) if amount_range is not None else 1
                rewards[item] = rewards.get(item, 0) + amount
            granted = self._grant_rewards(rewards)
            self._add_item_popups(granted, corpse.position)
            return

        node = self._find_nearest_node()
        if node is None:
            self._play_sfx("ui_denied")
            return

        self.player.start_pickup_animation()
        if node.node_type == "carro":
            self._play_sfx("search_car")
        elif node.node_type in {"arvore", "natureza", "erva"}:
            self._play_sfx("search_tree")
        else:
            self._play_sfx("pickup_item")
        rewards, ambush_count = node.search()
        granted = self._grant_rewards(rewards)
        if granted:
            self._play_sfx("pickup_ammo" if any(item in AMMO_LOOT_RANGES for item in granted) else "pickup_item")
            self._add_item_popups(granted, node.position)

        for _ in range(ambush_count):
            self._spawn_zombie(node.position)
        if ambush_count > 0:
            self._play_sfx("zombie_alert")
            self._add_alert_popup(node.position)

    def _grant_rewards(self, rewards: Dict[str, int]) -> Dict[str, int]:
        granted: Dict[str, int] = {}
        salvaged_weapon = False

        for item, amount in rewards.items():
            if amount <= 0:
                continue

            if item in WEAPON_ITEMS and item != "maos":
                for _ in range(amount):
                    if self.inventory.get_quantity(item) > 0:
                        salvage = {"madeira": 2} if item == "taco" else {"metal": 2, "polvora": 1}
                        for salvage_item, salvage_amount in salvage.items():
                            self.inventory.add_item(salvage_item, salvage_amount)
                            granted[salvage_item] = granted.get(salvage_item, 0) + salvage_amount
                        salvaged_weapon = True
                    else:
                        self.inventory.add_item(item, 1)
                        granted[item] = granted.get(item, 0) + 1
                continue

            self.inventory.add_item(item, amount)
            granted[item] = granted.get(item, 0) + amount

        if salvaged_weapon:
            self._set_message("Arma repetida desmontada em recursos.")
        return granted

    def _add_item_popups(self, rewards: Dict[str, int], origin: Tuple[float, float] | pygame.Vector2 | None = None) -> None:
        if not rewards:
            return

        base = pygame.Vector2(origin) if origin is not None else pygame.Vector2(self.player.player_position)
        ordered_rewards = list(rewards.items())
        center_offset = (len(ordered_rewards) - 1) * 0.5
        for index, (item_name, amount) in enumerate(ordered_rewards):
            offset = pygame.Vector2((index - center_offset) * 38, -8 - (index % 2) * 8)
            self._floating_popups.append(
                FloatingPopup(
                    base + offset,
                    icon_name=ITEM_ICONS.get(item_name),
                    amount=amount,
                    label="" if item_name in ITEM_ICONS else ITEM_LABELS.get(item_name, item_name),
                )
            )

    def _add_alert_popup(self, origin: Tuple[float, float] | pygame.Vector2 | None = None) -> None:
        base = pygame.Vector2(origin) if origin is not None else pygame.Vector2(self.player.player_position)
        self._floating_popups.append(FloatingPopup(base, label="!", color=PALETTE["danger"]))

    def _update_floating_popups(self, dt: float) -> None:
        for popup in self._floating_popups:
            popup.update(dt)
        self._floating_popups = [popup for popup in self._floating_popups if not popup.is_finished()]

    def _handle_attack(self, attack_pressed: bool) -> None:
        if not attack_pressed or self._attack_timer > 0:
            return

        stats = WEAPONS.get(self.player.current_weapon, WEAPONS["maos"])
        attack_range = float(stats["range"])
        damage = int(stats["damage"])
        cooldown = float(stats["cooldown"])
        ammo_cost = int(stats.get("ammo", 0))
        ammo_item = str(stats.get("ammo_item", "balas"))

        if ammo_cost > 0 and self.inventory.get_quantity(ammo_item) < ammo_cost:
            self._play_sfx("gun_empty")
            self._set_message(f"Sem {ITEM_LABELS.get(ammo_item, ammo_item)}.")
            self._attack_timer = 0.2
            return

        player_pos = pygame.Vector2(self.player.player_position)
        self.player.start_attack_animation()
        if ammo_cost > 0:
            self.inventory.remove_item(ammo_item, ammo_cost)
            weapon_family = str(stats.get("family", self.player.current_weapon))
            self._play_sfx("shotgun" if weapon_family == "escopeta" else "pistol")
            self._fire_gun(player_pos, attack_range, damage, stats)
        else:
            self._play_sfx("melee")
            self._attack_melee(player_pos, attack_range, damage)

        self._attack_timer = cooldown

    def _attack_melee(self, player_pos: pygame.Vector2, attack_range: float, damage: int) -> None:
        facing = self.player.facing_direction
        closest = None
        closest_distance = attack_range + 20

        for zombie in self.zombies:
            if zombie.is_dying():
                continue
            offset = zombie.position - player_pos
            distance = offset.length()
            effective_range = attack_range + zombie.radius
            if distance > effective_range or distance == 0:
                continue
            direction_to_zombie = offset.normalize()
            if facing.dot(direction_to_zombie) < 0.5:
                continue
            if distance <= closest_distance:
                closest_distance = distance
                closest = zombie

        if closest:
            self._damage_zombie(closest, damage)

    def _fire_gun(
        self,
        player_pos: pygame.Vector2,
        attack_range: float,
        damage: int,
        stats: Dict[str, object],
    ) -> None:
        if self._gamepad_aim_vector.length_squared() > 0.04:
            aim = self._gamepad_aim_vector.normalize()
        else:
            mouse_world = self.screen_to_world(self._window_to_screen(pygame.mouse.get_pos()))
            aim = mouse_world - player_pos
        if aim.length_squared() <= 0.01:
            aim = self.player.facing_direction.copy()
        else:
            aim = aim.normalize()

        pellets = int(stats.get("pellets", 1))
        spread = float(stats.get("spread", 0))
        hit_width = float(stats.get("hit_width", 4))
        effect = str(stats.get("effect", ""))
        pierce = int(stats.get("pierce", 1)) if effect == "pierce" else 1
        projectile_color = stats.get("projectile_color", (255, 224, 120))
        if not isinstance(projectile_color, tuple):
            projectile_color = (255, 224, 120)
        pellet_damage = max(1, damage // max(1, pellets))
        shot_origin = player_pos + (aim * 18)
        hit_any = False

        if pellets <= 1:
            angles = [0.0]
        else:
            step = spread / max(1, pellets - 1)
            angles = [(-spread / 2) + (step * index) for index in range(pellets)]

        for angle in angles:
            direction = aim.rotate(angle)
            hits = self._find_shot_hits(shot_origin, direction, attack_range, hit_width, pierce)
            if not hits:
                impact_position = shot_origin + (direction * attack_range)
            else:
                for zombie, _ in hits:
                    self._damage_zombie(zombie, pellet_damage)
                impact_position = shot_origin + (direction * hits[-1][1])
                hit_any = True

            impact_position.x = max(0, min(WORLD_WIDTH, impact_position.x))
            impact_position.y = max(0, min(WORLD_HEIGHT, impact_position.y))
            if effect == "fire":
                self._apply_fire_splash(impact_position, stats, {id(zombie) for zombie, _ in hits})
            self.shot_impacts.append(ShotImpact(impact_position, shot_origin, projectile_color))

        if not hit_any:
            self._set_message("Disparo sem alvo.")

    def _find_shot_hits(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        max_range: float,
        hit_width: float,
        max_hits: int,
    ) -> List[Tuple[Zombie, float]]:
        hits: List[Tuple[Zombie, float]] = []

        for zombie in self.zombies:
            if zombie.is_dying():
                continue
            to_zombie = zombie.position - origin
            projection = to_zombie.dot(direction)
            if projection < 0 or projection > max_range + zombie.radius:
                continue
            closest_point = origin + (direction * projection)
            miss_distance = zombie.position.distance_to(closest_point)
            if miss_distance > zombie.radius + hit_width:
                continue
            hit_distance = max(0.0, projection - zombie.radius)
            hits.append((zombie, hit_distance))

        hits.sort(key=lambda item: item[1])
        return hits[:max(1, max_hits)]

    def _apply_fire_splash(
        self,
        center: pygame.Vector2,
        stats: Dict[str, object],
        excluded_ids: set[int],
    ) -> None:
        radius = float(stats.get("splash_radius", 0))
        damage = int(stats.get("splash_damage", 0))
        if radius <= 0 or damage <= 0:
            return

        for zombie in self.zombies:
            if id(zombie) in excluded_ids or zombie.is_dying():
                continue
            distance = zombie.position.distance_to(center)
            if distance > radius + zombie.radius:
                continue
            falloff = max(0.35, 1.0 - (distance / max(1.0, radius + zombie.radius)))
            self._damage_zombie(zombie, max(1, int(damage * falloff)))

    def _damage_zombie(self, zombie: Zombie, damage: int) -> None:
        zombie.take_damage(damage)
        if zombie.is_dying() and not zombie.loot_given:
            zombie.loot_given = True
            self._play_sfx("zombie_death")
            self._set_message("Zumbi abatido. Vasculhe o corpo com E.")
        else:
            self._play_sfx("hit_flesh")
            self._set_message("Acerto!")

    def _handle_heal(self, heal_pressed: bool) -> None:
        if not heal_pressed:
            return

        selected_item = self._quick_slots[self._selected_quick_slot]
        if selected_item == "kit_medico":
            if self.inventory.get_quantity("kit_medico") > 0 and self.player.player_health < self.player.max_health:
                self.inventory.remove_item("kit_medico", 1)
                healed_amount = self.player.heal(55)
                self._play_sfx("heal")
                self._set_message(f"Kit medico usado. +{healed_amount} vida.")
                return
            self._play_sfx("ui_denied")
            self._set_message("Kit medico indisponivel.")
            return

        if selected_item == "comida":
            if self.inventory.get_quantity("comida") <= 0:
                self._play_sfx("ui_denied")
                self._set_message("Comida indisponivel.")
                return
            self.inventory.remove_item("comida", 1)
            hunger_restored = int(self.player.restore_hunger(32))
            healed_amount = self.player.heal(12)
            self._play_sfx("eat")
            self._set_message(f"Voce comeu. Fome +{hunger_restored}, vida +{healed_amount}.")
            return

        if self.inventory.get_quantity("kit_medico") > 0 and self.player.player_health < self.player.max_health:
            self.inventory.remove_item("kit_medico", 1)
            healed_amount = self.player.heal(55)
            self._play_sfx("heal")
            self._set_message(f"Kit medico usado. +{healed_amount} vida.")
            return

        if self.inventory.get_quantity("comida") <= 0:
            self._play_sfx("ui_denied")
            self._set_message("Voce nao tem comida nem kit medico.")
            return

        self.inventory.remove_item("comida", 1)
        hunger_restored = int(self.player.restore_hunger(32))
        healed_amount = self.player.heal(12)
        self._play_sfx("eat")
        self._set_message(f"Voce comeu. Fome +{hunger_restored}, vida +{healed_amount}.")

    def _handle_crafting(self, craft_pressed: bool) -> None:
        if not craft_pressed:
            return

        recipe_name = self._get_selected_recipe()
        success, message = self.crafting.craft(recipe_name, self.inventory)
        self._play_sfx("craft_success" if success else "ui_denied")
        if success:
            recipe = self.crafting.get_recipe(recipe_name)
            self._add_item_popups({recipe_name: int(recipe.get("amount", 1)) if recipe else 1})
        else:
            self._set_message(message)

    def _handle_crafting_click(self, mouse_pos: Tuple[int, int]) -> None:
        if self._crafting_close_button_rect().collidepoint(mouse_pos):
            self._show_crafting = False
            self._play_sfx("ui_close")
            return

        for recipe_name, recipe_rect in self._crafting_recipe_rects():
            if not recipe_rect.collidepoint(mouse_pos):
                continue

            recipe = self.crafting.get_recipe(recipe_name)
            if recipe is None:
                return
            recipe_cost = recipe.get("cost", {})
            if not self.inventory.has_items(recipe_cost):
                self._play_sfx("ui_denied")
                self._set_message("Recursos insuficientes.")
                return

            success, message = self.crafting.craft(recipe_name, self.inventory)
            self._play_sfx("craft_success" if success else "ui_denied")
            if success:
                self._add_item_popups({recipe_name: int(recipe.get("amount", 1))})
            else:
                self._set_message(message)
            return

    def _set_message(self, text: str) -> None:
        self._message = text
        self._message_timer = 2.8

    def update_game_state(
        self,
        direction: pygame.Vector2,
        running: bool,
        craft_pressed: bool,
        search_pressed: bool,
        attack_pressed: bool,
        heal_pressed: bool,
        dt: float,
    ) -> None:
        if self._game_over:
            self.player.update(dt)
            return

        self._attack_timer = max(0.0, self._attack_timer - dt)
        self._transition_cooldown = max(0.0, self._transition_cooldown - dt)
        self._update_difficulty(dt)
        self._update_survival(dt)
        self.player.move(direction, dt, running)
        self.player.clamp_to_area(WORLD_WIDTH, WORLD_HEIGHT)
        self._resolve_player_collisions()
        if self._gamepad_aim_vector.length_squared() > 0.04:
            aim_target = pygame.Vector2(self.player.player_position) + self._gamepad_aim_vector.normalize() * 120
            self.player.aim_at(aim_target)
        else:
            self.player.aim_at(self.screen_to_world(self._window_to_screen(pygame.mouse.get_pos())))
        self.player.update(dt)

        self._update_spawns(dt)
        self._update_zombies(dt)
        self._update_shot_impacts(dt)
        self._update_floating_popups(dt)
        transition_used = self._handle_map_transitions(search_pressed)
        if not transition_used:
            self._handle_search(search_pressed)
        self._handle_attack(attack_pressed)
        self._handle_heal(heal_pressed)
        self._handle_crafting(craft_pressed)

        if self.player.is_dead():
            self._game_over = True
            self._set_message("Game Over - pressione ESC")

    def render_menu(self, dt: float) -> None:
        if self._menu_message_timer > 0:
            self._menu_message_timer = max(0.0, self._menu_message_timer - dt)

        self._update_camera()
        self.screen.fill(BG_COLOR)
        self._draw_world_scene()
        self._draw_menu_background_overlay()

        if self._screen_state == "saves":
            self._draw_saves_menu()
        elif self._screen_state == "settings":
            self._draw_settings_menu()
        else:
            self._draw_main_menu()

        if self._menu_message_timer > 0:
            text = self.font.render(self._menu_message, True, PALETTE["accent"])
            self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT - 28)))

        self._draw_gamepad_debug()

        scaled_frame = pygame.transform.smoothscale(self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.window.blit(scaled_frame, (0, 0))
        pygame.display.flip()

    def _draw_menu_background_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 13, 176))
        self.screen.blit(overlay, (0, 0))

    def _draw_main_menu(self) -> None:
        self._draw_menu_title()
        mouse_pos = self._window_to_screen(pygame.mouse.get_pos())
        save_available = save_exists(str(SAVE_GAME_PATH)) or (self._has_started_game and not self._game_over)
        self._clamp_menu_selection()
        for index, (action, sprite_base, rect) in enumerate(self._main_menu_button_rects()):
            pressed = self._menu_pressed_button == action
            sprite_state = "Pressed" if pressed else "Not-Pressed"
            sprite = _load_ui_sprite(f"{sprite_base}_{sprite_state}.png", 3)
            if action == "continue_game" and not save_available:
                sprite = _dim_sprite(sprite)
            sprite_rect = sprite.get_rect(center=(rect.centerx, rect.centery + (2 if pressed else 0)))
            if rect.collidepoint(mouse_pos) or index == self._menu_selected_index:
                pygame.draw.rect(self.screen, PALETTE["accent"], rect.inflate(12, 8), 2)
            self.screen.blit(sprite, sprite_rect)

    def _draw_menu_title(self) -> None:
        ticks = pygame.time.get_ticks() / 1000.0
        bob = int(2 * pygame.math.Vector2(0, 1).rotate(ticks * 55).y)
        title = "RUA MORTA"
        shadow = self.title_font.render(title, True, (22, 24, 29))
        accent = self.title_font.render(title, True, PALETTE["accent"])
        text = self.title_font.render(title, True, PALETTE["text"])
        title_rect = text.get_rect(center=(WIDTH // 2, 70 + bob))
        self.screen.blit(shadow, title_rect.move(5, 5))
        self.screen.blit(accent, title_rect.move(-2, 2))
        self.screen.blit(text, title_rect)
        if int(ticks * 4) % 9 == 0:
            glitch = self.title_font.render(title, True, PALETTE["danger"])
            self.screen.blit(glitch, title_rect.move(3, -2), special_flags=pygame.BLEND_RGBA_ADD)

        subtitle = self.small_font.render("SOBREVIVENCIA ZUMBI", True, PALETTE["text_soft"])
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 118)))

    def _draw_menu_panel(self, rect: pygame.Rect) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 232), panel.get_rect())
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 2)
        pygame.draw.rect(panel, (28, 34, 37, 210), panel.get_rect().inflate(-10, -10), 1)
        self.screen.blit(panel, rect)

    def _draw_saves_menu(self) -> None:
        panel_rect = pygame.Rect(0, 0, 510, 390 if self._has_started_game else 320)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2 + 18)
        self._draw_menu_panel(panel_rect)
        title = self.menu_font.render("SAVES", True, PALETTE["text"])
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, panel_rect.y + 38)))

        slot_rect = pygame.Rect(panel_rect.x + 54, panel_rect.y + 78, panel_rect.width - 108, 72)
        pygame.draw.rect(self.screen, (43, 46, 48), slot_rect)
        pygame.draw.rect(self.screen, PALETTE["panel_edge"], slot_rect, 2)
        status = "SAVE ENCONTRADO" if save_exists(str(SAVE_GAME_PATH)) else "SLOT VAZIO"
        slot_title = self.font.render("SLOT 1", True, PALETTE["accent"])
        slot_status = self.small_font.render(status, True, PALETTE["text_soft"])
        self.screen.blit(slot_title, (slot_rect.x + 18, slot_rect.y + 14))
        self.screen.blit(slot_status, (slot_rect.x + 18, slot_rect.y + 42))

        mouse_pos = self._window_to_screen(pygame.mouse.get_pos())
        self._clamp_menu_selection()
        for index, (action, label, rect) in enumerate(self._saves_menu_button_rects()):
            enabled = action != "load" or save_exists(str(SAVE_GAME_PATH))
            self._draw_blank_menu_button(rect, label, rect.collidepoint(mouse_pos) or index == self._menu_selected_index, enabled)

    def _draw_settings_menu(self) -> None:
        panel_rect = pygame.Rect(0, 0, 560, 400)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2 + 18)
        self._draw_menu_panel(panel_rect)
        title = self.menu_font.render("CONFIGURACOES", True, PALETTE["text"])
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, panel_rect.y + 42)))

        for key, label, rect in self._settings_slider_rects():
            value = self._settings.get(key, 0)
            selected = key == self._current_menu_actions()[self._menu_selected_index % len(self._current_menu_actions())]
            label_text = self.font.render(label, True, PALETTE["text"])
            value_text = self.font.render(f"{value:03d}", True, PALETTE["accent"])
            if selected:
                pygame.draw.rect(self.screen, PALETTE["accent"], rect.inflate(150, 28), 2)
            self.screen.blit(label_text, (rect.x - 112, rect.y - 7))
            self.screen.blit(value_text, (rect.right + 24, rect.y - 7))
            pygame.draw.rect(self.screen, (37, 41, 42), rect)
            pygame.draw.rect(self.screen, PALETTE["panel_edge"], rect, 2)
            fill_rect = rect.copy()
            fill_rect.width = int(rect.width * (value / 100))
            pygame.draw.rect(self.screen, PALETTE["accent"], fill_rect.inflate(-4, -4))
            knob_x = rect.left + int(rect.width * (value / 100))
            knob_rect = pygame.Rect(0, 0, 12, 28)
            knob_rect.center = (knob_x, rect.centery)
            pygame.draw.rect(self.screen, PALETTE["text"], knob_rect)
            pygame.draw.rect(self.screen, PALETTE["bg_deep"], knob_rect, 2)

        mouse_pos = self._window_to_screen(pygame.mouse.get_pos())
        back_rect = self._settings_back_button_rect()
        back_selected = self._current_menu_actions()[self._menu_selected_index % len(self._current_menu_actions())] == "back"
        self._draw_blank_menu_button(back_rect, "VOLTAR", back_rect.collidepoint(mouse_pos) or back_selected, True)

    def _draw_blank_menu_button(self, rect: pygame.Rect, label: str, hover: bool, enabled: bool = True) -> None:
        pressed = self._menu_pressed_button == label.lower()
        sprite_name = "Blank_Pressed.png" if pressed else "Blank_Not-Pressed.png"
        sprite = _load_ui_sprite(sprite_name, 3)
        if not enabled:
            sprite = _dim_sprite(sprite)
        sprite_rect = sprite.get_rect(center=(rect.centerx, rect.centery + (2 if pressed else 0)))
        if hover and enabled:
            pygame.draw.rect(self.screen, PALETTE["accent"], rect.inflate(10, 8), 2)
        self.screen.blit(sprite, sprite_rect)
        color = PALETTE["text"] if enabled else (112, 116, 116)
        text = self.menu_font.render(label, True, color)
        self.screen.blit(text, text.get_rect(center=sprite_rect.center))

    def _resolve_player_collisions(self) -> None:
        if not self.collision_rects:
            return

        position = pygame.Vector2(self.player.player_position)
        player_rect = self._entity_collision_rect(position, self.player.radius)

        for rect in self.collision_rects:
            if not player_rect.colliderect(rect):
                continue

            overlap_left = player_rect.right - rect.left
            overlap_right = rect.right - player_rect.left
            overlap_top = player_rect.bottom - rect.top
            overlap_bottom = rect.bottom - player_rect.top
            smallest = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

            if smallest == overlap_left:
                position.x -= overlap_left
            elif smallest == overlap_right:
                position.x += overlap_right
            elif smallest == overlap_top:
                position.y -= overlap_top
            else:
                position.y += overlap_bottom

            player_rect = self._entity_collision_rect(position, self.player.radius)

        radius = self.player.radius
        position.x = max(radius, min(WORLD_WIDTH - radius, position.x))
        position.y = max(radius, min(WORLD_HEIGHT - radius, position.y))
        self.player.set_position((position.x, position.y))

    def _player_collision_rect(self, position: pygame.Vector2) -> pygame.Rect:
        return self._entity_collision_rect(position, self.player.radius)

    def _entity_collision_rect(self, position: pygame.Vector2, radius: int) -> pygame.Rect:
        rect = pygame.Rect(0, 0, radius * 2, max(8, radius))
        rect.midbottom = (round(position.x), round(position.y + radius))
        return rect

    def _position_hits_obstacle(self, position: pygame.Vector2, radius: int) -> bool:
        if position.x < radius or position.y < radius or position.x > WORLD_WIDTH - radius or position.y > WORLD_HEIGHT - radius:
            return True
        collision_rect = self._entity_collision_rect(position, radius)
        return any(collision_rect.colliderect(rect) for rect in self.collision_rects)

    def _movement_crosses_obstacle(self, start: pygame.Vector2, end: pygame.Vector2, radius: int) -> bool:
        movement = end - start
        distance = movement.length()
        if distance <= 0.01:
            return False

        step_size = max(4.0, radius * 0.5)
        steps = max(1, int(distance / step_size))
        for step in range(1, steps + 1):
            if self._position_hits_obstacle(start.lerp(end, step / steps), radius):
                return True
        return False

    def _push_entity_out_of_obstacles(self, position: pygame.Vector2, radius: int) -> pygame.Vector2:
        collision_rect = self._entity_collision_rect(position, radius)
        for rect in self.collision_rects:
            if not collision_rect.colliderect(rect):
                continue

            overlap_left = collision_rect.right - rect.left
            overlap_right = rect.right - collision_rect.left
            overlap_top = collision_rect.bottom - rect.top
            overlap_bottom = rect.bottom - collision_rect.top
            smallest = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

            if smallest == overlap_left:
                position.x -= overlap_left
            elif smallest == overlap_right:
                position.x += overlap_right
            elif smallest == overlap_top:
                position.y -= overlap_top
            else:
                position.y += overlap_bottom

            collision_rect = self._entity_collision_rect(position, radius)

        position.x = max(radius, min(WORLD_WIDTH - radius, position.x))
        position.y = max(radius, min(WORLD_HEIGHT - radius, position.y))
        return position

    def _resolve_zombie_obstacles(self, zombie: Zombie, old_position: pygame.Vector2, dt: float) -> None:
        if not self.collision_rects or zombie.is_dying():
            return
        if not self._position_hits_obstacle(zombie.position, zombie.radius) and not self._movement_crosses_obstacle(
            old_position,
            zombie.position,
            zombie.radius,
        ):
            return

        attempted_delta = zombie.position - old_position
        step_distance = max(attempted_delta.length(), zombie.speed * dt, 1.0)
        if attempted_delta.length_squared() > 0.01:
            base_direction = attempted_delta.normalize()
        else:
            target_delta = pygame.Vector2(self.player.player_position) - old_position
            base_direction = target_delta.normalize() if target_delta.length_squared() > 0 else pygame.Vector2(1, 0)

        best_position = old_position.copy()
        best_score = float("inf")
        target = pygame.Vector2(self.player.player_position)
        for angle in ZOMBIE_AVOIDANCE_ANGLES:
            candidate = old_position + (base_direction.rotate(angle) * step_distance)
            candidate.x = max(zombie.radius, min(WORLD_WIDTH - zombie.radius, candidate.x))
            candidate.y = max(zombie.radius, min(WORLD_HEIGHT - zombie.radius, candidate.y))
            if self._position_hits_obstacle(candidate, zombie.radius):
                continue
            score = candidate.distance_to(target) + abs(angle) * 0.35
            if score < best_score:
                best_score = score
                best_position = candidate

        if best_score < float("inf"):
            zombie.position = best_position
        else:
            zombie.position = self._push_entity_out_of_obstacles(old_position.copy(), zombie.radius)

    def _separate_zombies(self, dt: float) -> None:
        living_zombies = [zombie for zombie in self.zombies if not zombie.is_dying()]
        if len(living_zombies) < 2:
            return

        max_push = ZOMBIE_SEPARATION_STRENGTH * dt
        for _ in range(ZOMBIE_SEPARATION_ITERATIONS):
            for index, zombie in enumerate(living_zombies):
                for other in living_zombies[index + 1:]:
                    offset = zombie.position - other.position
                    distance_sq = offset.length_squared()
                    min_distance = zombie.radius + other.radius + 10
                    if distance_sq <= 0.01:
                        offset = pygame.Vector2(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
                        if offset.length_squared() <= 0.01:
                            offset = pygame.Vector2(1, 0)
                        distance_sq = offset.length_squared()
                    if distance_sq >= min_distance * min_distance:
                        continue

                    distance = distance_sq ** 0.5
                    direction = offset / distance
                    push = min(max_push, (min_distance - distance) * 0.5)
                    zombie.position += direction * push
                    other.position -= direction * push
                    if self._position_hits_obstacle(zombie.position, zombie.radius):
                        zombie.position = self._push_entity_out_of_obstacles(zombie.position, zombie.radius)
                    if self._position_hits_obstacle(other.position, other.radius):
                        other.position = self._push_entity_out_of_obstacles(other.position, other.radius)

    def render(self, dt: float) -> None:
        self._update_camera()
        self.screen.fill(BG_COLOR)
        self._draw_world_scene()

        self._draw_crosshair()
        self._draw_interact_hint()
        self._draw_ui()
        self._draw_damage_overlay()
        self._draw_gamepad_debug()

        if self._message_timer > 0:
            self._message_timer = max(0.0, self._message_timer - dt)

        scaled_frame = pygame.transform.smoothscale(self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.window.blit(scaled_frame, (0, 0))
        pygame.display.flip()

    def _draw_world_scene(self) -> None:
        self._draw_ground()

        world_drawables: List[Tuple[float, int, object]] = []
        for decoration in self.decorations:
            world_drawables.append((decoration.position.y, 0, decoration))
        for node in self.nodes:
            world_drawables.append((node.position.y, 2, node))
        for zombie in self.zombies:
            world_drawables.append((zombie.position.y, 3, zombie))
        for impact in self.shot_impacts:
            world_drawables.append((impact.position.y, 5, impact))
        world_drawables.append((self.player.player_position[1], 4, self.player))

        for _, _, drawable in sorted(world_drawables, key=lambda item: (item[0], item[1])):
            drawable.draw(self.screen, self._camera)

        for popup in self._floating_popups:
            popup.draw(self.screen, self._camera, self.font)

    def _update_camera(self) -> None:
        player_pos = pygame.Vector2(self.player.player_position)
        if WORLD_WIDTH <= WIDTH:
            self._camera.x = (WORLD_WIDTH - WIDTH) / 2
        else:
            self._camera.x = max(0, min(WORLD_WIDTH - WIDTH, player_pos.x - (WIDTH / 2)))
        if WORLD_HEIGHT <= HEIGHT:
            self._camera.y = (WORLD_HEIGHT - HEIGHT) / 2
        else:
            max_camera_y = WORLD_HEIGHT - HEIGHT + BOTTOM_WORLD_PADDING
            self._camera.y = max(0, min(max_camera_y, player_pos.y - (HEIGHT / 2)))

    def screen_to_world(self, screen_position: Tuple[int, int]) -> pygame.Vector2:
        return pygame.Vector2(screen_position) + self._camera

    def _window_to_screen(self, window_position: Tuple[int, int]) -> Tuple[int, int]:
        scale_x = WIDTH / WINDOW_WIDTH
        scale_y = HEIGHT / WINDOW_HEIGHT
        return (
            int(window_position[0] * scale_x),
            int(window_position[1] * scale_y),
        )

    def _draw_ground(self) -> None:
        if self.tile_map is not None:
            self.tile_map.draw(self.screen, self._camera)
            return

        tile_size = 64
        for x in range(0, WORLD_WIDTH, tile_size):
            for y in range(0, WORLD_HEIGHT, tile_size):
                rect = pygame.Rect(x - self._camera.x, y - self._camera.y, tile_size, tile_size)
                if rect.right < 0 or rect.left > WIDTH or rect.bottom < 0 or rect.top > HEIGHT:
                    continue
                tile_color = PALETTE["ground_a"] if (x // tile_size + y // tile_size) % 2 == 0 else PALETTE["ground_b"]
                pygame.draw.rect(self.screen, tile_color, rect)
                pygame.draw.rect(self.screen, PALETTE["bg_deep"], rect, 1)

    def _draw_crosshair(self) -> None:
        if self._gamepad_aim_vector.length_squared() > 0.04:
            world_pos = pygame.Vector2(self.player.player_position) + self._gamepad_aim_vector.normalize() * 120
            crosshair_pos = world_pos - self._camera
        else:
            crosshair_pos = pygame.Vector2(self._window_to_screen(pygame.mouse.get_pos()))
        pygame.draw.circle(self.screen, (220, 220, 220), (round(crosshair_pos.x), round(crosshair_pos.y)), 6, 1)

    def _draw_interact_hint(self) -> None:
        hint_position: pygame.Vector2 | None = None
        corpse = self._find_nearest_corpse()
        node = self._find_nearest_node()
        door = None if self._inside_interior else self._find_nearest_trigger(self.doors, DOOR_RANGE)
        exit_trigger = self._find_nearest_trigger(self.exits, EXIT_RANGE)
        near_interior_exit = False
        if self._inside_interior and self._interior_exit is not None:
            near_interior_exit = (
                self._interior_exit.position.distance_to(pygame.Vector2(self.player.player_position))
                <= self._interior_exit.radius
            )

        if near_interior_exit:
            hint_position = self._interior_exit.position if self._interior_exit is not None else None
        elif door is not None:
            hint_position = door.position
        elif exit_trigger is not None:
            hint_position = exit_trigger.position
        elif corpse is not None:
            hint_position = corpse.position
        elif node is not None:
            hint_position = node.position

        if hint_position is None:
            return

        screen_pos = hint_position - self._camera + pygame.Vector2(0, -34)
        text = self.menu_font.render("E", True, PALETTE["accent"])
        self.screen.blit(text, text.get_rect(center=(round(screen_pos.x), round(screen_pos.y))))

    def _draw_damage_overlay(self) -> None:
        if self.player.hit_flash_timer <= 0 and self.player.heal_flash_timer <= 0:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self.player.hit_flash_timer > 0:
            alpha = int(120 * (self.player.hit_flash_timer / 0.22))
            overlay.fill((*PALETTE["danger"], alpha))
        else:
            alpha = int(90 * (self.player.heal_flash_timer / 0.25))
            overlay.fill((62, 136, 90, alpha))
        self.screen.blit(overlay, (0, 0))

    def _draw_gamepad_debug(self) -> None:
        if not self._show_gamepad_debug:
            return

        gamepad = self._get_gamepad()
        if gamepad is None:
            lines = ["Controle: nenhum", "F2 ou botao PS/touchpad fecha"]
        else:
            try:
                name = gamepad.get_name()
            except (AttributeError, pygame.error):
                name = "controle"
            axis_count = self._gamepad_axis_count(gamepad)
            axes = [f"{index}:{self._gamepad_axis(gamepad, index):+.2f}" for index in range(axis_count)]
            buttons = sorted(self._poll_gamepad_buttons(gamepad))
            mapping = "SDL" if self._uses_sdl_gamepad_mapping(gamepad) else "raw/web"
            right_pair = self._right_stick_axes if self._right_stick_axes is not None else "auto"
            lines = [
                f"Controle: {name} ({mapping})",
                "Eixos: " + " ".join(axes),
                "Botoes: " + (" ".join(str(button) for button in buttons) if buttons else "-"),
                f"Mira dir: {right_pair}  vetor {self._gamepad_aim_vector.x:+.2f},{self._gamepad_aim_vector.y:+.2f}",
                "F2 ou botao PS/touchpad fecha",
            ]

        padding = 10
        line_height = self.small_font.get_height() + 4
        width = max(self.small_font.size(line)[0] for line in lines) + padding * 2
        height = line_height * len(lines) + padding * 2
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((7, 10, 12, 210))
        pygame.draw.rect(panel, PALETTE["accent"], panel.get_rect(), 1)
        self.screen.blit(panel, (12, 92))
        for index, line in enumerate(lines):
            text = self.small_font.render(line, True, PALETTE["text"])
            self.screen.blit(text, (12 + padding, 92 + padding + index * line_height))

    def _draw_ui(self) -> None:
        self._draw_icon_meter(
            18,
            18,
            self.player.player_health / self.player.max_health,
            "Heart_Full.png",
            "Heart_Half.png",
            "Heart_Empty.png",
        )
        self._draw_icon_meter(
            18,
            48,
            self.player.player_hunger / self.player.max_hunger,
            "Hunger_Full.png",
            "Hunger_Half.png",
            "Hunger_Empty.png",
        )

        self._draw_quick_access_bar()
        self._draw_ammo_indicator()

        if self._show_inventory:
            self._draw_inventory_panel()
        if self._show_crafting:
            self._draw_crafting_panel()

    def _draw_quick_access_bar(self) -> None:
        scale = 3
        bar = _load_ui_sprite("Quick-Access-Inventory.png", scale)
        bar_rect = self._quick_access_bar_rect()
        self.screen.blit(bar, bar_rect)

        for index, item_name in enumerate(self._quick_slots):
            slot_rect = self._quick_slot_rect(index)
            display_item = self._display_item_for_slot(item_name)
            quantity = self._slot_quantity(item_name)
            available = quantity > 0
            self._draw_slot_item(slot_rect, display_item, quantity, available)

            if index == self._selected_quick_slot:
                pygame.draw.rect(self.screen, PALETTE["accent"], slot_rect.inflate(5, 5), 2, border_radius=2)

    def _quick_access_bar_rect(self) -> pygame.Rect:
        return _load_ui_sprite("Quick-Access-Inventory.png", 3).get_rect(center=(WIDTH // 2, HEIGHT - 54))

    def _quick_slot_rect(self, index: int) -> pygame.Rect:
        scale = 3
        bar_rect = self._quick_access_bar_rect()
        slot_size = 19 * scale
        slot_pitch = 21 * scale
        return pygame.Rect(
            round(bar_rect.x + scale + index * slot_pitch),
            round(bar_rect.y),
            slot_size,
            slot_size,
        )

    def _quick_slot_index_at(self, mouse_pos: Tuple[int, int]) -> int | None:
        for index in range(len(self._quick_slots)):
            if self._quick_slot_rect(index).collidepoint(mouse_pos):
                return index
        return None

    def _draw_ammo_indicator(self) -> None:
        weapon_name = self.player.current_weapon
        stats = WEAPONS.get(weapon_name, WEAPONS["maos"])
        ammo_item = str(stats.get("ammo_item", "balas"))
        ammo_count = self.inventory.get_quantity(ammo_item)
        weapon_family = str(stats.get("family", weapon_name))
        if weapon_family == "escopeta":
            bullet_name = "Shotgun-Bullet.png"
            empty_name = "Shotgun-Bullet_Empty.png"
            visible_rounds = int(stats.get("visible_rounds", 4))
        elif weapon_family == "pistola":
            bullet_name = "Pistol-Bullet.png"
            empty_name = "Pistol-Bullet_Empty.png"
            visible_rounds = int(stats.get("visible_rounds", 6))
        else:
            bullet_name = "Gun-Bullet.png"
            empty_name = "Gun-Bullet_Empty.png"
            visible_rounds = int(stats.get("visible_rounds", 6))

        bullet = _load_ui_sprite(bullet_name, 2)
        empty_bullet = _load_ui_sprite(empty_name, 2)
        projectile_color = stats.get("projectile_color")
        if isinstance(projectile_color, tuple) and ammo_item != "balas":
            bullet = _tint_sprite(bullet, projectile_color)
        icon = _load_ui_sprite(ITEM_ICONS.get(ammo_item, "Icon_Bullet-box_Red.png"), 3)
        tint = ITEM_TINTS.get(ammo_item)
        if tint is not None:
            icon = _tint_sprite(icon, tint)
        x = WIDTH - 164
        y = HEIGHT - 86
        self.screen.blit(icon, icon.get_rect(midleft=(x, y + 18)))

        count_text = self.font.render(str(ammo_count), True, PALETTE["text"])
        if isinstance(projectile_color, tuple) and ammo_item != "balas":
            count_text = self.font.render(str(ammo_count), True, projectile_color)
        self.screen.blit(count_text, count_text.get_rect(midleft=(x + 48, y + 18)))

        bullet_x = x + 94
        for index in range(visible_rounds):
            sprite = bullet if index < min(ammo_count, visible_rounds) else empty_bullet
            bullet_pos = (bullet_x + index * (sprite.get_width() + 4), y)
            self.screen.blit(sprite, bullet_pos)
            if isinstance(projectile_color, tuple) and ammo_item != "balas":
                marker_rect = pygame.Rect(bullet_pos[0] + 2, bullet_pos[1] + sprite.get_height() - 4, sprite.get_width() - 4, 3)
                pygame.draw.rect(self.screen, projectile_color, marker_rect)

    def _draw_inventory_panel(self) -> None:
        panel_scale = 4
        cell_scale = 3
        panel = _load_ui_sprite("Inventory_1_Scrollbar.png", panel_scale)
        cell = _load_ui_sprite("Inventory-Cell.png", cell_scale)
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", panel_scale)
        panel_rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(panel, panel_rect)

        title = self.font.render("INVENTARIO", True, PALETTE["text"])
        self.screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))
        self.screen.blit(close_button, self._inventory_close_button_rect())

        visible_items = self._visible_inventory_items()
        for index, slot_rect in enumerate(self._inventory_item_rects()):
            self.screen.blit(cell, slot_rect)
            if index >= len(visible_items):
                continue
            item_name = visible_items[index]
            self._draw_slot_item(slot_rect, item_name, self.inventory.get_quantity(item_name), True)

    def _visible_inventory_items(self) -> List[str]:
        return [item_name for item_name in INVENTORY_ITEM_ORDER if self.inventory.get_quantity(item_name) > 0]

    def _inventory_item_rects(self) -> List[pygame.Rect]:
        panel_scale = 4
        cell_scale = 3
        panel = _load_ui_sprite("Inventory_1_Scrollbar.png", panel_scale)
        cell = _load_ui_sprite("Inventory-Cell.png", cell_scale)
        panel_rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        columns = 5
        rows = 4
        cell_width, cell_height = cell.get_size()
        grid_width = columns * cell_width
        grid_height = rows * cell_height
        gap_x = max(8, (panel_rect.width - grid_width) // (columns + 1))
        gap_y = max(6, (panel_rect.height - grid_height - 62) // (rows + 1))
        start_x = panel_rect.x + gap_x
        start_y = panel_rect.y + 58 + gap_y

        rects: List[pygame.Rect] = []
        for index in range(columns * rows):
            col = index % columns
            row = index // columns
            rects.append(
                pygame.Rect(
                    start_x + col * (cell_width + gap_x),
                    start_y + row * (cell_height + gap_y),
                    cell_width,
                    cell_height,
                )
            )
        return rects

    def _inventory_item_at(self, mouse_pos: Tuple[int, int]) -> str | None:
        visible_items = self._visible_inventory_items()
        for index, rect in enumerate(self._inventory_item_rects()):
            if index < len(visible_items) and rect.collidepoint(mouse_pos):
                return visible_items[index]
        return None

    def _draw_slot_item(self, slot_rect: pygame.Rect, item_name: str, quantity: int, available: bool) -> None:
        text_color = PALETTE["text"] if available else (115, 118, 118)
        icon_name = ITEM_ICONS.get(item_name)
        if icon_name is not None:
            icon_scale = 3 if slot_rect.width <= 64 else 4
            icon = _load_ui_sprite(icon_name, icon_scale)
            tint = ITEM_TINTS.get(item_name)
            if tint is not None:
                icon = _tint_sprite(icon, tint)
            icon_rect = icon.get_rect(center=slot_rect.center)
            self.screen.blit(icon, icon_rect)
        else:
            label = ITEM_LABELS.get(item_name, item_name[:3]).upper()
            label_text = self.small_font.render(label, True, text_color)
            self.screen.blit(label_text, label_text.get_rect(center=slot_rect.center))

        if quantity > 1:
            qty_text = self.small_font.render(str(quantity), True, text_color)
            qty_rect = qty_text.get_rect(topright=(slot_rect.right - 5, slot_rect.top + 3))
            self.screen.blit(qty_text, qty_rect)
        if not available:
            overlay = pygame.Surface(slot_rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 95))
            self.screen.blit(overlay, slot_rect)

    def _inventory_close_button_rect(self) -> pygame.Rect:
        panel = _load_ui_sprite("Inventory_1_Scrollbar.png", 4)
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", 4)
        panel_rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        return close_button.get_rect(topright=(panel_rect.right - 18, panel_rect.y + 16))

    def _crafting_panel_rect(self) -> pygame.Rect:
        panel = _load_ui_sprite("Crafting-main-menu.png", 5)
        return panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    def _crafting_close_button_rect(self) -> pygame.Rect:
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", 4)
        panel_rect = self._crafting_panel_rect()
        return close_button.get_rect(topright=(panel_rect.right - 16, panel_rect.y + 14))

    def _crafting_recipe_rects(self) -> List[Tuple[str, pygame.Rect]]:
        panel_rect = self._crafting_panel_rect()
        recipe_names = self._available_recipe_names()
        rects: List[Tuple[str, pygame.Rect]] = []
        row_width = panel_rect.width - 52
        available_height = max(120, panel_rect.height - 92)
        gap = 8
        row_height = min(86, max(48, (available_height - max(0, len(recipe_names) - 1) * gap) // max(1, len(recipe_names))))
        start_y = panel_rect.y + 62
        for index, recipe_name in enumerate(recipe_names):
            rect = pygame.Rect(
                panel_rect.x + 26,
                start_y + index * (row_height + gap),
                row_width,
                row_height,
            )
            rects.append((recipe_name, rect))
        return rects

    def _draw_crafting_panel(self) -> None:
        panel = _load_ui_sprite("Crafting-main-menu.png", 5)
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", 4)
        panel_rect = self._crafting_panel_rect()
        self.screen.blit(panel, panel_rect)
        self.screen.blit(close_button, self._crafting_close_button_rect())

        title = self.font.render("CRAFTING", True, PALETTE["text"])
        self.screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))

        recipe_names = self._available_recipe_names()
        cell_scale = 2 if len(recipe_names) > 4 else 3
        cell = _load_ui_sprite("Crafting-cell.png", cell_scale)
        plus = _load_ui_sprite("Crafting_Plus.png", cell_scale)
        equal = _load_ui_sprite("Crafting_Equal.png", cell_scale)

        for recipe_name, row_rect in self._crafting_recipe_rects():
            recipe = self.crafting.get_recipe(recipe_name)
            if recipe is None:
                continue
            recipe_cost = dict(recipe.get("cost", {}))
            craftable = self.inventory.has_items(recipe_cost)

            row_surface = pygame.Surface(row_rect.size, pygame.SRCALPHA)
            input_items = list(recipe_cost.items())[:2]
            cell_y = (row_rect.height - cell.get_height()) // 2
            cursor_x = 12
            for index, (item_name, amount) in enumerate(input_items):
                cell_rect = pygame.Rect(cursor_x, cell_y, cell.get_width(), cell.get_height())
                row_surface.blit(cell, cell_rect)
                self._draw_crafting_item_on(row_surface, cell_rect, item_name, amount, self.inventory.get_quantity(item_name) >= amount)
                cursor_x += cell.get_width() + 9
                if index < len(input_items) - 1:
                    row_surface.blit(plus, plus.get_rect(center=(cursor_x + plus.get_width() // 2, row_rect.height // 2)))
                    cursor_x += plus.get_width() + 9

            row_surface.blit(equal, equal.get_rect(center=(cursor_x + equal.get_width() // 2, row_rect.height // 2)))
            cursor_x += equal.get_width() + 9
            result_rect = pygame.Rect(cursor_x, cell_y, cell.get_width(), cell.get_height())
            row_surface.blit(cell, result_rect)
            self._draw_crafting_item_on(row_surface, result_rect, recipe_name, int(recipe.get("amount", 1)), craftable)

            if not craftable:
                row_surface.fill((80, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
                overlay = pygame.Surface(row_surface.get_size(), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 105))
                row_surface.blit(overlay, (0, 0))

            self.screen.blit(row_surface, row_rect)
            if craftable:
                pygame.draw.rect(self.screen, PALETTE["accent"], row_rect, 2, border_radius=4)

    def _draw_crafting_item_on(
        self,
        surface: pygame.Surface,
        cell_rect: pygame.Rect,
        item_name: str,
        amount: int,
        available: bool,
    ) -> None:
        icon_name = ITEM_ICONS.get(item_name)
        if icon_name is not None:
            icon = _load_ui_sprite(icon_name, 2 if cell_rect.width <= 48 else 3)
            tint = ITEM_TINTS.get(item_name)
            if tint is not None:
                icon = _tint_sprite(icon, tint)
            if not available:
                icon = _dim_sprite(icon)
            surface.blit(icon, icon.get_rect(center=(cell_rect.centerx, cell_rect.centery - 5)))
        else:
            label = ITEM_LABELS.get(item_name, item_name[:3]).upper()
            color = PALETTE["text"] if available else (125, 125, 125)
            label_text = self.small_font.render(label, True, color)
            surface.blit(label_text, label_text.get_rect(center=(cell_rect.centerx, cell_rect.centery - 5)))

        if amount > 1:
            color = PALETTE["text"] if available else (125, 125, 125)
            amount_text = self.small_font.render(str(amount), True, color)
            surface.blit(amount_text, amount_text.get_rect(bottomright=(cell_rect.right - 4, cell_rect.bottom - 4)))

    def _draw_icon_meter(
        self,
        x: int,
        y: int,
        ratio: float,
        full_icon_name: str,
        half_icon_name: str,
        empty_icon_name: str,
        max_icons: int = 5,
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        filled = ratio * max_icons
        full_icon = _load_ui_sprite(full_icon_name, 2)
        half_icon = _load_ui_sprite(half_icon_name, 2)
        empty_icon = _load_ui_sprite(empty_icon_name, 2)
        spacing = full_icon.get_width() + 8

        for index in range(max_icons):
            value = filled - index
            if value >= 0.75:
                icon = full_icon
            elif value >= 0.25:
                icon = half_icon
            else:
                icon = empty_icon
            self.screen.blit(icon, (x + index * spacing, y))

    def _available_recipe_names(self) -> List[str]:
        names = self.crafting.get_recipe_names(self.inventory)
        if names and self._selected_recipe_index >= len(names):
            self._selected_recipe_index = 0
        self._recipe_names = names
        return names

    def _get_selected_recipe(self) -> str:
        recipe_names = self._available_recipe_names()
        if not recipe_names:
            return "taco"
        return recipe_names[self._selected_recipe_index]

    def _cycle_recipe(self) -> None:
        recipe_names = self._available_recipe_names()
        if not recipe_names:
            return
        self._selected_recipe_index = (self._selected_recipe_index + 1) % len(recipe_names)
        self._play_sfx("inventory_move")

    def _cycle_quick_slot(self, direction: int) -> None:
        if not self._quick_slots or direction == 0:
            return
        self._select_quick_slot((self._selected_quick_slot + direction) % len(self._quick_slots))

    def _select_quick_slot(self, index: int) -> None:
        if not 0 <= index < len(self._quick_slots):
            return
        cycle_variant = self._selected_quick_slot == index
        self._selected_quick_slot = index
        item_name = self._quick_slots[index]
        if item_name in WEAPON_ITEMS or item_name in WEAPON_FAMILIES:
            self._equip_weapon_slot(item_name, cycle_variant)
            return
        self._play_sfx("inventory_move")

    def _assign_quick_slot_item(self, item_name: str) -> None:
        if item_name not in WEAPON_ITEMS and item_name not in CONSUMABLE_ITEMS:
            self._play_sfx("ui_denied")
            self._set_message("Esse item fica no inventario.")
            return
        if self.inventory.get_quantity(item_name) <= 0:
            self._play_sfx("ui_denied")
            return

        self._quick_slots[self._selected_quick_slot] = item_name
        self._play_sfx("inventory_move")
        self._set_message(f"{ITEM_LABELS.get(item_name, item_name)} no atalho {self._selected_quick_slot + 1}.")
        if item_name in WEAPON_ITEMS:
            self._equip_weapon(item_name)

    def _weapon_variants_for_slot(self, slot_name: str) -> List[str]:
        return WEAPON_FAMILIES.get(slot_name, [slot_name])

    def _owned_weapon_variants(self, slot_name: str) -> List[str]:
        return [
            weapon_name
            for weapon_name in self._weapon_variants_for_slot(slot_name)
            if weapon_name == "maos" or self.inventory.get_quantity(weapon_name) > 0
        ]

    def _slot_quantity(self, item_name: str) -> int:
        if item_name == "maos":
            return 1
        if item_name in WEAPON_FAMILIES:
            return len(self._owned_weapon_variants(item_name))
        return self.inventory.get_quantity(item_name)

    def _display_item_for_slot(self, item_name: str) -> str:
        variants = self._owned_weapon_variants(item_name) if item_name in WEAPON_FAMILIES else []
        if self.player.current_weapon in variants:
            return self.player.current_weapon
        if variants:
            return variants[0]
        return item_name

    def _equip_weapon_slot(self, slot_name: str, cycle_variant: bool = False) -> None:
        variants = self._owned_weapon_variants(slot_name)
        if not variants:
            self._play_sfx("ui_denied")
            return

        weapon_name = variants[0]
        if self.player.current_weapon in variants:
            current_index = variants.index(self.player.current_weapon)
            weapon_name = variants[(current_index + 1) % len(variants)] if cycle_variant else self.player.current_weapon
        self._equip_weapon(weapon_name)

    def _equip_weapon(self, weapon_name: str) -> None:
        if weapon_name not in WEAPONS:
            return
        if self.inventory.get_quantity(weapon_name) <= 0:
            self._play_sfx("ui_denied")
            return
        self.player.current_weapon = weapon_name
        self._play_sfx("inventory_move")

    async def run(self) -> None:
        while self.is_game_running:
            dt = self.clock.tick(60) / 1000.0
            if IS_WEB:
                await asyncio.sleep(0)
            if self._screen_state == "playing":
                direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed = self.process_input()
                self.update_game_state(direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed, dt)
                self.render(dt)
            else:
                self.process_menu_input()
                self.render_menu(dt)
        pygame.quit()


async def main() -> None:
    await Game().run()


if __name__ == "__main__":
    asyncio.run(main())
