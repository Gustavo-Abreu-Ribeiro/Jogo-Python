from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import random
import re
from typing import ClassVar, Tuple

import pygame


SPRITE_BASE_ROOT = Path(__file__).resolve().parent / "sprites"
ZOMBIE_TYPES = {
    "axe": {"root": SPRITE_BASE_ROOT / "Zombie_Axe", "prefix": "Zombie_Axe", "scale": 3},
    "small": {"root": SPRITE_BASE_ROOT / "Zombie_Small", "prefix": "Zombie_Small", "scale": 3},
    "big": {"root": SPRITE_BASE_ROOT / "Zombie_Big", "prefix": "Zombie_Big", "scale": 3},
}
DIRECTION_NAMES = {
    "down": "down",
    "side-left": "left",
    "side": "right",
    "up": "up",
}
ANIMATION_NAMES = {
    "idle": "idle",
    "walk": "walk",
    "first-attack": "attack_1",
    "second-attack": "attack_2",
    "first-death": "death_1",
    "second-death": "death_2",
}
ANIMATION_FPS = {
    "idle": 6.0,
    "walk": 10.0,
    "attack_1": 9.0,
    "attack_2": 9.0,
    "death_1": 9.0,
    "death_2": 9.0,
}

SMALL_LUNGE_MIN_DISTANCE = 86.0
SMALL_LUNGE_MAX_DISTANCE = 150.0
SMALL_LUNGE_MAX_TRAVEL = 132.0
SMALL_LUNGE_START_FRAME_RATIO = 0.28
SMALL_LUNGE_END_FRAME_RATIO = 0.78
SMALL_LUNGE_HIT_FRAME_RATIO = 0.62
SMALL_RETREAT_TRIGGER_DISTANCE = 78.0
SMALL_RETREAT_TARGET_DISTANCE = 116.0
SMALL_RETREAT_SPEED_MULTIPLIER = 1.35
SMALL_RETREAT_MIN_TIME = 0.42
SMALL_RETREAT_FORCED_LUNGE_TIME = 0.65


@dataclass
class Zombie:
    position: pygame.Vector2
    speed: float
    health: int = 30
    radius: int = 12
    zombie_type: str = "axe"
    hit_flash_timer: float = 0.0
    animation_time: float = 0.0
    facing_direction: str = field(default="down", init=False, repr=False)
    loot_given: bool = field(default=False, init=False)
    corpse_timer: float = field(default=18.0, init=False)
    corpse_searched: bool = field(default=False, init=False)
    _is_moving: bool = field(default=False, init=False, repr=False)
    _state: str = field(default="idle", init=False, repr=False)
    _attack_variant: str = field(default="attack_1", init=False, repr=False)
    _death_variant: str = field(default="death_1", init=False, repr=False)
    _death_finished: bool = field(default=False, init=False, repr=False)
    _attack_has_hit: bool = field(default=False, init=False, repr=False)
    _attack_started: bool = field(default=False, init=False, repr=False)
    _attack_start_position: pygame.Vector2 = field(default_factory=pygame.Vector2, init=False, repr=False)
    _attack_target_position: pygame.Vector2 = field(default_factory=pygame.Vector2, init=False, repr=False)
    _retreat_timer: float = field(default=0.0, init=False, repr=False)

    ATTACK_RANGE: ClassVar[float] = 34.0
    _sprite_cache: ClassVar[dict[str, dict[str, dict[str, list[pygame.Surface]]]]] = {}

    def __post_init__(self) -> None:
        self.position = pygame.Vector2(self.position)
        if self.zombie_type not in ZOMBIE_TYPES:
            self.zombie_type = "axe"
        self._load_sprites(self.zombie_type)

    @classmethod
    def _load_sprites(cls, zombie_type: str) -> None:
        if zombie_type in cls._sprite_cache:
            return

        data = ZOMBIE_TYPES[zombie_type]
        root = Path(data["root"])
        prefix = str(data["prefix"])
        pattern = re.compile(
            rf"{re.escape(prefix)}_(?P<direction>Down|Up|Side-left|Side)_(?P<animation>.+)-Sheet(?P<frames>\d+)\.png$",
            re.IGNORECASE,
        )
        sprite_set: dict[str, dict[str, list[pygame.Surface]]] = {}

        for spritesheet_path in root.glob(f"{prefix}_*.png"):
            match = pattern.match(spritesheet_path.name)
            if match is None:
                continue

            direction = DIRECTION_NAMES[match.group("direction").lower()]
            animation = ANIMATION_NAMES.get(match.group("animation").lower())
            if animation is None:
                continue

            frames = cls._load_spritesheet(spritesheet_path, int(match.group("frames")), int(data["scale"]))
            sprite_set.setdefault(animation, {})[direction] = frames

        if "walk" not in sprite_set:
            raise FileNotFoundError(f"Nenhuma spritesheet de zumbi encontrada em {root}")

        cls._sprite_cache[zombie_type] = sprite_set

    @classmethod
    def _load_spritesheet(cls, path: Path, frame_count: int, scale: int) -> list[pygame.Surface]:
        display_ready = pygame.display.get_surface() is not None
        sheet = pygame.image.load(str(path))
        if display_ready:
            sheet = sheet.convert_alpha()

        frame_width = sheet.get_width() // frame_count
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []
        for frame_index in range(frame_count):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(
                sheet,
                (0, 0),
                pygame.Rect(frame_index * frame_width, 0, frame_width, frame_height),
            )
            frames.append(
                pygame.transform.scale(
                    frame,
                    (frame_width * scale, frame_height * scale),
                )
            )
        return frames

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

    def _available_animation(self, animation: str, direction: str) -> tuple[str, str]:
        sprites = self._sprite_cache[self.zombie_type]
        animations = sprites.get(animation)
        if animations and direction in animations:
            return animation, direction
        if animations and "right" in animations:
            return animation, "right"
        if animations and "left" in animations:
            return animation, "left"
        return "walk", direction if direction in sprites["walk"] else "down"

    def _animation_key(self) -> str:
        if self._state == "dead":
            return self._death_variant
        if self._state == "attack":
            return self._attack_variant
        if self._state == "retreat":
            return "walk"
        return self._state

    def _current_frames(self) -> list[pygame.Surface]:
        animation, direction = self._available_animation(self._animation_key(), self.facing_direction)
        return self._sprite_cache[self.zombie_type][animation][direction]

    def _current_sprite(self) -> pygame.Surface:
        frames = self._current_frames()
        frame_index = min(int(self.animation_time), len(frames) - 1)
        if self._state not in {"attack", "dead"}:
            frame_index %= len(frames)
        return frames[frame_index]

    def _has_animation(self, animation: str) -> bool:
        return animation in self._sprite_cache[self.zombie_type]

    def _choose_attack_variant(self, distance: float, force_lunge: bool = False) -> str:
        if self.zombie_type == "small" and (force_lunge or self._can_start_lunge(distance)):
            return "attack_2"
        if self.zombie_type == "small":
            return "walk"
        variants = [name for name in ("attack_1", "attack_2") if self._has_animation(name)]
        if self.zombie_type != "small" and variants:
            return random.choice(variants)
        if self._has_animation("attack_1"):
            return "attack_1"
        if self._has_animation("attack_2"):
            return "attack_2"
        return "walk"

    def _can_start_lunge(self, distance: float) -> bool:
        return (
            self.zombie_type == "small"
            and self._has_animation("attack_2")
            and SMALL_LUNGE_MIN_DISTANCE <= distance <= SMALL_LUNGE_MAX_DISTANCE
        )

    def _start_attack(
        self,
        target: pygame.Vector2,
        distance: float,
        world_rect: pygame.Rect | None,
        force_lunge: bool = False,
    ) -> None:
        if self.zombie_type == "small" and not force_lunge and not self._can_start_lunge(distance):
            self._start_retreat()
            return

        if self._state != "attack":
            self._set_state("attack")
        else:
            self.animation_time = 0.0
            self._attack_has_hit = False

        self._attack_variant = self._choose_attack_variant(distance, force_lunge)
        self._attack_started = True
        self._attack_start_position = self.position.copy()
        self._attack_target_position = self.position.copy()

        if self._attack_variant != "attack_2" or self.zombie_type != "small" or distance <= 0:
            return

        direction = (target - self.position).normalize()
        travel_distance = min(SMALL_LUNGE_MAX_TRAVEL, max(0.0, distance - self.radius * 0.35))
        landing_position = self.position + (direction * travel_distance)
        if world_rect is not None:
            landing_position.x = max(world_rect.left + self.radius, min(world_rect.right - self.radius, landing_position.x))
            landing_position.y = max(world_rect.top + self.radius, min(world_rect.bottom - self.radius, landing_position.y))
        self._attack_target_position = landing_position

    def _start_retreat(self) -> None:
        if self._state != "retreat":
            self._set_state("retreat")
        self._retreat_timer = max(self._retreat_timer, SMALL_RETREAT_MIN_TIME)

    def _set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self.animation_time = 0.0
        if state == "attack":
            self._attack_has_hit = False
        elif state == "retreat":
            self._attack_has_hit = False
        elif state == "dead":
            sprites = self._sprite_cache[self.zombie_type]
            variants = [
                name
                for name in ("death_1", "death_2")
                if name in sprites and self.facing_direction in sprites[name]
            ]
            if not variants:
                variants = [name for name in ("death_1", "death_2") if name in sprites]
            self._death_variant = random.choice(variants) if variants else "walk"

    def is_dying(self) -> bool:
        return self.health <= 0

    def consume_attack_started(self) -> bool:
        started = self._attack_started
        self._attack_started = False
        return started

    def attack_sfx_name(self) -> str:
        if self.zombie_type == "small" and self._attack_variant == "attack_2":
            return "zombie_small_dash"
        if self.zombie_type == "big":
            return "zombie_big_attack"
        return "zombie_normal_attack"

    def can_be_searched(self) -> bool:
        return self._death_finished and not self.corpse_searched and self.corpse_timer > 0

    def _update_lunge_motion(self, frame_count: int) -> None:
        if self.zombie_type != "small" or self._state != "attack" or self._attack_variant != "attack_2":
            return

        start_frame = max(1.0, frame_count * SMALL_LUNGE_START_FRAME_RATIO)
        end_frame = max(start_frame + 1.0, frame_count * SMALL_LUNGE_END_FRAME_RATIO)
        progress = (self.animation_time - start_frame) / (end_frame - start_frame)
        progress = max(0.0, min(1.0, progress))
        eased_progress = progress * progress * (3.0 - (2.0 * progress))
        self.position = self._attack_start_position.lerp(self._attack_target_position, eased_progress)

    def _clamp_to_world(self, world_rect: pygame.Rect | None) -> None:
        if world_rect is None:
            return
        self.position.x = max(world_rect.left + self.radius, min(world_rect.right - self.radius, self.position.x))
        self.position.y = max(world_rect.top + self.radius, min(world_rect.bottom - self.radius, self.position.y))

    def _move_away_from_target(
        self,
        target: pygame.Vector2,
        dt: float,
        world_rect: pygame.Rect | None,
    ) -> float:
        away = self.position - target
        if away.length_squared() <= 0:
            away = pygame.Vector2(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
            if away.length_squared() <= 0:
                away = pygame.Vector2(1, 0)

        base_direction = away.normalize()
        step_distance = self.speed * SMALL_RETREAT_SPEED_MULTIPLIER * dt
        direction = base_direction
        if world_rect is not None:
            best_position = self.position
            best_distance = -1.0
            best_moved_position: pygame.Vector2 | None = None
            best_moved_direction: pygame.Vector2 | None = None
            best_moved_distance = -1.0
            for candidate in (
                base_direction,
                base_direction.rotate(35),
                base_direction.rotate(-35),
                base_direction.rotate(75),
                base_direction.rotate(-75),
                base_direction.rotate(115),
                base_direction.rotate(-115),
            ):
                test_position = self.position + candidate * step_distance
                test_position.x = max(world_rect.left + self.radius, min(world_rect.right - self.radius, test_position.x))
                test_position.y = max(world_rect.top + self.radius, min(world_rect.bottom - self.radius, test_position.y))
                test_distance = test_position.distance_to(target)
                if test_position.distance_squared_to(self.position) > 0.01 and test_distance > best_moved_distance:
                    best_moved_distance = test_distance
                    best_moved_position = test_position
                    best_moved_direction = candidate
                if test_distance > best_distance:
                    best_distance = test_distance
                    best_position = test_position
                    direction = candidate
            if best_moved_position is not None and best_position.distance_squared_to(self.position) <= 0.01:
                best_position = best_moved_position
                if best_moved_direction is not None:
                    direction = best_moved_direction

        self.facing_direction = self._direction_from_vector(direction)
        if world_rect is None:
            self.position += direction * step_distance
        else:
            self.position = best_position
        self._is_moving = True
        return self.position.distance_to(target)

    def _update_small_behavior(
        self,
        target: pygame.Vector2,
        distance: float,
        dt: float,
        world_rect: pygame.Rect | None,
    ) -> None:
        if self._state == "attack":
            return

        if self._state == "retreat":
            self._retreat_timer -= dt
            distance = self._move_away_from_target(target, dt, world_rect)
            if distance >= SMALL_RETREAT_TARGET_DISTANCE and self._retreat_timer <= 0:
                self._set_state("idle")
            elif self._retreat_timer <= -SMALL_RETREAT_FORCED_LUNGE_TIME:
                self._start_attack(target, distance, world_rect, force_lunge=True)
            return

        if distance < SMALL_RETREAT_TRIGGER_DISTANCE:
            self._start_retreat()
            self._move_away_from_target(target, dt, world_rect)
            return

        if self._can_start_lunge(distance):
            self._start_attack(target, distance, world_rect)
            return

        if distance > 0:
            direction = (target - self.position).normalize()
            self.facing_direction = self._direction_from_vector(direction)
            self._set_state("walk")
            self.position += direction * self.speed * dt
            self._clamp_to_world(world_rect)
            self._is_moving = True

    def update(
        self,
        player_position: Tuple[float, float],
        dt: float,
        world_rect: pygame.Rect | None = None,
    ) -> None:
        if self._state == "dead":
            frames = self._current_frames()
            self.animation_time = min(len(frames) - 1, self.animation_time + dt * ANIMATION_FPS.get(self._death_variant, 9.0))
            self._death_finished = self.animation_time >= len(frames) - 1
            if self._death_finished:
                self.corpse_timer = max(0.0, self.corpse_timer - dt)
            if self.hit_flash_timer > 0:
                self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
            return

        target = pygame.Vector2(player_position)
        offset = target - self.position
        distance = offset.length()
        self._is_moving = False

        if self.zombie_type == "small":
            self._update_small_behavior(target, distance, dt, world_rect)
        elif distance > 0:
            direction = offset.normalize()
            self.facing_direction = self._direction_from_vector(direction)

            if self._state == "attack":
                pass
            elif self._can_start_lunge(distance) or distance <= self.ATTACK_RANGE + 14:
                self._start_attack(target, distance, world_rect)
            else:
                self._set_state("walk")
                self.position += direction * self.speed * dt
                self._is_moving = True
        else:
            self._set_state("idle")

        frames = self._current_frames()
        fps = ANIMATION_FPS.get(self._animation_key(), 10.0)
        self.animation_time += dt * fps
        self._update_lunge_motion(len(frames))
        if self._state == "attack" and self.animation_time >= len(frames):
            if self.zombie_type == "small" and self._attack_variant == "attack_2":
                self._start_retreat()
            else:
                self._set_state("idle")
        elif self._state in {"idle", "walk", "retreat"}:
            self.animation_time %= len(frames)

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
        if self.is_dying():
            return False
        return self.position.distance_to(pygame.Vector2(player_position)) < (self.radius + player_radius)

    def can_damage_player(self, player_position: Tuple[float, float], player_radius: int) -> bool:
        if self.is_dying() or self._state != "attack" or self._attack_has_hit:
            return False

        frames = self._current_frames()
        if self.zombie_type == "small" and self._attack_variant == "attack_2":
            impact_frame = max(1, int(len(frames) * SMALL_LUNGE_HIT_FRAME_RATIO))
        else:
            impact_frame = max(1, len(frames) - 2)
        if int(self.animation_time) < impact_frame:
            return False

        player_offset = pygame.Vector2(player_position) - self.position
        hit_range = (self.ATTACK_RANGE + 8) if self._attack_variant == "attack_2" else self.ATTACK_RANGE
        if player_offset.length() > hit_range + player_radius:
            return False

        self._attack_has_hit = True
        return True

    def take_damage(self, amount: int) -> None:
        if self.is_dying():
            return
        self.health = max(0, self.health - amount)
        self.hit_flash_timer = 0.18
        if self.health <= 0:
            self._set_state("dead")

    def is_dead(self) -> bool:
        return self._death_finished and self.corpse_timer <= 0
