from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pygame


@dataclass
class Zombie:
    position: pygame.Vector2
    speed: float
    health: int = 30
    radius: int = 12

    def update(self, player_position: Tuple[float, float], dt: float) -> None:
        target = pygame.Vector2(player_position)
        direction = target - self.position
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.position += direction * self.speed * dt

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, (30, 180, 60), self.position, self.radius)

    def collides_with_player(self, player_position: Tuple[float, float], player_radius: int) -> bool:
        return self.position.distance_to(pygame.Vector2(player_position)) < (self.radius + player_radius)

    def take_damage(self, amount: int) -> None:
        self.health = max(0, self.health - amount)

    def is_dead(self) -> bool:
        return self.health <= 0
