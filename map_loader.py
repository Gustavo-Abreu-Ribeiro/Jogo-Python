from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from typing import Iterable

import pygame


TILED_FLIP_H = 0x80000000
TILED_FLIP_V = 0x40000000
TILED_FLIP_D = 0x20000000
TILED_ROT_HEX = 0x10000000
TILED_GID_MASK = ~(TILED_FLIP_H | TILED_FLIP_V | TILED_FLIP_D | TILED_ROT_HEX)


SOLID_LAYER_KEYWORDS = ("objects", "building", "buildign", "wall", "car")
SEARCH_NODE_LAYERS = {
    "loot": "despensa",
}


@dataclass(frozen=True)
class SearchNodeSpawn:
    node_type: str
    position: tuple[int, int]


@dataclass
class TileSet:
    firstgid: int
    tile_width: int
    tile_height: int
    columns: int
    tilecount: int
    image_path: Path | None
    tile_image_paths: dict[int, Path]
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
        self.collision_rects: list[pygame.Rect] = []
        self.search_nodes: list[SearchNodeSpawn] = []
        self.unrendered_tiles_by_layer: dict[str, int] = {}

        self._load_layers(data.get("layers", []))

    def _load_tilesets(self, tileset_refs: Iterable[dict]) -> list[TileSet]:
        tilesets: list[TileSet] = []
        for tileset_ref in tileset_refs:
            source = tileset_ref.get("source")
            if source is None:
                continue

            tsx_path = (self.path.parent / str(source)).resolve()
            root = ET.parse(tsx_path).getroot()
            image_element = root.find("image")
            image_path = None
            tile_image_paths: dict[int, Path] = {}
            tile_width = int(root.attrib.get("tilewidth", self.tile_width))
            tile_height = int(root.attrib.get("tileheight", self.tile_height))
            columns = int(root.attrib.get("columns", 0))
            tilecount = int(root.attrib.get("tilecount", 0))

            if image_element is not None:
                image_path = (tsx_path.parent / image_element.attrib["source"]).resolve()

            for tile_element in root.findall("tile"):
                tile_image = tile_element.find("image")
                if tile_image is None:
                    continue
                tile_id = int(tile_element.attrib["id"])
                tile_image_paths[tile_id] = (tsx_path.parent / tile_image.attrib["source"]).resolve()

            tilesets.append(
                TileSet(
                    firstgid=int(tileset_ref["firstgid"]),
                    tile_width=tile_width,
                    tile_height=tile_height,
                    columns=columns,
                    tilecount=tilecount,
                    image_path=image_path,
                    tile_image_paths=tile_image_paths,
                    image=self._load_tileset_image(image_path),
                )
            )

        return sorted(tilesets, key=lambda tileset: tileset.firstgid)

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

                tile = self._get_tile_surface(raw_gid)
                if tile is not None:
                    tiles.append((world_x, world_y, tile))
                else:
                    unrendered_tiles += 1

            self.layers.append(TileLayer(name=name, tiles=tuple(tiles)))
            if unrendered_tiles:
                self.unrendered_tiles_by_layer[name] = unrendered_tiles
            self.search_nodes.extend(self._make_search_nodes(name, occupied_tiles))

    def _get_tile_surface(self, raw_gid: int) -> pygame.Surface | None:
        gid = raw_gid & TILED_GID_MASK
        flipped_h = bool(raw_gid & TILED_FLIP_H)
        flipped_v = bool(raw_gid & TILED_FLIP_V)
        cache_key = (gid, flipped_h, flipped_v)
        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        tileset = self._find_tileset(gid)
        if tileset is None:
            return None

        local_id = gid - tileset.firstgid
        if local_id in tileset.tile_image_paths:
            tile = self._load_tileset_image(tileset.tile_image_paths[local_id])
            if tile is None:
                return None
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
            return None

        if flipped_h or flipped_v:
            tile = pygame.transform.flip(tile, flipped_h, flipped_v)
        if self.scale != 1:
            tile = pygame.transform.scale(tile, (tile.get_width() * self.scale, tile.get_height() * self.scale))

        self._tile_cache[cache_key] = tile
        return tile

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
        node_type = SEARCH_NODE_LAYERS.get(layer_name.lower())
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
        view_rect = pygame.Rect(
            int(camera_offset.x) - self.render_tile_width,
            int(camera_offset.y) - self.render_tile_height,
            surface.get_width() + self.render_tile_width * 2,
            surface.get_height() + self.render_tile_height * 2,
        )

        for layer in self.layers:
            for world_x, world_y, tile in layer.tiles:
                if view_rect.collidepoint(world_x, world_y):
                    surface.blit(tile, (world_x - camera_offset.x, world_y - camera_offset.y))
