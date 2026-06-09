from __future__ import annotations

import ast
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_loader import TiledMap


DOCS_DIR = ROOT / "docs"
ASSET_DIR = DOCS_DIR / "assets"
HTML_PATH = DOCS_DIR / "documentacao_tecnica_dead_streets_abnt.html"
PDF_PATH = DOCS_DIR / "documentacao_tecnica_dead_streets_abnt.pdf"
PREVIEW_PDF_PATH = DOCS_DIR / "documentacao_tecnica_dead_streets_abnt.preview.pdf"
PRIMARY_MAP_NAMES = [
    "Boss 1.tmj",
    "Boss 2.tmj",
    "Boss 3.tmj",
    "Interior 1.tmj",
    "Mapa 1.tmj",
    "Mapa 2.tmj",
    "Mapa 3.tmj",
    "Mapa 4.tmj",
]


PROJECT_TITLE = "Dead Streets"
AUTHOR = "Gustavo Emanuel Abreu Ribeiro"
RGM = "32237740"
COURSE_CONTEXT = "Programação de Computadores - UDF"
ADVISOR = "Professora Karla Roberto Sartin"
CITY = "Brasília"
YEAR = "2026"


def ensure_dirs() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    ASSET_DIR.mkdir(exist_ok=True)
    PREVIEW_PDF_PATH.unlink(missing_ok=True)
    for pattern in ("mapa-*.png", "diagrama-*.svg", "fluxo-*.svg", "showcase-sprites.png"):
        for path in ASSET_DIR.glob(pattern):
            path.unlink(missing_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def slug(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in " ._-":
            allowed.append("-")
    return "-".join("".join(allowed).split("-")).strip("-")


def parse_python_files() -> dict[str, dict[str, object]]:
    modules: dict[str, dict[str, object]] = {}
    for path in sorted(ROOT.glob("*.py")):
        tree = ast.parse(read_text(path))
        classes = []
        functions = []
        constants = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [
                    {
                        "name": item.name,
                        "line": item.lineno,
                        "args": [arg.arg for arg in item.args.args],
                    }
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes.append({"name": node.name, "line": node.lineno, "methods": methods})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({"name": node.name, "line": node.lineno})
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append({"name": target.id, "line": node.lineno})
        modules[path.name] = {
            "lines": len(read_text(path).splitlines()),
            "classes": classes,
            "functions": functions,
            "constants": constants,
        }
    return modules


def map_metadata() -> list[dict[str, object]]:
    maps = []
    for path in sorted((ROOT / "maps").glob("*.tmj")):
        data = json.loads(read_text(path))
        layers = data.get("layers", [])
        maps.append(
            {
                "name": path.name,
                "width": data.get("width"),
                "height": data.get("height"),
                "tilewidth": data.get("tilewidth"),
                "tileheight": data.get("tileheight"),
                "layers": [layer.get("name", "") for layer in layers],
                "tilesets": len(data.get("tilesets", [])),
            }
        )
    return maps


def inventory_defaults() -> dict[str, int]:
    namespace: dict[str, object] = {}
    exec(read_text(ROOT / "inventory.py"), namespace)
    inv = namespace["Inventory"]()
    return dict(inv.inventory)


def crafting_recipes() -> dict[str, dict[str, object]]:
    namespace: dict[str, object] = {}
    exec(read_text(ROOT / "crafting.py"), namespace)
    return dict(namespace["CraftingSystem"].crafting_recipes)


def weapon_data() -> dict[str, dict[str, object]]:
    namespace: dict[str, object] = {}
    exec(read_text(ROOT / "weapons.py"), namespace)
    return dict(namespace["WEAPONS"])


def line_count() -> int:
    return sum(len(read_text(path).splitlines()) for path in ROOT.glob("*.py"))


def file_size_summary() -> dict[str, object]:
    sprite_count = len(list((ROOT / "sprites").rglob("*.png")))
    audio_count = len(list((ROOT / "audio").rglob("*.ogg")))
    map_count = len(list((ROOT / "maps").glob("*.tmj")))
    tileset_count = len(list((ROOT / "maps" / "tilesets").glob("*.tsx")))
    return {
        "python_files": len(list(ROOT.glob("*.py"))),
        "python_lines": line_count(),
        "sprites": sprite_count,
        "audio": audio_count,
        "maps": map_count,
        "tilesets": tileset_count,
    }


def surface_to_png(surface: pygame.Surface, path: Path) -> None:
    pygame.image.save(surface, str(path))


def make_map_images() -> list[dict[str, str]]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    generated = []
    for name in PRIMARY_MAP_NAMES:
        path = ROOT / "maps" / name
        if not path.exists():
            continue
        try:
            tiled = TiledMap(path, scale=2)
            world = pygame.Surface((tiled.world_width, tiled.world_height), pygame.SRCALPHA)
            world.fill((23, 28, 30))
            tiled.draw(world, pygame.Vector2(0, 0))
            max_width = 1280
            if world.get_width() > max_width:
                ratio = max_width / world.get_width()
                world = pygame.transform.smoothscale(world, (max_width, max(1, int(world.get_height() * ratio))))
            output = ASSET_DIR / f"mapa-{slug(path.stem)}.png"
            surface_to_png(world, output)

            generated.append({"name": path.name, "map": output.name})
        except Exception as exc:
            print(f"Falha ao gerar mapa {path.name}: {exc}")
    return generated


def load_image(path: Path) -> pygame.Surface | None:
    if not path.exists():
        return None
    image = pygame.image.load(str(path))
    return image.convert_alpha() if pygame.display.get_surface() else image


def make_sprite_showcase() -> str:
    pygame.init()
    pygame.display.set_mode((1, 1))
    samples = [
        ROOT / "sprites" / "character" / "Main" / "Run" / "Character_down_run-Sheet6.png",
        ROOT / "sprites" / "character" / "Guns" / "Pistol" / "Pistol_side_shoot-Sheet3.png",
        ROOT / "sprites" / "character" / "Guns" / "Shotgun" / "Shotgun_down_idle-and-run-Sheet6.png",
        ROOT / "sprites" / "Zombie_Axe" / "Zombie_Axe_Down_Walk-Sheet8.png",
        ROOT / "sprites" / "Zombie_Small" / "Zombie_Small_Side_Walk-Sheet6.png",
        ROOT / "sprites" / "Zombie_Big" / "Zombie_Big_Down_First-Attack-Sheet8.png",
        ROOT / "sprites" / "Objects" / "Pickable" / "Pistol.png",
        ROOT / "sprites" / "Objects" / "Pickable" / "Shotgun.png",
        ROOT / "sprites" / "ui" / "Heart_Full.png",
        ROOT / "sprites" / "ui" / "Hunger_Full.png",
        ROOT / "sprites" / "ui" / "Icon_First-Aid-Kit_Red.png",
        ROOT / "sprites" / "ui" / "Icon_Bullet-box_Red.png",
    ]
    images = [load_image(path) for path in samples]
    images = [image for image in images if image is not None]
    cell_w, cell_h = 280, 110
    atlas = pygame.Surface((cell_w * 2, cell_h * ((len(images) + 1) // 2)), pygame.SRCALPHA)
    atlas.fill((246, 246, 242, 255))
    font = pygame.font.Font(None, 22)
    for index, image in enumerate(images):
        col = index % 2
        row = index // 2
        x = col * cell_w
        y = row * cell_h
        pygame.draw.rect(atlas, (220, 220, 214), (x + 8, y + 8, cell_w - 16, cell_h - 16), border_radius=4)
        ratio = min((cell_w - 46) / image.get_width(), (cell_h - 34) / image.get_height(), 3.0)
        scaled = pygame.transform.scale(image, (max(1, int(image.get_width() * ratio)), max(1, int(image.get_height() * ratio))))
        atlas.blit(scaled, (x + (cell_w - scaled.get_width()) // 2, y + (cell_h - scaled.get_height()) // 2))
        label = font.render(f"Amostra {index + 1}", True, (45, 45, 45))
        atlas.blit(label, (x + 14, y + 14))
    output = ASSET_DIR / "showcase-sprites.png"
    surface_to_png(atlas, output)
    return output.name


def make_architecture_svg() -> str:
    output = ASSET_DIR / "diagrama-arquitetura.svg"
    boxes = [
        ("Entrada", "Teclado, mouse e controle", 55, 70, 220, 76),
        ("Interface", "Menus, HUD, inventário e crafting", 55, 245, 220, 76),
        ("Persistência", "JSON desktop e localStorage web", 55, 420, 220, 76),
        ("Game", "Loop, estados, regras, câmera e renderização", 340, 245, 240, 88),
        ("Player", "Movimento, animação, vida, fome e stamina", 635, 35, 230, 76),
        ("Zombie", "IA, ataques, bosses, efeitos e loot", 635, 150, 230, 76),
        ("Inventário", "Itens, munições, atalhos e armas", 635, 265, 230, 76),
        ("TiledMap", "TMJ/TSX, tiles, colisões e gatilhos", 635, 380, 230, 76),
        ("Assets", "Sprites PNG, UI e áudio OGG", 340, 420, 240, 76),
    ]
    arrows = [
        ((275, 108), (340, 270)),
        ((275, 283), (340, 289)),
        ((275, 458), (340, 316)),
        ((580, 260), (635, 73)),
        ((580, 278), (635, 188)),
        ((580, 296), (635, 303)),
        ((580, 314), (635, 418)),
        ((460, 333), (460, 420)),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="920" height="535" viewBox="0 0 920 535">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#444"/></marker></defs>',
        '<rect width="920" height="535" fill="#fbfbf7"/>',
        '<text x="38" y="35" font-family="Times New Roman" font-size="22" font-weight="700" fill="#111">Arquitetura lógica do sistema</text>',
    ]
    for start, end in arrows:
        svg.append(f'<line x1="{start[0]}" y1="{start[1]}" x2="{end[0]}" y2="{end[1]}" stroke="#444" stroke-width="2" marker-end="url(#arrow)"/>')
    for title, desc, x, y, w, h in boxes:
        fill = "#e7efe7" if title == "Game" else "#f0efe8"
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="#333" stroke-width="1.4"/>')
        svg.append(f'<text x="{x + 14}" y="{y + 28}" font-family="Times New Roman" font-size="18" font-weight="700" fill="#111">{esc(title)}</text>')
        svg.append(f'<text x="{x + 14}" y="{y + 55}" font-family="Times New Roman" font-size="13" fill="#333">{esc(desc)}</text>')
    svg.append("</svg>")
    output.write_text("\n".join(svg), encoding="utf-8")
    return output.name


def make_use_case_svg() -> str:
    output = ASSET_DIR / "diagrama-caso-de-uso.svg"
    use_cases = [
        ("Iniciar novo jogo", 520, 95),
        ("Carregar jogo salvo", 520, 155),
        ("Explorar mapa", 520, 215),
        ("Buscar loot", 520, 275),
        ("Combater zumbis", 520, 335),
        ("Craftar item", 520, 395),
        ("Gerenciar inventário", 520, 455),
        ("Salvar partida", 520, 515),
        ("Acessar interior/portal", 520, 575),
        ("Derrotar boss", 520, 635),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="940" height="730" viewBox="0 0 940 730">',
        '<defs><marker id="arrow-open" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="none" stroke="#555" stroke-width="1.4"/></marker></defs>',
        '<rect width="940" height="730" fill="#fbfbf7"/>',
        '<text x="38" y="35" font-family="Times New Roman" font-size="22" font-weight="700">Diagrama de caso de uso</text>',
        '<rect x="270" y="58" width="585" height="620" rx="4" fill="#fffdf5" stroke="#333" stroke-width="1.5"/>',
        '<text x="290" y="82" font-family="Times New Roman" font-size="15" font-weight="700">Sistema Dead Streets</text>',
        '<circle cx="95" cy="190" r="22" fill="none" stroke="#111" stroke-width="2"/>',
        '<line x1="95" y1="212" x2="95" y2="300" stroke="#111" stroke-width="2"/>',
        '<line x1="52" y1="240" x2="138" y2="240" stroke="#111" stroke-width="2"/>',
        '<line x1="95" y1="300" x2="58" y2="365" stroke="#111" stroke-width="2"/>',
        '<line x1="95" y1="300" x2="132" y2="365" stroke="#111" stroke-width="2"/>',
        '<text x="65" y="395" font-family="Times New Roman" font-size="16" font-weight="700">Jogador</text>',
        '<line x1="138" y1="240" x2="215" y2="240" stroke="#555" stroke-width="1.2"/>',
        '<line x1="215" y1="95" x2="215" y2="635" stroke="#555" stroke-width="1.2"/>',
    ]
    for label, cx, cy in use_cases:
        svg.append(f'<line x1="215" y1="{cy}" x2="{cx - 150}" y2="{cy}" stroke="#555" stroke-width="1.1"/>')
        svg.append(f'<ellipse cx="{cx}" cy="{cy}" rx="150" ry="25" fill="#f0efe8" stroke="#333" stroke-width="1.2"/>')
        svg.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="Times New Roman" font-size="14">{esc(label)}</text>')
    dashed = [
        ((670, 215), (670, 275), 750, "<<include>>"),
        ((670, 335), (670, 635), 790, "<<extend>>"),
        ((670, 455), (670, 395), 750, "<<include>>"),
        ((670, 575), (670, 155), 820, "<<include>>"),
    ]
    for start, end, outside_x, label in dashed:
        mid_y = (start[1] + end[1]) // 2
        svg.append(
            f'<polyline points="{start[0]},{start[1]} {outside_x},{start[1]} {outside_x},{end[1]} {end[0]},{end[1]}" '
            'fill="none" stroke="#555" stroke-dasharray="5 4" stroke-width="1.2" marker-end="url(#arrow-open)"/>'
        )
        svg.append(f'<text x="{outside_x + 6}" y="{mid_y - 5}" font-family="Times New Roman" font-size="11" fill="#444">{esc(label)}</text>')
    svg.append("</svg>")
    output.write_text("\n".join(svg), encoding="utf-8")
    return output.name


def make_flow_svg(name: str, steps: list[str]) -> str:
    output = ASSET_DIR / f"{slug(name)}.svg"
    width = 920
    height = 120 + len(steps) * 76
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#444"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#fbfbf7"/>',
        f'<text x="40" y="44" font-family="Times New Roman" font-size="22" font-weight="700">{esc(name)}</text>',
    ]
    x, y = 90, 76
    for index, step in enumerate(steps):
        yy = y + index * 76
        svg.append(f'<rect x="{x}" y="{yy}" width="740" height="46" rx="4" fill="#f0efe8" stroke="#333"/>')
        svg.append(f'<text x="{x + 18}" y="{yy + 29}" font-family="Times New Roman" font-size="15">{index + 1}. {esc(step)}</text>')
        if index < len(steps) - 1:
            svg.append(f'<line x1="{x + 370}" y1="{yy + 46}" x2="{x + 370}" y2="{yy + 76}" stroke="#444" stroke-width="2" marker-end="url(#arrow)"/>')
    svg.append("</svg>")
    output.write_text("\n".join(svg), encoding="utf-8")
    return output.name


def code_excerpt(path: str, start: int, end: int) -> str:
    lines = read_text(ROOT / path).splitlines()
    selected = []
    for number in range(start, min(end, len(lines)) + 1):
        selected.append(f"{number:>4} | {lines[number - 1]}")
    return f'<pre class="code"><code>{esc(chr(10).join(selected))}</code></pre>'


def table(headers: list[str], rows: list[list[object]], class_name: str = "") -> str:
    thead = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" if isinstance(cell, str) and cell.startswith("<") else f"<td>{esc(cell)}</td>" for cell in row) + "</tr>")
    return f'<table class="{class_name}"><thead><tr>{thead}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def figure(filename: str, caption: str, klass: str = "") -> str:
    return f'<figure class="{klass}"><img src="assets/{esc(filename)}" alt="{esc(caption)}"><figcaption>{esc(caption)}</figcaption></figure>'


def section(number: str, title: str, body: str, new_page: bool = False) -> str:
    page = " page-break" if new_page else ""
    return f'<section class="section{page}" id="s-{slug(number + title)}"><h1>{esc(number)} {esc(title)}</h1>{body}</section>'


def subsection(number: str, title: str, body: str) -> str:
    return f'<h2>{esc(number)} {esc(title)}</h2>{body}'


def paragraph(text: str) -> str:
    return f"<p>{esc(text)}</p>"


def bullet(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def note_box(title: str, items: list[str]) -> str:
    return (
        '<div class="tech-note">'
        f'<p class="no-indent"><strong>{esc(title)}</strong></p>'
        + bullet(items)
        + "</div>"
    )


def default_toc_items() -> list[tuple[str, str]]:
    return [
        ("1", "Introdução"),
        ("2", "Metodologia de desenvolvimento"),
        ("3", "Escopo e requisitos"),
        ("4", "Arquitetura do sistema"),
        ("5", "Modelagem de dados e assets"),
        ("6", "Implementação dos sistemas principais"),
        ("7", "Casos de uso e fluxos"),
        ("8", "Interface, experiência e controles"),
        ("9", "Persistência, build web e implantação"),
        ("10", "Validação e qualidade"),
        ("11", "Conclusão"),
        ("12", "Referências"),
        ("A", "Apêndice A - Inventário técnico de funções"),
        ("B", "Apêndice B - Trechos de código comentados"),
    ]


def build_html(
    map_images: list[dict[str, str]],
    sprite_showcase: str,
    architecture_svg: str,
    use_case_svg: str,
    flow_svgs: dict[str, str],
    toc_pages: dict[str, int] | None = None,
) -> str:
    modules = parse_python_files()
    maps = map_metadata()
    stats = file_size_summary()
    inventory = inventory_defaults()
    recipes = crafting_recipes()
    weapons = weapon_data()

    module_rows = []
    descriptions = {
        "main.py": "Núcleo do jogo: inicialização, loop, estados de menu/jogo, renderização, entrada, combate, loot, bosses, UI, transições e áudio.",
        "player.py": "Entidade do jogador, animações compostas por loadout, movimentação, dano, cura, fome, stamina e estado de morte.",
        "zombie.py": "Entidade dos inimigos, variantes, animação, ataques corpo a corpo, arremesso de machado, efeitos e comportamento de perseguição.",
        "map_loader.py": "Leitura de mapas Tiled, tilesets TSX, layers, colisões, pontos de busca e gatilhos de porta/teleporte.",
        "inventory.py": "Estrutura simples de armazenamento de itens, munições e armas, com operações de adicionar/remover/consultar.",
        "crafting.py": "Sistema de receitas, validação de recursos, desbloqueio por posse de armas e produção de itens.",
        "weapons.py": "Tabela declarativa de armas, munições, dano, alcance, cooldown, dispersão e efeitos especiais.",
        "save_system.py": "Persistência em JSON no desktop e localStorage no navegador WebAssembly.",
    }
    for name, data in modules.items():
        module_rows.append(
            [
                name,
                data["lines"],
                len(data["classes"]),
                len(data["functions"]),
                len(data["constants"]),
                descriptions.get(name, "Módulo auxiliar do projeto."),
            ]
        )

    map_rows = [
        [
            item["name"],
            f'{item["width"]}x{item["height"]}',
            f'{item["tilewidth"]}x{item["tileheight"]}',
            item["tilesets"],
            ", ".join(item["layers"]),
        ]
        for item in maps
    ]

    recipe_rows = []
    for name, recipe in recipes.items():
        cost = ", ".join(f"{k}: {v}" for k, v in dict(recipe.get("cost", {})).items())
        unlock = recipe.get("unlock") or ", ".join(recipe.get("unlock_any", [])) if recipe.get("unlock_any") else recipe.get("unlock", "-")
        recipe_rows.append([name, cost, recipe.get("amount", 1), unlock or "-"])

    weapon_rows = []
    for name, weapon in weapons.items():
        weapon_rows.append(
            [
                name,
                weapon.get("family", "-"),
                weapon.get("damage", "-"),
                weapon.get("range", "-"),
                weapon.get("cooldown", "-"),
                weapon.get("ammo_item", "-"),
                weapon.get("pellets", "-"),
                weapon.get("effect", "-"),
            ]
        )

    inventory_rows = [[name, qty] for name, qty in inventory.items()]

    class_rows = []
    for module, data in modules.items():
        for cls in data["classes"]:
            methods = ", ".join(method["name"] for method in cls["methods"][:18])
            if len(cls["methods"]) > 18:
                methods += " ..."
            class_rows.append([module, cls["name"], cls["line"], len(cls["methods"]), methods])

    function_rows = []
    for module, data in modules.items():
        for fn in data["functions"]:
            function_rows.append([module, fn["name"], fn["line"]])

    game_method_rows = []
    for cls in modules["main.py"]["classes"]:
        if cls["name"] == "Game":
            for method in cls["methods"]:
                game_method_rows.append(["Game", method["name"], method["line"]])

    method_group_rows = [
        [
            "Configuração e áudio",
            "_load_settings, _save_settings, _apply_audio_settings, _load_sfx, _play_music",
            "Carrega preferências, aplica volumes, inicializa efeitos e alterna música de menu, jogo e boss.",
        ],
        [
            "Mundo e mapas",
            "_load_tiled_world, _switch_to_tiled_map, _enter_random_interior, _leave_interior, _use_map_exit",
            "Resolve mapas TMJ, preserva estado externo, troca áreas e sincroniza gatilhos de portas e teletransportes.",
        ],
        [
            "Entrada e menus",
            "process_input, process_menu_input, _apply_gamepad_input, _handle_main_menu_action",
            "Converte eventos de teclado, mouse e controle em ações de jogo ou navegação de interface.",
        ],
        [
            "Inimigos e bosses",
            "_spawn_zombie, _create_boss_zombie, _update_zombies, _update_boss_phase, _summon_boss_wave",
            "Gera inimigos, atualiza IA, controla bosses, ondas, minions e condições de derrota.",
        ],
        [
            "Interação e loot",
            "_handle_search, _corpse_loot_rewards, _grant_rewards, _add_item_popups",
            "Processa busca em nós/corpos, sorteia recompensas e apresenta feedback visual e sonoro.",
        ],
        [
            "Combate",
            "_handle_attack, _attack_melee, _fire_gun, _find_shot_hits, _damage_zombie, _apply_weapon_status",
            "Centraliza cooldowns, dano, munição, projéteis, impacto, fogo, gelo e morte de zumbis.",
        ],
        [
            "Interface",
            "_draw_ui, _draw_inventory_panel, _draw_crafting_panel, _draw_quick_access_bar, _draw_ammo_indicator",
            "Renderiza HUD, painéis, atalhos, munição, barras e mensagens do jogo.",
        ],
        [
            "Colisão e câmera",
            "_resolve_player_collisions, _resolve_zombie_obstacles, _separate_zombies, _update_camera",
            "Mantém jogador/inimigos dentro do mundo, evita obstáculos e posiciona a câmera.",
        ],
    ]

    use_case_rows = [
        ["UC01", "Iniciar novo jogo", "Jogador", "Selecionar Novo Jogo no menu", "Estado reiniciado, mapa inicial carregado, inventário padrão disponível."],
        ["UC02", "Carregar jogo salvo", "Jogador", "Existir save local ou localStorage", "Jogador, inventário, arma atual e atalhos restaurados."],
        ["UC03", "Explorar mapa", "Jogador", "Partida em andamento", "Câmera acompanha jogador, colisões bloqueiam obstáculos, recursos podem ser encontrados."],
        ["UC04", "Buscar loot", "Jogador", "Estar próximo de nó de busca/corpo", "Inventário recebe recompensas e pode ocorrer emboscada."],
        ["UC05", "Combater zumbis", "Jogador e inimigos", "Existirem inimigos vivos", "Dano aplicado, munição consumida, morte gera corpo pesquisável e recompensas."],
        ["UC06", "Craftar item", "Jogador", "Ter recursos e receita desbloqueada", "Recursos são removidos e item produzido no inventário."],
        ["UC07", "Trocar arma/atalho", "Jogador", "Possuir item ou arma", "Slot rápido seleciona item ou equipa arma compatível."],
        ["UC08", "Salvar partida", "Jogador", "Jogo em estado válido", "Arquivo JSON ou localStorage atualizado."],
        ["UC09", "Acessar interior/portal", "Jogador", "Estar dentro do raio do gatilho", "Mapa atual é trocado mantendo estado externo quando necessário."],
        ["UC10", "Derrotar boss", "Jogador e bosses", "Mapa de boss ativo", "Boss removido, recompensas concedidas e progressão liberada."],
    ]

    validation_rows = [
        ["Inicialização desktop", "Executar python main.py", "Tela de menu deve abrir e tocar música do menu.", "Manual"],
        ["Novo jogo", "Selecionar Novo Jogo", "Mapa inicial carregado com jogador no ponto seguro.", "Manual"],
        ["Movimento e colisão", "Mover com WASD contra paredes/carros", "Jogador não atravessa camadas sólidas.", "Manual"],
        ["Busca", "Aproximar de loot/carro/natureza e pressionar E", "Mensagem de recompensa e atualização do inventário.", "Manual"],
        ["Crafting", "Abrir B e craftar receita possível", "Recursos consumidos, item gerado e som de confirmação.", "Manual"],
        ["Combate melee", "Atacar zumbi próximo", "Zumbi recebe dano e morre ao zerar vida.", "Manual"],
        ["Combate arma de fogo", "Equipar pistola/escopeta e atirar", "Munição correta consumida, projéteis e impactos renderizados.", "Manual"],
        ["Status especiais", "Usar munição incendiária/perfurante", "Queimadura ou congelamento aplicado no inimigo.", "Manual"],
        ["Save/load", "Salvar F5 e carregar F9", "Estado principal restaurado.", "Manual"],
        ["Build web", "python -m pygbag --build .", "Pacote build/web criado para GitHub Pages.", "Pipeline"],
    ]

    toc_items = default_toc_items()
    toc_pages = toc_pages or {}

    css = dedent(
        """
        @page {
          size: A4;
          margin: 3cm 2cm 2cm 3cm;
        }
        * { box-sizing: border-box; }
        html { font-family: "Times New Roman", Times, serif; color: #111; }
        body { margin: 0; font-size: 12pt; line-height: 1.5; text-align: justify; orphans: 3; widows: 3; }
        .cover, .abstract-page, .toc-page { min-height: 24.7cm; page-break-after: always; }
        .cover { display: flex; flex-direction: column; align-items: center; text-align: center; }
        .institution { margin-top: 0.5cm; text-transform: uppercase; font-weight: 700; }
        .cover-title { margin-top: 8cm; font-size: 16pt; text-transform: uppercase; font-weight: 700; max-width: 15cm; }
        .cover-subtitle { margin-top: 1.2cm; font-size: 13pt; max-width: 15cm; }
        .cover-bottom { margin-top: auto; margin-bottom: 0.5cm; }
        .title-page-title { margin-top: 4cm; text-align: center; text-transform: uppercase; font-weight: 700; }
        .note { margin-left: 7cm; margin-top: 3cm; font-size: 11pt; text-align: justify; }
        h1 { font-size: 12pt; text-transform: uppercase; margin: 0 0 18pt; page-break-after: avoid; break-after: avoid; }
        h2 { font-size: 12pt; margin: 18pt 0 8pt; page-break-after: avoid; break-after: avoid; }
        h3 { font-size: 12pt; margin: 14pt 0 6pt; page-break-after: avoid; break-after: avoid; font-style: italic; }
        p { margin: 0 0 10pt; text-indent: 1.25cm; text-align: justify; }
        ul { margin: 0 0 12pt 1.25cm; }
        li { margin-bottom: 4pt; text-align: justify; }
        table { width: 100%; border-collapse: collapse; margin: 10pt 0 16pt; font-size: 9.2pt; line-height: 1.25; page-break-inside: auto; break-inside: auto; }
        tr { page-break-inside: avoid; break-inside: avoid; }
        th, td { border: 0.4pt solid #555; padding: 4.5pt; vertical-align: top; text-align: left; }
        th { background: #e9e8df; font-weight: 700; }
        figure { margin: 12pt 0 16pt; text-align: center; page-break-inside: avoid; break-inside: avoid; }
        figure img { max-width: 100%; max-height: 20cm; object-fit: contain; border: 0.4pt solid #777; }
        figure.diagram img { max-height: 17.5cm; border: 0.4pt solid #777; }
        figcaption { margin-top: 5pt; font-size: 10pt; text-align: center; }
        .section { page-break-before: always; break-before: page; }
        .page-break { page-break-before: always; }
        .code { white-space: pre-wrap; text-align: left; background: #f5f5f1; border: 0.4pt solid #777; padding: 7pt; font-family: "Courier New", monospace; font-size: 7pt; line-height: 1.15; page-break-inside: avoid; break-inside: avoid; overflow-wrap: anywhere; }
        .toc-list { margin-top: 1cm; }
        .toc-row { display: flex; justify-content: space-between; border-bottom: 0.3pt dotted #777; margin: 6pt 0; text-align: left; }
        .toc-row span:first-child { background: white; padding-right: 6pt; }
        .toc-row span:last-child { background: white; padding-left: 6pt; }
        .small { font-size: 10pt; }
        .no-indent { text-indent: 0; }
        .center { text-align: center; text-indent: 0; }
        .map-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt 12pt; page-break-inside: auto; break-inside: auto; }
        .map-grid figure { margin: 0 0 10pt; }
        .map-grid img { max-height: 6.8cm; }
        .appendix-table { font-size: 8pt; }
        .compact-table { font-size: 8pt; line-height: 1.18; }
        .caption-note { font-size: 9pt; text-align: center; text-indent: 0; }
        .tech-note { border-left: 2pt solid #777; background: #f7f7f2; padding: 7pt 9pt 3pt; margin: 8pt 0 12pt; page-break-inside: avoid; break-inside: avoid; }
        .tech-note p { margin-bottom: 4pt; }
        .tech-note ul { margin-bottom: 4pt; }
        """
    )

    cover = f"""
    <div class="cover">
      <div class="institution">CENTRO UNIVERSITÁRIO DO DISTRITO FEDERAL - UDF<br>{esc(COURSE_CONTEXT)}</div>
      <div class="cover-title">{esc(PROJECT_TITLE)}: DOCUMENTAÇÃO TÉCNICA DO DESENVOLVIMENTO DE UM JOGO 2D DE SOBREVIVÊNCIA EM PYTHON</div>
      <div class="cover-subtitle">{esc(AUTHOR)}<br>RGM {esc(RGM)}</div>
      <div class="cover-bottom">{esc(CITY)}<br>{esc(YEAR)}</div>
    </div>
    <div class="cover">
      <div class="institution">{esc(AUTHOR)}<br>RGM {esc(RGM)}</div>
      <div class="title-page-title">{esc(PROJECT_TITLE)}: DOCUMENTAÇÃO TÉCNICA DO DESENVOLVIMENTO DE UM JOGO 2D DE SOBREVIVÊNCIA EM PYTHON</div>
      <p class="note">Documentação técnica apresentada à disciplina {esc(COURSE_CONTEXT)}, ministrada por {esc(ADVISOR)}, como registro profissional do processo de desenvolvimento, arquitetura, implementação, fluxos de uso, validação e implantação do projeto Dead Streets.</p>
      <div class="cover-bottom">{esc(CITY)}<br>{esc(YEAR)}</div>
    </div>
    """

    pre_text = f"""
    <div class="abstract-page">
      <h1>RESUMO</h1>
      <p>Este documento apresenta a documentação técnica completa do jogo {esc(PROJECT_TITLE)}, um jogo 2D de sobrevivência desenvolvido em Python com Pygame, mapas criados no Tiled, sprites em pixel art, áudio em OGG, suporte a desktop e empacotamento web por Pygbag/WebAssembly. O projeto implementa exploração em mapas, movimentação com teclado, mouse e controle, inventário, atalhos rápidos, crafting, armas corpo a corpo e de fogo, munições especiais, inimigos com variantes, arenas de boss, transições de áreas, save local e persistência no navegador. A documentação descreve os objetivos, metodologia, requisitos, arquitetura, módulos, estruturas de dados, fluxos de jogo, casos de uso, validação e implantação. Também são incluídas figuras geradas a partir dos próprios mapas e assets do repositório, além de trechos de código numerados e tabelas técnicas.</p>
      <p class="no-indent"><strong>Palavras-chave:</strong> Python. Pygame. Jogo 2D. Sobrevivência. Tiled. WebAssembly. Documentação técnica.</p>
    </div>
    <div class="toc-page">
      <h1>SUMÁRIO</h1>
      <div class="toc-list">
        {''.join(f'<div class="toc-row"><span>{esc(num)} {esc(title)}</span><span>{esc(toc_pages.get(num, "00"))}</span></div>' for num, title in toc_items)}
      </div>
    </div>
    """

    intro = section(
        "1",
        "Introdução",
        "".join(
            [
                paragraph(
                    "O projeto Dead Streets é um jogo 2D de sobrevivência em visão superior, construído em Python com a biblioteca Pygame. A proposta combina exploração de cenários pós-apocalípticos, combate contra zumbis, gerenciamento de recursos, criação de itens, coleta de loot e progressão por mapas normais, interiores e arenas de boss. O jogo foi estruturado para execução local em desktop e para publicação em navegador por meio de Pygbag/WebAssembly."
                ),
                paragraph(
                    "A documentação técnica tem como finalidade registrar o desenvolvimento de forma profissional, detalhando decisões de arquitetura, organização do código, regras de negócio, estruturas de dados, assets, fluxos de uso, requisitos, validação e implantação. O documento também preserva uma visão acadêmica do projeto, com introdução, metodologia e conclusão, e uma visão operacional, com tabelas, diagramas, trechos de código e especificações dos módulos."
                ),
                paragraph(
                    f"O repositório analisado contém {stats['python_files']} arquivos Python principais, {stats['python_lines']} linhas de código Python, {stats['maps']} mapas TMJ, {stats['tilesets']} tilesets externos, {stats['sprites']} sprites PNG e {stats['audio']} arquivos de áudio OGG. Esses números evidenciam que o projeto extrapola um protótipo mínimo e já possui subsistemas integrados de jogo, apresentação, entrada, persistência e publicação."
                ),
                subsection(
                    "1.1",
                    "Problema",
                    paragraph(
                        "Jogos 2D com múltiplos sistemas exigem coordenação entre renderização, entrada, física simplificada, IA, colisão, dados de mapa, áudio, inventário e persistência. Sem documentação, a manutenção se torna difícil porque regras importantes ficam implícitas no código. O problema tratado por este documento é transformar o conhecimento disperso no repositório em uma referência técnica organizada, capaz de orientar manutenção, avaliação acadêmica e futuras evoluções."
                    ),
                ),
                subsection(
                    "1.2",
                    "Objetivo geral",
                    paragraph(
                        "Descrever detalhadamente o processo de desenvolvimento e a arquitetura do Dead Streets, apresentando seus módulos, fluxos, requisitos, casos de uso, assets, regras internas e procedimentos de execução e publicação."
                    ),
                ),
                subsection(
                    "1.3",
                    "Objetivos específicos",
                    bullet(
                        [
                            "Identificar os módulos e responsabilidades técnicas do projeto.",
                            "Documentar a integração entre Pygame, mapas Tiled, sprites, áudio e persistência.",
                            "Registrar requisitos funcionais e não funcionais do jogo.",
                            "Apresentar casos de uso, fluxos de execução e diagramas de apoio.",
                            "Listar inventário, receitas, armas, mapas e funções relevantes.",
                            "Descrever validação, build web, limitações e oportunidades de evolução.",
                        ]
                    ),
                ),
                subsection(
                    "1.4",
                    "Escopo do documento",
                    paragraph(
                        "O documento cobre o código existente no repositório local, incluindo os arquivos Python, mapas, tilesets, sprites, áudio, configurações de build e README. Não são tratados aspectos jurídicos de licenciamento de assets além da menção de que os recursos visuais e sonoros compõem o pacote do projeto. A análise técnica se concentra no funcionamento implementado e nos contratos observáveis entre módulos."
                    ),
                ),
            ]
        ),
        new_page=True,
    )

    methodology = section(
        "2",
        "Metodologia de desenvolvimento",
        "".join(
            [
                paragraph(
                    "O desenvolvimento seguiu uma abordagem incremental e orientada a protótipos jogáveis. Em vez de separar longamente análise e implementação, os sistemas foram incorporados ao loop principal de jogo e refinados conforme novas necessidades surgiram: primeiro a movimentação e renderização, depois colisão e mapas, em seguida inventário, crafting, combate, inimigos, bosses, áudio, save e empacotamento web."
                ),
                paragraph(
                    "A escolha de Pygame permitiu controlar diretamente surfaces, sprites, eventos, joystick, mixer de áudio e temporização. O Tiled foi usado como ferramenta de autoria de mapas, separando o conteúdo espacial do código. O Pygbag foi adotado como solução de empacotamento web, permitindo que o jogo Python fosse executado no navegador via WebAssembly."
                ),
                subsection(
                    "2.1",
                    "Etapas executadas",
                    table(
                        ["Etapa", "Descrição", "Evidência no projeto"],
                        [
                            ["Concepção", "Definição de um jogo de sobrevivência zumbi com exploração e combate.", "README, título Dead Streets e assets pós-apocalípticos."],
                            ["Base técnica", "Inicialização do Pygame, janela, loop, FPS e estados de menu/jogo.", "main.py, classe Game e função main."],
                            ["Mundo e mapas", "Criação de mapas TMJ no Tiled e carregamento por camadas.", "maps/*.tmj, map_loader.py."],
                            ["Jogador", "Implementação de movimento, stamina, vida, fome, mira e animações.", "player.py."],
                            ["Sistemas", "Inventário, crafting, armas, loot e atalhos rápidos.", "inventory.py, crafting.py, weapons.py, main.py."],
                            ["IA e combate", "Zumbis com tipos, colisões, ataques, bosses e projéteis.", "zombie.py e métodos de combate em main.py."],
                            ["Polimento", "Áudio OGG, UI, mensagens, popups e suporte a controle.", "audio/, sprites/ui, métodos de menu/UI."],
                            ["Persistência e web", "Save em JSON/localStorage e build Pygbag.", "save_system.py, pygbag.ini e tools/patch_web_build.py."],
                        ],
                    ),
                ),
                subsection(
                    "2.2",
                    "Critérios de organização",
                    paragraph(
                        "A organização foi baseada em separação por responsabilidade. Dados estáticos de armas ficam em weapons.py; receitas em crafting.py; inventário em inventory.py; persistência em save_system.py; mapas em map_loader.py; jogador em player.py; inimigos em zombie.py. O arquivo main.py concentra o loop e a orquestração porque muitos comportamentos dependem simultaneamente de entrada, estado, renderização e interação entre entidades."
                    ),
                ),
                subsection(
                    "2.3",
                    "Padrões de implementação adotados",
                    bullet(
                        [
                            "Uso de constantes para configurar dimensões, alcance de interação, áudio, controle e dificuldade.",
                            "Uso de dicionários declarativos para receitas, armas, labels e ícones.",
                            "Uso de classes para entidades persistentes do domínio do jogo.",
                            "Uso de cache de sprites e tiles para reduzir carregamentos repetidos.",
                            "Uso de layers do Tiled para derivar colisões, loot, portas e teletransportes.",
                            "Uso de validação manual e execução local para confirmar comportamento de gameplay.",
                        ]
                    ),
                ),
            ]
        ),
    )

    requirements = section(
        "3",
        "Escopo e requisitos",
        "".join(
            [
                paragraph(
                    "O escopo funcional do jogo inclui uma experiência jogável completa: o usuário inicia ou carrega uma partida, explora mapas, coleta recursos, enfrenta inimigos, gerencia itens, cria equipamentos, atravessa áreas e salva progresso. O escopo técnico inclui execução desktop e web, carregamento de assets, suporte a controle e persistência compatível com ambiente local e navegador."
                ),
                subsection(
                    "3.1",
                    "Requisitos funcionais",
                    table(
                        ["Código", "Requisito", "Descrição"],
                        [
                            ["RF01", "Menu inicial", "Permitir iniciar novo jogo, carregar saves, ajustar configurações e acessar tutorial."],
                            ["RF02", "Movimentação", "Permitir mover o jogador por teclado e controle, com corrida condicionada à stamina."],
                            ["RF03", "Mira e ataque", "Permitir mirar com mouse ou analógico e atacar com melee ou arma equipada."],
                            ["RF04", "Inventário", "Armazenar recursos, consumíveis, munições e armas coletadas."],
                            ["RF05", "Atalhos rápidos", "Permitir selecionar slots de 1 a 6 para armas e itens úteis."],
                            ["RF06", "Crafting", "Permitir criar itens a partir de receitas e recursos disponíveis."],
                            ["RF07", "Loot", "Permitir buscar recursos em carros, natureza, despensas e corpos."],
                            ["RF08", "Inimigos", "Gerar zumbis com variantes, vida, ataques, animações e morte."],
                            ["RF09", "Mapas", "Carregar mapas externos do Tiled com colisões, portas e teletransportes."],
                            ["RF10", "Bosses", "Executar arenas de boss e conceder recompensas após derrota."],
                            ["RF11", "Áudio", "Reproduzir música e efeitos sonoros configuráveis."],
                            ["RF12", "Persistência", "Salvar e carregar partida em arquivo JSON ou localStorage."],
                        ],
                    ),
                ),
                subsection(
                    "3.2",
                    "Requisitos não funcionais",
                    table(
                        ["Código", "Requisito", "Descrição"],
                        [
                            ["RNF01", "Portabilidade", "Rodar em desktop Python e em navegador via Pygbag."],
                            ["RNF02", "Desempenho", "Evitar desenhar entidades fora da câmera e usar buckets para tiles/colisões."],
                            ["RNF03", "Manutenibilidade", "Separar dados de armas, receitas, inventário e mapas em módulos dedicados."],
                            ["RNF04", "Compatibilidade de áudio", "Utilizar OGG para simplificar desktop e web."],
                            ["RNF05", "Usabilidade", "Fornecer controles por teclado/mouse e controle, além de tutorial e mensagens."],
                            ["RNF06", "Persistência resiliente", "Adaptar save para filesystem no desktop e storage do navegador na web."],
                            ["RNF07", "Escalabilidade de conteúdo", "Permitir novos mapas TMJ e assets sem reescrever o carregador principal."],
                        ],
                    ),
                ),
                subsection(
                    "3.3",
                    "Regras de negócio de gameplay",
                    bullet(
                        [
                            "O jogador possui vida, fome e stamina; a stamina limita corrida e se recupera com o tempo.",
                            "Consumíveis como comida e kit médico recuperam necessidades específicas.",
                            "Armas de fogo dependem de munição correspondente, salvo código de munição infinita existente no projeto.",
                            "Receitas podem ser bloqueadas até que armas relacionadas estejam no inventário.",
                            "Zumbis mortos podem permanecer como corpos pesquisáveis antes de desaparecerem.",
                            "Bosses têm comportamento especial e conclusão própria de fase.",
                            "Gatilhos de mapa são derivados de camadas do Tiled, reduzindo acoplamento entre mapa e código.",
                        ]
                    ),
                ),
            ]
        ),
    )

    architecture = section(
        "4",
        "Arquitetura do sistema",
        "".join(
            [
                paragraph(
                    "A arquitetura é centralizada por uma classe Game, responsável por orquestrar estados, entrada, atualização, renderização e integração entre os demais módulos. Essa escolha é comum em jogos Pygame de porte acadêmico porque o loop principal precisa coordenar muitos dados a cada frame. Os módulos auxiliares encapsulam dados e comportamentos de domínio para reduzir a complexidade direta do arquivo principal."
                ),
                figure(architecture_svg, "Diagrama geral de arquitetura e dependências lógicas do projeto.", "diagram"),
                subsection(
                    "4.1",
                    "Visão por módulos",
                    table(["Módulo", "Linhas", "Classes", "Funções livres", "Constantes", "Responsabilidade"], module_rows, "appendix-table"),
                ),
                subsection(
                    "4.2",
                    "Classes principais",
                    table(["Módulo", "Classe", "Linha", "Métodos", "Resumo dos métodos"], class_rows, "appendix-table"),
                ),
                subsection(
                    "4.3",
                    "Agrupamento técnico dos métodos da classe Game",
                    paragraph(
                        "Como a classe Game é a coordenadora do projeto, seus métodos foram agrupados por responsabilidade para facilitar leitura e manutenção. Essa tabela complementa o inventário completo do apêndice e mostra a intenção arquitetural por trás da concentração do loop principal."
                    )
                    + table(["Grupo", "Métodos representativos", "Responsabilidade"], method_group_rows, "appendix-table"),
                ),
                subsection(
                    "4.4",
                    "Loop principal",
                    paragraph(
                        "O loop principal fica no método run da classe Game e mantém a cadência de atualização. Em cada iteração, o jogo processa entrada, atualiza estado, renderiza o frame e apresenta o resultado. A constante TARGET_FPS diferencia desktop e web, usando 60 FPS localmente e 45 FPS na web para reduzir custo de renderização no canvas WebAssembly."
                    )
                    + code_excerpt("main.py", 4767, 4789)
                    + note_box(
                        "Leitura técnica do loop",
                        [
                            "process_input isola a interpretação de eventos antes da atualização de mundo.",
                            "update_game_state aplica regras dependentes do tempo, como inimigos, fome, stamina, projéteis e interações.",
                            "render desenha o frame final em uma surface interna antes da apresentação pela janela ou canvas web.",
                            "clock.tick(TARGET_FPS) limita a taxa de quadros e fornece delta time para movimento proporcional ao tempo real.",
                        ],
                    ),
                ),
                subsection(
                    "4.5",
                    "Estados de aplicação",
                    paragraph(
                        "O estado de aplicação alterna entre menu, jogo, painéis e condições especiais como tutorial, inventário, crafting e morte. A separação de métodos de entrada e renderização por contexto reduz conflitos: menus usam process_menu_input e render_menu; jogo usa process_input, update_game_state e render; painéis bloqueiam parcialmente gameplay por meio de checagens específicas."
                    ),
                ),
            ]
        ),
    )

    data_assets = section(
        "5",
        "Modelagem de dados e assets",
        "".join(
            [
                paragraph(
                    "O projeto utiliza dados em diferentes níveis: dados declarativos em Python para armas e receitas, dados espaciais em mapas TMJ/TSX, dados visuais em PNG, áudio em OGG e dados persistidos em JSON/localStorage. Essa combinação permite que regras e conteúdo sejam alterados sem que toda a lógica precise ser reescrita."
                ),
                subsection(
                    "5.1",
                    "Mapas e camadas",
                    table(["Mapa", "Dimensão em tiles", "Tile", "Tilesets", "Camadas"], map_rows, "appendix-table")
                    + paragraph(
                        "As camadas dos mapas possuem papel semântico. Nomes contendo collision, solid, objects, building, wall ou car geram retângulos de colisão. Camadas Nature, Loot e Cars geram pontos de busca. Camadas Portas/Door geram transições de porta, enquanto Teleport gera saídas entre mapas ou arenas."
                    ),
                ),
                subsection(
                    "5.2",
                    "Visualização dos mapas",
                    paragraph(
                        "As figuras a seguir apresentam apenas a renderização visual dos mapas principais do jogo. A visualização técnica com sobreposição de colisões foi removida desta versão para evitar repetição visual e dar espaço a todos os cenários principais: bosses, interior e mapas externos."
                    )
                    + '<div class="map-grid">'
                    + "".join(figure(item["map"], f"Renderização do mapa {item['name']}.") for item in map_images)
                    + "</div>",
                ),
                subsection(
                    "5.3",
                    "Sprites e UI",
                    paragraph(
                        "Os sprites são organizados por categoria: personagem, armas, zumbis, objetos, UI e pacote visual pós-apocalíptico. O carregamento de spritesheets extrai frames por contagem declarada no nome do arquivo, o que simplifica adicionar novas animações desde que o padrão de nome seja preservado."
                    )
                    + figure(sprite_showcase, "Amostra de sprites e elementos de interface carregados do repositório."),
                ),
                subsection(
                    "5.4",
                    "Inventário base",
                    table(["Item", "Quantidade inicial"], inventory_rows, "appendix-table"),
                ),
                subsection(
                    "5.5",
                    "Receitas de crafting",
                    table(["Item produzido", "Custo", "Quantidade", "Desbloqueio"], recipe_rows, "appendix-table"),
                ),
                subsection(
                    "5.6",
                    "Tabela de armas",
                    table(["Arma", "Família", "Dano", "Alcance", "Cooldown", "Munição", "Projéteis", "Efeito"], weapon_rows, "appendix-table"),
                ),
            ]
        ),
    )

    implementation = section(
        "6",
        "Implementação dos sistemas principais",
        "".join(
            [
                subsection(
                    "6.1",
                    "Carregamento de mapas",
                    paragraph(
                        "O carregador TiledMap lê arquivos JSON TMJ, resolve tilesets externos TSX, carrega imagens, aplica flips horizontais e verticais do Tiled e gera surfaces escaladas. Para desempenho, tiles são armazenados em cache por GID e buckets de desenho agrupam elementos por região, evitando percorrer o mapa inteiro a cada frame."
                    )
                    + code_excerpt("map_loader.py", 80, 113)
                    + note_box(
                        "Documentação do trecho",
                        [
                            "O construtor transforma metadados do Tiled em medidas de mundo usadas pela câmera e colisão.",
                            "self.tilesets mantém os tilesets resolvidos por firstgid, preservando compatibilidade com mapas exportados pelo Tiled.",
                            "self.collision_rects, self.search_nodes, self.door_triggers e self.exit_triggers são produtos técnicos das layers.",
                            "A chamada _build_draw_buckets prepara o mapa para renderização parcial por região visível.",
                        ],
                    )
                    + paragraph(
                        "A criação de pontos de busca e gatilhos usa clusters de tiles ocupados. Em vez de criar um ponto por tile, o carregador agrupa tiles adjacentes, calcula o centro médio e registra um spawn técnico. Isso reduz ruído de interação e torna as camadas do Tiled mais intuitivas."
                    )
                    + code_excerpt("map_loader.py", 306, 341)
                    + note_box(
                        "Contrato de camadas",
                        [
                            "Nature vira ponto de busca de natureza.",
                            "Loot vira despensa e Cars vira carro, ambos como SearchNodeSpawn.",
                            "Portas/Door vira gatilho de porta e Teleport vira gatilho de saída.",
                            "Clusters adjacentes evitam múltiplos prompts de interação sobre o mesmo objeto visual.",
                        ],
                    ),
                ),
                subsection(
                    "6.2",
                    "Jogador",
                    paragraph(
                        "A classe Player concentra atributos vitais e cinemáticos: vida, fome, stamina, posição, arma atual, velocidade base, velocidade de corrida, cooldowns e estado de animação. O movimento usa vetores Pygame, normalização de direção e atualização por delta time, permitindo comportamento independente da taxa de quadros."
                    )
                    + code_excerpt("player.py", 78, 112)
                    + note_box(
                        "Responsabilidades do Player",
                        [
                            "Armazena estado vital do personagem e mantém posição em pygame.Vector2.",
                            "Controla velocidade base, corrida, consumo e recuperação de stamina.",
                            "Gerencia timers de dano, cura, ataque, coleta e animação de morte.",
                            "Expõe métodos de movimentação, dano, cura, mira e desenho usados pelo Game.",
                        ],
                    )
                    + paragraph(
                        "O sistema de sprites do jogador combina corpo e camadas de armas. Isso permite que o mesmo corpo seja reaproveitado com mãos, taco, pistola e escopeta, reduzindo duplicação visual. Variações especiais de armas recebem tintura aplicada sobre as camadas correspondentes."
                    ),
                ),
                subsection(
                    "6.3",
                    "Inimigos e IA",
                    paragraph(
                        "A classe Zombie é uma dataclass com atributos de posição, velocidade, vida, raio, tipo, dano, alcance, timers e flags de ataque. O projeto implementa variantes axe, small e big, cada uma com sprites e comportamento próprio. O zumbi pequeno possui investida e recuo; o zumbi com machado pode arremessar projétil dentro de uma faixa de distância; bosses usam estatísticas e regras próprias criadas pela classe Game."
                    )
                    + code_excerpt("zombie.py", 58, 102)
                    + note_box(
                        "Responsabilidades do Zombie",
                        [
                            "Representa inimigos comuns e variantes usadas como base para bosses.",
                            "Controla estados de animação como idle, walk, attack, retreat e dead.",
                            "Usa timers internos para impedir dano contínuo sem janela de ataque.",
                            "Armazena efeitos temporários como burn_timer e freeze_timer para munições especiais.",
                        ],
                    )
                    + paragraph(
                        "A IA evita atravessar obstáculos por resolução de colisões e também aplica separação entre zumbis para reduzir sobreposição visual. A atualização dos inimigos conversa com o estado do mapa, a posição do jogador, efeitos de fogo e gelo, morte, loot de corpo e eventos sonoros."
                    ),
                ),
                subsection(
                    "6.4",
                    "Combate",
                    paragraph(
                        "O combate é dividido em melee e armas de fogo. Armas melee usam alcance circular/retangular próximo ao jogador. Armas de fogo usam dados declarativos da tabela WEAPONS, consomem munição específica, calculam dispersão e podem gerar múltiplos projéteis no caso da escopeta. Munições incendiárias aplicam dano em área e queimadura; munições perfurantes/congelantes aplicam efeito de gelo."
                    )
                    + code_excerpt("weapons.py", 6, 55)
                    + note_box(
                        "Como a tabela WEAPONS é usada",
                        [
                            "family define se a arma usa lógica melee, pistola ou escopeta.",
                            "damage, range e cooldown controlam dano, alcance e ritmo de ataque.",
                            "ammo_item define qual item do inventário será consumido no disparo.",
                            "pellets e spread permitem que a escopeta use múltiplas trajetórias no mesmo ataque.",
                            "effect ativa regras adicionais como fogo em área ou congelamento.",
                        ],
                    )
                    + paragraph(
                        "A função _handle_attack decide quando um ataque pode ocorrer, respeitando cooldown e arma equipada. A partir dela, o fluxo chama _attack_melee ou _fire_gun, que aplicam dano, geram efeitos visuais e atualizam munição. Esse desenho centraliza a regra de entrada e distribui a aplicação conforme a família da arma."
                    ),
                ),
                subsection(
                    "6.5",
                    "Inventário e crafting",
                    paragraph(
                        "O inventário é intencionalmente simples: um dicionário de item para quantidade. Essa escolha funciona bem para um jogo de recursos empilháveis e facilita serialização. O crafting valida receita existente, bloqueio, recursos necessários, remoção dos custos e adição do item produzido."
                    )
                    + code_excerpt("inventory.py", 6, 43)
                    + note_box(
                        "Contrato do Inventory",
                        [
                            "add_item ignora quantidades negativas ou zero, evitando alteração inválida.",
                            "remove_item só altera o dicionário se houver saldo suficiente.",
                            "has_items é a função de validação usada pelo crafting antes de consumir recursos.",
                            "to_dict entrega uma cópia simples para save em JSON.",
                        ],
                    )
                    + code_excerpt("crafting.py", 8, 57)
                    + note_box(
                        "Contrato do CraftingSystem",
                        [
                            "is_recipe_unlocked bloqueia receitas avançadas até que o inventário possua o item necessário.",
                            "craft retorna uma tupla com sucesso e mensagem, facilitando feedback direto na UI.",
                            "Os custos são removidos antes da adição do produto, mantendo consistência de recursos.",
                            "get_recipe_names filtra dinamicamente o painel para mostrar apenas receitas disponíveis ao estado atual.",
                        ],
                    ),
                ),
                subsection(
                    "6.6",
                    "Save e configurações",
                    paragraph(
                        "A persistência salva vida, fome, posição, inventário, tempo de jogo, arma atual e slots rápidos. No desktop, os dados são escritos em savegame.json; no navegador, a função detecta sys.platform igual a emscripten e grava no localStorage. A mesma API pública atende os dois ambientes."
                    )
                    + code_excerpt("save_system.py", 24, 63)
                    + note_box(
                        "Contrato do save",
                        [
                            "save_game recebe objetos Player e Inventory e converte apenas dados serializáveis.",
                            "load_game normaliza player_position para tupla ao restaurar JSON.",
                            "save_exists consulta localStorage na web e arquivo físico no desktop.",
                            "A chave WEB_SAVE_KEY evita conflito com outros dados do navegador.",
                        ],
                    ),
                ),
                subsection(
                    "6.7",
                    "Áudio",
                    paragraph(
                        "O áudio é dividido entre música de menu, música de jogo, música de boss e efeitos sonoros. Os arquivos OGG são carregados a partir de audio/ e audio/sfx/. O volume de música e SFX é configurável, persistido em settings.json ou localStorage na web, e aplicado ao mixer do Pygame."
                    ),
                ),
                subsection(
                    "6.8",
                    "Suporte a controle",
                    paragraph(
                        "O jogo usa pygame.joystick e, quando disponível, pygame._sdl2.controller. Existem mapas de botões e eixos para controles SDL e controles crus, varredura periódica de gamepads, deadzone de eixos, analógico esquerdo para movimento, analógico direito para mira e botões dedicados para interagir, atacar, abrir inventário e alternar slots."
                    ),
                ),
            ]
        ),
    )

    flows = section(
        "7",
        "Casos de uso e fluxos",
        "".join(
            [
                paragraph(
                    "Os casos de uso descrevem interações observáveis entre jogador e sistema. Em jogos, um caso de uso frequentemente atravessa vários módulos: iniciar partida envolve menu, reset de estado, mapa e áudio; combater envolve entrada, jogador, arma, inimigo, colisão, áudio, UI e loot."
                ),
                figure(use_case_svg, "Diagrama UML de casos de uso do Dead Streets.", "diagram"),
                table(["Código", "Caso de uso", "Atores", "Pré-condição", "Pós-condição"], use_case_rows, "appendix-table"),
                figure(flow_svgs["novo_jogo"], "Fluxo principal de início de partida."),
                figure(flow_svgs["exploracao"], "Fluxo de exploração, busca e recompensa."),
                figure(flow_svgs["combate"], "Fluxo de ataque e resolução de dano."),
                figure(flow_svgs["crafting"], "Fluxo de criação de itens por receita."),
                figure(flow_svgs["save"], "Fluxo de salvamento e carregamento."),
                subsection(
                    "7.1",
                    "Fluxo de boss",
                    paragraph(
                        "A progressão para bosses é controlada por sequência e contagem de mapas. Após determinado número de mapas normais, o jogo seleciona arena de boss. A derrota do boss concede recompensas, remove minions quando necessário e libera continuidade da partida. O terceiro boss utiliza comportamento de invocador, criando ondas que aumentam a pressão no jogador."
                    ),
                ),
            ]
        ),
    )

    ui = section(
        "8",
        "Interface, experiência e controles",
        "".join(
            [
                paragraph(
                    "A interface combina elementos desenhados por código com sprites de UI. O menu principal apresenta ações, o HUD mostra vida, fome, stamina, munição, atalhos e mensagens, e os painéis de inventário/crafting organizam itens em células. A câmera segue o jogador no mundo, mantendo o foco na exploração e nos inimigos próximos."
                ),
                subsection(
                    "8.1",
                    "Controles de teclado e mouse",
                    table(
                        ["Ação", "Entrada"],
                        [
                            ["Mover", "WASD"],
                            ["Correr", "Shift"],
                            ["Mirar", "Mouse"],
                            ["Atacar", "Clique esquerdo ou Espaço"],
                            ["Interagir/buscar/porta", "E"],
                            ["Usar consumível", "Q"],
                            ["Crafting", "B"],
                            ["Craftar selecionado", "C"],
                            ["Alternar receita", "Tab"],
                            ["Inventário", "I"],
                            ["Atalhos", "1 a 6"],
                            ["Salvar/carregar", "F5/F9"],
                            ["Voltar/sair", "Esc"],
                        ],
                    ),
                ),
                subsection(
                    "8.2",
                    "Controles de gamepad",
                    table(
                        ["Ação", "Entrada"],
                        [
                            ["Movimento", "Analógico esquerdo"],
                            ["Mira", "Analógico direito"],
                            ["Correr", "L3"],
                            ["Atacar", "R2"],
                            ["Interagir", "X"],
                            ["Crafting", "Quadrado"],
                            ["Usar item", "Triângulo"],
                            ["Inventário", "R3"],
                            ["Alternar atalhos", "L1/R1 ou direcional"],
                            ["Menu/voltar", "Options/Share"],
                        ],
                    ),
                ),
                subsection(
                    "8.3",
                    "Feedback ao jogador",
                    paragraph(
                        "O feedback combina som, popups flutuantes, mensagens textuais, efeitos de impacto, overlays de dano, barras de vida de boss e indicadores de munição. Esses elementos reduzem ambiguidade: o jogador sabe quando recebeu dano, quando coletou itens, quando uma receita falhou ou quando uma arma está sem munição."
                    ),
                ),
            ]
        ),
    )

    deployment = section(
        "9",
        "Persistência, build web e implantação",
        "".join(
            [
                paragraph(
                    "O projeto pode ser executado localmente com Python e Pygame ou empacotado para web. A execução desktop usa pygame>=2.5, enquanto o build web usa pygame-ce e pygbag. A configuração pygbag.ini ignora diretórios e arquivos que não devem entrar no pacote final, como build, .git, __pycache__, savegame.json e settings.json."
                ),
                subsection(
                    "9.1",
                    "Execução desktop",
                    code_excerpt("README.md", 63, 74),
                ),
                subsection(
                    "9.2",
                    "Build web",
                    code_excerpt("README.md", 76, 84)
                    + paragraph(
                        "Após a geração do build, o script tools/patch_web_build.py ajusta a página gerada pelo Pygbag. O workflow de GitHub Pages descrito no README executa build, aplica o patch e publica os artefatos para acesso online."
                    ),
                ),
                subsection(
                    "9.3",
                    "Persistência multiplataforma",
                    paragraph(
                        "A persistência foi pensada com abstração mínima. A mesma chamada save_game grava no meio adequado ao ambiente. Essa solução evita duplicar lógica de jogo e limita diferenças de plataforma a uma função de acesso ao storage."
                    ),
                ),
                subsection(
                    "9.4",
                    "Configurações locais",
                    paragraph(
                        "settings.json armazena preferências como volume. Esse arquivo é tratado como gerado localmente e não precisa ser versionado. Na web, o projeto usa uma chave própria em localStorage para manter configurações entre sessões do navegador."
                    ),
                ),
            ]
        ),
    )

    validation = section(
        "10",
        "Validação e qualidade",
        "".join(
            [
                paragraph(
                    "A validação do projeto é predominantemente funcional e manual, adequada ao estágio acadêmico e à natureza interativa do jogo. Como jogos dependem de percepção visual, áudio e resposta de entrada, a validação manual continua importante mesmo quando testes automatizados são adicionados futuramente."
                ),
                table(["Área", "Procedimento", "Resultado esperado", "Tipo"], validation_rows, "appendix-table"),
                subsection(
                    "10.1",
                    "Riscos técnicos",
                    table(
                        ["Risco", "Impacto", "Mitigação existente", "Evolução sugerida"],
                        [
                            ["main.py muito concentrado", "Dificulta manutenção de longo prazo.", "Módulos auxiliares já separam dados e entidades.", "Extrair serviços de UI, combate e transições."],
                            ["Validação manual", "Regressões podem passar despercebidas.", "Fluxos principais documentados.", "Criar testes unitários para inventário, crafting, save e map_loader."],
                            ["Dependência de padrões de nome de sprites", "Assets fora do padrão não carregam.", "Regex e exceções explícitas ajudam diagnóstico.", "Documentar convenção para artistas/conteúdo."],
                            ["Diferenças desktop/web", "Áudio, controle e performance podem variar.", "Uso de OGG, FPS menor na web e localStorage.", "Criar checklist por navegador."],
                            ["Colisões por camada", "Nomes de layers incorretos quebram colisão.", "Palavras-chave amplas e fallback de assets.", "Criar validação automática de mapas TMJ."],
                        ],
                    ),
                ),
                subsection(
                    "10.2",
                    "Boas práticas observadas",
                    bullet(
                        [
                            "Uso de type hints em grande parte dos módulos.",
                            "Separação de dados declarativos em dicionários reutilizáveis.",
                            "Cache de sprites e tiles para evitar recomputação.",
                            "Compatibilidade com ambiente web considerada no save, áudio e FPS.",
                            "Uso de ferramentas externas apropriadas para mapas e empacotamento.",
                        ]
                    ),
                ),
            ]
        ),
    )

    conclusion = section(
        "11",
        "Conclusão",
        "".join(
            [
                paragraph(
                    "O Dead Streets demonstra a construção de um jogo 2D de sobrevivência com escopo significativo para um projeto acadêmico em Python. A implementação integra renderização, mapas externos, inventário, crafting, armas, inimigos, bosses, áudio, persistência e publicação web. O projeto mostra domínio de estruturas de dados, eventos, orientação a objetos, manipulação de arquivos, modularização e uso de bibliotecas."
                ),
                paragraph(
                    "Do ponto de vista técnico, a maior força do projeto está na integração entre conteúdo externo e lógica de jogo. Mapas criados no Tiled geram colisões, loot e transições; spritesheets são interpretadas por padrão de nomes; dados de armas e receitas ficam declarativos; save funciona em desktop e web. Esses elementos tornam o jogo expansível e documentável."
                ),
                paragraph(
                    "Como evolução, recomenda-se criar testes automatizados para módulos de regras, dividir gradualmente o arquivo main.py em componentes de domínio, adicionar validação automática de mapas, padronizar documentação de assets e criar um roteiro formal de testes por plataforma. Ainda assim, o estado atual já constitui uma base funcional, jogável e tecnicamente coerente."
                ),
            ]
        ),
    )

    references = section(
        "12",
        "Referências",
        "".join(
            [
                '<p class="no-indent">PYTHON SOFTWARE FOUNDATION. <strong>Python Documentation</strong>. Disponível em: https://docs.python.org/. Acesso em: 28 maio 2026.</p>',
                '<p class="no-indent">PYGAME COMMUNITY. <strong>Pygame documentation</strong>. Disponível em: https://www.pygame.org/docs/. Acesso em: 28 maio 2026.</p>',
                '<p class="no-indent">PYGBAG. <strong>Pygbag project documentation</strong>. Disponível em: https://pygame-web.github.io/. Acesso em: 28 maio 2026.</p>',
                '<p class="no-indent">TILED. <strong>Tiled Map Editor documentation</strong>. Disponível em: https://doc.mapeditor.org/. Acesso em: 28 maio 2026.</p>',
                '<p class="no-indent">RIBEIRO, Gustavo Emanuel Abreu. <strong>Dead Streets</strong>: repositório local do projeto Jogo-Python. Brasília, 2026.</p>',
            ]
        ),
    )

    appendix_a = section(
        "A",
        "Apêndice A - Inventário técnico de funções",
        "".join(
            [
                paragraph(
                    "Este apêndice lista funções e métodos identificados por análise estática dos arquivos Python. O objetivo é oferecer rastreabilidade para manutenção, revisão e estudo do código."
                ),
                subsection("A.1", "Funções livres", table(["Módulo", "Função", "Linha"], function_rows, "appendix-table")),
                subsection("A.2", "Métodos da classe Game", table(["Classe", "Método", "Linha"], game_method_rows, "appendix-table")),
            ]
        ),
        new_page=True,
    )

    appendix_b = section(
        "B",
        "Apêndice B - Trechos de código comentados",
        "".join(
            [
                paragraph(
                    "Os trechos abaixo foram selecionados por representarem os contratos centrais do projeto: configuração global, carregamento de sprites, criação de receitas, persistência e leitura de mapas."
                ),
                subsection("B.1", "Constantes principais", code_excerpt("main.py", 20, 64)),
                subsection("B.2", "Configuração de efeitos sonoros", code_excerpt("main.py", 83, 133)),
                subsection("B.3", "Sprites do jogador", code_excerpt("player.py", 120, 172)),
                subsection("B.4", "Sprites de zumbis", code_excerpt("zombie.py", 114, 165)),
                subsection("B.5", "Leitura de tiles", code_excerpt("map_loader.py", 260, 294)),
                subsection("B.6", "Receitas completas", code_excerpt("crafting.py", 8, 35)),
                subsection("B.7", "Inventário completo", code_excerpt("inventory.py", 8, 31)),
                subsection("B.8", "Save completo", code_excerpt("save_system.py", 13, 63)),
            ]
        ),
        new_page=True,
    )

    all_sections = [
        cover,
        pre_text,
        intro,
        methodology,
        requirements,
        architecture,
        data_assets,
        implementation,
        flows,
        ui,
        deployment,
        validation,
        conclusion,
        references,
        appendix_a,
        appendix_b,
    ]

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{esc(PROJECT_TITLE)} - Documentação Técnica ABNT</title>
  <style>{css}</style>
</head>
<body>
{''.join(all_sections)}
</body>
</html>
"""


def write_html(html_text: str) -> None:
    HTML_PATH.write_text(html_text, encoding="utf-8")


def print_pdf_with_chrome(output_path: Path = PDF_PATH) -> bool:
    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    chrome = next((path for path in chrome_candidates if path.exists()), None)
    if chrome is None:
        return False
    profile = DOCS_DIR / ".chrome-profile"
    profile.mkdir(exist_ok=True)
    command = [
        str(chrome),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={output_path}",
        str(HTML_PATH),
    ]
    try:
        result = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return False
        return output_path.exists()
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def count_pdf_pages(path: Path) -> int:
    if not path.exists():
        return 0
    return len(PdfReader(str(path)).pages)


def _normalize_pdf_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split()).casefold()


def extract_toc_pages(pdf_path: Path) -> dict[str, int]:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(_normalize_pdf_text(page.extract_text() or ""))
        except Exception:
            pages.append("")

    toc_pages: dict[str, int] = {}
    for number, title in default_toc_items():
        target = _normalize_pdf_text(f"{number} {title}")
        for page_index, text in enumerate(pages):
            # The first four physical pages are cover, title page, resumo and sumario.
            if page_index < 4:
                continue
            if target in text:
                toc_pages[number] = page_index + 1
                break
    return toc_pages


def main() -> None:
    ensure_dirs()
    map_images = make_map_images()
    sprite_showcase = make_sprite_showcase()
    architecture_svg = make_architecture_svg()
    use_case_svg = make_use_case_svg()
    flow_svgs = {
        "novo_jogo": make_flow_svg(
            "Fluxo de novo jogo",
            [
                "Usuário seleciona Novo Jogo no menu principal",
                "Game executa reset de estado, inventário e variáveis de progressão",
                "Mapa inicial TMJ é carregado pelo TiledMap",
                "Jogador é posicionado em área livre e segura",
                "Música de gameplay é ativada e loop passa para estado de jogo",
            ],
        ),
        "exploracao": make_flow_svg(
            "Fluxo de exploração e loot",
            [
                "Jogador se move pelo mapa com câmera acompanhando a posição",
                "Sistema resolve colisões contra retângulos derivados das layers",
                "Game procura nó de busca, corpo, porta ou teleporte dentro do alcance",
                "Ao pressionar interagir, recompensas são sorteadas e aplicadas",
                "Inventário, popups, sons e mensagens são atualizados",
            ],
        ),
        "combate": make_flow_svg(
            "Fluxo de combate",
            [
                "Entrada de ataque é recebida por mouse, teclado ou controle",
                "Game valida cooldown e arma equipada",
                "Ataque melee ou disparo é calculado conforme dados de WEAPONS",
                "Zumbi atingido recebe dano e possíveis efeitos de fogo ou gelo",
                "Morte gera corpo, recompensa, som e atualização de objetivo",
            ],
        ),
        "crafting": make_flow_svg(
            "Fluxo de crafting",
            [
                "Jogador abre painel de crafting",
                "Sistema lista receitas desbloqueadas pelo inventário atual",
                "Jogador seleciona uma receita",
                "CraftingSystem valida recursos e bloqueios",
                "Recursos são removidos e item produzido é adicionado",
            ],
        ),
        "save": make_flow_svg(
            "Fluxo de save/load",
            [
                "Jogador solicita salvar ou carregar",
                "save_system detecta se está em desktop ou WebAssembly",
                "Desktop grava ou lê savegame.json",
                "Web grava ou lê localStorage com chave própria",
                "Game aplica dados carregados ao jogador, inventário e atalhos",
            ],
        ),
    }
    write_html(build_html(map_images, sprite_showcase, architecture_svg, use_case_svg, flow_svgs))
    preview_ok = print_pdf_with_chrome(PREVIEW_PDF_PATH)
    toc_pages = extract_toc_pages(PREVIEW_PDF_PATH) if preview_ok else {}
    write_html(build_html(map_images, sprite_showcase, architecture_svg, use_case_svg, flow_svgs, toc_pages))
    pdf_ok = print_pdf_with_chrome(PDF_PATH)
    PREVIEW_PDF_PATH.unlink(missing_ok=True)
    pages = count_pdf_pages(PDF_PATH)
    print(f"HTML: {HTML_PATH}")
    print(f"PDF: {PDF_PATH if pdf_ok else 'não gerado'}")
    print(f"Páginas estimadas: {pages}")
    if toc_pages:
        print("Sumário:", ", ".join(f"{key}={value}" for key, value in toc_pages.items()))


if __name__ == "__main__":
    main()
