from __future__ import annotations

from pathlib import Path
import random
from typing import Dict, List, Tuple

import pygame

from crafting import CraftingSystem
from inventory import Inventory
from map_loader import TiledMap
from player import Player
from save_system import load_game, save_game
from weapons import WEAPONS
from zombie import Zombie


WIDTH, HEIGHT = 960, 540
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
WORLD_WIDTH, WORLD_HEIGHT = 2200, 1400
PROJECT_ROOT = Path(__file__).resolve().parent
MAP_ROOT = PROJECT_ROOT.parent
MAP_SEQUENCE = [
    MAP_ROOT / "Mapa 1.1.tmj",
]
INTERIOR_MAP_PATHS = [
    MAP_ROOT / "interior 1.1.tmj",
    MAP_ROOT / "Interior 1.tmj",
]
TILED_MAP_PATH = MAP_SEQUENCE[0]
TILED_MAP_SCALE = 2
BG_COLOR = (24, 29, 31)
SEARCH_RANGE = 50
DOOR_RANGE = 74
EXIT_RANGE = 64
SAFE_ZONE_RADIUS = 170
ZOMBIE_AVOIDANCE_ANGLES = (0, 25, -25, 50, -50, 85, -85, 125, -125, 180)
ZOMBIE_SEPARATION_STRENGTH = 58.0
ZOMBIE_SEPARATION_ITERATIONS = 2

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
    "safe_fill": (80, 107, 110),
    "safe_ring": (150, 192, 192),
    "safe_core": (228, 234, 219),
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
        "loot": ["metal", "metal", "balas", "balas", "balas", "pistola", "polvora", "comida"],
        "drops": (0, 4),
        "ambush": 0.18,
    },
    "edificio": {
        "label": "Predio abandonado",
        "color": (155, 142, 91),
        "loot": ["pano", "balas", "balas", "balas", "polvora", "pistola", "pistola", "escopeta", "kit_medico"],
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
    "comida",
    "kit_medico",
    "taco",
    "pistola",
    "escopeta",
]
ITEM_LABELS = {
    "madeira": "MAD",
    "metal": "MET",
    "pano": "PAN",
    "erva": "ERV",
    "polvora": "POL",
    "balas": "BAL",
    "comida": "COM",
    "kit_medico": "KIT",
    "maos": "MAO",
    "taco": "TAC",
    "pistola": "PIS",
    "escopeta": "ESC",
}
ITEM_ICONS = {
    "madeira": "Icon_Wooden-wall.png",
    "metal": "Icon_Rock.png",
    "pano": "Icon_Bandage.png",
    "erva": "Icon_Bandage.png",
    "polvora": "Icon_Bullet-crate_Red.png",
    "balas": "Icon_Bullet-box_Red.png",
    "taco": "Icon_Bat.png",
    "pistola": "Icon_Pistol.png",
    "escopeta": "Icon_Shotgun.png",
    "comida": "Icon_Canned-food.png",
    "kit_medico": "Icon_First-Aid-Kit_Red.png",
}
WEAPON_ITEMS = {"maos", "taco", "pistola", "escopeta"}
CONSUMABLE_ITEMS = {"comida", "kit_medico"}

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
            amount = random.randint(3, 8) if item == "balas" else 1
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

        if not self.searched:
            pygame.draw.circle(surface, PALETTE["accent"], sprite_rect.center, self.radius + 4, 1)
        if self.searched:
            center = pygame.Vector2(sprite_rect.center)
            pygame.draw.line(surface, PALETTE["text"], center + (-8, -8), center + (8, 8), 2)


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
    ) -> None:
        self.position = pygame.Vector2(position)
        self.origin = pygame.Vector2(origin) if origin is not None else self.position.copy()
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
            pygame.draw.line(trail, (255, 224, 120, alpha), start, end, 2)
            pygame.draw.circle(trail, (255, 245, 190, min(255, alpha + 35)), bullet_pos, 3)
            surface.blit(trail, (0, 0))

        frame_index = min(int(self.animation_time), len(self.frames) - 1)
        sprite = self.frames[frame_index]
        surface.blit(sprite, sprite.get_rect(center=(round(end.x), round(end.y))))


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Jogo de Sobrevivencia Zumbi")
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 16)

        self.game_time: float = 0.0
        self.difficulty_scale: float = 1.0
        self.spawn_rate: float = 1.0
        self.is_game_running: bool = True

        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.crafting = CraftingSystem()

        self.zombies: List[Zombie] = []
        self.shot_impacts: List[ShotImpact] = []
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

        self._recipe_names = self.crafting.get_recipe_names()
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
        self._show_help = False
        self._quick_slots = ["maos", "taco", "pistola", "escopeta", "comida", "kit_medico"]
        self._selected_quick_slot = 0

        self._generate_world()
        self.player.set_position(tuple(self._base_position))
        self.inventory.add_item("comida", 2)

    @staticmethod
    def _first_existing_path(paths: List[Path], fallback: Path) -> Path:
        for path in paths:
            if path.exists():
                return path
        return fallback

    def _clear_world_content(self) -> None:
        self.nodes.clear()
        self.zombies.clear()
        self.shot_impacts.clear()
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
            self._set_message("Nenhum interior configurado.")
            return

        self._return_map_path = self._current_map_path
        self._return_map_index = self._current_map_index
        self._return_position = self._find_open_position_near(door.position + pygame.Vector2(0, 78))
        interior_path = random.choice(interior_paths)
        if self._switch_to_tiled_map(interior_path, inside_interior=True):
            self._set_message("Voce entrou no predio.")

    def _leave_interior(self) -> None:
        if self._return_map_path is None or self._return_position is None:
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
            self._set_message("Voce saiu do predio.")

    def _use_map_exit(self, trigger: MapTrigger) -> None:
        available_maps = [path for path in MAP_SEQUENCE if path.exists()]
        if not available_maps:
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
        self._set_message("Voce continuou pela rua.")

    def _populate_decorations(self) -> None:
        decor_plan = [
            ("tree", 20, 130, SAFE_ZONE_RADIUS + 120, (0.95, 1.0, 1.08, 1.16)),
            ("bush", 16, 110, SAFE_ZONE_RADIUS + 90, (0.9, 1.0, 1.08)),
            ("rock", 10, 100, SAFE_ZONE_RADIUS + 85, (0.9, 1.0, 1.1)),
            ("vehicle", 7, 180, SAFE_ZONE_RADIUS + 150, (0.95, 1.0, 1.05)),
            ("container", 5, 180, SAFE_ZONE_RADIUS + 160, (0.95, 1.0)),
            ("building", 5, 220, SAFE_ZONE_RADIUS + 200, (0.95, 1.0, 1.05)),
            ("street_light", 8, 120, SAFE_ZONE_RADIUS + 100, (1.0, 1.1)),
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
                        self.is_game_running = False
                elif event.key == pygame.K_c:
                    if self._quick_slots[self._selected_quick_slot] in CONSUMABLE_ITEMS:
                        heal_pressed = True
                    else:
                        search_pressed = True
                elif event.key == pygame.K_b:
                    self._show_crafting = not self._show_crafting
                    if self._show_crafting:
                        self._show_inventory = False
                elif event.key == pygame.K_TAB:
                    self._cycle_recipe()
                elif event.key == pygame.K_e:
                    search_pressed = True
                elif event.key == pygame.K_i:
                    self._show_inventory = not self._show_inventory
                    if self._show_inventory:
                        self._show_crafting = False
                elif event.key == pygame.K_h:
                    self._show_help = not self._show_help
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
                elif event.key == pygame.K_F5:
                    save_game("savegame.json", self.player, self.inventory, self.game_time)
                    self._set_message("Jogo salvo.")
                elif event.key == pygame.K_F9:
                    data = load_game("savegame.json")
                    if data is None:
                        self._set_message("Sem save encontrado.")
                    else:
                        self._apply_loaded_state(data)
                        self._set_message("Save carregado.")
            elif event.type == pygame.MOUSEWHEEL:
                self._cycle_quick_slot(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._window_to_screen(event.pos)
                if self._show_inventory:
                    if self._inventory_close_button_rect().collidepoint(mouse_pos):
                        self._show_inventory = False
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
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        return direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed

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
                    self._set_message("Voce esta morrendo de fome!")
        else:
            self._starvation_timer = 0.0

    def _update_zombies(self, dt: float) -> None:
        base_pos = pygame.Vector2(self._base_position)
        world_rect = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
        for zombie in self.zombies:
            old_position = zombie.position.copy()
            zombie.update(self.player.player_position, dt, world_rect)
            self._resolve_zombie_obstacles(zombie, old_position, dt)
            if not zombie.is_dying() and zombie.position.distance_to(base_pos) < SAFE_ZONE_RADIUS - 10:
                push_direction = zombie.position - base_pos
                if push_direction.length_squared() > 0:
                    zombie.position += push_direction.normalize() * 110 * dt
                    self._resolve_zombie_obstacles(zombie, old_position, dt)
            if zombie.can_damage_player(self.player.player_position, self.player.radius):
                if self.player.take_damage(10):
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
            corpse.corpse_searched = True
            rewards: Dict[str, int] = {}
            for _ in range(random.randint(1, 2)):
                item = random.choice(["pano", "balas", "balas", "polvora", "comida"])
                amount = random.randint(2, 6) if item == "balas" else 1
                rewards[item] = rewards.get(item, 0) + amount
            for item, amount in rewards.items():
                self.inventory.add_item(item, amount)
            reward_text = ", ".join(f"{item} x{amount}" for item, amount in rewards.items())
            self._set_message(f"Voce vasculhou o corpo: {reward_text}")
            return

        node = self._find_nearest_node()
        if node is None:
            self._set_message("Nada interessante por perto.")
            return

        self.player.start_pickup_animation()
        rewards, ambush_count = node.search()
        for item, amount in rewards.items():
            self.inventory.add_item(item, amount)

        reward_text = ", ".join(f"{item} x{amount}" for item, amount in rewards.items())
        message = f"Voce encontrou: {reward_text}" if reward_text else "Voce vasculhou, mas nao achou nada util."

        for _ in range(ambush_count):
            self._spawn_zombie(node.position)
        if ambush_count > 0:
            message = f"{message} | Emboscada: {ambush_count} zumbi(s)!"
        self._set_message(message)

    def _handle_attack(self, attack_pressed: bool) -> None:
        if not attack_pressed or self._attack_timer > 0:
            return

        stats = WEAPONS.get(self.player.current_weapon, WEAPONS["maos"])
        attack_range = float(stats["range"])
        damage = int(stats["damage"])
        cooldown = float(stats["cooldown"])
        ammo_cost = int(stats.get("ammo", 0))

        if ammo_cost > 0 and self.inventory.get_quantity("balas") < ammo_cost:
            self._set_message("Sem balas.")
            self._attack_timer = 0.2
            return

        player_pos = pygame.Vector2(self.player.player_position)
        self.player.start_attack_animation()
        if ammo_cost > 0:
            self.inventory.remove_item("balas", ammo_cost)
            self._fire_gun(player_pos, attack_range, damage, stats)
        else:
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
        stats: Dict[str, float | int],
    ) -> None:
        mouse_world = self.screen_to_world(self._window_to_screen(pygame.mouse.get_pos()))
        aim = mouse_world - player_pos
        if aim.length_squared() <= 0.01:
            aim = self.player.facing_direction.copy()
        else:
            aim = aim.normalize()

        pellets = int(stats.get("pellets", 1))
        spread = float(stats.get("spread", 0))
        hit_width = float(stats.get("hit_width", 4))
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
            hit = self._find_shot_hit(shot_origin, direction, attack_range, hit_width)
            if hit is None:
                impact_position = shot_origin + (direction * attack_range)
            else:
                zombie, hit_distance = hit
                impact_position = shot_origin + (direction * hit_distance)
                self._damage_zombie(zombie, pellet_damage)
                hit_any = True

            impact_position.x = max(0, min(WORLD_WIDTH, impact_position.x))
            impact_position.y = max(0, min(WORLD_HEIGHT, impact_position.y))
            self.shot_impacts.append(ShotImpact(impact_position, shot_origin))

        if not hit_any:
            self._set_message("Disparo sem alvo.")

    def _find_shot_hit(
        self,
        origin: pygame.Vector2,
        direction: pygame.Vector2,
        max_range: float,
        hit_width: float,
    ) -> Tuple[Zombie, float] | None:
        closest_hit = None
        closest_distance = max_range + 1

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
            if hit_distance < closest_distance:
                closest_distance = hit_distance
                closest_hit = (zombie, hit_distance)

        return closest_hit

    def _damage_zombie(self, zombie: Zombie, damage: int) -> None:
        zombie.take_damage(damage)
        if zombie.is_dying() and not zombie.loot_given:
            zombie.loot_given = True
            self._set_message("Zumbi abatido. Vasculhe o corpo com E.")
        else:
            self._set_message("Acerto!")

    def _handle_heal(self, heal_pressed: bool) -> None:
        if not heal_pressed:
            return

        selected_item = self._quick_slots[self._selected_quick_slot]
        if selected_item == "kit_medico":
            if self.inventory.get_quantity("kit_medico") > 0 and self.player.player_health < self.player.max_health:
                self.inventory.remove_item("kit_medico", 1)
                healed_amount = self.player.heal(55)
                self._set_message(f"Kit medico usado. +{healed_amount} vida.")
                return
            self._set_message("Kit medico indisponivel.")
            return

        if selected_item == "comida":
            if self.inventory.get_quantity("comida") <= 0:
                self._set_message("Comida indisponivel.")
                return
            self.inventory.remove_item("comida", 1)
            hunger_restored = int(self.player.restore_hunger(32))
            healed_amount = self.player.heal(12)
            self._set_message(f"Voce comeu. Fome +{hunger_restored}, vida +{healed_amount}.")
            return

        if self.inventory.get_quantity("kit_medico") > 0 and self.player.player_health < self.player.max_health:
            self.inventory.remove_item("kit_medico", 1)
            healed_amount = self.player.heal(55)
            self._set_message(f"Kit medico usado. +{healed_amount} vida.")
            return

        if self.inventory.get_quantity("comida") <= 0:
            self._set_message("Voce nao tem comida nem kit medico.")
            return

        self.inventory.remove_item("comida", 1)
        hunger_restored = int(self.player.restore_hunger(32))
        healed_amount = self.player.heal(12)
        self._set_message(f"Voce comeu. Fome +{hunger_restored}, vida +{healed_amount}.")

    def _handle_crafting(self, craft_pressed: bool) -> None:
        if not craft_pressed:
            return

        recipe_name = self._get_selected_recipe()
        success, message = self.crafting.craft(recipe_name, self.inventory)
        self._set_message(message)

    def _handle_crafting_click(self, mouse_pos: Tuple[int, int]) -> None:
        if self._crafting_close_button_rect().collidepoint(mouse_pos):
            self._show_crafting = False
            return

        for recipe_name, recipe_rect in self._crafting_recipe_rects():
            if not recipe_rect.collidepoint(mouse_pos):
                continue

            recipe = self.crafting.get_recipe(recipe_name)
            if recipe is None:
                return
            recipe_cost = recipe.get("cost", {})
            if not self.inventory.has_items(recipe_cost):
                self._set_message("Recursos insuficientes.")
                return

            success, message = self.crafting.craft(recipe_name, self.inventory)
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
        self.player.aim_at(self.screen_to_world(self._window_to_screen(pygame.mouse.get_pos())))
        self.player.update(dt)

        self._update_spawns(dt)
        self._update_zombies(dt)
        self._update_shot_impacts(dt)
        transition_used = self._handle_map_transitions(search_pressed)
        if not transition_used:
            self._handle_search(search_pressed)
        self._handle_attack(attack_pressed)
        self._handle_heal(heal_pressed)
        self._handle_crafting(craft_pressed)

        if self.player.is_dead():
            self._game_over = True
            self._set_message("Game Over - pressione ESC")

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

        self._draw_crosshair()
        self._draw_prompt()
        self._draw_ui()
        self._draw_damage_overlay()

        if self._message_timer > 0:
            self._message_timer = max(0.0, self._message_timer - dt)

        scaled_frame = pygame.transform.smoothscale(self.screen, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.window.blit(scaled_frame, (0, 0))
        pygame.display.flip()

    def _update_camera(self) -> None:
        player_pos = pygame.Vector2(self.player.player_position)
        if WORLD_WIDTH <= WIDTH:
            self._camera.x = (WORLD_WIDTH - WIDTH) / 2
        else:
            self._camera.x = max(0, min(WORLD_WIDTH - WIDTH, player_pos.x - (WIDTH / 2)))
        if WORLD_HEIGHT <= HEIGHT:
            self._camera.y = (WORLD_HEIGHT - HEIGHT) / 2
        else:
            self._camera.y = max(0, min(WORLD_HEIGHT - HEIGHT, player_pos.y - (HEIGHT / 2)))

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
            self._draw_base_area()
            border_rect = pygame.Rect(-self._camera.x, -self._camera.y, WORLD_WIDTH, WORLD_HEIGHT)
            pygame.draw.rect(self.screen, PALETTE["border"], border_rect, 8)
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

        self._draw_base_area()
        border_rect = pygame.Rect(-self._camera.x, -self._camera.y, WORLD_WIDTH, WORLD_HEIGHT)
        pygame.draw.rect(self.screen, PALETTE["border"], border_rect, 8)

    def _draw_base_area(self) -> None:
        draw_pos = self._base_position - self._camera
        aura_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(aura_surface, (*PALETTE["safe_fill"], 50), draw_pos, SAFE_ZONE_RADIUS)
        self.screen.blit(aura_surface, (0, 0))
        pygame.draw.circle(self.screen, PALETTE["safe_ring"], draw_pos, SAFE_ZONE_RADIUS, 2)
        pygame.draw.circle(self.screen, PALETTE["safe_core"], draw_pos, 22)
        pygame.draw.circle(self.screen, PALETTE["safe_fill"], draw_pos, 22, 4)

    def _draw_crosshair(self) -> None:
        mouse_pos = self._window_to_screen(pygame.mouse.get_pos())
        pygame.draw.circle(self.screen, (220, 220, 220), mouse_pos, 6, 1)

    def _draw_prompt(self) -> None:
        prompt = ""
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
            prompt = "E sair do predio"
        elif door is not None:
            prompt = "E entrar no predio"
        elif exit_trigger is not None:
            prompt = "Saida para o proximo mapa"
        elif corpse is not None:
            prompt = "E vasculhar corpo"
        elif node is not None:
            label = NODE_TYPES[node.node_type]["label"]
            prompt = f"E buscar em {label}"

        if not prompt:
            return

        text = self.small_font.render(prompt, True, PALETTE["accent"])
        bg_rect = pygame.Rect(0, 0, text.get_width() + 24, 28)
        bg_rect.center = (WIDTH // 2, HEIGHT - 26)
        panel = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 220), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (*PALETTE["accent"], 200), panel.get_rect(), 1, border_radius=8)
        self.screen.blit(panel, bg_rect.topleft)
        text_rect = text.get_rect(center=bg_rect.center)
        self.screen.blit(text, text_rect)

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
        if self._show_help:
            self._draw_help_panel()

        if self._message_timer > 0:
            msg = self.font.render(self._message, True, (255, 210, 80))
            self.screen.blit(msg, (10, HEIGHT - 30))

    def _draw_quick_access_bar(self) -> None:
        scale = 3
        bar = _load_ui_sprite("Quick-Access-Inventory.png", scale)
        bar_rect = bar.get_rect(center=(WIDTH // 2, HEIGHT - 54))
        self.screen.blit(bar, bar_rect)

        slot_size = 19 * scale
        slot_pitch = 21 * scale
        slot_origin = pygame.Vector2(bar_rect.x + scale, bar_rect.y)
        for index, item_name in enumerate(self._quick_slots):
            slot_rect = pygame.Rect(
                round(slot_origin.x + index * slot_pitch),
                round(slot_origin.y),
                slot_size,
                slot_size,
            )
            quantity = self.inventory.get_quantity(item_name)
            if item_name == "maos":
                quantity = 1
            available = quantity > 0
            self._draw_slot_item(slot_rect, item_name, quantity, available)

            if index == self._selected_quick_slot:
                pygame.draw.rect(self.screen, PALETTE["accent"], slot_rect.inflate(5, 5), 2, border_radius=2)

    def _draw_ammo_indicator(self) -> None:
        ammo_count = self.inventory.get_quantity("balas")
        weapon_name = self.player.current_weapon
        if weapon_name == "escopeta":
            bullet_name = "Shotgun-Bullet.png"
            empty_name = "Shotgun-Bullet_Empty.png"
            visible_rounds = 4
        elif weapon_name == "pistola":
            bullet_name = "Pistol-Bullet.png"
            empty_name = "Pistol-Bullet_Empty.png"
            visible_rounds = 6
        else:
            bullet_name = "Gun-Bullet.png"
            empty_name = "Gun-Bullet_Empty.png"
            visible_rounds = 6

        bullet = _load_ui_sprite(bullet_name, 2)
        empty_bullet = _load_ui_sprite(empty_name, 2)
        icon = _load_ui_sprite("Icon_Bullet-box_Red.png", 3)
        x = WIDTH - 164
        y = HEIGHT - 86
        self.screen.blit(icon, icon.get_rect(midleft=(x, y + 18)))

        count_text = self.font.render(str(ammo_count), True, PALETTE["text"])
        self.screen.blit(count_text, count_text.get_rect(midleft=(x + 48, y + 18)))

        bullet_x = x + 94
        for index in range(visible_rounds):
            sprite = bullet if index < min(ammo_count, visible_rounds) else empty_bullet
            self.screen.blit(sprite, (bullet_x + index * (sprite.get_width() + 4), y))

    def _draw_inventory_panel(self) -> None:
        panel_scale = 4
        cell_scale = 4
        panel = _load_ui_sprite("Inventory_1_Scrollbar.png", panel_scale)
        cell = _load_ui_sprite("Inventory-Cell.png", cell_scale)
        close_button = _load_ui_sprite("Inventory_Close_Not-Pressed.png", panel_scale)
        panel_rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(panel, panel_rect)

        title = self.font.render("INVENTARIO", True, PALETTE["text"])
        self.screen.blit(title, (panel_rect.x + 24, panel_rect.y + 18))
        self.screen.blit(close_button, self._inventory_close_button_rect())

        columns = 5
        rows = 3
        cell_width, cell_height = cell.get_size()
        grid_width = columns * cell_width
        grid_height = rows * cell_height
        gap_x = (panel_rect.width - grid_width) // (columns + 1)
        gap_y = (panel_rect.height - grid_height - 62) // (rows + 1)
        start_x = panel_rect.x + gap_x
        start_y = panel_rect.y + 58 + gap_y

        visible_items = [
            item_name
            for item_name in INVENTORY_ITEM_ORDER
            if self.inventory.get_quantity(item_name) > 0
        ]
        slot_count = columns * rows

        for index in range(slot_count):
            col = index % columns
            row = index // columns
            slot_rect = pygame.Rect(
                start_x + col * (cell_width + gap_x),
                start_y + row * (cell_height + gap_y),
                cell_width,
                cell_height,
            )
            self.screen.blit(cell, slot_rect)
            if index >= len(visible_items):
                continue
            item_name = visible_items[index]
            self._draw_slot_item(slot_rect, item_name, self.inventory.get_quantity(item_name), True)

    def _draw_slot_item(self, slot_rect: pygame.Rect, item_name: str, quantity: int, available: bool) -> None:
        text_color = PALETTE["text"] if available else (115, 118, 118)
        icon_name = ITEM_ICONS.get(item_name)
        if icon_name is not None:
            icon_scale = 3 if slot_rect.width <= 64 else 4
            icon = _load_ui_sprite(icon_name, icon_scale)
            icon_rect = icon.get_rect(center=(slot_rect.centerx, slot_rect.centery - (8 if quantity > 1 else 0)))
            self.screen.blit(icon, icon_rect)
        else:
            label = ITEM_LABELS.get(item_name, item_name[:3]).upper()
            label_text = self.small_font.render(label, True, text_color)
            self.screen.blit(label_text, label_text.get_rect(center=slot_rect.center))

        if quantity > 1:
            qty_text = self.small_font.render(str(quantity), True, text_color)
            qty_rect = qty_text.get_rect(bottomright=(slot_rect.right - 6, slot_rect.bottom - 5))
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
        recipe_names = self.crafting.get_recipe_names()
        rects: List[Tuple[str, pygame.Rect]] = []
        row_width = panel_rect.width - 52
        row_height = 86
        start_y = panel_rect.y + 62
        gap = 18
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

        cell = _load_ui_sprite("Crafting-cell.png", 3)
        plus = _load_ui_sprite("Crafting_Plus.png", 3)
        equal = _load_ui_sprite("Crafting_Equal.png", 3)

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
            icon = _load_ui_sprite(icon_name, 3)
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

    def _draw_help_panel(self) -> None:
        panel_width = 420
        panel_height = 260
        panel_x = (WIDTH - panel_width) // 2
        panel_y = HEIGHT - panel_height - 18
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 232), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        title = self.font.render("Ajuda", True, PALETTE["text"])
        self.screen.blit(title, (panel_x + 14, panel_y + 12))

        help_lines = [
            "WASD mover | Shift correr | Clique/SPACE atacar",
            "E vasculhar pontos, carros, natureza e portas",
            "Mouse wheel ou 1-6 navega atalhos rapidos",
            "B abre crafting | C usa item, entra ou vasculha",
            "Q ainda usa cura/comida",
            "F5 salvar | F9 carregar",
            "Objetivo: explorar, lootear e seguir vivo",
            "Feche este painel com H",
        ]

        y = panel_y + 46
        for line in help_lines:
            text = self.small_font.render(line, True, PALETTE["text"])
            self.screen.blit(text, (panel_x + 14, y))
            y += 26

    def run(self) -> None:
        while self.is_game_running:
            dt = self.clock.tick(60) / 1000.0
            direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed = self.process_input()
            self.update_game_state(direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed, dt)
            self.render(dt)

    def _get_selected_recipe(self) -> str:
        if not self._recipe_names:
            return "taco"
        return self._recipe_names[self._selected_recipe_index]

    def _cycle_recipe(self) -> None:
        if not self._recipe_names:
            return
        self._selected_recipe_index = (self._selected_recipe_index + 1) % len(self._recipe_names)
        self._set_message(f"Receita: {self._get_selected_recipe()}")

    def _cycle_quick_slot(self, direction: int) -> None:
        if not self._quick_slots or direction == 0:
            return
        self._select_quick_slot((self._selected_quick_slot + direction) % len(self._quick_slots))

    def _select_quick_slot(self, index: int) -> None:
        if not 0 <= index < len(self._quick_slots):
            return
        self._selected_quick_slot = index
        item_name = self._quick_slots[index]
        if item_name in WEAPON_ITEMS:
            self._equip_weapon(item_name)
            return
        label = ITEM_LABELS.get(item_name, item_name).lower()
        quantity = self.inventory.get_quantity(item_name)
        suffix = f" x{quantity}" if quantity > 0 else " vazio"
        self._set_message(f"Atalho: {label}{suffix}")

    def _equip_weapon(self, weapon_name: str) -> None:
        if weapon_name not in WEAPONS:
            return
        if self.inventory.get_quantity(weapon_name) <= 0:
            self._set_message("Arma nao disponivel.")
            return
        self.player.current_weapon = weapon_name
        self._set_message(f"Arma equipada: {weapon_name}")


if __name__ == "__main__":
    Game().run()
