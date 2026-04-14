from __future__ import annotations

from typing import Tuple

import pygame

from weapons import WEAPONS


class Player:
    def __init__(self, position: Tuple[float, float]) -> None:
       
        self.max_health: int = 100
        self.max_hunger: float = 100.0
        self.player_health: int = 100
        self.player_hunger: float = 100.0
        self.player_stamina: float = 100.0
        self.player_position: Tuple[float, float] = position
        self.current_weapon: str = "lanca"

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
        self._walk_cycle = 0.0
        self._is_moving = False

    def move(self, direction: pygame.Vector2, dt: float, running: bool) -> None:
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.facing_direction = direction
            self._walk_cycle += dt * (12 if running else 8)
            self._is_moving = True
        else:
            self._is_moving = False

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
        self.attack_animation_timer = 0.12

    def update(self, dt: float) -> None:
        if self._damage_cooldown > 0:
            self._damage_cooldown = max(0.0, self._damage_cooldown - dt)
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        if self.heal_flash_timer > 0:
            self.heal_flash_timer = max(0.0, self.heal_flash_timer - dt)
        if self.attack_animation_timer > 0:
            self.attack_animation_timer = max(0.0, self.attack_animation_timer - dt)

    def is_dead(self) -> bool:
        return self.player_health <= 0

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2 | None = None) -> None:
        offset = camera_offset or pygame.Vector2()
        draw_pos = self._pos - offset
        weapon_stats = WEAPONS.get(self.current_weapon, WEAPONS["lanca"])
        base_reach = 18
        attack_reach = int(weapon_stats["range"] * 0.55)
        attack_progress = self.attack_animation_timer / 0.12 if self.attack_animation_timer > 0 else 0.0
        current_reach = base_reach + int(attack_reach * attack_progress)

        weapon_start = draw_pos + self.facing_direction * (self.radius - 2)
        weapon_tip = weapon_start + self.facing_direction * current_reach
        sweep_side = pygame.Vector2(-self.facing_direction.y, self.facing_direction.x)

        weapon_shadow_start = weapon_start + pygame.Vector2(2, 2)
        weapon_shadow_tip = weapon_tip + pygame.Vector2(2, 2)
        pygame.draw.line(surface, (18, 22, 24), weapon_shadow_start, weapon_shadow_tip, 5)

        if self.current_weapon == "lanca":
            pygame.draw.line(surface, (170, 134, 87), weapon_start, weapon_tip, 4)
            pygame.draw.circle(surface, (222, 227, 221), weapon_tip, 5)
        elif self.current_weapon == "machado":
            axe_head = weapon_tip + sweep_side * 8
            pygame.draw.line(surface, (128, 86, 58), weapon_start, weapon_tip, 6)
            pygame.draw.line(surface, (213, 217, 210), weapon_tip, axe_head, 8)
        else:
            blade_left = weapon_tip + sweep_side * 4
            blade_right = weapon_tip - sweep_side * 4
            pygame.draw.line(surface, (136, 101, 69), weapon_start, weapon_tip, 5)
            pygame.draw.polygon(surface, (221, 225, 220), [weapon_tip, blade_left, blade_right])

        player_color = (85, 140, 164)
        if self.heal_flash_timer > 0:
            player_color = (103, 194, 125)
        elif self.hit_flash_timer > 0:
            player_color = (214, 96, 88)

        walk_swing = 0.0
        if self._is_moving:
            walk_swing = pygame.math.Vector2(0, 1).rotate(self._walk_cycle * 24).y * 2.4
        side = pygame.Vector2(-self.facing_direction.y, self.facing_direction.x)
        back_pos = draw_pos - self.facing_direction * 3
        front_pos = draw_pos + self.facing_direction * 3

        shadow_points = [
            back_pos - side * 8 + pygame.Vector2(2, 4),
            back_pos + side * 8 + pygame.Vector2(2, 4),
            front_pos + side * 10 + pygame.Vector2(2, 4),
            front_pos - side * 10 + pygame.Vector2(2, 4),
        ]
        pygame.draw.polygon(surface, (18, 22, 24), shadow_points)

        back_leg = back_pos - side * (3 + walk_swing * 0.4)
        front_leg = back_pos + side * (3 + walk_swing * 0.4)
        pygame.draw.line(surface, (55, 73, 78), back_leg, back_leg - self.facing_direction * 8, 4)
        pygame.draw.line(surface, (55, 73, 78), front_leg, front_leg - self.facing_direction * 8, 4)

        body_points = [
            back_pos - side * 8,
            back_pos + side * 8,
            front_pos + side * 10,
            front_pos - side * 10,
        ]
        pygame.draw.polygon(surface, player_color, body_points)
        pygame.draw.polygon(surface, (214, 222, 217), [point + pygame.Vector2(-2, -2) for point in body_points[:3]], 0)

        arm_offset = side * (5 + walk_swing * 0.2)
        arm_anchor = draw_pos + self.facing_direction * 1
        pygame.draw.line(surface, (201, 173, 142), arm_anchor - arm_offset, weapon_start, 5)
        pygame.draw.line(surface, (201, 173, 142), arm_anchor + arm_offset, weapon_start - side * 2, 5)

        head_pos = draw_pos + self.facing_direction * 7
        pygame.draw.circle(surface, (42, 58, 63), head_pos + pygame.Vector2(0, -1), 10)
        pygame.draw.circle(surface, (216, 192, 164), head_pos, 8)
        eye_pos = head_pos + self.facing_direction * 3
        pygame.draw.circle(surface, (24, 30, 32), eye_pos + side * 2, 1)
        pygame.draw.circle(surface, (24, 30, 32), eye_pos - side * 2, 1)
