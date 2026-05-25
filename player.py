from __future__ import annotations

from pathlib import Path
import random
import re
from typing import ClassVar, Tuple

import pygame


CHARACTER_ROOT = Path(__file__).resolve().parent / "sprites" / "character"
LOADOUTS = {
    "maos": {"root": CHARACTER_ROOT / "Main", "prefix": "Character"},
    "taco": {"root": CHARACTER_ROOT / "Bat", "prefix": "Bat"},
    "pistola": {"root": CHARACTER_ROOT / "Guns" / "Pistol", "prefix": "Pistol"},
    "escopeta": {"root": CHARACTER_ROOT / "Guns" / "Shotgun", "prefix": "Shotgun"},
}
LOADOUT_ALIASES = {
    "pistola_incendiaria": "pistola",
    "pistola_perfurante": "pistola",
    "escopeta_incendiaria": "escopeta",
}
WEAPON_TINTS = {
    "pistola_incendiaria": (255, 118, 72),
    "pistola_perfurante": (92, 178, 255),
    "escopeta_incendiaria": (255, 96, 70),
}
WEAPON_LAYER_OFFSETS = {
    "taco": {
        "down": (0, -12),
        "left": (0, -9),
        "right": (0, -9),
        "up": (0, -6),
    },
    "pistola": {
        "down": (0, -12),
        "left": (0, -12),
        "right": (0, -12),
        "up": (0, -6),
    },
    "escopeta": {
        "down": (0, -12),
        "left": (0, -12),
        "right": (0, -12),
        "up": (0, -6),
    },
}
EQUIPPED_WEAPON_Y_SHIFT = 6
DIRECTION_NAMES = {
    "down": "down",
    "side-left": "left",
    "side": "right",
    "up": "up",
}
ANIMATION_NAMES = {
    "idle": "idle",
    "idle-and-run": "idle_and_run",
    "run": "run",
    "punch": "attack",
    "attack": "attack",
    "shoot": "attack",
    "pick-up": "pickup",
    "death1": "death_1",
    "death2": "death_2",
    "death3": "death_3",
}
ANIMATION_FPS = {
    "idle": 6.0,
    "run": 10.0,
    "attack": 14.0,
    "pickup": 10.0,
    "death_1": 9.0,
    "death_2": 9.0,
    "death_3": 9.0,
}


class Player:
    SPRITE_SCALE: ClassVar[int] = 3
    _sprite_cache: ClassVar[dict[str, dict[str, dict[str, list[pygame.Surface]]]]] = {}
    _shadow_cache: ClassVar[dict[tuple[int, int], pygame.Surface]] = {}

    def __init__(self, position: Tuple[float, float]) -> None:
        self.max_health: int = 100
        self.max_hunger: float = 100.0
        self.player_health: int = 100
        self.player_hunger: float = 100.0
        self.player_stamina: float = 100.0
        self.player_position: Tuple[float, float] = position
        self.current_weapon: str = "maos"

        self._pos = pygame.Vector2(position)
        self.facing_direction = pygame.Vector2(1, 0)
        self.radius = 14
        self.base_speed = 140.0
        self.run_speed = 210.0
        self.stamina_recovery = 18.0
        self.stamina_cost = 28.0
        self._damage_cooldown = 0.0
        self.hit_flash_timer = 0.0
        self.heal_flash_timer = 0.0
        self.attack_animation_timer = 0.0
        self._is_moving = False
        self._is_running = False
        self._state = "idle"
        self._animation_time = 0.0
        self._pickup_timer = 0.0
        self._death_variant = "death_1"
        self._death_finished = False
        self._load_sprites()

    @classmethod
    def _load_sprites(cls) -> None:
        if cls._sprite_cache:
            return

        main_full = cls._load_loadout_sprites("maos", LOADOUTS["maos"], include_no_hands=False)
        main_body = cls._load_loadout_sprites("body", LOADOUTS["maos"], include_no_hands=True)
        cls._sprite_cache["maos"] = main_full

        for loadout_name in ("taco", "pistola", "escopeta"):
            weapon_layers = cls._load_loadout_sprites(loadout_name, LOADOUTS[loadout_name], include_no_hands=False)
            cls._sprite_cache[loadout_name] = cls._compose_weapon_loadout(loadout_name, main_body, weapon_layers)

        for variant_name, base_name in LOADOUT_ALIASES.items():
            weapon_layers = cls._load_loadout_sprites(base_name, LOADOUTS[base_name], include_no_hands=False)
            weapon_layers = cls._tint_weapon_layers(weapon_layers, WEAPON_TINTS[variant_name])
            cls._sprite_cache[variant_name] = cls._compose_weapon_loadout(variant_name, main_body, weapon_layers)

        if "maos" not in cls._sprite_cache or "idle" not in cls._sprite_cache["maos"]:
            raise FileNotFoundError(f"Nenhuma spritesheet do personagem encontrada em {CHARACTER_ROOT}")

    @classmethod
    def _load_loadout_sprites(
        cls,
        loadout_name: str,
        data: dict[str, object],
        include_no_hands: bool,
    ) -> dict[str, dict[str, list[pygame.Surface]]]:
        animations: dict[str, dict[str, list[pygame.Surface]]] = {}
        root = Path(data["root"])
        prefix = str(data["prefix"])
        pattern = re.compile(
            rf"{re.escape(prefix)}_(?P<direction>down|up|side-left|side)_(?P<animation>.+)-Sheet(?P<frames>\d+)\.png$",
            re.IGNORECASE,
        )

        for spritesheet_path in root.rglob(f"{prefix}_*.png"):
            filename = spritesheet_path.name.lower()
            is_no_hands = "no-hands" in filename or "nohands" in filename
            if is_no_hands != include_no_hands:
                continue

            match = pattern.match(spritesheet_path.name)
            if match is None:
                continue

            direction = DIRECTION_NAMES[match.group("direction").lower()]
            raw_animation = match.group("animation").lower()
            raw_animation = raw_animation.replace("_nohands", "").replace("_no-hands", "")
            animation = ANIMATION_NAMES.get(raw_animation)
            if animation is None:
                continue

            frames = cls._load_spritesheet(spritesheet_path, int(match.group("frames")))
            if animation == "idle_and_run":
                animations.setdefault("idle", {})[direction] = frames
                animations.setdefault("run", {})[direction] = frames
            else:
                animations.setdefault(animation, {})[direction] = frames

        return animations

    @classmethod
    def _compose_weapon_loadout(
        cls,
        loadout_name: str,
        body: dict[str, dict[str, list[pygame.Surface]]],
        weapon_layers: dict[str, dict[str, list[pygame.Surface]]],
    ) -> dict[str, dict[str, list[pygame.Surface]]]:
        composed: dict[str, dict[str, list[pygame.Surface]]] = {}

        for animation, directions in weapon_layers.items():
            body_animation = "attack" if animation == "attack" else animation
            if body_animation not in body:
                continue

            for direction, weapon_frames in directions.items():
                body_frames = body[body_animation].get(direction)
                if not body_frames:
                    continue
                frame_count = min(len(body_frames), len(weapon_frames))
                frames = [
                    cls._compose_frame(body_frames[index], weapon_frames[index], loadout_name, direction)
                    for index in range(frame_count)
                ]
                composed.setdefault(animation, {})[direction] = frames

        for animation in ("pickup", "death_1", "death_2", "death_3"):
            if animation in body:
                composed[animation] = body[animation]

        return composed

    @staticmethod
    def _compose_frame(
        body: pygame.Surface,
        weapon_layer: pygame.Surface,
        loadout_name: str,
        direction: str,
    ) -> pygame.Surface:
        offset_source = LOADOUT_ALIASES.get(loadout_name, loadout_name)
        offset_x, offset_y = WEAPON_LAYER_OFFSETS.get(offset_source, {}).get(direction, (0, 0))
        offset_y += EQUIPPED_WEAPON_Y_SHIFT
        width = max(body.get_width(), weapon_layer.get_width())
        height = max(body.get_height(), weapon_layer.get_height() + abs(offset_y))
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        body_rect = body.get_rect(midbottom=(width // 2, height))
        weapon_rect = weapon_layer.get_rect(midbottom=(width // 2 + offset_x, height + offset_y))
        if direction == "up":
            frame.blit(weapon_layer, weapon_rect)
            frame.blit(body, body_rect)
        else:
            frame.blit(body, body_rect)
            frame.blit(weapon_layer, weapon_rect)
        return frame

    @classmethod
    def _tint_weapon_layers(
        cls,
        weapon_layers: dict[str, dict[str, list[pygame.Surface]]],
        color: tuple[int, int, int],
    ) -> dict[str, dict[str, list[pygame.Surface]]]:
        tinted_layers: dict[str, dict[str, list[pygame.Surface]]] = {}
        for animation, directions in weapon_layers.items():
            for direction, frames in directions.items():
                tinted_layers.setdefault(animation, {})[direction] = [cls._tint_sprite(frame, color) for frame in frames]
        return tinted_layers

    @staticmethod
    def _tint_sprite(sprite: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
        tinted = sprite.copy()
        overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        overlay.fill((*color, 0))
        tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tinted

    @classmethod
    def _load_spritesheet(cls, path: Path, frame_count: int) -> list[pygame.Surface]:
        display_ready = pygame.display.get_surface() is not None
        sheet = pygame.image.load(str(path))
        if display_ready:
            sheet = sheet.convert_alpha()

        frame_count = cls._resolve_frame_count(path, sheet.get_width(), frame_count)
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
                    (frame_width * cls.SPRITE_SCALE, frame_height * cls.SPRITE_SCALE),
                )
            )
        return frames

    @staticmethod
    def _resolve_frame_count(path: Path, sheet_width: int, declared_frame_count: int) -> int:
        if declared_frame_count > 0 and sheet_width % declared_frame_count == 0:
            return declared_frame_count

        # Some death spritesheets are exported with a wrong SheetN suffix.
        for candidate in range(max(1, declared_frame_count - 2), declared_frame_count + 4):
            if candidate > 0 and sheet_width % candidate == 0:
                return candidate

        return max(1, declared_frame_count)

    def move(self, direction: pygame.Vector2, dt: float, running: bool) -> None:
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.facing_direction = direction
            self._is_moving = True
            self._is_running = running and self.player_stamina > 0
        else:
            self._is_moving = False
            self._is_running = False

        hunger_ratio = self.player_hunger / self.max_hunger
        speed_penalty = 0.72 if hunger_ratio < 0.2 else 1.0
        recovery_bonus = 0.55 if hunger_ratio < 0.25 else 1.0

        speed = self.base_speed * speed_penalty
        if running and self.player_stamina > 0:
            speed = self.run_speed * speed_penalty
            self.player_stamina = max(0.0, self.player_stamina - self.stamina_cost * dt)
        else:
            self.player_stamina = min(100.0, self.player_stamina + (self.stamina_recovery * recovery_bonus * dt))

        self._pos += direction * speed * dt
        self.player_position = (self._pos.x, self._pos.y)

    def clamp_to_area(self, width: int, height: int) -> None:
        self._pos.x = max(self.radius, min(width - self.radius, self._pos.x))
        self._pos.y = max(self.radius, min(height - self.radius, self._pos.y))
        self.player_position = (self._pos.x, self._pos.y)

    def set_position(self, position: Tuple[float, float]) -> None:
        self._pos.update(position)
        self.player_position = (self._pos.x, self._pos.y)

    def aim_at(self, target_position: Tuple[float, float]) -> None:
        direction = pygame.Vector2(target_position) - self._pos
        if direction.length_squared() > 0:
            self.facing_direction = direction.normalize()

    def take_damage(self, amount: int) -> bool:
        if self._damage_cooldown > 0:
            return False
        self.player_health = max(0, self.player_health - amount)
        self._damage_cooldown = 0.6
        self.hit_flash_timer = 0.22
        if self.player_health <= 0:
            self.start_death_animation()
        return True

    def heal(self, amount: int) -> int:
        previous_health = self.player_health
        self.player_health = min(self.max_health, self.player_health + amount)
        healed_amount = self.player_health - previous_health
        if healed_amount > 0:
            self.heal_flash_timer = 0.25
        return healed_amount

    def restore_hunger(self, amount: float) -> float:
        previous_hunger = self.player_hunger
        self.player_hunger = min(self.max_hunger, self.player_hunger + amount)
        return self.player_hunger - previous_hunger

    def start_attack_animation(self) -> None:
        frames = self._frames_for("attack", self._direction_key())
        self.attack_animation_timer = len(frames) / ANIMATION_FPS["attack"]
        self._pickup_timer = 0.0
        self._set_state("attack")

    def start_pickup_animation(self) -> None:
        frames = self._frames_for("pickup", self._direction_key())
        self.attack_animation_timer = 0.0
        self._pickup_timer = len(frames) / ANIMATION_FPS["pickup"] if frames else 0.3
        self._set_state("pickup")

    def start_death_animation(self) -> None:
        if self._state == "dead":
            return
        variants = [
            name
            for name in ("death_1", "death_2", "death_3")
            if self._has_animation(name, self._direction_key())
        ]
        if not variants:
            variants = [name for name in ("death_1", "death_2", "death_3") if self._has_animation(name)]
        self._death_variant = random.choice(variants) if variants else "idle"
        self._set_state("dead")

    def update(self, dt: float) -> None:
        if self._damage_cooldown > 0:
            self._damage_cooldown = max(0.0, self._damage_cooldown - dt)
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        if self.heal_flash_timer > 0:
            self.heal_flash_timer = max(0.0, self.heal_flash_timer - dt)
        if self.attack_animation_timer > 0:
            self.attack_animation_timer = max(0.0, self.attack_animation_timer - dt)
        if self._pickup_timer > 0:
            self._pickup_timer = max(0.0, self._pickup_timer - dt)

        if self.player_health <= 0:
            self.start_death_animation()
        elif self.attack_animation_timer > 0:
            self._set_state("attack")
        elif self._pickup_timer > 0:
            self._set_state("pickup")
        elif self._is_moving:
            self._set_state("run")
        else:
            self._set_state("idle")

        frames = self._current_frames()
        fps = ANIMATION_FPS.get(self._animation_key(), 8.0)
        if self._state == "run" and self._is_running:
            fps = 13.0
        if self._state == "dead":
            self._animation_time = min(len(frames) - 1, self._animation_time + dt * fps)
            self._death_finished = self._animation_time >= len(frames) - 1
        else:
            self._animation_time = (self._animation_time + dt * fps) % len(frames)

    def is_dead(self) -> bool:
        return self.player_health <= 0

    @staticmethod
    def _direction_from_vector(direction: pygame.Vector2) -> str:
        if abs(direction.x) > abs(direction.y):
            return "right" if direction.x > 0 else "left"
        return "down" if direction.y > 0 else "up"

    @staticmethod
    def _flash_sprite(sprite: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
        flashed = sprite.copy()
        overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        overlay.fill((*color, 85))
        flashed.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return flashed

    def _set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self._animation_time = 0.0

    def _direction_key(self) -> str:
        return self._direction_from_vector(self.facing_direction)

    def _animation_key(self) -> str:
        if self._state == "dead":
            return self._death_variant
        return self._state

    def _loadout_key(self) -> str:
        return self.current_weapon if self.current_weapon in self._sprite_cache else "maos"

    def _has_animation(self, animation: str, direction: str | None = None) -> bool:
        loadout_animations = self._sprite_cache.get(self._loadout_key(), {})
        fallback_animations = self._sprite_cache.get("maos", {})
        animations = loadout_animations.get(animation) or fallback_animations.get(animation)
        if not animations:
            return False
        return direction is None or direction in animations

    def _available_animation(self, animation: str, direction: str) -> tuple[str, str, str]:
        loadout = self._loadout_key()
        animations = self._sprite_cache.get(loadout, {}).get(animation)
        if animations and direction in animations:
            return loadout, animation, direction
        if animations and "right" in animations:
            return loadout, animation, "right"
        if animations and "left" in animations:
            return loadout, animation, "left"

        animations = self._sprite_cache["maos"].get(animation)
        if animations and direction in animations:
            return "maos", animation, direction
        if animations and "right" in animations:
            return "maos", animation, "right"
        if animations and "left" in animations:
            return "maos", animation, "left"

        idle_frames = self._sprite_cache["maos"]["idle"]
        return "maos", "idle", direction if direction in idle_frames else "down"

    def _frames_for(self, animation: str, direction: str) -> list[pygame.Surface]:
        loadout, animation, direction = self._available_animation(animation, direction)
        return self._sprite_cache[loadout][animation][direction]

    def _current_frames(self) -> list[pygame.Surface]:
        return self._frames_for(self._animation_key(), self._direction_key())

    def _current_sprite(self) -> pygame.Surface:
        frames = self._current_frames()
        frame_index = min(int(self._animation_time), len(frames) - 1)
        if self._state != "dead":
            frame_index %= len(frames)
        sprite = frames[frame_index]
        if self.heal_flash_timer > 0:
            sprite = self._flash_sprite(sprite, (70, 150, 80))
        elif self.hit_flash_timer > 0:
            sprite = self._flash_sprite(sprite, (155, 55, 50))
        return sprite

    @classmethod
    def _shadow_surface(cls, size: tuple[int, int]) -> pygame.Surface:
        cached = cls._shadow_cache.get(size)
        if cached is not None:
            return cached
        shadow = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (18, 22, 24, 115), shadow.get_rect())
        cls._shadow_cache[size] = shadow
        return shadow

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2 | None = None) -> None:
        offset = camera_offset or pygame.Vector2()
        draw_pos = self._pos - offset
        sprite = self._current_sprite()

        sprite_rect = sprite.get_rect(midbottom=(round(draw_pos.x), round(draw_pos.y + self.radius + 4)))
        shadow_size = (
            max(12, int(sprite_rect.width * 0.56)),
            max(6, int(sprite_rect.height * 0.18)),
        )
        shadow_surface = self._shadow_surface(shadow_size)
        shadow_rect = shadow_surface.get_rect(center=(sprite_rect.centerx + 2, sprite_rect.bottom - 3))
        surface.blit(shadow_surface, shadow_rect)
        surface.blit(sprite, sprite_rect)
