from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from typing import Iterable

import pygame


PROJECT_ROOT = Path(__file__).resolve().parent
TILED_FLIP_H = 0x80000000
TILED_FLIP_V = 0x40000000
TILED_FLIP_D = 0x20000000
TILED_ROT_HEX = 0x10000000
TILED_GID_MASK = ~(TILED_FLIP_H | TILED_FLIP_V | TILED_FLIP_D | TILED_ROT_HEX)


SOLID_LAYER_KEYWORDS = ("collider", "collision", "solid", "objects", "building", "buildign", "wall", "car")
DRAW_BUCKET_SIZE = 256
SEARCH_NODE_LAYERS = {
    "loot": "despensa",
    "cars": "carro",
}
TRIGGER_LAYER_TYPES = {
    "portas": "door",
    "porta": "door",
    "doors": "door",
    "door": "door",
    "teleport": "exit",
    "teleports": "exit",
}


@dataclass(frozen=True)
class SearchNodeSpawn:
    node_type: str
    position: tuple[int, int]
    draw_sprite: bool = False
    radius: int = 36


@dataclass(frozen=True)
class MapTriggerSpawn:
    trigger_type: str
    position: tuple[int, int]
    radius: int = 54


@dataclass
class TileSet:
    firstgid: int
    tile_width: int
    tile_height: int
    columns: int
    tilecount: int
    image_path: Path | None
    tile_image_paths: dict[int, Path]
    tile_offset_x: int = 0
    tile_offset_y: int = 0
    image: pygame.Surface | None = None

    @property
    def lastgid(self) -> int:
        highest_collection_id = max(self.tile_image_paths.keys(), default=-1)
        highest_local_id = max(self.tilecount - 1, highest_collection_id)
        return self.firstgid + max(0, highest_local_id)

    def contains(self, gid: int) -> bool:
        return self.firstgid <= gid <= self.lastgid


@dataclass(frozen=True)
class TileLayer:
    name: str
    tiles: tuple[tuple[int, int, pygame.Surface], ...]


class TiledMap:
    def __init__(self, map_path: str | Path, scale: int = 2) -> None:
        self.path = Path(map_path)
        self.scale = max(1, int(scale))
        data = json.loads(self.path.read_text(encoding="utf-8"))

        self.tile_width = int(data["tilewidth"])
        self.tile_height = int(data["tileheight"])
        self.width_tiles = int(data["width"])
        self.height_tiles = int(data["height"])
        self.render_tile_width = self.tile_width * self.scale
        self.render_tile_height = self.tile_height * self.scale
        self.world_width = self.width_tiles * self.render_tile_width
        self.world_height = self.height_tiles * self.render_tile_height

        self.tilesets = self._load_tilesets(data.get("tilesets", []))
        self._tile_cache: dict[tuple[int, bool, bool], pygame.Surface] = {}
        self.layers: list[TileLayer] = []
        self._layer_tile_buckets: list[dict[tuple[int, int], tuple[tuple[int, int, pygame.Surface], ...]]] = []
        self._max_tile_width = self.render_tile_width
        self._max_tile_height = self.render_tile_height
        self.collision_rects: list[pygame.Rect] = []
        self.search_nodes: list[SearchNodeSpawn] = []
        self.door_triggers: list[MapTriggerSpawn] = []
        self.exit_triggers: list[MapTriggerSpawn] = []
        self.unrendered_tiles_by_layer: dict[str, int] = {}

        self._load_layers(data.get("layers", []))
        self._build_draw_buckets()

    def _load_tilesets(self, tileset_refs: Iterable[dict]) -> list[TileSet]:
        tilesets: list[TileSet] = []
        for tileset_ref in tileset_refs:
            source = tileset_ref.get("source")
            if source is None:
                continue

            tsx_path = self._resolve_tileset_path(str(source))
            root = ET.parse(tsx_path).getroot()
            image_element = root.find("image")
            image_path = None
            tile_image_paths: dict[int, Path] = {}
            tile_width = int(root.attrib.get("tilewidth", self.tile_width))
            tile_height = int(root.attrib.get("tileheight", self.tile_height))
            columns = int(root.attrib.get("columns", 0))
            tilecount = int(root.attrib.get("tilecount", 0))

            if image_element is not None:
                image_path = self._resolve_image_path(tsx_path, image_element.attrib["source"])

            tile_offset = root.find("tileoffset")
            tile_offset_x = int(tile_offset.attrib.get("x", 0)) if tile_offset is not None else 0
            tile_offset_y = int(tile_offset.attrib.get("y", 0)) if tile_offset is not None else 0

            for tile_element in root.findall("tile"):
                tile_image = tile_element.find("image")
                if tile_image is None:
                    continue
                tile_id = int(tile_element.attrib["id"])
                tile_image_paths[tile_id] = self._resolve_image_path(tsx_path, tile_image.attrib["source"])

            tilesets.append(
                TileSet(
                    firstgid=int(tileset_ref["firstgid"]),
                    tile_width=tile_width,
                    tile_height=tile_height,
                    columns=columns,
                    tilecount=tilecount,
                    image_path=image_path,
                    tile_image_paths=tile_image_paths,
                    tile_offset_x=tile_offset_x,
                    tile_offset_y=tile_offset_y,
                    image=self._load_tileset_image(image_path),
                )
            )

        return sorted(tilesets, key=lambda tileset: tileset.firstgid)

    def _resolve_tileset_path(self, source: str) -> Path:
        tsx_path = (self.path.parent / source).resolve()
        if tsx_path.exists():
            return tsx_path

        fallback = PROJECT_ROOT / "sprites" / "Sprites" / Path(source).name
        if fallback.exists():
            return fallback.resolve()
        return tsx_path

    @staticmethod
    def _resolve_image_path(tsx_path: Path, source: str) -> Path:
        image_path = (tsx_path.parent / source).resolve()
        if image_path.exists():
            return image_path

        marker = "PostApocalypse_AssetPack_v1.1.2/"
        normalized_source = source.replace("\\", "/")
        if marker in normalized_source:
            relative_asset = normalized_source.split(marker, 1)[1]
            fallback = PROJECT_ROOT / "web_assets" / "PostApocalypse_AssetPack_v1.1.2" / relative_asset
            if fallback.exists():
                return fallback.resolve()

        return image_path

    @staticmethod
    def _load_tileset_image(image_path: Path | None) -> pygame.Surface | None:
        if image_path is None or not image_path.exists():
            return None

        image = pygame.image.load(str(image_path))
        if pygame.display.get_surface() is not None:
            return image.convert_alpha()
        return image

    def _load_layers(self, layers: Iterable[dict]) -> None:
        for layer in layers:
            if layer.get("type") != "tilelayer" or not layer.get("visible", True):
                continue

            name = str(layer.get("name", ""))
            width = int(layer.get("width", self.width_tiles))
            data = list(layer.get("data", []))
            tiles: list[tuple[int, int, pygame.Surface]] = []
            occupied_tiles: set[tuple[int, int]] = set()
            unrendered_tiles = 0

            for index, raw_gid in enumerate(data):
                raw_gid = int(raw_gid)
                if raw_gid == 0:
                    continue

                x = index % width
                y = index // width
                world_x = x * self.render_tile_width
                world_y = y * self.render_tile_height
                occupied_tiles.add((x, y))

                if self._is_solid_layer(name):
                    self.collision_rects.append(
                        pygame.Rect(world_x, world_y, self.render_tile_width, self.render_tile_height)
                    )

                tile, tileset = self._get_tile_surface(raw_gid)
                if tile is not None:
                    self._max_tile_width = max(self._max_tile_width, tile.get_width())
                    self._max_tile_height = max(self._max_tile_height, tile.get_height())
                    offset_x = tileset.tile_offset_x * self.scale if tileset is not None else 0
                    offset_y = tileset.tile_offset_y * self.scale if tileset is not None else 0
                    draw_x = world_x + offset_x
                    draw_y = world_y + self.render_tile_height - tile.get_height() + offset_y
                    tiles.append((draw_x, draw_y, tile))
                else:
                    unrendered_tiles += 1

            self.layers.append(TileLayer(name=name, tiles=tuple(tiles)))
            if unrendered_tiles:
                self.unrendered_tiles_by_layer[name] = unrendered_tiles
            self.search_nodes.extend(self._make_search_nodes(name, occupied_tiles))
            triggers = self._make_trigger_spawns(name, occupied_tiles)
            for trigger in triggers:
                if trigger.trigger_type == "door":
                    self.door_triggers.append(trigger)
                elif trigger.trigger_type == "exit":
                    self.exit_triggers.append(trigger)

    def _build_draw_buckets(self) -> None:
        self._layer_tile_buckets = []
        for layer in self.layers:
            buckets: dict[tuple[int, int], list[tuple[int, int, pygame.Surface]]] = {}
            for world_x, world_y, tile in layer.tiles:
                bucket_key = (world_x // DRAW_BUCKET_SIZE, world_y // DRAW_BUCKET_SIZE)
                buckets.setdefault(bucket_key, []).append((world_x, world_y, tile))
            self._layer_tile_buckets.append(
                {bucket_key: tuple(items) for bucket_key, items in buckets.items()}
            )

    def _get_tile_surface(self, raw_gid: int) -> tuple[pygame.Surface | None, TileSet | None]:
        gid = raw_gid & TILED_GID_MASK
        flipped_h = bool(raw_gid & TILED_FLIP_H)
        flipped_v = bool(raw_gid & TILED_FLIP_V)
        cache_key = (gid, flipped_h, flipped_v)

        tileset = self._find_tileset(gid)
        if tileset is None:
            return None, None

        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key], tileset

        local_id = gid - tileset.firstgid
        if local_id in tileset.tile_image_paths:
            tile = self._load_tileset_image(tileset.tile_image_paths[local_id])
            if tile is None:
                return None, tileset
        elif tileset.image is not None and tileset.columns > 0:
            source_x = (local_id % tileset.columns) * tileset.tile_width
            source_y = (local_id // tileset.columns) * tileset.tile_height
            tile = pygame.Surface((tileset.tile_width, tileset.tile_height), pygame.SRCALPHA)
            tile.blit(
                tileset.image,
                (0, 0),
                pygame.Rect(source_x, source_y, tileset.tile_width, tileset.tile_height),
            )
        else:
            return None, tileset

        if flipped_h or flipped_v:
            tile = pygame.transform.flip(tile, flipped_h, flipped_v)
        if self.scale != 1:
            tile = pygame.transform.scale(tile, (tile.get_width() * self.scale, tile.get_height() * self.scale))

        self._tile_cache[cache_key] = tile
        return tile, tileset

    def _find_tileset(self, gid: int) -> TileSet | None:
        for tileset in reversed(self.tilesets):
            if gid >= tileset.firstgid:
                return tileset if tileset.contains(gid) else None
        return None

    @staticmethod
    def _is_solid_layer(layer_name: str) -> bool:
        normalized = layer_name.lower()
        return any(keyword in normalized for keyword in SOLID_LAYER_KEYWORDS)

    def _make_search_nodes(self, layer_name: str, occupied_tiles: set[tuple[int, int]]) -> list[SearchNodeSpawn]:
        normalized = layer_name.lower()
        if normalized == "nature":
            node_type = "natureza"
        else:
            node_type = SEARCH_NODE_LAYERS.get(normalized)
        if node_type is None:
            return []

        nodes: list[SearchNodeSpawn] = []
        seen: set[tuple[int, int]] = set()
        for start in occupied_tiles:
            if start in seen:
                continue
            cluster = self._collect_cluster(start, occupied_tiles, seen)
            if not cluster:
                continue

            avg_x = sum(tile[0] for tile in cluster) / len(cluster)
            avg_y = sum(tile[1] for tile in cluster) / len(cluster)
            nodes.append(
                SearchNodeSpawn(
                    node_type=node_type,
                    position=(
                        int((avg_x + 0.5) * self.render_tile_width),
                        int((avg_y + 0.5) * self.render_tile_height),
                    ),
                )
            )
        return nodes

    def _make_trigger_spawns(self, layer_name: str, occupied_tiles: set[tuple[int, int]]) -> list[MapTriggerSpawn]:
        trigger_type = TRIGGER_LAYER_TYPES.get(layer_name.lower())
        if trigger_type is None:
            return []

        triggers: list[MapTriggerSpawn] = []
        seen: set[tuple[int, int]] = set()
        for start in occupied_tiles:
            if start in seen:
                continue
            cluster = self._collect_cluster(start, occupied_tiles, seen)
            if not cluster:
                continue

            avg_x = sum(tile[0] for tile in cluster) / len(cluster)
            avg_y = sum(tile[1] for tile in cluster) / len(cluster)
            radius = max(self.render_tile_width, self.render_tile_height)
            if len(cluster) > 1:
                radius = max(radius, int((len(cluster) ** 0.5) * self.render_tile_width))
            triggers.append(
                MapTriggerSpawn(
                    trigger_type=trigger_type,
                    position=(
                        int((avg_x + 0.5) * self.render_tile_width),
                        int((avg_y + 0.5) * self.render_tile_height),
                    ),
                    radius=radius,
                )
            )
        return triggers

    @staticmethod
    def _collect_cluster(
        start: tuple[int, int],
        occupied_tiles: set[tuple[int, int]],
        seen: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        cluster: list[tuple[int, int]] = []
        stack = [start]
        seen.add(start)

        while stack:
            tile = stack.pop()
            cluster.append(tile)
            x, y = tile
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in occupied_tiles and neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        return cluster

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        left = int(camera_offset.x) - self._max_tile_width
        top = int(camera_offset.y) - self._max_tile_height
        right = int(camera_offset.x) + surface.get_width() + self._max_tile_width
        bottom = int(camera_offset.y) + surface.get_height() + self._max_tile_height
        min_bucket_x = left // DRAW_BUCKET_SIZE
        max_bucket_x = right // DRAW_BUCKET_SIZE
        min_bucket_y = top // DRAW_BUCKET_SIZE
        max_bucket_y = bottom // DRAW_BUCKET_SIZE

        for buckets in self._layer_tile_buckets:
            for bucket_y in range(min_bucket_y, max_bucket_y + 1):
                for bucket_x in range(min_bucket_x, max_bucket_x + 1):
                    for world_x, world_y, tile in buckets.get((bucket_x, bucket_y), ()):
                        surface.blit(tile, (world_x - camera_offset.x, world_y - camera_offset.y))
