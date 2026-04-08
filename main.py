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
WORLD_WIDTH, WORLD_HEIGHT = 2200, 1400
BG_COLOR = (24, 29, 31)
SEARCH_RANGE = 50
STATION_RANGE = 70
SAFE_ZONE_RADIUS = 170

PALETTE = {
    "bg_deep": (18, 24, 27),
    "ground_a": (49, 62, 58),
    "ground_b": (56, 71, 66),
    "border": (86, 102, 94),
    "panel": (14, 18, 21),
    "panel_edge": (84, 96, 101),
    "text": (233, 233, 224),
    "text_soft": (188, 193, 186),
    "accent": (214, 188, 121),
    "safe_fill": (80, 107, 110),
    "safe_ring": (150, 192, 192),
    "safe_core": (228, 234, 219),
    "danger": (195, 87, 79),
}

NODE_TYPES: Dict[str, Dict[str, object]] = {
    "caixote": {
        "label": "Caixote",
        "color": (155, 111, 69),
        "loot": ["madeira", "madeira", "metal", "pano"],
        "drops": (2, 4),
        "ambush": 0.15,
    },
    "sucata": {
        "label": "Monte de Sucata",
        "color": (116, 126, 129),
        "loot": ["metal", "metal", "madeira", "pano"],
        "drops": (2, 4),
        "ambush": 0.25,
    },
    "despensa": {
        "label": "Despensa",
        "color": (174, 108, 89),
        "loot": ["comida", "comida", "pano", "erva", "kit_medico"],
        "drops": (2, 3),
        "ambush": 0.1,
    },
    "erva": {
        "label": "Ervas",
        "color": (92, 149, 96),
        "loot": ["erva", "erva", "comida"],
        "drops": (2, 3),
        "ambush": 0.05,
    },
    "arsenal": {
        "label": "Arsenal",
        "color": (155, 142, 91),
        "loot": ["metal", "pano", "lanca", "machado", "espada"],
        "drops": (1, 2),
        "ambush": 0.35,
    },
}

STATION_TYPES: Dict[str, Dict[str, object]] = {
    "bancada": {"label": "Bancada", "color": (102, 138, 157)},
    "fogueira": {"label": "Fogueira", "color": (216, 132, 81)},
}


class Decoration:
    def __init__(self, decor_type: str, position: Tuple[int, int], scale: float = 1.0) -> None:
        self.decor_type = decor_type
        self.position = pygame.Vector2(position)
        self.scale = scale

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = self.position - camera_offset
        if self.decor_type == "tree":
            trunk_rect = pygame.Rect(0, 0, int(12 * self.scale), int(22 * self.scale))
            trunk_rect.midbottom = (draw_pos.x, draw_pos.y + 12 * self.scale)
            pygame.draw.ellipse(surface, PALETTE["bg_deep"], trunk_rect.move(2, 3))
            pygame.draw.rect(surface, (104, 78, 56), trunk_rect, border_radius=4)

            leaf_colors = [(74, 116, 74), (92, 139, 92), (118, 156, 104)]
            leaf_offsets = [(-12, -6), (10, -8), (0, -18)]
            for color, (off_x, off_y) in zip(leaf_colors, leaf_offsets):
                pygame.draw.circle(
                    surface,
                    color,
                    draw_pos + pygame.Vector2(off_x * self.scale, off_y * self.scale),
                    int(14 * self.scale),
                )
        elif self.decor_type == "rock":
            points = [
                draw_pos + pygame.Vector2(-12, 8) * self.scale,
                draw_pos + pygame.Vector2(-8, -8) * self.scale,
                draw_pos + pygame.Vector2(6, -10) * self.scale,
                draw_pos + pygame.Vector2(14, 2) * self.scale,
                draw_pos + pygame.Vector2(8, 12) * self.scale,
                draw_pos + pygame.Vector2(-6, 14) * self.scale,
            ]
            pygame.draw.polygon(surface, PALETTE["bg_deep"], [point + pygame.Vector2(2, 3) for point in points])
            pygame.draw.polygon(surface, (108, 118, 119), points)
            pygame.draw.polygon(surface, (138, 148, 148), points[:4])
        else:
            pygame.draw.circle(surface, (92, 149, 96), draw_pos, int(10 * self.scale))


class SearchNode:
    def __init__(self, node_type: str, position: Tuple[int, int]) -> None:
        self.node_type = node_type
        self.position = pygame.Vector2(position)
        self.radius = 18
        self.searched = False

    def search(self) -> Tuple[Dict[str, int], int]:
        node_data = NODE_TYPES[self.node_type]
        min_drops, max_drops = node_data["drops"]
        loot_items = node_data["loot"]
        drop_count = random.randint(min_drops, max_drops)

        rewards: Dict[str, int] = {}
        for _ in range(drop_count):
            item = random.choice(loot_items)
            rewards[item] = rewards.get(item, 0) + 1

        ambush_count = 0
        if random.random() < float(node_data["ambush"]):
            ambush_count = random.randint(1, 2)

        self.searched = True
        return rewards, ambush_count

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = self.position - camera_offset
        node_data = NODE_TYPES[self.node_type]
        color = node_data["color"]
        if self.searched:
            color = tuple(max(40, channel // 2) for channel in color)

        shadow_pos = draw_pos + pygame.Vector2(2, 3)
        if self.node_type == "caixote":
            rect = pygame.Rect(0, 0, 28, 24)
            rect.center = draw_pos
            pygame.draw.rect(surface, PALETTE["bg_deep"], rect.move(2, 3), border_radius=4)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.line(surface, (101, 72, 48), rect.midtop, rect.midbottom, 2)
            pygame.draw.line(surface, (101, 72, 48), rect.midleft, rect.midright, 2)
        elif self.node_type == "sucata":
            points = [draw_pos + pygame.Vector2(-16, 8), draw_pos + pygame.Vector2(-10, -8), draw_pos + pygame.Vector2(5, -10), draw_pos + pygame.Vector2(16, 6), draw_pos + pygame.Vector2(2, 14)]
            pygame.draw.polygon(surface, PALETTE["bg_deep"], [point + pygame.Vector2(2, 3) for point in points])
            pygame.draw.polygon(surface, color, points)
            pygame.draw.line(surface, (160, 168, 171), points[0], points[2], 2)
        elif self.node_type == "despensa":
            rect = pygame.Rect(0, 0, 24, 28)
            rect.center = draw_pos
            pygame.draw.rect(surface, PALETTE["bg_deep"], rect.move(2, 3), border_radius=6)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            pygame.draw.rect(surface, (214, 190, 163), rect.inflate(-10, -12).move(0, -2), border_radius=4)
        elif self.node_type == "erva":
            pygame.draw.circle(surface, PALETTE["bg_deep"], shadow_pos, self.radius)
            for angle in (-40, -15, 10, 35):
                tip = draw_pos + pygame.Vector2(0, -16).rotate(angle)
                base_left = draw_pos + pygame.Vector2(-3, 8)
                base_right = draw_pos + pygame.Vector2(3, 8)
                pygame.draw.polygon(surface, color, [base_left, tip, base_right])
        else:
            pygame.draw.circle(surface, PALETTE["bg_deep"], shadow_pos, self.radius)
            pygame.draw.circle(surface, color, draw_pos, self.radius)
            pygame.draw.rect(surface, (110, 90, 64), pygame.Rect(draw_pos.x - 12, draw_pos.y - 3, 24, 8), border_radius=3)

        if not self.searched:
            pygame.draw.circle(surface, PALETTE["accent"], draw_pos, self.radius + 4, 1)
        if self.searched:
            pygame.draw.line(surface, PALETTE["text"], draw_pos + (-8, -8), draw_pos + (8, 8), 2)


class Station:
    def __init__(self, station_type: str, position: Tuple[int, int]) -> None:
        self.station_type = station_type
        self.position = pygame.Vector2(position)
        self.size = 30

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = self.position - camera_offset
        station_data = STATION_TYPES[self.station_type]
        rect = pygame.Rect(0, 0, self.size, self.size)
        rect.center = (draw_pos.x, draw_pos.y)
        pygame.draw.rect(surface, PALETTE["bg_deep"], rect.move(2, 3), border_radius=5)
        pygame.draw.circle(surface, (*station_data["color"], 0), draw_pos, STATION_RANGE, 1)
        if self.station_type == "bancada":
            table_rect = pygame.Rect(0, 0, self.size + 8, self.size - 6)
            table_rect.center = (draw_pos.x, draw_pos.y)
            pygame.draw.rect(surface, station_data["color"], table_rect, border_radius=5)
            pygame.draw.rect(surface, tuple(min(255, c + 20) for c in station_data["color"]), table_rect.inflate(-10, -12).move(0, -2), border_radius=4)
            for off_x in (-10, 10):
                pygame.draw.line(surface, (82, 61, 46), draw_pos + pygame.Vector2(off_x, 6), draw_pos + pygame.Vector2(off_x, 16), 4)
        else:
            pygame.draw.circle(surface, (88, 68, 48), draw_pos + pygame.Vector2(0, 2), 12)
            flame_colors = [(252, 219, 124), (240, 145, 74), station_data["color"]]
            flame_offsets = [(0, -8), (-4, -2), (4, -1)]
            flame_sizes = [9, 7, 7]
            for flame_color, flame_offset, flame_size in zip(flame_colors, flame_offsets, flame_sizes):
                pygame.draw.circle(surface, flame_color, draw_pos + pygame.Vector2(flame_offset), flame_size)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Jogo de Sobrevivencia Zumbi")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 16)

        self.game_time: float = 0.0
        self.difficulty_scale: float = 1.0
        self.spawn_rate: float = 1.0
        self.is_game_running: bool = True

        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.inventory = Inventory()
        self.crafting = CraftingSystem()

        self.zombies: List[Zombie] = []
        self.nodes: List[SearchNode] = []
        self.stations: List[Station] = []
        self.decorations: List[Decoration] = []

        self._spawn_timer = 0.0
        self._starvation_timer = 0.0
        self._message = ""
        self._message_timer = 0.0
        self._game_over = False
        self._attack_timer = 0.0
        self._camera = pygame.Vector2()

        self._recipe_names = self.crafting.get_recipe_names()
        self._selected_recipe_index = 0
        self._base_position = pygame.Vector2(WORLD_WIDTH * 0.48, WORLD_HEIGHT * 0.52)
        self._show_inventory = False
        self._show_help = False

        self._generate_world()
        self.player.set_position(tuple(self._base_position))
        self.inventory.add_item("comida", 2)

    def _generate_world(self) -> None:
        self.nodes.clear()
        self.stations.clear()
        self.zombies.clear()
        self.decorations.clear()

        for station_type, position in [
            ("bancada", (int(self._base_position.x - 90), int(self._base_position.y - 30))),
            ("fogueira", (int(self._base_position.x + 90), int(self._base_position.y + 20))),
            ("fogueira", (WORLD_WIDTH - 260, 260)),
            ("bancada", (WORLD_WIDTH - 320, WORLD_HEIGHT - 240)),
            ("fogueira", (340, WORLD_HEIGHT - 260)),
        ]:
            self.stations.append(Station(station_type, position))

        node_pool = [
            "caixote",
            "caixote",
            "sucata",
            "sucata",
            "despensa",
            "despensa",
            "erva",
            "erva",
            "arsenal",
        ]
        for _ in range(28):
            self.nodes.append(SearchNode(random.choice(node_pool), self._random_world_position()))

        for _ in range(44):
            decor_type = "tree" if random.random() < 0.7 else "rock"
            decor_pos = self._random_world_position(80)
            if pygame.Vector2(decor_pos).distance_to(self._base_position) > SAFE_ZONE_RADIUS + 90:
                self.decorations.append(Decoration(decor_type, decor_pos, random.uniform(0.85, 1.25)))

        for _ in range(6):
            self._spawn_zombie()

    def _random_world_position(self, margin: int = 120) -> Tuple[int, int]:
        return (
            random.randint(margin, WORLD_WIDTH - margin),
            random.randint(margin, WORLD_HEIGHT - margin),
        )

    def _spawn_zombie(self, near_position: Tuple[float, float] | pygame.Vector2 | None = None) -> None:
        if near_position is None:
            pos = pygame.Vector2(self._random_world_position())
            while pos.distance_to(pygame.Vector2(self.player.player_position)) < 260:
                pos = pygame.Vector2(self._random_world_position())
        else:
            base = pygame.Vector2(near_position)
            offset = pygame.Vector2(random.randint(-120, 120), random.randint(-120, 120))
            pos = base + offset
            pos.x = max(30, min(WORLD_WIDTH - 30, pos.x))
            pos.y = max(30, min(WORLD_HEIGHT - 30, pos.y))

        speed = 55.0 + (self.difficulty_scale * 5.0)
        health = int(24 + (self.difficulty_scale * 4.0))
        self.zombies.append(Zombie(pos, speed, health=health))

    def _apply_loaded_state(self, data: Dict) -> None:
        self.player.player_health = int(data.get("player_health", 100))
        self.player.player_hunger = float(data.get("player_hunger", 100.0))
        position = data.get("player_position", tuple(self._base_position))
        self.player.set_position(position)
        self.inventory = Inventory(data.get("inventory", None))
        self.game_time = float(data.get("game_time", 0.0))
        loaded_weapon = data.get("current_weapon")
        if loaded_weapon in WEAPONS:
            self.player.current_weapon = loaded_weapon

    def process_input(self) -> Tuple[pygame.Vector2, bool, bool, bool, bool, bool]:
        direction = pygame.Vector2(0, 0)
        running = False
        craft_pressed = False
        search_pressed = False
        attack_pressed = False
        heal_pressed = False

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
                    search_pressed = True
                elif event.key == pygame.K_i:
                    self._show_inventory = not self._show_inventory
                elif event.key == pygame.K_h:
                    self._show_help = not self._show_help
                elif event.key == pygame.K_q:
                    heal_pressed = True
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

        return direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed

    def _update_difficulty(self, dt: float) -> None:
        self.game_time += dt
        self.difficulty_scale = 1.0 + (self.game_time / 150.0)
        self.spawn_rate = 1.0 + (self.game_time / 180.0)

    def _update_survival(self, dt: float) -> None:
        self.player.player_hunger = max(0.0, self.player.player_hunger - (0.75 * dt))
        if self.player.player_hunger <= 0:
            self._starvation_timer += dt
            if self._starvation_timer >= 1.4:
                self._starvation_timer = 0.0
                if self.player.take_damage(5):
                    self._set_message("Voce esta morrendo de fome!")
        else:
            self._starvation_timer = 0.0

    def _update_zombies(self, dt: float) -> None:
        base_pos = pygame.Vector2(self._base_position)
        for zombie in self.zombies:
            zombie.update(self.player.player_position, dt)
            if zombie.position.distance_to(base_pos) < SAFE_ZONE_RADIUS - 10:
                push_direction = zombie.position - base_pos
                if push_direction.length_squared() > 0:
                    zombie.position += push_direction.normalize() * 110 * dt
            if zombie.collides_with_player(self.player.player_position, self.player.radius):
                if self.player.take_damage(10):
                    self._set_message("Voce foi atingido!")
        self.zombies = [zombie for zombie in self.zombies if not zombie.is_dead()]

    def _update_spawns(self, dt: float) -> None:
        self._spawn_timer += dt
        max_zombies = 6 + int(self.game_time / 120.0)
        if self._spawn_timer >= max(14.0, 22.0 / self.spawn_rate) and len(self.zombies) < max_zombies:
            self._spawn_timer = 0.0
            unexplored_nodes = [node for node in self.nodes if not node.searched]
            if unexplored_nodes:
                target_node = random.choice(unexplored_nodes)
                self._spawn_zombie(target_node.position)
            else:
                self._spawn_zombie()

    def _find_nearest_node(self) -> SearchNode | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = SEARCH_RANGE

        for node in self.nodes:
            if node.searched:
                continue
            distance = node.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = node

        return closest

    def _find_nearest_station(self) -> Station | None:
        player_pos = pygame.Vector2(self.player.player_position)
        closest = None
        closest_distance = STATION_RANGE

        for station in self.stations:
            distance = station.position.distance_to(player_pos)
            if distance <= closest_distance:
                closest_distance = distance
                closest = station

        return closest

    def _handle_search(self, search_pressed: bool) -> None:
        if not search_pressed:
            return

        node = self._find_nearest_node()
        if node is None:
            self._set_message("Nada interessante por perto.")
            return

        rewards, ambush_count = node.search()
        for item, amount in rewards.items():
            self.inventory.add_item(item, amount)

        reward_text = ", ".join(f"{item} x{amount}" for item, amount in rewards.items())
        message = f"Voce encontrou: {reward_text}"

        for _ in range(ambush_count):
            self._spawn_zombie(node.position)
        if ambush_count > 0:
            message = f"{message} | Emboscada: {ambush_count} zumbi(s)!"
        self._set_message(message)

    def _handle_attack(self, attack_pressed: bool) -> None:
        if not attack_pressed or self._attack_timer > 0:
            return

        stats = WEAPONS.get(self.player.current_weapon, WEAPONS["lanca"])
        attack_range = float(stats["range"])
        damage = int(stats["damage"])
        cooldown = float(stats["cooldown"])

        player_pos = pygame.Vector2(self.player.player_position)
        facing = self.player.facing_direction
        closest = None
        closest_distance = attack_range

        for zombie in self.zombies:
            offset = zombie.position - player_pos
            distance = offset.length()
            if distance > attack_range or distance == 0:
                continue
            direction_to_zombie = offset.normalize()
            if facing.dot(direction_to_zombie) < 0.35:
                continue
            if distance <= closest_distance:
                closest_distance = distance
                closest = zombie

        self.player.start_attack_animation()
        if closest:
            closest.take_damage(damage)
            if closest.is_dead():
                self.zombies.remove(closest)
                if random.random() < 0.35:
                    dropped_item = random.choice(["comida", "metal", "erva"])
                    self.inventory.add_item(dropped_item, 1)
                    self._set_message(f"Zumbi derrotado! +1 {dropped_item}")
                else:
                    self._set_message("Zumbi derrotado!")
            else:
                self._set_message("Acerto!")

        self._attack_timer = cooldown

    def _handle_heal(self, heal_pressed: bool) -> None:
        if not heal_pressed:
            return

        if self.inventory.get_quantity("kit_medico") > 0 and self.player.player_health < self.player.max_health:
            self.inventory.remove_item("kit_medico", 1)
            healed_amount = self.player.heal(55)
            self._set_message(f"Kit medico usado. +{healed_amount} vida.")
            return

        if self.inventory.get_quantity("comida") <= 0:
            self._set_message("Voce nao tem comida nem kit medico.")
            return

        self.inventory.remove_item("comida", 1)
        hunger_restored = int(self.player.restore_hunger(32))
        healed_amount = self.player.heal(12)
        self._set_message(f"Voce comeu. Fome +{hunger_restored}, vida +{healed_amount}.")

    def _handle_crafting(self, craft_pressed: bool) -> None:
        if not craft_pressed:
            return

        nearby_station = self._find_nearest_station()
        station_name = nearby_station.station_type if nearby_station else None
        recipe_name = self._get_selected_recipe()
        success, message = self.crafting.craft(recipe_name, self.inventory, station_name)
        self._set_message(message)

    def _set_message(self, text: str) -> None:
        self._message = text
        self._message_timer = 2.8

    def update_game_state(
        self,
        direction: pygame.Vector2,
        running: bool,
        craft_pressed: bool,
        search_pressed: bool,
        attack_pressed: bool,
        heal_pressed: bool,
        dt: float,
    ) -> None:
        if self._game_over:
            return

        self._attack_timer = max(0.0, self._attack_timer - dt)
        self._update_difficulty(dt)
        self._update_survival(dt)
        self.player.move(direction, dt, running)
        self.player.clamp_to_area(WORLD_WIDTH, WORLD_HEIGHT)
        self.player.aim_at(self.screen_to_world(pygame.mouse.get_pos()))
        self.player.update(dt)

        self._update_spawns(dt)
        self._update_zombies(dt)
        self._handle_search(search_pressed)
        self._handle_attack(attack_pressed)
        self._handle_heal(heal_pressed)
        self._handle_crafting(craft_pressed)

        if self.player.is_dead():
            self._game_over = True
            self._set_message("Game Over - pressione ESC")

    def render(self, dt: float) -> None:
        self._update_camera()
        self.screen.fill(BG_COLOR)
        self._draw_ground()

        for decoration in self.decorations:
            decoration.draw(self.screen, self._camera)

        for station in self.stations:
            station.draw(self.screen, self._camera)

        for node in self.nodes:
            node.draw(self.screen, self._camera)

        for zombie in self.zombies:
            zombie.draw(self.screen, self._camera)

        self.player.draw(self.screen, self._camera)
        self._draw_crosshair()
        self._draw_prompt()
        self._draw_ui()
        self._draw_damage_overlay()

        if self._message_timer > 0:
            self._message_timer = max(0.0, self._message_timer - dt)

        pygame.display.flip()

    def _update_camera(self) -> None:
        player_pos = pygame.Vector2(self.player.player_position)
        self._camera.x = max(0, min(WORLD_WIDTH - WIDTH, player_pos.x - (WIDTH / 2)))
        self._camera.y = max(0, min(WORLD_HEIGHT - HEIGHT, player_pos.y - (HEIGHT / 2)))

    def screen_to_world(self, screen_position: Tuple[int, int]) -> pygame.Vector2:
        return pygame.Vector2(screen_position) + self._camera

    def _draw_ground(self) -> None:
        tile_size = 64
        for x in range(0, WORLD_WIDTH, tile_size):
            for y in range(0, WORLD_HEIGHT, tile_size):
                rect = pygame.Rect(x - self._camera.x, y - self._camera.y, tile_size, tile_size)
                if rect.right < 0 or rect.left > WIDTH or rect.bottom < 0 or rect.top > HEIGHT:
                    continue
                tile_color = PALETTE["ground_a"] if (x // tile_size + y // tile_size) % 2 == 0 else PALETTE["ground_b"]
                pygame.draw.rect(self.screen, tile_color, rect)
                pygame.draw.rect(self.screen, PALETTE["bg_deep"], rect, 1)

        self._draw_base_area()
        border_rect = pygame.Rect(-self._camera.x, -self._camera.y, WORLD_WIDTH, WORLD_HEIGHT)
        pygame.draw.rect(self.screen, PALETTE["border"], border_rect, 8)

    def _draw_base_area(self) -> None:
        draw_pos = self._base_position - self._camera
        aura_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(aura_surface, (*PALETTE["safe_fill"], 50), draw_pos, SAFE_ZONE_RADIUS)
        self.screen.blit(aura_surface, (0, 0))
        pygame.draw.circle(self.screen, PALETTE["safe_ring"], draw_pos, SAFE_ZONE_RADIUS, 2)
        pygame.draw.circle(self.screen, PALETTE["safe_core"], draw_pos, 22)
        pygame.draw.circle(self.screen, PALETTE["safe_fill"], draw_pos, 22, 4)

    def _draw_crosshair(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, (220, 220, 220), mouse_pos, 6, 1)

    def _draw_prompt(self) -> None:
        prompt = ""
        node = self._find_nearest_node()
        station = self._find_nearest_station()

        if node is not None:
            label = NODE_TYPES[node.node_type]["label"]
            prompt = f"E buscar em {label}"
        elif station is not None:
            label = STATION_TYPES[station.station_type]["label"]
            prompt = f"Perto de {label}: pressione C para craftar"

        if not prompt:
            return

        text = self.small_font.render(prompt, True, PALETTE["accent"])
        bg_rect = pygame.Rect(0, 0, text.get_width() + 24, 28)
        bg_rect.center = (WIDTH // 2, HEIGHT - 26)
        panel = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 220), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (*PALETTE["accent"], 200), panel.get_rect(), 1, border_radius=8)
        self.screen.blit(panel, bg_rect.topleft)
        text_rect = text.get_rect(center=bg_rect.center)
        self.screen.blit(text, text_rect)

    def _draw_damage_overlay(self) -> None:
        if self.player.hit_flash_timer <= 0 and self.player.heal_flash_timer <= 0:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self.player.hit_flash_timer > 0:
            alpha = int(120 * (self.player.hit_flash_timer / 0.22))
            overlay.fill((*PALETTE["danger"], alpha))
        else:
            alpha = int(90 * (self.player.heal_flash_timer / 0.25))
            overlay.fill((62, 136, 90, alpha))
        self.screen.blit(overlay, (0, 0))

    def _draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        ratio: float,
        fill_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
    ) -> None:
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=4)
        pygame.draw.rect(self.screen, PALETTE["text"], (x, y, width, height), 1, border_radius=4)
        fill_width = max(0, min(width, int(width * ratio)))
        if fill_width > 0:
            pygame.draw.rect(self.screen, fill_color, (x, y, fill_width, height), border_radius=4)

    def _draw_ui(self) -> None:
        current_recipe = self._get_selected_recipe()
        recipe = self.crafting.get_recipe(current_recipe) or {}
        recipe_cost = recipe.get("cost", {})
        station_needed = recipe.get("station", "-")
        nearby_station = self._find_nearest_station()
        weapon_stats = WEAPONS.get(self.player.current_weapon, WEAPONS["lanca"])
        nearby_node = self._find_nearest_node()
        nearby_node_text = NODE_TYPES[nearby_node.node_type]["label"] if nearby_node else ""

        left_panel = pygame.Surface((258, 112), pygame.SRCALPHA)
        pygame.draw.rect(left_panel, (*PALETTE["panel"], 210), left_panel.get_rect(), border_radius=10)
        pygame.draw.rect(left_panel, PALETTE["panel_edge"], left_panel.get_rect(), 1, border_radius=10)
        self.screen.blit(left_panel, (8, 8))

        self._draw_stat_row(18, 18, (210, 60, 60), self.player.player_health / self.player.max_health, "HP")
        self._draw_stat_row(18, 46, (80, 170, 240), self.player.player_stamina / 100.0, "ST")
        self._draw_stat_row(18, 74, (220, 170, 70), self.player.player_hunger / self.player.max_hunger, "FO")

        self._draw_equipment_card(current_recipe, recipe_cost, station_needed, weapon_stats, nearby_station, nearby_node_text)

        self._draw_minimap()
        self._draw_corner_hints()

        if self._show_inventory:
            self._draw_inventory_panel()
        if self._show_help:
            self._draw_help_panel()

        if self._message_timer > 0:
            msg = self.font.render(self._message, True, (255, 210, 80))
            self.screen.blit(msg, (10, HEIGHT - 30))

    def _draw_minimap(self) -> None:
        map_width = 220
        map_height = 140
        map_x = WIDTH - map_width - 14
        map_y = 14
        panel = pygame.Surface((map_width, map_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 220), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (map_x, map_y))

        inner_rect = pygame.Rect(map_x + 10, map_y + 10, map_width - 20, map_height - 20)
        pygame.draw.rect(self.screen, PALETTE["bg_deep"], inner_rect, border_radius=6)

        scale_x = inner_rect.width / WORLD_WIDTH
        scale_y = inner_rect.height / WORLD_HEIGHT

        base_dot = (
            inner_rect.x + int(self._base_position.x * scale_x),
            inner_rect.y + int(self._base_position.y * scale_y),
        )
        pygame.draw.circle(self.screen, PALETTE["safe_ring"], base_dot, 5)

        for station in self.stations:
            dot = (
                inner_rect.x + int(station.position.x * scale_x),
                inner_rect.y + int(station.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, STATION_TYPES[station.station_type]["color"], dot, 4)

        for node in self.nodes:
            if node.searched:
                continue
            dot = (
                inner_rect.x + int(node.position.x * scale_x),
                inner_rect.y + int(node.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, NODE_TYPES[node.node_type]["color"], dot, 2)

        for zombie in self.zombies:
            dot = (
                inner_rect.x + int(zombie.position.x * scale_x),
                inner_rect.y + int(zombie.position.y * scale_y),
            )
            pygame.draw.circle(self.screen, PALETTE["danger"], dot, 2)

        player_dot = (
            inner_rect.x + int(self.player.player_position[0] * scale_x),
            inner_rect.y + int(self.player.player_position[1] * scale_y),
        )
        pygame.draw.circle(self.screen, PALETTE["text"], player_dot, 4)

        view_rect = pygame.Rect(
            inner_rect.x + int(self._camera.x * scale_x),
            inner_rect.y + int(self._camera.y * scale_y),
            max(12, int(WIDTH * scale_x)),
            max(8, int(HEIGHT * scale_y)),
        )
        pygame.draw.rect(self.screen, PALETTE["text"], view_rect, 1)

        title = self.small_font.render("Mapa", True, PALETTE["text"])
        self.screen.blit(title, (map_x + 10, map_y - 2))

    def _draw_corner_hints(self) -> None:
        hint_text = f"I inventario [{'ON' if self._show_inventory else 'OFF'}] | H ajuda [{'ON' if self._show_help else 'OFF'}]"
        text = self.small_font.render(hint_text, True, PALETTE["text_soft"])
        rect = text.get_rect(topright=(WIDTH - 14, 164))
        self.screen.blit(text, rect)

    def _draw_inventory_panel(self) -> None:
        panel_width = 280
        panel_height = 290
        panel_x = WIDTH - panel_width - 14
        panel_y = 190
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 228), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        title = self.font.render("Inventario", True, PALETTE["text"])
        self.screen.blit(title, (panel_x + 14, panel_y + 12))

        items = [
            f"madeira: {self.inventory.get_quantity('madeira')}",
            f"metal: {self.inventory.get_quantity('metal')}",
            f"pano: {self.inventory.get_quantity('pano')}",
            f"erva: {self.inventory.get_quantity('erva')}",
            f"comida: {self.inventory.get_quantity('comida')}",
            f"kit_medico: {self.inventory.get_quantity('kit_medico')}",
            f"lanca: {self.inventory.get_quantity('lanca')}",
            f"machado: {self.inventory.get_quantity('machado')}",
            f"espada: {self.inventory.get_quantity('espada')}",
        ]

        y = panel_y + 46
        for item in items:
            text = self.font.render(item, True, PALETTE["text"])
            self.screen.blit(text, (panel_x + 14, y))
            y += 24

    def _draw_help_panel(self) -> None:
        panel_width = 420
        panel_height = 210
        panel_x = (WIDTH - panel_width) // 2
        panel_y = HEIGHT - panel_height - 18
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 232), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        title = self.font.render("Ajuda", True, PALETTE["text"])
        self.screen.blit(title, (panel_x + 14, panel_y + 12))

        help_lines = [
            "WASD mover | Shift correr | Clique/SPACE atacar",
            "E vasculhar pontos | Q comer ou usar kit medico",
            "TAB trocar receita | C craftar na estacao correta",
            "1/2/3 equipar arma | F5 salvar | F9 carregar",
            "Objetivo: explorar, lootear e voltar para a base vivo",
            "Feche este painel com H",
        ]

        y = panel_y + 46
        for line in help_lines:
            text = self.small_font.render(line, True, PALETTE["text"])
            self.screen.blit(text, (panel_x + 14, y))
            y += 26

    def _draw_stat_row(self, x: int, y: int, color: Tuple[int, int, int], ratio: float, label: str) -> None:
        icon_rect = pygame.Rect(x, y, 22, 18)
        pygame.draw.rect(self.screen, color, icon_rect, border_radius=4)
        label_text = self.small_font.render(label, True, (15, 18, 20))
        self.screen.blit(label_text, (x + 3, y + 1))
        self._draw_bar(x + 30, y + 3, 190, 12, ratio, color, (45, 48, 55))

    def _draw_equipment_card(
        self,
        current_recipe: str,
        recipe_cost: Dict[str, int],
        station_needed: str,
        weapon_stats: Dict[str, float | int],
        nearby_station: Station | None,
        nearby_node_text: str,
    ) -> None:
        panel_x = 8
        panel_y = 126
        panel = pygame.Surface((258, 114), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PALETTE["panel"], 210), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, PALETTE["panel_edge"], panel.get_rect(), 1, border_radius=10)
        self.screen.blit(panel, (panel_x, panel_y))

        weapon_name = self.font.render(self.player.current_weapon.upper(), True, PALETTE["text"])
        self.screen.blit(weapon_name, (panel_x + 12, panel_y + 10))

        stats_text = self.small_font.render(f"ATK {weapon_stats['damage']}  RNG {weapon_stats['range']}", True, PALETTE["text_soft"])
        self.screen.blit(stats_text, (panel_x + 12, panel_y + 36))

        recipe_title = self.small_font.render(f"Craft: {current_recipe}", True, PALETTE["accent"])
        self.screen.blit(recipe_title, (panel_x + 12, panel_y + 60))

        cost_parts = [f"{item[:2]} {amount}" for item, amount in recipe_cost.items()]
        costs = "  ".join(cost_parts) if cost_parts else "-"
        cost_text = self.small_font.render(costs, True, PALETTE["text_soft"])
        self.screen.blit(cost_text, (panel_x + 12, panel_y + 82))

        station_ready = nearby_station is not None and nearby_station.station_type == station_needed
        station_color = (90, 200, 120) if station_ready else (210, 120, 90)
        station_label = self.small_font.render(station_needed[:3].upper(), True, station_color)
        self.screen.blit(station_label, (panel_x + 190, panel_y + 60))

        if nearby_node_text:
            point_text = self.small_font.render(nearby_node_text, True, PALETTE["text_soft"])
            self.screen.blit(point_text, (panel_x + 150, panel_y + 10))

    def run(self) -> None:
        while self.is_game_running:
            dt = self.clock.tick(60) / 1000.0
            direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed = self.process_input()
            self.update_game_state(direction, running, craft_pressed, search_pressed, attack_pressed, heal_pressed, dt)
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
