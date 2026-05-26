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
TARGET_FPS = 60
COLLISION_BUCKET_SIZE = 128
WORLD_WIDTH, WORLD_HEIGHT = 2200, 1400
PROJECT_ROOT = Path(__file__).resolve().parent
GAME_TITLE = "Dead Streets"
GAME_SUBTITLE = "ZOMBIE SURVIVAL"
IS_WEB = sys.platform == "emscripten"
LOCAL_MAP_ROOT = PROJECT_ROOT / "maps"
MAP_ROOT = LOCAL_MAP_ROOT if LOCAL_MAP_ROOT.exists() else PROJECT_ROOT.parent


def _resolve_tmj_groups(groups: List[Tuple[str, ...]], pattern: str) -> List[Path]:
    paths: List[Path] = []
    known_names = {name.lower() for group in groups for name in group}

    for group in groups:
        selected = next((MAP_ROOT / name for name in group if (MAP_ROOT / name).exists()), MAP_ROOT / group[0])
        if selected.name.lower() not in {path.name.lower() for path in paths}:
            paths.append(selected)

    if MAP_ROOT.exists():
        for path in sorted(MAP_ROOT.glob(pattern), key=lambda item: item.name.lower()):
            if path.suffix.lower() == ".tmj" and path.name.lower() not in known_names:
                paths.append(path)
    return paths


NORMAL_MAP_PATHS = _resolve_tmj_groups(
    [
        ("Mapa 1.tmj", "Mapa 1.1.tmj"),
        ("Mapa 2.tmj",),
        ("Mapa 3.tmj",),
        ("Mapa 4.tmj",),
    ],
    "Mapa *.tmj",
)
BOSS_MAP_PATHS = _resolve_tmj_groups(
    [
        ("Boss 1.tmj",),
        ("Boss 2.tmj",),
        ("Boss 3.tmj",),
    ],
    "Boss *.tmj",
)
BOSS_SEQUENCE = ["boss 1.tmj", "boss 2.tmj", "summoner"]
BOSS_MAP_PATH = BOSS_MAP_PATHS[0]
MAP_SEQUENCE = NORMAL_MAP_PATHS
MAPS_BEFORE_BOSS = 3
INTERIOR_MAP_PATHS = _resolve_tmj_groups([("Interior 1.tmj", "interior 1.1.tmj")], "Interior *.tmj")
TILED_MAP_PATH = MAP_SEQUENCE[0]
INFINITE_AMMO_CHEAT_CODE = "150328"
SAVE_GAME_PATH = PROJECT_ROOT / "savegame.json"
SETTINGS_PATH = PROJECT_ROOT / "settings.json"
MUSIC_ROOT = PROJECT_ROOT / "musics"
TITLE_MUSIC_PATH = MUSIC_ROOT / "Menu_Music.mp3"
GAME_MUSIC_PATH = MUSIC_ROOT / "Loop_Music.mp3"
BOSS_MUSIC_PATH = MUSIC_ROOT / "Boss_Fight.mp3"
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
ZOMBIE_SEPARATION_BUCKET_SIZE = 96
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
            "escopeta",
            "kit_medico",
        ],
        "drops": (2, 5),
        "ambush": 0.22,
    },
}

OBJECT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "objects"
SHOT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "Shot"
AXE_SPRITE_ROOT = PROJECT_ROOT / "sprites" / "Zombie_Axe" / "Axe"
UI_SPRITE_ROOT = PROJECT_ROOT / "UIMENU"
_RAW_SPRITE_CACHE: Dict[str, pygame.Surface] = {}
_SCALED_SPRITE_CACHE: Dict[Tuple[str, float], pygame.Surface] = {}
_COMPOSITE_SPRITE_CACHE: Dict[Tuple[str, str, str, str, float], pygame.Surface] = {}
_UI_SPRITE_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_TINTED_SPRITE_CACHE: Dict[Tuple[int, Tuple[int, int], Tuple[int, int, int], float], pygame.Surface] = {}
_SHOT_IMPACT_CACHE: List[List[pygame.Surface]] | None = None
_AXE_PROJECTILE_CACHE: Dict[tuple[str, float], List[pygame.Surface]] = {}
_SHADOW_CACHE: Dict[Tuple[Tuple[int, int], int], pygame.Surface] = {}

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
    "pistola_perfurante": (90, 170, 255),
    "escopeta_incendiaria": (255, 102, 76),
    "balas_incendiarias": (255, 132, 86),
    "balas_perfurantes": (90, 170, 255),
    "cartuchos_incendiarios": (255, 132, 86),
}
ADVANCED_WEAPON_ITEMS = {"pistola_incendiaria", "pistola_perfurante", "escopeta_incendiaria"}

ZOMBIE_VARIANTS: Dict[str, Dict[str, float | int]] = {
    "axe": {"weight": 7, "speed": 1.0, "health": 1.0, "radius": 12},
    "small": {"weight": 4, "speed": 1.68, "health": 0.72, "radius": 10},
    "big": {"weight": 3, "speed": 0.66, "health": 1.95, "radius": 18},
}
BOSS_ZOMBIE_STATS: Dict[str, Dict[str, object]] = {
    "boss 1.tmj": {
        "name": "",
        "message": "Derrote a criatura para liberar o teleporte.",
        "zombie_type": "big",
        "speed": 58.0,
        "health": 900,
        "radius": 44,
        "sprite_scale": 1.85,
        "attack_damage": 28,
        "attack_range": 64.0,
        "can_throw_axe": False,
    },
    "boss 2.tmj": {
        "name": "",
        "message": "A criatura do machado apareceu. A primeira metade e corpo a corpo.",
        "phase_two_message": "Segunda fase! Ela comecou a arremessar o machado.",
        "zombie_type": "axe",
        "speed": 42.0,
        "health": 1250,
        "radius": 46,
        "sprite_scale": 2.05,
        "attack_damage": 32,
        "attack_range": 72.0,
        "can_throw_axe": False,
    },
    "summoner": {
        "name": "",
        "message": "Ela nao luta sozinha.",
        "phase_two_message": "Segunda fase! Agora ela chama zumbis com machado.",
        "zombie_type": "big",
        "speed": 34.0,
        "health": 1450,
        "radius": 48,
        "sprite_scale": 2.12,
        "attack_damage": 0,
        "attack_range": 0.0,
        "can_throw_axe": False,
        "summon_interval": 5.4,
        "summon_count": 5,
        "summon_max": 18,
        "phase_two_summon_interval": 4.6,
        "phase_two_small_count": 4,
        "phase_two_axe_count": 2,
        "phase_two_summon_max": 24,
        "shield_reduction": 0.18,
    },
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
    cache_key = (size, alpha)
    cached = _SHADOW_CACHE.get(cache_key)
    if cached is not None:
        return cached
    shadow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (18, 22, 24, alpha), shadow.get_rect())
    _SHADOW_CACHE[cache_key] = shadow
    return shadow


def _dim_sprite(sprite: pygame.Surface) -> pygame.Surface:
    dimmed = sprite.copy()
    dimmed.fill((125, 125, 125, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return dimmed


def _desaturate_sprite(sprite: pygame.Surface, strength: float = 0.72) -> pygame.Surface:
    desaturated = sprite.copy()
    width, height = desaturated.get_size()
    strength = max(0.0, min(1.0, strength))
    desaturated.lock()
    try:
        for y in range(height):
            for x in range(width):
                r, g, b, a = desaturated.get_at((x, y))
                if a <= 0:
                    continue
                gray = int(r * 0.3 + g * 0.59 + b * 0.11)
                desaturated.set_at(
                    (x, y),
                    (
                        int(r * (1.0 - strength) + gray * strength),
                        int(g * (1.0 - strength) + gray * strength),
                        int(b * (1.0 - strength) + gray * strength),
                        a,
                    ),
                )
    finally:
        desaturated.unlock()
    return desaturated


def _tint_sprite(sprite: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    strength = 0.18
    cache_key = (id(sprite), sprite.get_size(), color, strength)
    cached = _TINTED_SPRITE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    tinted = sprite.copy()
    width, height = tinted.get_size()
    tinted.lock()
    try:
        for y in range(height):
            for x in range(width):
                r, g, b, a = tinted.get_at((x, y))
                if a <= 0:
                    continue
                tinted.set_at(
                    (x, y),
                    (
                        int(r * (1.0 - strength) + color[0] * strength),
                        int(g * (1.0 - strength) + color[1] * strength),
                        int(b * (1.0 - strength) + color[2] * strength),
                        a,
                    ),
                )
    finally:
        tinted.unlock()
    _TINTED_SPRITE_CACHE[cache_key] = tinted
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


def _load_axe_projectile_frames(direction_name: str, scale: float = 1.0) -> List[pygame.Surface]:
    visual_scale = max(0.5, float(scale))
    cache_key = (direction_name, round(visual_scale, 2))
    cached = _AXE_PROJECTILE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if direction_name == "left":
        spritesheet_path = AXE_SPRITE_ROOT / "Axe_Side-left_Thrown-Sheet9.png"
    elif direction_name == "right":
        spritesheet_path = AXE_SPRITE_ROOT / "Axe_Side_Thrown-Sheet9.png"
    else:
        spritesheet_path = AXE_SPRITE_ROOT / "Axe_Vertical_Thrown-Sheet9.png"

    frame_count = 9
    sheet = pygame.image.load(str(spritesheet_path)).convert_alpha()
    frame_width = sheet.get_width() // frame_count
    frame_height = sheet.get_height()
    frames: List[pygame.Surface] = []
    for frame_index in range(frame_count):
        frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), pygame.Rect(frame_index * frame_width, 0, frame_width, frame_height))
        if direction_name == "up":
            frame = pygame.transform.flip(frame, False, True)
        scaled_width = max(1, int(frame_width * 3 * visual_scale))
        scaled_height = max(1, int(frame_height * 3 * visual_scale))
        frames.append(pygame.transform.scale(frame, (scaled_width, scaled_height)))

    _AXE_PROJECTILE_CACHE[cache_key] = frames
    return frames


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
            self._shadow = _make_shadow(
                (
                    max(10, int(self._sprite.get_width() * 0.62)),
                    max(5, int(self._sprite.get_height() * 0.18)),
                ),
                alpha=105,
            )
        else:
            self.radius = radius or SEARCH_RANGE
            self._shadow = None
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
        shadow = self._shadow
        if shadow is None:
            return
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
        effect: str = "",
    ) -> None:
        self.position = pygame.Vector2(position)
        self.origin = pygame.Vector2(origin) if origin is not None else self.position.copy()
        self.color = color
        self.effect = effect
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
            fade = alpha / 255.0
            trail_color = tuple(max(0, min(255, int(component * fade))) for component in self.color)
            glow = tuple(max(0, min(255, int((component + 35) * fade))) for component in self.color)
            width = 3 if self.effect == "fire" else 2
            pygame.draw.line(surface, trail_color, start, end, width)
            pygame.draw.circle(surface, glow, bullet_pos, 4 if self.effect == "fire" else 3)
            if self.effect == "fire":
                flame_color = (255, 150, 48)
                pygame.draw.line(surface, (*flame_color, alpha), start.lerp(end, 0.18), bullet_pos, 1)
                pygame.draw.circle(surface, (255, 80, 32), bullet_pos + pygame.Vector2(0, -3), 2)
            elif self.effect == "ice":
                pygame.draw.circle(surface, (150, 215, 255), bullet_pos, 5, 1)

        frame_index = min(int(self.animation_time), len(self.frames) - 1)
        sprite = self.frames[frame_index]
        surface.blit(sprite, sprite.get_rect(center=(round(end.x), round(end.y))))


class AxeProjectile:
    def __init__(
        self,
        position: Tuple[float, float] | pygame.Vector2,
        direction: pygame.Vector2,
        damage: int,
        max_distance: float = 420.0,
        speed: float = 330.0,
        sprite_scale: float = 1.0,
    ) -> None:
        self.position = pygame.Vector2(position)
        self.origin = self.position.copy()
        self.direction = pygame.Vector2(direction)
        if self.direction.length_squared() <= 0:
            self.direction = pygame.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.damage = damage
        self.max_distance = max_distance
        self.speed = speed
        self.sprite_scale = max(0.5, float(sprite_scale))
        self.radius = max(15, int(15 * self.sprite_scale))
        self.animation_time = 0.0
        self.has_hit = False
        self.direction_name = self._direction_name(self.direction)
        self.frames = _load_axe_projectile_frames(self.direction_name, self.sprite_scale)

    @staticmethod
    def _direction_name(direction: pygame.Vector2) -> str:
        if abs(direction.x) > abs(direction.y):
            return "right" if direction.x > 0 else "left"
        return "down" if direction.y > 0 else "up"

    def update(self, dt: float) -> None:
        self.position += self.direction * self.speed * dt
        self.animation_time += dt * 14.0

    def is_finished(self) -> bool:
        return self.has_hit or self.position.distance_to(self.origin) >= self.max_distance

    def can_damage_player(self, player_position: Tuple[float, float], player_radius: int) -> bool:
        if self.has_hit:
            return False
        return self.position.distance_to(pygame.Vector2(player_position)) <= self.radius + player_radius

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        frame_index = int(self.animation_time) % len(self.frames)
        sprite = self.frames[frame_index]
        draw_pos = self.position - camera_offset
        surface.blit(sprite, sprite.get_rect(center=(round(draw_pos.x), round(draw_pos.y))))


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
        pygame.display.set_caption(GAME_TITLE)
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self._present_surface = (
            pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
            if (WINDOW_WIDTH, WINDOW_HEIGHT) != (WIDTH, HEIGHT)
            else self.screen
        )
        self._menu_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._menu_overlay.fill((8, 10, 13, 176))
        self._damage_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.menu_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 56, bold=True)
        self._menu_title_layers = self._build_menu_title_layers()

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
        self.axe_projectiles: List[AxeProjectile] = []
        self._floating_popups: List[FloatingPopup] = []
        self.nodes: List[SearchNode] = []
        self.decorations: List[Decoration] = []
        self._static_world_drawables: List[Tuple[float, int, object]] = []
        self.doors: List[MapTrigger] = []
        self.exits: List[MapTrigger] = []
        self._occupied_exit_triggers: set[int] = set()
        self.tile_map: TiledMap | None = None
        self.collision_rects: List[pygame.Rect] = []
        self._collision_buckets: Dict[Tuple[int, int], List[pygame.Rect]] = {}

        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._transition_cooldown = 0.0
        self._camera = pygame.Vector2()
        self._cheat_buffer = ""
        self._infinite_ammo = False

        self._recipe_names = self.crafting.get_recipe_names(self.inventory)
        self._selected_recipe_index = 0
        self._crafting_scroll_index = 0
        self._base_position = pygame.Vector2(WORLD_WIDTH * 0.48, WORLD_HEIGHT * 0.52)
        self._current_map_index = 0
        self._current_map_path = self._first_existing_path(MAP_SEQUENCE, TILED_MAP_PATH)
        self._normal_maps_completed = 0
        self._progress_level = 0
        self._bosses_defeated = 0
        self._boss_zombie: Zombie | None = None
        self._extra_boss_zombies: List[Zombie] = []
        self._boss_defeated = False
        self._boss_phase_two_active = False
        self._boss_name = ""
        self._current_boss_key = "boss 1.tmj"
        self._summoner_timer = 0.0
        self._summoner_minion_ids: set[int] = set()
        self._stored_exterior_state: Dict[str, object] | None = None
        self._inside_interior = False
        self._return_map_path: Path | None = None
        self._return_map_index = 0
        self._return_position: pygame.Vector2 | None = None
        self._interior_exit: MapTrigger | None = None
        self._show_inventory = False
        self._show_crafting = False
        self._show_tutorial = False
        self._tutorial_page = 0
        self._quick_slots = ["maos", "taco", "pistola", "escopeta", "comida", "kit_medico"]
        self._selected_quick_slot = 0

        self._load_sfx()
        self._reset_game()
        self._play_title_music()

    def _present_frame(self) -> None:
        if (WINDOW_WIDTH, WINDOW_HEIGHT) == (WIDTH, HEIGHT):
            self.window.blit(self.screen, (0, 0))
        else:
            # Nearest-neighbor scaling is much cheaper and keeps the pixel-art look.
            pygame.transform.scale(self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT), self._present_surface)
            self.window.blit(self._present_surface, (0, 0))
        pygame.display.flip()

    def _build_menu_title_layers(self) -> Dict[str, pygame.Surface]:
        return {
            "shadow": self.title_font.render(GAME_TITLE, False, (22, 24, 29)),
            "accent": self.title_font.render(GAME_TITLE, False, PALETTE["accent"]),
            "text": self.title_font.render(GAME_TITLE, False, PALETTE["text"]),
            "glitch": self.title_font.render(GAME_TITLE, False, PALETTE["danger"]),
            "subtitle": self.small_font.render(GAME_SUBTITLE, False, PALETTE["text_soft"]),
        }

    @staticmethod
    def _first_existing_path(paths: List[Path], fallback: Path) -> Path:
        for path in paths:
            if path.exists():
                return path
        return fallback

    def _available_normal_maps(self) -> List[Path]:
        return [path for path in NORMAL_MAP_PATHS if path.exists()]

    def _is_boss_map_path(self, map_path: Path | None = None) -> bool:
        path = map_path or self._current_map_path
        return any(path.name.lower() == boss_path.name.lower() for boss_path in BOSS_MAP_PATHS)

    def _available_boss_maps(self) -> List[Path]:
        return [path for path in BOSS_MAP_PATHS if path.exists()]

    def _boss_loop_level(self) -> int:
        available_keys = [key for key in BOSS_SEQUENCE if key in BOSS_ZOMBIE_STATS]
        if not available_keys:
            return 0
        return max(0, self._bosses_defeated // len(available_keys))

    def _next_boss_key(self) -> str | None:
        available_keys = [key for key in BOSS_SEQUENCE if key in BOSS_ZOMBIE_STATS]
        if not available_keys:
            return None
        return available_keys[self._bosses_defeated % len(available_keys)]

    def _next_boss_map_path(self) -> Path | None:
        if self._next_boss_key() is None:
            return None
        available_bosses = self._available_boss_maps()
        if not available_bosses:
            return None
        return random.choice(available_bosses)

    def _boss_stats_for_map(self, map_path: Path | None = None) -> Dict[str, object]:
        if (
            self._current_boss_key in BOSS_ZOMBIE_STATS
            and (
                map_path is None
                or any(Path(map_path).name.lower() == boss_path.name.lower() for boss_path in BOSS_MAP_PATHS)
            )
        ):
            return BOSS_ZOMBIE_STATS[self._current_boss_key]
        path = map_path or self._current_map_path
        return BOSS_ZOMBIE_STATS.get(path.name.lower(), BOSS_ZOMBIE_STATS["boss 1.tmj"])

    def _is_summoner_boss_active(self) -> bool:
        return self._is_boss_map_path() and self._current_boss_key == "summoner"

    def _choose_random_normal_map(self, exclude_current: bool = False) -> Path:
        available_maps = self._available_normal_maps()
        if not available_maps:
            return TILED_MAP_PATH
        choices = available_maps
        if exclude_current and len(available_maps) > 1:
            current_name = self._current_map_path.name.lower()
            choices = [path for path in available_maps if path.name.lower() != current_name] or available_maps
        return random.choice(choices)

    def _normal_map_index(self, map_path: Path) -> int:
        for index, path in enumerate(NORMAL_MAP_PATHS):
            if path.name.lower() == map_path.name.lower():
                return index
        return 0

    def _boss_is_alive(self) -> bool:
        return self._is_boss_map_path() and not self._boss_defeated and any(
            boss is not None and not boss.is_dying() for boss in self._boss_enemies()
        )

    def _boss_enemies(self) -> List[Zombie]:
        bosses: List[Zombie] = []
        if self._boss_zombie is not None:
            bosses.append(self._boss_zombie)
        bosses.extend(boss for boss in self._extra_boss_zombies if boss is not None)
        return bosses

    def _is_boss_enemy(self, zombie: Zombie) -> bool:
        return zombie is self._boss_zombie or any(zombie is boss for boss in self._extra_boss_zombies)

    def _is_horde_map(self) -> bool:
        return self._current_map_path.name.lower() == "mapa 3.tmj"

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

    def _play_boss_music(self) -> None:
        self._play_music(BOSS_MUSIC_PATH)

    def _play_active_music(self) -> None:
        if self._boss_is_alive():
            self._play_boss_music()
            return
        self._play_game_music()

    def _reset_game(self) -> None:
        self.game_time = 0.0
        self.difficulty_scale = 1.0
        self.spawn_rate = 1.0
        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.zombies = []
        self.shot_impacts = []
        self.axe_projectiles = []
        self._floating_popups = []
        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._transition_cooldown = 0.0
        self._camera = pygame.Vector2()
        self._cheat_buffer = ""
        self._infinite_ammo = False
        self._current_map_path = self._first_existing_path(NORMAL_MAP_PATHS, TILED_MAP_PATH)
        self._current_map_index = self._normal_map_index(self._current_map_path)
        self._normal_maps_completed = 0
        self._progress_level = 0
        self._bosses_defeated = 0
        self._boss_zombie = None
        self._extra_boss_zombies = []
        self._boss_defeated = False
        self._boss_phase_two_active = False
        self._boss_name = ""
        self._current_boss_key = "boss 1.tmj"
        self._summoner_timer = 0.0
        self._summoner_minion_ids = set()
        self._stored_exterior_state = None
        self._inside_interior = False
        self._return_map_path = None
        self._return_map_index = 0
        self._return_position = None
        self._occupied_exit_triggers.clear()
        self._show_inventory = False
        self._show_crafting = False
        self._show_tutorial = False
        self._tutorial_page = 0
        self._selected_quick_slot = 0
        self._menu_selected_index = 0
        self._gamepad_aim_vector = pygame.Vector2()
        self._crafting_scroll_index = 0

        self._generate_world()
        self.player.set_position(tuple(self._base_position))
        self._sync_exit_trigger_state()
        self.inventory.add_item("comida", 2)

    def _clear_world_content(self) -> None:
        self.nodes.clear()
        self.zombies.clear()
        self.shot_impacts.clear()
        self.axe_projectiles.clear()
        self._floating_popups.clear()
        self.decorations.clear()
        self._static_world_drawables.clear()
        self.doors.clear()
        self.exits.clear()
        self._occupied_exit_triggers.clear()
        self._set_collision_rects([])
        self.tile_map = None
        self._interior_exit = None
        self._boss_zombie = None
        self._extra_boss_zombies.clear()
        self._boss_phase_two_active = False
        self._summoner_timer = 0.0
        self._summoner_minion_ids.clear()

    def _store_exterior_world_state(self) -> None:
        self._stored_exterior_state = {
            "nodes": list(self.nodes),
            "zombies": list(self.zombies),
            "shot_impacts": list(self.shot_impacts),
            "axe_projectiles": list(self.axe_projectiles),
            "floating_popups": list(self._floating_popups),
            "decorations": list(self.decorations),
            "static_world_drawables": list(self._static_world_drawables),
            "doors": list(self.doors),
            "exits": list(self.exits),
            "occupied_exit_triggers": set(self._occupied_exit_triggers),
            "collision_rects": list(self.collision_rects),
            "collision_buckets": {key: list(value) for key, value in self._collision_buckets.items()},
            "tile_map": self.tile_map,
            "world_width": WORLD_WIDTH,
            "world_height": WORLD_HEIGHT,
            "current_map_path": self._current_map_path,
            "current_map_index": self._current_map_index,
            "base_position": self._base_position.copy(),
            "boss_zombie": self._boss_zombie,
            "extra_boss_zombies": list(self._extra_boss_zombies),
            "boss_defeated": self._boss_defeated,
            "boss_phase_two_active": self._boss_phase_two_active,
            "boss_name": self._boss_name,
            "summoner_timer": self._summoner_timer,
            "summoner_minion_ids": set(self._summoner_minion_ids),
        }

    def _restore_exterior_world_state(self) -> bool:
        if self._stored_exterior_state is None:
            return False

        global WORLD_WIDTH, WORLD_HEIGHT
        state = self._stored_exterior_state
        self.nodes = list(state["nodes"])
        self.zombies = list(state["zombies"])
        self.shot_impacts = list(state["shot_impacts"])
        self.axe_projectiles = list(state["axe_projectiles"])
        self._floating_popups = list(state["floating_popups"])
        self.decorations = list(state["decorations"])
        self._static_world_drawables = list(state["static_world_drawables"])
        self.doors = list(state["doors"])
        self.exits = list(state["exits"])
        self._occupied_exit_triggers = set(state["occupied_exit_triggers"])
        self.collision_rects = list(state["collision_rects"])
        self._collision_buckets = {
            key: list(value) for key, value in dict(state["collision_buckets"]).items()
        }
        self.tile_map = state["tile_map"]
        WORLD_WIDTH = int(state["world_width"])
        WORLD_HEIGHT = int(state["world_height"])
        self._current_map_path = Path(state["current_map_path"])
        self._current_map_index = int(state["current_map_index"])
        self._base_position = pygame.Vector2(state["base_position"])
        self._boss_zombie = state["boss_zombie"]
        self._extra_boss_zombies = list(state.get("extra_boss_zombies", []))
        self._boss_defeated = bool(state["boss_defeated"])
        self._boss_phase_two_active = bool(state["boss_phase_two_active"])
        self._boss_name = str(state["boss_name"])
        self._summoner_timer = float(state["summoner_timer"])
        self._summoner_minion_ids = set(state["summoner_minion_ids"])
        self._inside_interior = False
        self._interior_exit = None
        self._stored_exterior_state = None
        return True

    def _set_collision_rects(self, rects: List[pygame.Rect]) -> None:
        self.collision_rects = list(rects)
        buckets: Dict[Tuple[int, int], List[pygame.Rect]] = {}
        for rect in self.collision_rects:
            min_x = rect.left // COLLISION_BUCKET_SIZE
            max_x = rect.right // COLLISION_BUCKET_SIZE
            min_y = rect.top // COLLISION_BUCKET_SIZE
            max_y = rect.bottom // COLLISION_BUCKET_SIZE
            for bucket_y in range(min_y, max_y + 1):
                for bucket_x in range(min_x, max_x + 1):
                    buckets.setdefault((bucket_x, bucket_y), []).append(rect)
        self._collision_buckets = buckets

    def _nearby_collision_rects(self, area: pygame.Rect) -> List[pygame.Rect]:
        if not self._collision_buckets:
            return []
        min_x = area.left // COLLISION_BUCKET_SIZE
        max_x = area.right // COLLISION_BUCKET_SIZE
        min_y = area.top // COLLISION_BUCKET_SIZE
        max_y = area.bottom // COLLISION_BUCKET_SIZE
        nearby: List[pygame.Rect] = []
        seen: set[int] = set()
        for bucket_y in range(min_y, max_y + 1):
            for bucket_x in range(min_x, max_x + 1):
                for rect in self._collision_buckets.get((bucket_x, bucket_y), ()):
                    rect_id = id(rect)
                    if rect_id in seen:
                        continue
                    seen.add(rect_id)
                    nearby.append(rect)
        return nearby

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
        self._rebuild_static_world_drawables()

    def _load_tiled_world(self, map_path: Path, inside_interior: bool = False) -> bool:
        if not map_path.exists():
            return False

        global WORLD_WIDTH, WORLD_HEIGHT
        self.tile_map = TiledMap(map_path, scale=TILED_MAP_SCALE)
        self._current_map_path = map_path
        self._inside_interior = inside_interior
        if not inside_interior:
            self._boss_defeated = not self._is_boss_map_path(map_path)
            self._boss_name = str(self._boss_stats_for_map(map_path).get("name", "CHEFE"))
        WORLD_WIDTH = self.tile_map.world_width
        WORLD_HEIGHT = self.tile_map.world_height
        self._set_collision_rects(list(self.tile_map.collision_rects))
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
            if self._is_boss_map_path(map_path):
                self._spawn_boss_zombie()
            else:
                initial_zombies = 6 if self._is_horde_map() else max(1, min(4, 1 + self._progress_level))
                for _ in range(initial_zombies):
                    self._spawn_zombie()
        else:
            self._interior_exit = MapTrigger(
                "interior_exit",
                tuple(self._find_open_position_near((WORLD_WIDTH * 0.5, WORLD_HEIGHT - self.tile_map.render_tile_height))),
                DOOR_RANGE,
            )

        if inside_interior:
            self._set_message("Interior carregado.")
        elif self._is_boss_map_path(map_path):
            self._set_message(str(self._boss_stats_for_map(map_path).get("message", "O chefe apareceu.")))
        else:
            self._set_message("Mapa do Tiled carregado.")
        self._rebuild_static_world_drawables()
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
        self._sync_exit_trigger_state()
        self._transition_cooldown = 0.8
        self._play_active_music()
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
        self._store_exterior_world_state()
        interior_path = random.choice(interior_paths)
        if self._switch_to_tiled_map(interior_path, inside_interior=True):
            self._play_sfx("door_open")
            self._set_message("Voce entrou no predio.")
        else:
            self._stored_exterior_state = None

    def _leave_interior(self) -> None:
        if self._return_map_path is None or self._return_position is None:
            self._play_sfx("door_locked")
            self._set_message("Saida sem destino.")
            return

        return_path = self._return_map_path
        return_index = self._return_map_index
        return_position = self._return_position.copy()
        if self._restore_exterior_world_state():
            self._current_map_path = return_path
            self._current_map_index = return_index
            spawn = self._find_open_position_near(return_position)
            self.player.set_position(tuple(spawn))
            self._sync_exit_trigger_state()
            self._transition_cooldown = 0.8
            self._return_map_path = None
            self._return_position = None
            self._play_sfx("door_open")
            self._play_active_music()
            self._set_message("Voce saiu do predio.")
            return

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
        if self._is_boss_map_path():
            if self._boss_is_alive():
                self._play_sfx("ui_denied")
                self._set_message("O teleporte esta bloqueado pelo chefe.")
                self._transition_cooldown = 0.45
                return
            self._normal_maps_completed = 0
            next_path = self._choose_random_normal_map()
            next_index = self._normal_map_index(next_path)
        else:
            available_maps = self._available_normal_maps()
            if not available_maps:
                self._play_sfx("ui_denied")
                self._set_message("Nenhum mapa configurado.")
                return

            self._normal_maps_completed += 1
            self._progress_level += 1
            next_boss_key = self._next_boss_key()
            next_boss_path = self._next_boss_map_path()
            if self._normal_maps_completed >= MAPS_BEFORE_BOSS and next_boss_path is not None:
                if next_boss_key is not None:
                    self._current_boss_key = next_boss_key
                next_path = next_boss_path
                next_index = -1
            else:
                next_path = self._choose_random_normal_map(exclude_current=True)
                next_index = self._normal_map_index(next_path)

        available_maps = self._available_normal_maps()
        if not available_maps:
            self._play_sfx("ui_denied")
            self._set_message("Nenhum mapa configurado.")
            return

        old_world_height = max(1, WORLD_HEIGHT)
        player_y_ratio = pygame.Vector2(self.player.player_position).y / old_world_height
        going_right = trigger.position.x > WORLD_WIDTH * 0.5

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
        self._sync_exit_trigger_state()
        self._transition_cooldown = 0.9
        self._play_active_music()
        self._play_sfx("objective")
        if self._is_boss_map_path(next_path):
            self._set_message("Arena do chefe. Teleportes bloqueados.")
        else:
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

    def _rebuild_static_world_drawables(self) -> None:
        static_drawables: List[Tuple[float, int, object]] = []
        for decoration in self.decorations:
            static_drawables.append((decoration.position.y, 0, decoration))
        for node in self.nodes:
            static_drawables.append((node.position.y, 2, node))
        static_drawables.sort(key=lambda item: (item[0], item[1]))
        self._static_world_drawables = static_drawables

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
        return any(test_rect.colliderect(rect) for rect in self._nearby_collision_rects(test_rect))

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

    def _spawn_zombie(
        self,
        near_position: Tuple[float, float] | pygame.Vector2 | None = None,
        forced_variant: str | None = None,
    ) -> Zombie | None:
        if near_position is None:
            pos = pygame.Vector2(self._random_world_position())
            while pos.distance_to(pygame.Vector2(self.player.player_position)) < 260:
                pos = pygame.Vector2(self._random_world_position())
        else:
            base = pygame.Vector2(near_position)
            pos = self._find_open_position_near(base + pygame.Vector2(random.randint(-120, 120), random.randint(-120, 120)))

        if forced_variant in ZOMBIE_VARIANTS:
            variant_name = str(forced_variant)
        else:
            variant_weights = self._zombie_variant_weights()
            variant_name = random.choices(
                list(variant_weights.keys()),
                weights=list(variant_weights.values()),
                k=1,
            )[0]
        variant = ZOMBIE_VARIANTS[variant_name]
        progress_boost = min(1.0, self._progress_level * 0.08)
        base_speed = 48.0 + (self.difficulty_scale * 5.0)
        base_health = 20 + (self.difficulty_scale * 4.0)
        speed = base_speed * float(variant["speed"])
        health = int(base_health * float(variant["health"]) * (0.82 + progress_boost))
        radius = int(variant["radius"])
        zombie = Zombie(
            pos,
            speed,
            health=max(8, health),
            radius=radius,
            zombie_type=variant_name,
            can_throw_axe=variant_name == "axe" and self._progress_level >= 2,
        )
        self.zombies.append(zombie)
        return zombie

    def _zombie_variant_weights(self) -> Dict[str, float]:
        if self._progress_level <= 0:
            return {"axe": 10.0, "small": 1.0, "big": 0.0}
        if self._progress_level == 1:
            return {"axe": 8.0, "small": 3.0, "big": 0.5}
        if self._progress_level == 2:
            return {"axe": 7.0, "small": 4.0, "big": 1.4}
        return {name: float(data["weight"]) for name, data in ZOMBIE_VARIANTS.items()}

    def _spawn_boss_zombie(self) -> None:
        stats = self._boss_stats_for_map()
        loop_level = self._boss_loop_level()
        speed_multiplier = 1.0 + min(0.5, loop_level * 0.1)
        health_multiplier = 1.0 + min(1.6, loop_level * 0.32)
        damage_multiplier = 1.0 + min(0.9, loop_level * 0.14)
        if self._current_boss_key == "summoner" and loop_level == 0:
            health_multiplier *= 0.9
            speed_multiplier *= 0.94
        center = pygame.Vector2(WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.48)
        pos = self._find_open_position_near(center)
        if pos.distance_to(pygame.Vector2(self.player.player_position)) < 260:
            pos = self._find_open_position_near((WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.34))
        self._boss_name = str(stats.get("name", "CHEFE"))
        self._boss_phase_two_active = False
        self._summoner_timer = 1.2 if self._current_boss_key == "summoner" else 0.0
        self._summoner_minion_ids.clear()
        self._extra_boss_zombies.clear()
        self._boss_zombie = self._create_boss_zombie(
            pos,
            stats,
            speed_multiplier,
            health_multiplier,
            damage_multiplier,
        )
        self.zombies.append(self._boss_zombie)
        self._spawn_loop_boss_partner(stats, loop_level, speed_multiplier, health_multiplier, damage_multiplier)
        self._play_sfx("zombie_alert")
        self._set_message(str(stats.get("message", "O chefe apareceu. Derrote-o para liberar o teleporte.")))

    def _create_boss_zombie(
        self,
        pos: pygame.Vector2,
        stats: Dict[str, object],
        speed_multiplier: float,
        health_multiplier: float,
        damage_multiplier: float,
    ) -> Zombie:
        return Zombie(
            pos,
            (float(stats["speed"]) + self.difficulty_scale * 2.0) * speed_multiplier,
            health=int((int(stats["health"]) + int(self.difficulty_scale * 80)) * health_multiplier),
            radius=int(stats["radius"]),
            zombie_type=str(stats["zombie_type"]),
            sprite_scale=float(stats["sprite_scale"]),
            attack_damage=int(int(stats["attack_damage"]) * damage_multiplier),
            attack_range=float(stats["attack_range"]),
            can_throw_axe=bool(stats.get("can_throw_axe", False)),
        )

    def _spawn_loop_boss_partner(
        self,
        stats: Dict[str, object],
        loop_level: int,
        speed_multiplier: float,
        health_multiplier: float,
        damage_multiplier: float,
    ) -> None:
        if loop_level <= 0 or self._current_boss_key not in {"boss 1.tmj", "boss 2.tmj"}:
            return

        partner_base = pygame.Vector2(WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.32)
        if self._boss_zombie is not None and partner_base.distance_to(self._boss_zombie.position) < 170:
            partner_base = pygame.Vector2(WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.64)
        partner = self._create_boss_zombie(
            self._find_open_position_near(partner_base),
            stats,
            speed_multiplier * 1.04,
            health_multiplier * 0.82,
            damage_multiplier,
        )
        if str(stats.get("zombie_type", "")) == "axe":
            partner.can_throw_axe = True
        partner.flank_side = -1
        partner.flank_distance = 190.0
        if self._boss_zombie is not None:
            self._boss_zombie.flank_side = 1
            self._boss_zombie.flank_distance = 170.0
        self._extra_boss_zombies.append(partner)
        self.zombies.append(partner)

    def _apply_loaded_state(self, data: Dict) -> None:
        self.player.player_health = int(data.get("player_health", 100))
        self.player.player_hunger = float(data.get("player_hunger", 100.0))
        position = data.get("player_position", tuple(self._base_position))
        self.player.set_position(position)
        self._sync_exit_trigger_state()
        self._play_active_music()
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
            elif event.type == pygame.KEYDOWN and self._handle_cheat_key(event):
                continue
            elif self._show_tutorial:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._close_tutorial()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                        self._advance_tutorial()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._advance_tutorial()
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
                        self._play_active_music()
                        self._play_sfx("objective")
                        self._set_message("Save carregado.")
            elif event.type == pygame.MOUSEWHEEL:
                if self._show_crafting:
                    self._scroll_crafting(-event.y)
                else:
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

        if self._show_tutorial:
            self._process_tutorial_gamepad_input()
            return direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed

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

    def _handle_cheat_key(self, event: pygame.event.Event) -> bool:
        digit = getattr(event, "unicode", "")
        if not digit or not str(digit).isdigit():
            return False

        self._cheat_buffer = (self._cheat_buffer + str(digit))[-len(INFINITE_AMMO_CHEAT_CODE):]
        if self._cheat_buffer != INFINITE_AMMO_CHEAT_CODE:
            return False

        self._infinite_ammo = True
        self._cheat_buffer = ""
        self._play_sfx("objective")
        self._set_message("Cheat ativado: municao infinita.")
        return True

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
                    self._play_active_music()
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
            self._show_tutorial = True
            self._tutorial_page = 0
            self._play_active_music()
            self._set_message("Novo jogo iniciado.")
        elif action == "continue_game":
            if self._has_started_game and not self._game_over:
                self._screen_state = "playing"
                self._play_active_music()
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

    def _tutorial_pages_legacy_unused(self) -> List[Tuple[str, List[str]]]:
        return [
            (
                "Objetivo",
                [
                    "Explore ruas e prédios, junte recursos e avance andando até o final da rua.",
                    "Guarde munição, comida e kit médico.",
                    "Derrote o chefe para liberar a saida.",
                ],
            ),
            (
                "Botoes",
                [
                    "WASD move. SHIFT corre. Mouse mira. Espaco ou mouse esquerdo ataca.",
                    "E busca recursos, abre portas e vasculha corpos.",
                    "Scroll do mouse muda itens da barra de atalhos",
                    "I abre inventario. B abre bancada de fabricacão. C usa item selecionado na barra de atalhos. Q usa cura ou comida rapidamente.",
                ],
            ),
            (
                "Armas",
                [
                    "Ao decorrer do jogo voce pode achar armas de fogo e de gelo, use a bancada de fabricação para fazer a munição.",
                    "Troque de armas ao abrir o iventario e selecionar uma arma diferente da selecionada na barra de atalhos",
                ],
            ),
        ]

    def _tutorial_pages(self) -> List[Tuple[str, List[str]]]:
        return [
            (
                "Objetivo",
                [
                    "Explore ruas e predios, junte recursos e avance andando ate o final da rua.",
                    "Guarde municao, comida e kit medico.",
                    "Derrote o chefe para liberar a saida.",
                ],
            ),
            (
                "Botoes",
                [
                    "WASD move. SHIFT corre. Mouse mira. Espaco ou mouse esquerdo ataca.",
                    "E busca recursos, abre portas e vasculha corpos.",
                    "Scroll do mouse muda itens da barra de atalhos.",
                    "I abre inventario. B abre bancada. C usa item selecionado. Q usa cura ou comida rapidamente.",
                ],
            ),
            (
                "Armas",
                [
                    "Voce pode achar armas de fogo e de gelo. Use a bancada para fazer municao.",
                    "Troque de arma abrindo o inventario e selecionando outra arma para a barra de atalhos.",
                ],
            ),
        ]

    def _advance_tutorial(self) -> None:
        pages = self._tutorial_pages()
        if self._tutorial_page < len(pages) - 1:
            self._tutorial_page += 1
            self._play_sfx("ui_move")
        else:
            self._close_tutorial()

    def _close_tutorial(self) -> None:
        if not self._show_tutorial:
            return
        self._show_tutorial = False
        self._tutorial_page = 0
        self._play_sfx("ui_close")

    def _process_tutorial_gamepad_input(self) -> None:
        gamepad = self._get_gamepad()
        if gamepad is None:
            self._gamepad_buttons_down.clear()
            return

        buttons = self._poll_gamepad_buttons(gamepad)
        pressed = buttons - self._gamepad_buttons_down
        button_map = self._gamepad_button_map(gamepad)
        if GAMEPAD_A in pressed or self._has_any_button(pressed, button_map["start"]):
            self._advance_tutorial()
        elif GAMEPAD_B in pressed or self._has_any_button(pressed, button_map["back"]):
            self._close_tutorial()
        self._gamepad_buttons_down = buttons

    def _load_saved_game(self) -> bool:
        data = load_game(str(SAVE_GAME_PATH))
        if data is None:
            self._play_sfx("ui_denied")
            self._set_menu_message("Nenhum save encontrado.")
            return False

        self._reset_game()
        self._apply_loaded_state(data)
        self._show_tutorial = False
        self._has_started_game = True
        self._screen_state = "playing"
        self._play_active_music()
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
        self.difficulty_scale = 0.78 + (self.game_time / 190.0) + (self._progress_level * 0.18)
        self.spawn_rate = 0.72 + (self.game_time / 230.0) + (self._progress_level * 0.16)

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
            if zombie is self._boss_zombie and self._is_summoner_boss_active():
                self._update_summoner_boss(dt, world_rect)
            elif self._is_flanking_boss(zombie):
                self._update_flanking_boss(zombie, dt, world_rect)
            else:
                zombie.update(self.player.player_position, dt, world_rect)
            if zombie.consume_attack_started():
                self._play_sfx(zombie.attack_sfx_name())
            if zombie.consume_axe_throw_ready():
                self._spawn_axe_projectile(zombie)
            self._resolve_zombie_obstacles(zombie, old_position, dt)
            if zombie.can_damage_player(self.player.player_position, self.player.radius):
                if self.player.take_damage(zombie.attack_damage):
                    self._play_sfx("player_damage")
                    self._set_message("Golpe pesado!" if self._is_boss_enemy(zombie) else "Voce foi atingido!")
            if zombie.is_dying() and not zombie.loot_given:
                self._handle_zombie_death(zombie)
        self._separate_zombies(dt)
        self.zombies = [zombie for zombie in self.zombies if not zombie.is_dead()]
        self._summoner_minion_ids = {
            minion_id
            for minion_id in self._summoner_minion_ids
            if any(id(zombie) == minion_id and not zombie.is_dying() for zombie in self.zombies)
        }

    def _is_flanking_boss(self, zombie: Zombie) -> bool:
        return self._is_boss_enemy(zombie) and hasattr(zombie, "flank_side") and not self._is_summoner_boss_active()

    def _update_flanking_boss(self, zombie: Zombie, dt: float, world_rect: pygame.Rect) -> None:
        if zombie.is_dying():
            zombie.update(self.player.player_position, dt, world_rect)
            return
        player_pos = pygame.Vector2(self.player.player_position)
        partner = next((boss for boss in self._boss_enemies() if boss is not zombie and not boss.is_dying()), None)
        side = float(getattr(zombie, "flank_side", 1.0))
        if partner is not None:
            side = 1.0 if id(zombie) > id(partner) else -1.0

        to_player = player_pos - zombie.position
        if to_player.length_squared() <= 0.01:
            forward = pygame.Vector2(1, 0)
        else:
            forward = to_player.normalize()
        lateral = pygame.Vector2(-forward.y, forward.x) * side
        flank_distance = float(getattr(zombie, "flank_distance", 170.0))
        target = player_pos - forward * min(95.0, max(45.0, zombie.attack_range + 28.0)) + lateral * flank_distance
        target.x = max(32, min(WORLD_WIDTH - 32, target.x))
        target.y = max(32, min(WORLD_HEIGHT - 32, target.y))

        if zombie.position.distance_to(player_pos) <= zombie.attack_range + 22:
            zombie.update(self.player.player_position, dt, world_rect)
        else:
            zombie.update(tuple(target), dt, world_rect)

    def _update_summoner_boss(self, dt: float, world_rect: pygame.Rect) -> None:
        boss = self._boss_zombie
        if boss is None:
            return
        if boss.is_dying():
            boss.update(self.player.player_position, dt, world_rect)
            return
        if boss.freeze_timer > 0:
            boss.update(boss.position, dt, world_rect)
            return

        player_pos = pygame.Vector2(self.player.player_position)
        offset = boss.position - player_pos
        if offset.length_squared() <= 0.01:
            offset = pygame.Vector2(1, 0)
        distance = offset.length()

        target_distance = 280.0
        if distance < target_distance:
            direction = offset.normalize()
        else:
            arena_center = pygame.Vector2(WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.5)
            direction = arena_center - boss.position
            if direction.length_squared() <= 0.01:
                direction = offset.rotate(90)
            direction = direction.normalize()

        boss.facing_direction = boss._direction_from_vector(player_pos - boss.position)
        boss.position += direction * boss.speed * dt
        boss._clamp_to_world(world_rect)
        boss.update(boss.position, dt, world_rect)

        self._summoner_timer -= dt
        stats = self._boss_stats_for_map()
        loop_level = self._boss_loop_level()
        living_minions = len(self._summoner_minion_ids)
        summon_max = int(
            stats.get("phase_two_summon_max", stats.get("summon_max", 10))
            if self._boss_phase_two_active
            else stats.get("summon_max", 10)
        ) + loop_level * 3
        if loop_level == 0:
            summon_max = max(8, summon_max - 6)
        if self._summoner_timer <= 0 and living_minions < summon_max:
            small_count = int(
                stats.get("phase_two_small_count", stats.get("summon_count", 4))
                if self._boss_phase_two_active
                else stats.get("summon_count", 4)
            ) + loop_level
            axe_count = (int(stats.get("phase_two_axe_count", 0)) + loop_level) if self._boss_phase_two_active else 0
            if loop_level == 0:
                small_count = max(2, small_count - 1)
                axe_count = max(0, axe_count - 1)
            total_count = min(small_count + axe_count, summon_max - living_minions)
            if total_count > 0:
                axe_count = min(axe_count, total_count)
                small_count = total_count - axe_count
                self._summon_boss_wave(small_count, axe_count)
            interval_key = "phase_two_summon_interval" if self._boss_phase_two_active else "summon_interval"
            interval = float(stats.get(interval_key, stats.get("summon_interval", 7.0)))
            if loop_level == 0:
                interval += 0.9
            self._summoner_timer = interval * max(0.68, 1.0 - loop_level * 0.08)

    def _summon_boss_wave(self, small_count: int, axe_count: int = 0) -> None:
        boss = self._boss_zombie
        total_count = small_count + axe_count
        if boss is None or total_count <= 0:
            return

        variants = ["small"] * small_count + ["axe"] * axe_count
        random.shuffle(variants)
        for index, variant_name in enumerate(variants):
            angle = (360.0 / max(1, total_count)) * index + random.uniform(-18.0, 18.0)
            spawn_base = boss.position + pygame.Vector2(1, 0).rotate(angle) * random.randint(90, 155)
            zombie = self._spawn_zombie(spawn_base, forced_variant=variant_name)
            if zombie is not None:
                if variant_name == "axe":
                    zombie.can_throw_axe = True
                self._summoner_minion_ids.add(id(zombie))
                self._add_alert_popup(zombie.position)

        self._play_sfx("zombie_alert")
        self._set_message("A criatura chamou mais mortos!")

    def _update_shot_impacts(self, dt: float) -> None:
        for impact in self.shot_impacts:
            impact.update(dt)
        self.shot_impacts = [impact for impact in self.shot_impacts if not impact.is_finished()]

    def _spawn_axe_projectile(self, zombie: Zombie) -> None:
        target = pygame.Vector2(self.player.player_position)
        direction = target - zombie.position
        if direction.length_squared() <= 0.01:
            direction = pygame.Vector2(1, 0)
        origin = zombie.position + direction.normalize() * max(18, zombie.radius * 0.7)
        self.axe_projectiles.append(
            AxeProjectile(
                origin,
                direction,
                damage=max(12, int(zombie.attack_damage * 0.9)),
                sprite_scale=zombie.sprite_scale,
            )
        )

    def _update_axe_projectiles(self, dt: float) -> None:
        for projectile in self.axe_projectiles:
            projectile.update(dt)
            if projectile.can_damage_player(self.player.player_position, self.player.radius):
                projectile.has_hit = True
                if self.player.take_damage(projectile.damage):
                    self._play_sfx("player_damage")
                    self._set_message("Machado arremessado!")
                continue
            if (
                projectile.position.x < 0
                or projectile.position.y < 0
                or projectile.position.x > WORLD_WIDTH
                or projectile.position.y > WORLD_HEIGHT
                or self._is_position_blocked(projectile.position, projectile.radius)
            ):
                projectile.has_hit = True

        self.axe_projectiles = [projectile for projectile in self.axe_projectiles if not projectile.is_finished()]

    def _update_boss_phase(self) -> None:
        boss = self._boss_zombie
        if boss is None or boss.is_dying() or self._boss_phase_two_active:
            return
        stats = self._boss_stats_for_map()
        if boss.health > boss.max_health * 0.5:
            return

        self._boss_phase_two_active = True
        if str(stats.get("zombie_type", "")) == "axe":
            boss.can_throw_axe = True
            boss.attack_damage = max(boss.attack_damage, int(stats.get("attack_damage", boss.attack_damage)) + 4)
            boss.attack_range = max(boss.attack_range, float(stats.get("attack_range", boss.attack_range)))
        elif self._is_summoner_boss_active():
            self._summoner_timer = 0.2
        self._play_sfx("zombie_alert")
        self._set_message(str(stats.get("phase_two_message", "Segunda fase!")))

    def _update_spawns(self, dt: float) -> None:
        if self._inside_interior or self._is_boss_map_path():
            return

        self._spawn_timer += dt
        if self._is_horde_map():
            max_zombies = 12 + self._progress_level * 3 + int(self.game_time / 120.0)
            spawn_interval = max(5.5, 13.0 / max(0.6, self.spawn_rate))
            spawn_count = random.randint(2, 3 + min(2, self._progress_level))
        else:
            max_zombies = 3 + min(6, self._progress_level) + int(self.game_time / 210.0)
            spawn_interval = max(12.0, 36.0 / max(0.6, self.spawn_rate))
            spawn_count = 1

        if self._spawn_timer >= spawn_interval and len(self.zombies) < max_zombies:
            self._spawn_timer = 0.0
            for _ in range(min(spawn_count, max_zombies - len(self.zombies))):
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

    def _triggers_in_range(self, triggers: List[MapTrigger], max_distance: float) -> List[MapTrigger]:
        player_pos = pygame.Vector2(self.player.player_position)
        active_triggers: list[tuple[float, MapTrigger]] = []

        for trigger in triggers:
            distance = trigger.position.distance_to(player_pos)
            effective_distance = max(float(trigger.radius), max_distance)
            if distance <= effective_distance:
                active_triggers.append((distance, trigger))

        active_triggers.sort(key=lambda item: item[0])
        return [trigger for _, trigger in active_triggers]

    def _sync_exit_trigger_state(self) -> None:
        self._occupied_exit_triggers = {
            id(trigger) for trigger in self._triggers_in_range(self.exits, EXIT_RANGE)
        }

    def _handle_map_transitions(self, interact_pressed: bool) -> bool:
        if self._transition_cooldown > 0:
            return False

        exit_triggers = self._triggers_in_range(self.exits, EXIT_RANGE)
        new_exit_trigger = next(
            (trigger for trigger in exit_triggers if id(trigger) not in self._occupied_exit_triggers),
            None,
        )
        self._occupied_exit_triggers = {id(trigger) for trigger in exit_triggers}
        if new_exit_trigger is not None:
            self._use_map_exit(new_exit_trigger)
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
            rewards = self._corpse_loot_rewards(corpse)
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

    def _corpse_loot_rewards(self, corpse: Zombie) -> Dict[str, int]:
        rewards: Dict[str, int] = {}
        if self._is_boss_map_path():
            loot_pool = [
                "balas",
                "balas",
                "balas",
                "cartuchos",
                "kit_medico",
                "comida",
                "balas_incendiarias",
                "balas_perfurantes",
                "cartuchos_incendiarios",
            ]
            rolls = random.randint(2, 3)
        else:
            loot_pool = ["pano", "balas", "balas", "polvora", "comida"]
            rolls = random.randint(1, 2)

        for _ in range(rolls):
            item = random.choice(loot_pool)
            amount_range = AMMO_LOOT_RANGES.get(item)
            amount = random.randint(*amount_range) if amount_range is not None else 1
            if item == "kit_medico" and corpse is self._boss_zombie:
                amount += 1
            rewards[item] = rewards.get(item, 0) + amount
        return rewards

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

    def _grant_boss_rewards(self) -> None:
        rewards: Dict[str, int] = {
            "balas_incendiarias": random.randint(8, 14),
            "balas_perfurantes": random.randint(8, 14),
            "cartuchos_incendiarios": random.randint(4, 7),
            "kit_medico": 1,
        }
        missing_weapons = [
            weapon_name
            for weapon_name in ("pistola_incendiaria", "pistola_perfurante", "escopeta_incendiaria")
            if self.inventory.get_quantity(weapon_name) <= 0
        ]
        for weapon_name in missing_weapons:
            rewards[weapon_name] = 1
        if not missing_weapons:
            rewards.update({"metal": 6, "polvora": 4})

        granted = self._grant_rewards(rewards)
        self._add_item_popups(granted, self._boss_zombie.position if self._boss_zombie is not None else None)

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

        if ammo_cost > 0 and not self._infinite_ammo and self.inventory.get_quantity(ammo_item) < ammo_cost:
            self._play_sfx("gun_empty")
            self._set_message(f"Sem {ITEM_LABELS.get(ammo_item, ammo_item)}.")
            self._attack_timer = 0.2
            return

        player_pos = pygame.Vector2(self.player.player_position)
        self.player.start_attack_animation()
        if ammo_cost > 0:
            if not self._infinite_ammo:
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
                    self._damage_zombie(zombie, pellet_damage, stats)
                impact_position = shot_origin + (direction * hits[-1][1])
                hit_any = True

            impact_position.x = max(0, min(WORLD_WIDTH, impact_position.x))
            impact_position.y = max(0, min(WORLD_HEIGHT, impact_position.y))
            if effect == "fire":
                self._apply_fire_splash(impact_position, stats, {id(zombie) for zombie, _ in hits})
            self.shot_impacts.append(ShotImpact(impact_position, shot_origin, projectile_color, effect))

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
            self._damage_zombie(zombie, max(1, int(damage * falloff)), stats)

    def _handle_zombie_death(self, zombie: Zombie) -> None:
        if zombie.is_dying() and not zombie.loot_given:
            zombie.loot_given = True
            self._play_sfx("zombie_death")
            if self._is_boss_enemy(zombie):
                if self._all_boss_enemies_defeated():
                    self._complete_boss_defeat()
                else:
                    self._set_message("Um chefe caiu. O outro ainda bloqueia a saida.")
            else:
                self._set_message("Zumbi abatido. Vasculhe o corpo com E.")

    def _all_boss_enemies_defeated(self) -> bool:
        bosses = self._boss_enemies()
        return bool(bosses) and all(boss.is_dying() for boss in bosses)

    def _complete_boss_defeat(self) -> None:
        if self._boss_defeated:
            return
        self._boss_defeated = True
        self._bosses_defeated += 1
        self._progress_level += 1
        if self._is_summoner_boss_active():
            self._despawn_summoner_minions()
        self._grant_boss_rewards()
        self._play_active_music()
        self._set_message("Chefe derrotado. Teleportes liberados.")

    def _despawn_summoner_minions(self) -> None:
        if not self._summoner_minion_ids:
            return
        self.zombies = [
            zombie
            for zombie in self.zombies
            if id(zombie) not in self._summoner_minion_ids or self._is_boss_enemy(zombie)
        ]
        self._summoner_minion_ids.clear()

    def _damage_zombie(self, zombie: Zombie, damage: int, stats: Dict[str, object] | None = None) -> None:
        shielded = False
        if self._is_boss_enemy(zombie) and self._is_summoner_boss_active() and self._summoner_minion_ids:
            if self._boss_loop_level() > 0:
                reduction = float(self._boss_stats_for_map().get("shield_reduction", 0.45))
                damage = max(1, int(damage * reduction))
                shielded = True
        zombie.take_damage(damage)
        self._apply_weapon_status(zombie, stats)
        if zombie.is_dying() and not zombie.loot_given:
            self._handle_zombie_death(zombie)
        else:
            self._play_sfx("hit_flesh")
            self._set_message("A horda protege o chefe!" if shielded else "Acerto!")

    def _apply_weapon_status(self, zombie: Zombie, stats: Dict[str, object] | None) -> None:
        if stats is None or zombie.is_dying():
            return
        effect = str(stats.get("effect", ""))
        if effect == "fire":
            zombie.apply_burn(
                float(stats.get("burn_duration", 3.0)),
                float(stats.get("burn_dps", 7.0)),
            )
        elif effect == "ice":
            zombie.apply_freeze(float(stats.get("freeze_duration", 1.8)))

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

    def _is_gameplay_paused_by_panel(self) -> bool:
        return self._show_inventory or self._show_crafting

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

        if self._show_tutorial:
            return

        if self._is_gameplay_paused_by_panel():
            self._handle_crafting(craft_pressed)
            return

        self._attack_timer = max(0.0, self._attack_timer - dt)
        self._transition_cooldown = max(0.0, self._transition_cooldown - dt)
        self._update_difficulty(dt)
        self._update_survival(dt)
        previous_player_position = pygame.Vector2(self.player.player_position)
        self.player.move(direction, dt, running)
        self.player.clamp_to_area(WORLD_WIDTH, WORLD_HEIGHT)
        self._resolve_player_collisions(previous_player_position)
        if self._gamepad_aim_vector.length_squared() > 0.04:
            aim_target = pygame.Vector2(self.player.player_position) + self._gamepad_aim_vector.normalize() * 120
            self.player.aim_at(aim_target)
        else:
            self.player.aim_at(self.screen_to_world(self._window_to_screen(pygame.mouse.get_pos())))
        self.player.update(dt)

        self._update_spawns(dt)
        self._update_zombies(dt)
        self._update_boss_phase()
        self._update_axe_projectiles(dt)
        self._update_shot_impacts(dt)
        self._update_floating_popups(dt)
        transition_used = self._handle_map_transitions(search_pressed)
        if not transition_used:
            self._handle_search(search_pressed)
        self._handle_attack(attack_pressed)
        self._handle_heal(heal_pressed)
        self._handle_crafting(craft_pressed)

        if self.player.is_dead():
            self._return_to_title_after_death()

    def _return_to_title_after_death(self) -> None:
        self._game_over = True
        self._show_inventory = False
        self._show_crafting = False
        self._show_tutorial = False
        self._screen_state = "main_menu"
        self._menu_selected_index = 0
        self._play_title_music()
        self._set_menu_message("Voce morreu. Prepare outra tentativa.")

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

        self._present_frame()

    def _draw_menu_background_overlay(self) -> None:
        self.screen.blit(self._menu_overlay, (0, 0))

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
        shadow = self._menu_title_layers["shadow"]
        accent = self._menu_title_layers["accent"]
        text = self._menu_title_layers["text"]
        title_rect = text.get_rect(center=(WIDTH // 2, 70 + bob))
        self.screen.blit(shadow, title_rect.move(5, 5))
        self.screen.blit(accent, title_rect.move(-2, 2))
        self.screen.blit(text, title_rect)
        if int(ticks * 5) % 11 == 0:
            glitch = self._menu_title_layers["glitch"]
            self.screen.blit(glitch, title_rect.move(2, -1))
            self.screen.blit(glitch, title_rect.move(-2, 1))

        subtitle = self._menu_title_layers["subtitle"]
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 118)))

    def _draw_menu_panel(self, rect: pygame.Rect) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 232), panel.get_rect())
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 2)
        pygame.draw.rect(panel, (28, 34, 37, 210), panel.get_rect().inflate(-10, -10), 1)
        self.screen.blit(panel, rect)

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        lines: List[str] = []
        current = ""
        for word in text.split():
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_tutorial_paragraph(
        self,
        text: str,
        font: pygame.font.Font,
        x: int,
        y: int,
        max_width: int,
    ) -> int:
        single_button_tokens = {"WASD", "SHIFT", "ESPACO", "E", "I", "B", "C", "Q", "ESC", "ENTER", "1", "2", "3", "4", "5", "6"}
        button_phrases = (("scroll", "do", "mouse"), ("mouse", "esquerdo"))
        raw_words = text.split()
        highlighted_indexes: set[int] = set()
        normalized_words = [word.strip(".,;:!?()").lower() for word in raw_words]
        for start in range(len(raw_words)):
            for phrase in button_phrases:
                if tuple(normalized_words[start : start + len(phrase)]) == phrase:
                    highlighted_indexes.update(range(start, start + len(phrase)))

        line_words: List[Tuple[str, bool]] = []
        line_width = 0
        space_width = font.size(" ")[0]

        def is_highlighted_word(index: int, word: str) -> bool:
            if index in highlighted_indexes:
                return True
            stripped = word.strip(".,;:!?()")
            return stripped in single_button_tokens

        def flush_line(current_y: int) -> int:
            draw_x = x
            for word, highlighted in line_words:
                surface = font.render(word, True, PALETTE["accent"] if highlighted else PALETTE["text"])
                self.screen.blit(surface, (draw_x, current_y))
                draw_x += surface.get_width() + space_width
            return current_y + font.get_height() + 4

        for index, word in enumerate(raw_words):
            word_width = font.size(word)[0]
            candidate_width = word_width if not line_words else line_width + space_width + word_width
            if line_words and candidate_width > max_width:
                y = flush_line(y)
                line_words = [(word, is_highlighted_word(index, word))]
                line_width = word_width
            else:
                line_words.append((word, is_highlighted_word(index, word)))
                line_width = candidate_width
        if line_words:
            y = flush_line(y)
        return y

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

    def _resolve_player_collisions(self, previous_position: pygame.Vector2 | None = None) -> None:
        if not self.collision_rects:
            return

        position = pygame.Vector2(self.player.player_position)
        if previous_position is not None:
            previous_position = pygame.Vector2(previous_position)
            target_position = position.copy()
            position = previous_position.copy()
            position = self._resolve_player_axis(position, target_position.x, axis="x")
            position = self._resolve_player_axis(position, target_position.y, axis="y")
        else:
            player_rect = self._entity_collision_rect(position, self.player.radius)

            for rect in self._nearby_collision_rects(player_rect.inflate(self.player.radius * 4, self.player.radius * 4)):
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

    def _resolve_player_axis(self, position: pygame.Vector2, target_value: float, axis: str) -> pygame.Vector2:
        resolved = position.copy()
        if axis == "x":
            delta = target_value - resolved.x
            if abs(delta) <= 0.001:
                return resolved
            resolved.x = target_value
        else:
            delta = target_value - resolved.y
            if abs(delta) <= 0.001:
                return resolved
            resolved.y = target_value

        collision_rect = self._entity_collision_rect(resolved, self.player.radius)
        nearby_rects = self._nearby_collision_rects(collision_rect.inflate(self.player.radius * 3, self.player.radius * 3))
        for rect in nearby_rects:
            if not collision_rect.colliderect(rect):
                continue

            if axis == "x":
                if delta > 0:
                    resolved.x = rect.left - self.player.radius
                else:
                    resolved.x = rect.right + self.player.radius
            else:
                if delta > 0:
                    resolved.y = rect.top - self.player.radius
                else:
                    resolved.y = rect.bottom
            collision_rect = self._entity_collision_rect(resolved, self.player.radius)

        return resolved

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
        return any(collision_rect.colliderect(rect) for rect in self._nearby_collision_rects(collision_rect))

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
        for rect in self._nearby_collision_rects(collision_rect.inflate(radius * 4, radius * 4)):
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
        bucket_size = ZOMBIE_SEPARATION_BUCKET_SIZE
        for _ in range(ZOMBIE_SEPARATION_ITERATIONS):
            buckets: Dict[Tuple[int, int], List[int]] = {}
            for index, zombie in enumerate(living_zombies):
                bucket_key = (int(zombie.position.x) // bucket_size, int(zombie.position.y) // bucket_size)
                buckets.setdefault(bucket_key, []).append(index)

            for bucket_key, indices in buckets.items():
                bucket_x, bucket_y = bucket_key
                nearby_indices: List[int] = []
                for offset_y in (-1, 0, 1):
                    for offset_x in (-1, 0, 1):
                        nearby_indices.extend(buckets.get((bucket_x + offset_x, bucket_y + offset_y), ()))

                for index in indices:
                    zombie = living_zombies[index]
                    for other_index in nearby_indices:
                        if other_index <= index:
                            continue
                        other = living_zombies[other_index]
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
        if self._show_tutorial:
            self._draw_tutorial_overlay()
        self._draw_gamepad_debug()

        if self._message_timer > 0:
            self._message_timer = max(0.0, self._message_timer - dt)

        self._present_frame()

    def _draw_world_scene(self) -> None:
        self._draw_ground()

        dynamic_drawables: List[Tuple[float, int, object]] = []
        for zombie in self.zombies:
            dynamic_drawables.append((zombie.position.y, 3, zombie))
        for projectile in self.axe_projectiles:
            dynamic_drawables.append((projectile.position.y, 5, projectile))
        for impact in self.shot_impacts:
            dynamic_drawables.append((impact.position.y, 5, impact))
        dynamic_drawables.append((self.player.player_position[1], 4, self.player))
        dynamic_drawables.sort(key=lambda item: (item[0], item[1]))

        static_index = 0
        dynamic_index = 0
        while static_index < len(self._static_world_drawables) and dynamic_index < len(dynamic_drawables):
            static_item = self._static_world_drawables[static_index]
            dynamic_item = dynamic_drawables[dynamic_index]
            if (static_item[0], static_item[1]) <= (dynamic_item[0], dynamic_item[1]):
                static_item[2].draw(self.screen, self._camera)
                static_index += 1
            else:
                dynamic_item[2].draw(self.screen, self._camera)
                dynamic_index += 1

        for _, _, drawable in self._static_world_drawables[static_index:]:
            drawable.draw(self.screen, self._camera)
        for _, _, drawable in dynamic_drawables[dynamic_index:]:
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
        self._camera.x = round(self._camera.x)
        self._camera.y = round(self._camera.y)

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

        overlay = self._damage_overlay
        overlay.fill((0, 0, 0, 0))
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
        self._draw_boss_health_bar()
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

    def _draw_tutorial_overlay(self) -> None:
        pages = self._tutorial_pages()
        page_index = max(0, min(self._tutorial_page, len(pages) - 1))
        title, paragraphs = pages[page_index]

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 10, 176))
        self.screen.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(0, 0, 690, 360)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2)
        self._draw_menu_panel(panel_rect)

        title_text = self.menu_font.render(title.upper(), True, PALETTE["accent"])
        self.screen.blit(title_text, (panel_rect.x + 34, panel_rect.y + 26))

        page_text = self.small_font.render(f"{page_index + 1}/{len(pages)}", True, PALETTE["text_soft"])
        self.screen.blit(page_text, page_text.get_rect(topright=(panel_rect.right - 34, panel_rect.y + 28)))

        y = panel_rect.y + 78
        max_width = panel_rect.width - 74
        for paragraph in paragraphs:
            y = self._draw_tutorial_paragraph(paragraph, self.font, panel_rect.x + 38, y, max_width)
            y += 12

        hint = "Enter Espaco E ou clique avanca    Esc pula"
        if page_index == len(pages) - 1:
            hint = "Enter Espaco E ou clique comeca    Esc pula"
        hint_width = self.small_font.size(hint)[0]
        self._draw_tutorial_paragraph(
            hint,
            self.small_font,
            panel_rect.centerx - hint_width // 2,
            panel_rect.bottom - 42,
            panel_rect.width - 70,
        )

    def _draw_boss_health_bar(self) -> None:
        boss = next((boss for boss in self._boss_enemies() if not boss.is_dying()), self._boss_zombie)
        if boss is None or boss.is_dying():
            return

        width = 520
        height = 18
        x = (WIDTH - width) // 2
        y = 18
        ratio = max(0.0, min(1.0, boss.health / max(1, boss.max_health)))
        frame_rect = pygame.Rect(x, y, width, height)
        fill_rect = frame_rect.inflate(-4, -4)
        fill_rect.width = int((width - 8) * ratio)

        panel = pygame.Surface((width, 38), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 10, 12, 218), pygame.Rect(0, 8, width, height + 8))
        pygame.draw.rect(panel, PALETTE["panel_edge"], pygame.Rect(0, 8, width, height + 8), 2)
        pygame.draw.rect(panel, (82, 18, 22), pygame.Rect(4, 12, width - 8, height))
        pygame.draw.rect(panel, (202, 55, 50), pygame.Rect(4, 12, fill_rect.width, height))
        pygame.draw.rect(panel, (255, 148, 110), pygame.Rect(4, 12, fill_rect.width, 4))

        if self._boss_name:
            title = self.small_font.render(self._boss_name, True, PALETTE["text"])
            panel.blit(title, title.get_rect(center=(width // 2, 7)))
        self.screen.blit(panel, (x, y))

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

        count_label = "INF" if self._infinite_ammo and int(stats.get("ammo", 0)) > 0 else str(ammo_count)
        count_text = self.font.render(count_label, True, PALETTE["text"])
        self.screen.blit(count_text, count_text.get_rect(midleft=(x + 48, y + 18)))

        bullet_x = x + 94
        for index in range(visible_rounds):
            loaded_rounds = visible_rounds if self._infinite_ammo and int(stats.get("ammo", 0)) > 0 else min(ammo_count, visible_rounds)
            sprite = bullet if index < loaded_rounds else empty_bullet
            bullet_pos = (bullet_x + index * (sprite.get_width() + 4), y)
            self.screen.blit(sprite, bullet_pos)
            if isinstance(projectile_color, tuple) and ammo_item != "balas":
                marker_rect = pygame.Rect(bullet_pos[0] + 2, bullet_pos[1] + sprite.get_height() - 4, sprite.get_width() - 4, 3)
                marker = pygame.Surface(marker_rect.size, pygame.SRCALPHA)
                marker.fill((*projectile_color, 95))
                self.screen.blit(marker, marker_rect)

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
        row_height = 68
        visible_count = max(1, available_height // (row_height + gap))
        max_scroll = max(0, len(recipe_names) - visible_count)
        self._crafting_scroll_index = max(0, min(self._crafting_scroll_index, max_scroll))
        visible_recipes = recipe_names[self._crafting_scroll_index : self._crafting_scroll_index + visible_count]
        start_y = panel_rect.y + 62
        for index, recipe_name in enumerate(visible_recipes):
            rect = pygame.Rect(
                panel_rect.x + 26,
                start_y + index * (row_height + gap),
                row_width,
                row_height,
            )
            rects.append((recipe_name, rect))
        return rects

    def _scroll_crafting(self, direction: int) -> None:
        recipe_names = self._available_recipe_names()
        panel_rect = self._crafting_panel_rect()
        row_height = 68
        gap = 8
        available_height = max(120, panel_rect.height - 92)
        visible_count = max(1, available_height // (row_height + gap))
        max_scroll = max(0, len(recipe_names) - visible_count)
        new_index = max(0, min(max_scroll, self._crafting_scroll_index + direction))
        if new_index != self._crafting_scroll_index:
            self._crafting_scroll_index = new_index
            self._play_sfx("inventory_move")

    def _draw_crafting_panel(self) -> None:
        panel = _load_ui_sprite("Crafting-main-menu.png", 5)
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", 4)
        panel_rect = self._crafting_panel_rect()
        self.screen.blit(panel, panel_rect)
        self.screen.blit(close_button, self._crafting_close_button_rect())

        title = self.font.render("CRAFTING", True, PALETTE["text"])
        self.screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))

        recipe_names = self._available_recipe_names()
        cell_scale = 2
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
                row_surface = _desaturate_sprite(row_surface, 0.86)

            self.screen.blit(row_surface, row_rect)
            if craftable:
                pygame.draw.rect(self.screen, PALETTE["accent"], row_rect, 2, border_radius=4)

        self._draw_crafting_scrollbar(panel_rect, len(recipe_names), len(self._crafting_recipe_rects()))

    def _draw_crafting_scrollbar(self, panel_rect: pygame.Rect, recipe_count: int, recipe_rect_count: int) -> None:
        if recipe_count <= recipe_rect_count:
            return
        track = pygame.Rect(panel_rect.right - 18, panel_rect.y + 62, 5, panel_rect.height - 98)
        max_scroll = max(1, recipe_count - recipe_rect_count)
        handle_height = max(24, int(track.height * (recipe_rect_count / max(1, recipe_count))))
        handle_y = track.y + int((track.height - handle_height) * (self._crafting_scroll_index / max_scroll))
        pygame.draw.rect(self.screen, (38, 42, 44), track, border_radius=2)
        pygame.draw.rect(self.screen, PALETTE["accent"], pygame.Rect(track.x, handle_y, track.width, handle_height), border_radius=2)

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
                icon = _desaturate_sprite(icon, 0.86)
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
            dt = self.clock.tick(TARGET_FPS) / 1000.0
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
