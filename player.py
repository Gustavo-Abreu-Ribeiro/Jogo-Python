from __future__ import annotations

from typing import Tuple

import pygame


class Player:
    def __init__(self, position: Tuple[float, float]) -> None:
        # Estruturas obrigatorias
        self.player_health: int = 100
        self.player_stamina: float = 100.0
        self.player_position: Tuple[float, float] = position
        self.current_weapon: str = "lanca"

        self._pos = pygame.Vector2(position)
        self.radius = 14
        self.base_speed = 140.0
        self.run_speed = 210.0
        self.stamina_recovery = 18.0
        self.stamina_cost = 28.0
        self._damage_cooldown = 0.0

    def move(self, direction: pygame.Vector2, dt: float, running: bool) -> None:
        if direction.length_squared() > 0:
            direction = direction.normalize()

        speed = self.base_speed
        if running and self.player_stamina > 0:
            speed = self.run_speed
            self.player_stamina = max(0.0, self.player_stamina - self.stamina_cost * dt)
        else:
            self.player_stamina = min(100.0, self.player_stamina + self.stamina_recovery * dt)

        self._pos += direction * speed * dt
        self.player_position = (self._pos.x, self._pos.y)

    def clamp_to_area(self, width: int, height: int) -> None:
        self._pos.x = max(self.radius, min(width - self.radius, self._pos.x))
        self._pos.y = max(self.radius, min(height - self.radius, self._pos.y))
        self.player_position = (self._pos.x, self._pos.y)

    def set_position(self, position: Tuple[float, float]) -> None:
        self._pos.update(position)
        self.player_position = (self._pos.x, self._pos.y)

    def take_damage(self, amount: int) -> None:
        if self._damage_cooldown > 0:
            return
        self.player_health = max(0, self.player_health - amount)
        self._damage_cooldown = 0.6

    def update(self, dt: float) -> None:
        if self._damage_cooldown > 0:
            self._damage_cooldown = max(0.0, self._damage_cooldown - dt)

    def is_dead(self) -> bool:
        return self.player_health <= 0

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, (70, 150, 230), self._pos, self.radius)
