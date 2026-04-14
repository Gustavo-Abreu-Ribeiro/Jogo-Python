from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Tuple

import pygame


SPRITE_ROOT = Path(__file__).resolve().parent / "sprites" / "zombie_normal" / "zombie_walk"
DIRECTION_FOLDERS = {
    "down": "zombie_walk_down",
    "left": "zombie_walk_left",
    "right": "zombie_walk_right",
    "up": "zombie_walk_up",
}


@dataclass
class Zombie:
    position: pygame.Vector2
    speed: float
    health: int = 30
    radius: int = 12
    hit_flash_timer: float = 0.0
    animation_time: float = 0.0
    facing_direction: str = field(default="down", init=False, repr=False)
    _is_moving: bool = field(default=False, init=False, repr=False)

    SPRITE_SCALE: ClassVar[int] = 2
    ANIMATION_FPS: ClassVar[float] = 12.0
    _sprite_cache: ClassVar[dict[str, list[pygame.Surface]]] = {}

    def __post_init__(self) -> None:
        self.position = pygame.Vector2(self.position)
        self._load_sprites()

    @classmethod
    def _load_sprites(cls) -> None:
        if cls._sprite_cache:
            return

        display_ready = pygame.display.get_surface() is not None
        for direction, folder_name in DIRECTION_FOLDERS.items():
            folder_path = SPRITE_ROOT / folder_name
            frame_paths = sorted(folder_path.glob("*.png"))
            if not frame_paths:
                raise FileNotFoundError(f"Nenhum sprite encontrado em {folder_path}")

            frames: list[pygame.Surface] = []
            for frame_path in frame_paths:
                image = pygame.image.load(str(frame_path))
                if display_ready:
                    image = image.convert_alpha()
                scaled_size = (
                    image.get_width() * cls.SPRITE_SCALE,
                    image.get_height() * cls.SPRITE_SCALE,
                )
                frames.append(pygame.transform.scale(image, scaled_size))
            cls._sprite_cache[direction] = frames

    @staticmethod
    def _direction_from_vector(direction: pygame.Vector2) -> str:
        if abs(direction.x) > abs(direction.y):
            return "right" if direction.x > 0 else "left"
        return "down" if direction.y > 0 else "up"

    @staticmethod
    def _flash_sprite(sprite: pygame.Surface) -> pygame.Surface:
        flashed = sprite.copy()
        overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        overlay.fill((95, 95, 95, 0))
        flashed.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return flashed

    def _current_sprite(self) -> pygame.Surface:
        frames = self._sprite_cache[self.facing_direction]
        if not self._is_moving:
            return frames[0]
        frame_index = int(self.animation_time) % len(frames)
        return frames[frame_index]

    def update(self, player_position: Tuple[float, float], dt: float) -> None:
        target = pygame.Vector2(player_position)
        direction = target - self.position
        self._is_moving = False

        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.position += direction * self.speed * dt
            self.facing_direction = self._direction_from_vector(direction)
            self._is_moving = True
            frame_count = len(self._sprite_cache[self.facing_direction])
            self.animation_time = (self.animation_time + dt * self.ANIMATION_FPS) % frame_count
        else:
            self.animation_time = 0.0

        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2 | None = None) -> None:
        offset = camera_offset or pygame.Vector2()
        draw_pos = self.position - offset
        sprite = self._current_sprite()
        if self.hit_flash_timer > 0:
            sprite = self._flash_sprite(sprite)

        sprite_rect = sprite.get_rect(
            midbottom=(round(draw_pos.x), round(draw_pos.y + self.radius + 6))
        )
        shadow_surface = pygame.Surface(
            (
                max(12, int(sprite_rect.width * 0.52)),
                max(6, int(sprite_rect.height * 0.18)),
            ),
            pygame.SRCALPHA,
        )
        pygame.draw.ellipse(shadow_surface, (18, 22, 24, 120), shadow_surface.get_rect())
        shadow_rect = shadow_surface.get_rect(center=(sprite_rect.centerx + 2, sprite_rect.bottom - 3))
        surface.blit(shadow_surface, shadow_rect)
        surface.blit(sprite, sprite_rect)

        if self.hit_flash_timer > 0:
            flash_radius = max(self.radius + 5, sprite_rect.width // 2)
            pygame.draw.circle(surface, (255, 120, 120), sprite_rect.center, flash_radius, 2)

    def collides_with_player(self, player_position: Tuple[float, float], player_radius: int) -> bool:
        return self.position.distance_to(pygame.Vector2(player_position)) < (self.radius + player_radius)

    def take_damage(self, amount: int) -> None:
        self.health = max(0, self.health - amount)
        self.hit_flash_timer = 0.18

    def is_dead(self) -> bool:
        return self.health <= 0
