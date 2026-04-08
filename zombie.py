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
    hit_flash_timer: float = 0.0
    walk_cycle: float = 0.0

    def update(self, player_position: Tuple[float, float], dt: float) -> None:
        target = pygame.Vector2(player_position)
        direction = target - self.position
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.position += direction * self.speed * dt
            self.walk_cycle += dt * 7.5
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2 | None = None) -> None:
        offset = camera_offset or pygame.Vector2()
        draw_pos = self.position - offset
        body_color = (94, 126, 88) if self.hit_flash_timer <= 0 else (230, 240, 240)
        side = pygame.Vector2(1, 0).rotate(self.walk_cycle * 20)
        sway = side.y * 2.2
        shadow_points = [
            draw_pos + pygame.Vector2(-10, 6),
            draw_pos + pygame.Vector2(10, 6),
            draw_pos + pygame.Vector2(8, 15),
            draw_pos + pygame.Vector2(-8, 15),
        ]
        pygame.draw.polygon(surface, (18, 22, 24), shadow_points)

        body_rect = pygame.Rect(0, 0, 18, 20)
        body_rect.center = (draw_pos.x, draw_pos.y + 4)
        pygame.draw.ellipse(surface, body_color, body_rect)
        pygame.draw.ellipse(surface, (166, 187, 149), body_rect.inflate(-6, -8).move(-2, -2))

        left_arm_start = draw_pos + pygame.Vector2(-7, 1)
        right_arm_start = draw_pos + pygame.Vector2(7, 1)
        pygame.draw.line(surface, (76, 103, 72), left_arm_start, left_arm_start + pygame.Vector2(-5, 7 + sway), 4)
        pygame.draw.line(surface, (76, 103, 72), right_arm_start, right_arm_start + pygame.Vector2(5, 7 - sway), 4)

        left_leg = draw_pos + pygame.Vector2(-4, 12)
        right_leg = draw_pos + pygame.Vector2(4, 12)
        pygame.draw.line(surface, (62, 82, 58), left_leg, left_leg + pygame.Vector2(-2, 7 - sway), 4)
        pygame.draw.line(surface, (62, 82, 58), right_leg, right_leg + pygame.Vector2(2, 7 + sway), 4)

        head_pos = draw_pos + pygame.Vector2(0, -6)
        pygame.draw.circle(surface, (126, 156, 109), head_pos, 8)
        pygame.draw.circle(surface, (48, 28, 24), head_pos + pygame.Vector2(-2, 0), 1)
        pygame.draw.circle(surface, (48, 28, 24), head_pos + pygame.Vector2(2, 0), 1)
        if self.hit_flash_timer > 0:
            flash_radius = self.radius + 5
            pygame.draw.circle(surface, (255, 120, 120), draw_pos, flash_radius, 2)

    def collides_with_player(self, player_position: Tuple[float, float], player_radius: int) -> bool:
        return self.position.distance_to(pygame.Vector2(player_position)) < (self.radius + player_radius)

    def take_damage(self, amount: int) -> None:
        self.health = max(0, self.health - amount)
        self.hit_flash_timer = 0.18

    def is_dead(self) -> bool:
        return self.health <= 0
