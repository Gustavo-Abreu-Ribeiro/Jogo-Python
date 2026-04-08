from __future__ import annotations

import random
from typing import Dict, List, Tuple

import pygame

from crafting import CraftingSystem
from inventory import Inventory
from player import Player
from save_system import load_game, save_game
from weapons import WEAPONS
from zombie import Zombie


WIDTH, HEIGHT = 960, 540
BG_COLOR = (20, 20, 25)
PICKUP_RANGE = 36

RESOURCE_TYPES = {
    "madeira": (160, 120, 60),
    "metal": (140, 140, 150),
    "comida": (180, 80, 70),
}


class Resource:
    def __init__(self, kind: str, position: Tuple[int, int]) -> None:
        self.kind = kind
        self.position = pygame.Vector2(position)
        self.radius = 8
        self.color = RESOURCE_TYPES[kind]

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, self.color, self.position, self.radius)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Jogo de Sobrevivencia Zumbi")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)

        # Estruturas obrigatorias
        self.game_time: float = 0.0
        self.difficulty_scale: float = 1.0
        self.spawn_rate: float = 1.0
        self.is_game_running: bool = True

        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.crafting = CraftingSystem()

        # Estrutura obrigatoria: lista de zumbis
        self.zombies: List[Zombie] = []
        self.resources: List[Resource] = []

        self._zombie_spawn_timer = 0.0
        self._resource_spawn_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0

        self._recipe_names = self.crafting.get_recipe_names()
        self._selected_recipe_index = 0

        self._spawn_initial_resources()

    def _spawn_initial_resources(self) -> None:
        for _ in range(8):
            self._spawn_resource()

    def _spawn_resource(self) -> None:
        kind = random.choice(list(RESOURCE_TYPES.keys()))
        x = random.randint(40, WIDTH - 40)
        y = random.randint(40, HEIGHT - 40)
        self.resources.append(Resource(kind, (x, y)))

    def _spawn_zombie(self) -> None:
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            pos = (random.randint(0, WIDTH), -20)
        elif side == "bottom":
            pos = (random.randint(0, WIDTH), HEIGHT + 20)
        elif side == "left":
            pos = (-20, random.randint(0, HEIGHT))
        else:
            pos = (WIDTH + 20, random.randint(0, HEIGHT))

        speed = 60.0 + (self.difficulty_scale * 12.0)
        health = int(30 + (self.difficulty_scale * 6.0))
        self.zombies.append(Zombie(pygame.Vector2(pos), speed, health=health))

    def _apply_loaded_state(self, data: Dict) -> None:
        self.player.player_health = int(data.get("player_health", 100))
        position = data.get("player_position", (WIDTH / 2, HEIGHT / 2))
        self.player.set_position(position)
        self.inventory = Inventory(data.get("inventory", None))
        self.game_time = float(data.get("game_time", 0.0))
        loaded_weapon = data.get("current_weapon")
        if loaded_weapon in WEAPONS:
            self.player.current_weapon = loaded_weapon

    def process_input(self) -> Tuple[pygame.Vector2, bool, bool, bool, bool]:
        direction = pygame.Vector2(0, 0)
        running = False
        craft_pressed = False
        collect_pressed = False
        attack_pressed = False

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
                    collect_pressed = True
                elif event.key == pygame.K_1:
                    self._equip_weapon("lanca")
                elif event.key == pygame.K_2:
                    self._equip_weapon("machado")
                elif event.key == pygame.K_3:
                    self._equip_weapon("espada")
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

        return direction, running, craft_pressed, collect_pressed, attack_pressed

    def _update_difficulty(self, dt: float) -> None:
        self.game_time += dt
        self.difficulty_scale = 1.0 + (self.game_time / 60.0)
        self.spawn_rate = 1.0 + (self.game_time / 45.0)

    def _update_zombies(self, dt: float) -> None:
        for zombie in self.zombies:
            zombie.update(self.player.player_position, dt)
            if zombie.collides_with_player(self.player.player_position, self.player.radius):
                self.player.take_damage(8)
        self.zombies = [zombie for zombie in self.zombies if not zombie.is_dead()]

    def _update_resources(self, dt: float) -> None:
        self._resource_spawn_timer += dt
        if self._resource_spawn_timer >= 6.0:
            self._resource_spawn_timer = 0.0
            if len(self.resources) < 12:
                self._spawn_resource()

    def _update_spawns(self, dt: float) -> None:
        self._zombie_spawn_timer += dt
        spawn_interval = max(0.4, 2.6 / self.spawn_rate)
        if self._zombie_spawn_timer >= spawn_interval:
            self._zombie_spawn_timer = 0.0
            self._spawn_zombie()

    def _handle_crafting(self, craft_pressed: bool) -> None:
        if not craft_pressed:
            return
        recipe_name = self._get_selected_recipe()
        success, message = self.crafting.craft(recipe_name, self.inventory)
        self._set_message(message)

    def _handle_collect(self, collect_pressed: bool) -> None:
        if not collect_pressed:
            return

        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = PICKUP_RANGE + self.player.radius

        for resource in self.resources:
            distance = resource.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = resource

        if closest:
            self.inventory.add_item(closest.kind, 1)
            self.resources.remove(closest)
            self._set_message(f"+1 {closest.kind}")
        else:
            self._set_message("Nada para coletar.")

    def _handle_attack(self, attack_pressed: bool) -> None:
        if not attack_pressed or self._attack_timer > 0:
            return

        stats = WEAPONS.get(self.player.current_weapon, WEAPONS["lanca"])
        attack_range = float(stats["range"])
        damage = int(stats["damage"])
        cooldown = float(stats["cooldown"])

        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = attack_range

        for zombie in self.zombies:
            distance = zombie.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = zombie

        if closest:
            closest.take_damage(damage)
            if closest.is_dead():
                self.zombies.remove(closest)

        self._attack_timer = cooldown

    def _set_message(self, text: str) -> None:
        self._message = text
        self._message_timer = 2.2

    def update_game_state(
        self,
        direction: pygame.Vector2,
        running: bool,
        craft_pressed: bool,
        collect_pressed: bool,
        attack_pressed: bool,
        dt: float,
    ) -> None:
        if self._game_over:
            return

        self._attack_timer = max(0.0, self._attack_timer - dt)
        self._update_difficulty(dt)
        self.player.move(direction, dt, running)
        self.player.clamp_to_area(WIDTH, HEIGHT)
        self.player.update(dt)

        self._update_spawns(dt)
        self._update_zombies(dt)
        self._update_resources(dt)
        self._handle_collect(collect_pressed)
        self._handle_attack(attack_pressed)
        self._handle_crafting(craft_pressed)

        if self.player.is_dead():
            self._game_over = True
            self._set_message("Game Over - pressione ESC")

    def render(self, dt: float) -> None:
        self.screen.fill(BG_COLOR)

        for resource in self.resources:
            resource.draw(self.screen)

        for zombie in self.zombies:
            zombie.draw(self.screen)

        self.player.draw(self.screen)
        self._draw_crosshair()
        self._draw_ui()

        if self._message_timer > 0:
            self._message_timer = max(0.0, self._message_timer - dt)

        pygame.display.flip()

    def _draw_crosshair(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, (220, 220, 220), mouse_pos, 6, 1)

    def _draw_ui(self) -> None:
        current_recipe = self._get_selected_recipe()
        recipe = self.crafting.get_recipe(current_recipe) or {}
        cost_text = ", ".join([f"{item}:{amount}" for item, amount in recipe.items()]) if recipe else "-"

        lines = [
            f"Vida: {self.player.player_health}",
            f"Stamina: {int(self.player.player_stamina)}",
            f"Tempo: {self.game_time:.1f}s",
            f"Dificuldade: {self.difficulty_scale:.2f}",
            f"Zumbis: {len(self.zombies)}",
            f"Arma atual: {self.player.current_weapon}",
            f"Receita: {current_recipe} ({cost_text})",
            "Inventario:",
            f"  madeira: {self.inventory.get_quantity('madeira')}",
            f"  metal: {self.inventory.get_quantity('metal')}",
            f"  comida: {self.inventory.get_quantity('comida')}",
            f"  lanca: {self.inventory.get_quantity('lanca')}",
            f"  machado: {self.inventory.get_quantity('machado')}",
            f"  espada: {self.inventory.get_quantity('espada')}",
            "TAB troca receita | C craftar | E coletar | Clique/SPACE atacar",
            "1/2/3 equipar (lanca/machado/espada) | F5 salvar | F9 carregar",
        ]

        y = 10
        for line in lines:
            text = self.font.render(line, True, (230, 230, 230))
            self.screen.blit(text, (10, y))
            y += 20

        if self._message_timer > 0:
            msg = self.font.render(self._message, True, (255, 210, 80))
            self.screen.blit(msg, (10, HEIGHT - 30))

    def run(self) -> None:
        while self.is_game_running:
            dt = self.clock.tick(60) / 1000.0
            direction, running, craft_pressed, collect_pressed, attack_pressed = self.process_input()
            self.update_game_state(direction, running, craft_pressed, collect_pressed, attack_pressed, dt)
            self.render(dt)

    def _get_selected_recipe(self) -> str:
        if not self._recipe_names:
            return "lanca"
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
