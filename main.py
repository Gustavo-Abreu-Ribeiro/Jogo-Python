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
TILED_MAP_PATH = Path(__file__).resolve().parent.parent / "Mapa 1.tmj"
TILED_MAP_SCALE = 2
BG_COLOR = (24, 29, 31)
SEARCH_RANGE = 50
STATION_RANGE = 70
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
        "loot": ["metal", "pano", "comida"],
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
        "loot": ["metal", "metal", "pano", "polvora"],
        "drops": (2, 4),
        "ambush": 0.25,
    },
    "despensa": {
        "label": "Despensa",
        "color": (174, 108, 89),
        "loot": ["comida", "comida", "pano", "erva", "kit_medico"],
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
    "carro": {
        "label": "Carro abandonado",
        "color": (120, 132, 138),
        "loot": ["metal", "metal", "balas", "pistola", "polvora"],
        "drops": (2, 4),
        "ambush": 0.25,
    },
    "edificio": {
        "label": "Predio abandonado",
        "color": (155, 142, 91),
        "loot": ["pano", "balas", "polvora", "pistola", "escopeta"],
        "drops": (2, 4),
        "ambush": 0.35,
    },
}

STATION_TYPES: Dict[str, Dict[str, object]] = {
    "bancada": {"label": "Bancada", "color": (102, 138, 157)},
    "fogueira": {"label": "Fogueira", "color": (216, 132, 81)},
}

OBJECT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "objects"
SHOT_SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "Shot"
_RAW_SPRITE_CACHE: Dict[str, pygame.Surface] = {}
_SCALED_SPRITE_CACHE: Dict[Tuple[str, float], pygame.Surface] = {}
_COMPOSITE_SPRITE_CACHE: Dict[Tuple[str, str, str, str, float], pygame.Surface] = {}
_SHOT_IMPACT_CACHE: List[List[pygame.Surface]] | None = None

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
    def __init__(self, node_type: str, position: Tuple[int, int]) -> None:
        self.node_type = node_type
        self.position = pygame.Vector2(position)
        variant = random.choice(NODE_SPRITES[self.node_type])
        self._sprite = _load_scaled_sprite(str(variant["path"]), float(variant["scale"]))
        self._searched_sprite = _dim_sprite(self._sprite)
        self.radius = max(18, int(max(self._sprite.get_width(), self._sprite.get_height()) * 0.42))
        self.searched = False

    def search(self) -> Tuple[Dict[str, int], int]:
        node_data = NODE_TYPES[self.node_type]
        min_drops, max_drops = node_data["drops"]
        loot_items = node_data["loot"]
        drop_count = random.randint(min_drops, max_drops)

        rewards: Dict[str, int] = {}
        for _ in range(drop_count):
            item = random.choice(loot_items)
            rewards[item] = rewards.get(item, 0) + 1

        ambush_count = 0
        if random.random() < float(node_data["ambush"]):
            ambush_count = random.randint(1, 2)

        self.searched = True
        return rewards, ambush_count

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
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


class Station:
    def __init__(self, station_type: str, position: Tuple[int, int]) -> None:
        self.station_type = station_type
        self.position = pygame.Vector2(position)
        self.size = 30

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = self.position - camera_offset
        station_data = STATION_TYPES[self.station_type]
        rect = pygame.Rect(0, 0, self.size, self.size)
        rect.center = (draw_pos.x, draw_pos.y)
        pygame.draw.rect(surface, PALETTE["bg_deep"], rect.move(2, 3), border_radius=5)
        pygame.draw.circle(surface, (*station_data["color"], 0), draw_pos, STATION_RANGE, 1)
        if self.station_type == "bancada":
            table_rect = pygame.Rect(0, 0, self.size + 8, self.size - 6)
            table_rect.center = (draw_pos.x, draw_pos.y)
            pygame.draw.rect(surface, station_data["color"], table_rect, border_radius=5)
            pygame.draw.rect(surface, tuple(min(255, c + 20) for c in station_data["color"]), table_rect.inflate(-10, -12).move(0, -2), border_radius=4)
            for off_x in (-10, 10):
                pygame.draw.line(surface, (82, 61, 46), draw_pos + pygame.Vector2(off_x, 6), draw_pos + pygame.Vector2(off_x, 16), 4)
        else:
            pygame.draw.circle(surface, (88, 68, 48), draw_pos + pygame.Vector2(0, 2), 12)
            flame_colors = [(252, 219, 124), (240, 145, 74), station_data["color"]]
            flame_offsets = [(0, -8), (-4, -2), (4, -1)]
            flame_sizes = [9, 7, 7]
            for flame_color, flame_offset, flame_size in zip(flame_colors, flame_offsets, flame_sizes):
                pygame.draw.circle(surface, flame_color, draw_pos + pygame.Vector2(flame_offset), flame_size)


class ShotImpact:
    def __init__(self, position: Tuple[float, float] | pygame.Vector2) -> None:
        self.position = pygame.Vector2(position)
        self.animation_time = 0.0
        self.frames = _load_shot_impact_frames()
        self.fps = 18.0

    def update(self, dt: float) -> None:
        self.animation_time += dt * self.fps

    def is_finished(self) -> bool:
        return self.animation_time >= len(self.frames)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        frame_index = min(int(self.animation_time), len(self.frames) - 1)
        sprite = self.frames[frame_index]
        draw_pos = self.position - camera_offset
        surface.blit(sprite, sprite.get_rect(center=(round(draw_pos.x), round(draw_pos.y))))


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
        self.stations: List[Station] = []
        self.decorations: List[Decoration] = []
        self.tile_map: TiledMap | None = None
        self.collision_rects: List[pygame.Rect] = []

        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._camera = pygame.Vector2()

        self._recipe_names = self.crafting.get_recipe_names()
        self._selected_recipe_index = 0
        self._base_position = pygame.Vector2(WORLD_WIDTH * 0.48, WORLD_HEIGHT * 0.52)
        self._show_inventory = False
        self._show_help = False

        self._generate_world()
        self.player.set_position(tuple(self._base_position))
        self.inventory.add_item("comida", 2)

    def _generate_world(self) -> None:
        self.nodes.clear()
        self.stations.clear()
        self.zombies.clear()
        self.shot_impacts.clear()
        self.decorations.clear()
        self.collision_rects.clear()

        if self._load_tiled_world():
            return

        for station_type, position in [
            ("bancada", (int(self._base_position.x - 90), int(self._base_position.y - 30))),
            ("fogueira", (int(self._base_position.x + 90), int(self._base_position.y + 20))),
            ("fogueira", (WORLD_WIDTH - 260, 260)),
            ("bancada", (WORLD_WIDTH - 320, WORLD_HEIGHT - 240)),
            ("fogueira", (340, WORLD_HEIGHT - 260)),
        ]:
            self.stations.append(Station(station_type, position))

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

    def _load_tiled_world(self) -> bool:
        if not TILED_MAP_PATH.exists():
            return False

        global WORLD_WIDTH, WORLD_HEIGHT
        self.tile_map = TiledMap(TILED_MAP_PATH, scale=TILED_MAP_SCALE)
        WORLD_WIDTH = self.tile_map.world_width
        WORLD_HEIGHT = self.tile_map.world_height
        self.collision_rects = list(self.tile_map.collision_rects)
        self._base_position = self._find_open_position_near((WORLD_WIDTH * 0.5, WORLD_HEIGHT * 0.72))

        station_positions = [
            self._find_open_position_near((self._base_position.x - 80, self._base_position.y - 30)),
            self._find_open_position_near((self._base_position.x + 80, self._base_position.y + 20)),
        ]
        self.stations.append(Station("bancada", tuple(station_positions[0])))
        self.stations.append(Station("fogueira", tuple(station_positions[1])))

        for spawn in self.tile_map.search_nodes:
            interaction_position = self._find_open_position_near(spawn.position)
            if interaction_position.distance_to(self._base_position) < 80:
                continue
            self.nodes.append(SearchNode(spawn.node_type, tuple(interaction_position)))

        for _ in range(5):
            self._spawn_zombie()

        self._set_message("Mapa do Tiled carregado.")
        return True

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
                    self.is_game_running = False
                elif event.key == pygame.K_c:
                    craft_pressed = True
                elif event.key == pygame.K_TAB:
                    self._cycle_recipe()
                elif event.key == pygame.K_e:
                    search_pressed = True
                elif event.key == pygame.K_i:
                    self._show_inventory = not self._show_inventory
                elif event.key == pygame.K_h:
                    self._show_help = not self._show_help
                elif event.key == pygame.K_q:
                    heal_pressed = True
                elif event.key == pygame.K_1:
                    self._equip_weapon("maos")
                elif event.key == pygame.K_2:
                    self._equip_weapon("taco")
                elif event.key == pygame.K_3:
                    self._equip_weapon("pistola")
                elif event.key == pygame.K_4:
                    self._equip_weapon("escopeta")
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
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        self._spawn_timer += dt
        max_zombies = 6 + int(self.game_time / 120.0)
        if self._spawn_timer >= max(14.0, 22.0 / self.spawn_rate) and len(self.zombies) < max_zombies:
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
        closest_distance = SEARCH_RANGE

        for node in self.nodes:
            if node.searched:
                continue
            distance = node.position.distance_to(player_pos)
            if distance <= closest_distance:
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

    def _find_nearest_station(self) -> Station | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = STATION_RANGE

        for station in self.stations:
            distance = station.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = station

        return closest

    def _handle_search(self, search_pressed: bool) -> None:
        if not search_pressed:
            return

        corpse = self._find_nearest_corpse()
        if corpse is not None:
            self.player.start_pickup_animation()
            corpse.corpse_searched = True
            rewards: Dict[str, int] = {}
            for _ in range(random.randint(1, 2)):
                item = random.choice(["pano", "balas", "polvora", "comida"])
                rewards[item] = rewards.get(item, 0) + 1
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
        message = f"Voce encontrou: {reward_text}"

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
            if facing.dot(direction_to_zombie) < 0.35:
                continue
            if distance <= closest_distance:
                closest_distance = distance
                closest = zombie

        self.player.start_attack_animation()
        if ammo_cost > 0:
            self.inventory.remove_item("balas", ammo_cost)
            impact_position = closest.position if closest else player_pos + (facing * attack_range)
            impact_position.x = max(0, min(WORLD_WIDTH, impact_position.x))
            impact_position.y = max(0, min(WORLD_HEIGHT, impact_position.y))
            self.shot_impacts.append(ShotImpact(impact_position))
        if closest:
            closest.take_damage(damage)
            if closest.is_dying() and not closest.loot_given:
                closest.loot_given = True
                self._set_message("Zumbi abatido. Vasculhe o corpo com E.")
            else:
                self._set_message("Acerto!")
        elif ammo_cost > 0:
            self._set_message("Disparo sem alvo.")

        self._attack_timer = cooldown

    def _handle_heal(self, heal_pressed: bool) -> None:
        if not heal_pressed:
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

        nearby_station = self._find_nearest_station()
        station_name = nearby_station.station_type if nearby_station else None
        recipe_name = self._get_selected_recipe()
        success, message = self.crafting.craft(recipe_name, self.inventory, station_name)
        self._set_message(message)

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
        for station in self.stations:
            world_drawables.append((station.position.y, 1, station))
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
        self._camera.x = max(0, min(WORLD_WIDTH - WIDTH, player_pos.x - (WIDTH / 2)))
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
        station = self._find_nearest_station()

        if corpse is not None:
            prompt = "E vasculhar corpo"
        elif node is not None:
            label = NODE_TYPES[node.node_type]["label"]
            prompt = f"E buscar em {label}"
        elif station is not None:
            label = STATION_TYPES[station.station_type]["label"]
            prompt = f"Perto de {label}: pressione C para craftar"

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

    def _draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        ratio: float,
        fill_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
    ) -> None:
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=4)
        pygame.draw.rect(self.screen, PALETTE["text"], (x, y, width, height), 1, border_radius=4)
        fill_width = max(0, min(width, int(width * ratio)))
        if fill_width > 0:
            pygame.draw.rect(self.screen, fill_color, (x, y, fill_width, height), border_radius=4)

    def _draw_ui(self) -> None:
        current_recipe = self._get_selected_recipe()
        recipe = self.crafting.get_recipe(current_recipe) or {}
        recipe_cost = recipe.get("cost", {})
        station_needed = recipe.get("station", "-")
        nearby_station = self._find_nearest_station()
        weapon_stats = WEAPONS.get(self.player.current_weapon, WEAPONS["maos"])
        nearby_corpse = self._find_nearest_corpse()
        nearby_node = self._find_nearest_node()
        nearby_node_text = "Corpo" if nearby_corpse else (NODE_TYPES[nearby_node.node_type]["label"] if nearby_node else "")

        left_panel = pygame.Surface((258, 112), pygame.SRCALPHA)
        pygame.draw.rect(left_panel, (*PALETTE["panel"], 210), left_panel.get_rect(), border_radius=10)
        pygame.draw.rect(left_panel, PALETTE["panel_edge"], left_panel.get_rect(), 1, border_radius=10)
        self.screen.blit(left_panel, (8, 8))

        self._draw_stat_row(18, 18, (210, 60, 60), self.player.player_health / self.player.max_health, "HP")
        self._draw_stat_row(18, 46, (80, 170, 240), self.player.player_stamina / 100.0, "ST")
        self._draw_stat_row(18, 74, (220, 170, 70), self.player.player_hunger / self.player.max_hunger, "FO")

        self._draw_equipment_card(current_recipe, recipe_cost, station_needed, weapon_stats, nearby_station, nearby_node_text)

        self._draw_minimap()
        self._draw_corner_hints()

        if self._show_inventory:
            self._draw_inventory_panel()
        if self._show_help:
            self._draw_help_panel()

        if self._message_timer > 0:
            msg = self.font.render(self._message, True, (255, 210, 80))
            self.screen.blit(msg, (10, HEIGHT - 30))

    def _draw_minimap(self) -> None:
        map_width = 220
        map_height = 140
        map_x = WIDTH - map_width - 14
        map_y = 14
        panel = pygame.Surface((map_width, map_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 220), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (map_x, map_y))

        inner_rect = pygame.Rect(map_x + 10, map_y + 10, map_width - 20, map_height - 20)
        pygame.draw.rect(self.screen, PALETTE["bg_deep"], inner_rect, border_radius=6)

        scale_x = inner_rect.width / WORLD_WIDTH
        scale_y = inner_rect.height / WORLD_HEIGHT

        base_dot = (
            inner_rect.x + int(self._base_position.x * scale_x),
            inner_rect.y + int(self._base_position.y * scale_y),
        )
        pygame.draw.circle(self.screen, PALETTE["safe_ring"], base_dot, 5)

        for station in self.stations:
            dot = (
                inner_rect.x + int(station.position.x * scale_x),
                inner_rect.y + int(station.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, STATION_TYPES[station.station_type]["color"], dot, 4)

        for node in self.nodes:
            if node.searched:
                continue
            dot = (
                inner_rect.x + int(node.position.x * scale_x),
                inner_rect.y + int(node.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, NODE_TYPES[node.node_type]["color"], dot, 2)

        for zombie in self.zombies:
            dot = (
                inner_rect.x + int(zombie.position.x * scale_x),
                inner_rect.y + int(zombie.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, PALETTE["danger"], dot, 2)

        player_dot = (
            inner_rect.x + int(self.player.player_position[0] * scale_x),
            inner_rect.y + int(self.player.player_position[1] * scale_y),
        )
        pygame.draw.circle(self.screen, PALETTE["text"], player_dot, 4)

        view_rect = pygame.Rect(
            inner_rect.x + int(self._camera.x * scale_x),
            inner_rect.y + int(self._camera.y * scale_y),
            max(12, int(WIDTH * scale_x)),
            max(8, int(HEIGHT * scale_y)),
        )
        pygame.draw.rect(self.screen, PALETTE["text"], view_rect, 1)

        title = self.small_font.render("Mapa", True, PALETTE["text"])
        self.screen.blit(title, (map_x + 10, map_y - 2))

    def _draw_corner_hints(self) -> None:
        hint_text = f"I inventario [{'ON' if self._show_inventory else 'OFF'}] | H ajuda [{'ON' if self._show_help else 'OFF'}]"
        text = self.small_font.render(hint_text, True, PALETTE["text_soft"])
        rect = text.get_rect(topright=(WIDTH - 14, 164))
        self.screen.blit(text, rect)

    def _draw_inventory_panel(self) -> None:
        panel_width = 280
        panel_height = 340
        panel_x = WIDTH - panel_width - 14
        panel_y = 190
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 228), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        title = self.font.render("Inventario", True, PALETTE["text"])
        self.screen.blit(title, (panel_x + 14, panel_y + 12))

        items = [
            f"madeira: {self.inventory.get_quantity('madeira')}",
            f"metal: {self.inventory.get_quantity('metal')}",
            f"pano: {self.inventory.get_quantity('pano')}",
            f"erva: {self.inventory.get_quantity('erva')}",
            f"polvora: {self.inventory.get_quantity('polvora')}",
            f"balas: {self.inventory.get_quantity('balas')}",
            f"comida: {self.inventory.get_quantity('comida')}",
            f"kit_medico: {self.inventory.get_quantity('kit_medico')}",
            f"taco: {self.inventory.get_quantity('taco')}",
            f"pistola: {self.inventory.get_quantity('pistola')}",
            f"escopeta: {self.inventory.get_quantity('escopeta')}",
        ]

        y = panel_y + 46
        for item in items:
            text = self.font.render(item, True, PALETTE["text"])
            self.screen.blit(text, (panel_x + 14, y))
            y += 24

    def _draw_help_panel(self) -> None:
        panel_width = 420
        panel_height = 235
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
            "E vasculhar pontos | Q comer ou usar kit medico",
            "TAB trocar receita | C craftar na estacao correta",
            "1 maos | 2 taco | 3 pistola | 4 escopeta",
            "F5 salvar | F9 carregar",
            "Objetivo: explorar, lootear e voltar para a base vivo",
            "Feche este painel com H",
        ]

        y = panel_y + 46
        for line in help_lines:
            text = self.small_font.render(line, True, PALETTE["text"])
            self.screen.blit(text, (panel_x + 14, y))
            y += 26

    def _draw_stat_row(self, x: int, y: int, color: Tuple[int, int, int], ratio: float, label: str) -> None:
        icon_rect = pygame.Rect(x, y, 22, 18)
        pygame.draw.rect(self.screen, color, icon_rect, border_radius=4)
        label_text = self.small_font.render(label, True, (15, 18, 20))
        self.screen.blit(label_text, (x + 3, y + 1))
        self._draw_bar(x + 30, y + 3, 190, 12, ratio, color, (45, 48, 55))

    def _draw_equipment_card(
        self,
        current_recipe: str,
        recipe_cost: Dict[str, int],
        station_needed: str,
        weapon_stats: Dict[str, float | int],
        nearby_station: Station | None,
        nearby_node_text: str,
    ) -> None:
        panel_x = 8
        panel_y = 126
        panel = pygame.Surface((258, 114), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 210), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        weapon_name = self.font.render(self.player.current_weapon.upper(), True, PALETTE["text"])
        self.screen.blit(weapon_name, (panel_x + 12, panel_y + 10))

        ammo_cost = int(weapon_stats.get("ammo", 0))
        ammo_text = f"  BL {self.inventory.get_quantity('balas')}" if ammo_cost > 0 else ""
        stats_text = self.small_font.render(f"ATK {weapon_stats['damage']}  RNG {weapon_stats['range']}{ammo_text}", True, PALETTE["text_soft"])
        self.screen.blit(stats_text, (panel_x + 12, panel_y + 36))

        recipe_title = self.small_font.render(f"Craft: {current_recipe}", True, PALETTE["accent"])
        self.screen.blit(recipe_title, (panel_x + 12, panel_y + 60))

        cost_parts = [f"{item[:2]} {amount}" for item, amount in recipe_cost.items()]
        costs = "  ".join(cost_parts) if cost_parts else "-"
        cost_text = self.small_font.render(costs, True, PALETTE["text_soft"])
        self.screen.blit(cost_text, (panel_x + 12, panel_y + 82))

        station_ready = nearby_station is not None and nearby_station.station_type == station_needed
        station_color = (90, 200, 120) if station_ready else (210, 120, 90)
        station_label = self.small_font.render(station_needed[:3].upper(), True, station_color)
        self.screen.blit(station_label, (panel_x + 190, panel_y + 60))

        if nearby_node_text:
            point_text = self.small_font.render(nearby_node_text, True, PALETTE["text_soft"])
            self.screen.blit(point_text, (panel_x + 150, panel_y + 10))

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
