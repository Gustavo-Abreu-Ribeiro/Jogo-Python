# Dead Streets

Dead Streets é um jogo 2D de sobrevivencia feito em Python com Pygame. O projeto roda como aplicativo desktop e tambem pode ser empacotado para navegador com Pygbag/WebAssembly.

O projeto foi para a matéria programação de computadores na UDF ministrada pela professora Karla Roberto Sartin

Aluno: Gustavo Emanuel Abreu Ribeiro
RGM 32237740

## Jogar

- Online: https://gustavo-abreu-ribeiro.github.io/Jogo-Python/
- APK Android gerado pelo Pygbag: https://gustavo-abreu-ribeiro.github.io/Jogo-Python/jogo-python.apk
- Pacote web: https://gustavo-abreu-ribeiro.github.io/Jogo-Python/jogo-python.tar.gz

## Estado Atual

O jogo usa mapas criados no Tiled (`.tmj`) com tilesets externos (`.tsx`), sprites em pixel art, audio OGG e um loop de exploracao, combate, inventario, crafting e transições entre areas. A camera segue o jogador em mapas, com colisão por camadas do mapa e pontos interativos derivados das layers do Tiled.

Sistemas implementados:

- Movimento com teclado, mouse e controle.
- Vida, fome, stamina e morte.
- Inventario com atalhos rapidos, consumiveis e armas.
- Crafting por receitas em estações de trabalho.
- Loot em pontos de busca, corpos e áreas do mapa.
- Armas corpo a corpo, armas de fogo e tipos especiais de municao.
- Zumbis com variantes, animações, colisão, separação e comportamento de ataque.
- Mapas normais, interiores, arenas e teleporte entre areas.
- Musica e efeitos sonoros com volume configuravel.
- Save em arquivo no desktop e `localStorage` no navegador.

## Estrutura

```text
.
|-- audio/                 # Musicas e efeitos em OGG
|   `-- sfx/
|-- maps/                  # Mapas TMJ e tilesets usados pelo Tiled
|   `-- tilesets/
|-- sprites/               # Sprites do jogo, UI e pacote visual base
|   |-- ui/
|   |-- character/
|   |-- Objects/
|   |-- Shot/
|   |-- Zombie_Axe/
|   |-- Zombie_Big/
|   |-- Zombie_Small/
|   `-- post_apocalypse/
|-- tools/
|   `-- patch_web_build.py # Ajuste da pagina gerada pelo Pygbag
|-- main.py                # Loop principal, estados, render e sistemas de jogo
|-- map_loader.py          # Leitura de mapas e tilesets do Tiled
|-- player.py              # Jogador, animacoes e movimentacao
|-- zombie.py              # Inimigos, animacoes e ataques
|-- inventory.py           # Inventario
|-- crafting.py            # Receitas de crafting
|-- weapons.py             # Dados das armas
`-- save_system.py         # Save/load
```

`build/`, `__pycache__/`, `savegame.json` e `settings.json` sao gerados localmente e ficam fora do versionamento.

## Rodar no Desktop

```powershell
python -m pip install -r requirements.txt
python main.py
```

Dependencia principal:

```text
pygame>=2.5
```

## Build Web

```powershell
python -m pip install -r requirements-web.txt
python -m pygbag --build .
python tools/patch_web_build.py
```

A saida fica em `build/web`. O workflow em `.github/workflows/pages.yml` executa o build, aplica o ajuste da tela de carregamento e publica no GitHub Pages.

## Controles

- `WASD`: mover
- `Shift`: correr
- `Mouse`: mirar
- `Clique esquerdo` ou `Space`: atacar
- `E`: interagir, buscar ou atravessar portas/teleportes
- `Q`: usar consumivel
- `B`: abrir crafting
- `C`: craftar receita selecionada
- `Tab`: trocar receita
- `I`: abrir inventario
- `1` a `6`: atalhos rapidos
- `F2`: debug de controle
- `F5`: salvar
- `F9`: carregar
- `Esc`: voltar ou sair

## Controle

O jogo le controles via `pygame.joystick` e, quando disponivel, `pygame._sdl2.controller`.

- Analogico esquerdo: movimento
- Analogico direito: mira
- L3: correr
- R2: atacar
- X: interagir
- Quadrado: crafting
- Triangulo: usar item
- R3: inventario
- L1/R1 ou direcional: alternar atalhos
- Options/Share: menu ou voltar

No navegador, o suporte depende da Gamepad API do browser e do sistema operacional. USB tende a ser mais consistente que Bluetooth.

## Notas Tecnicas

- A versao web usa resolucao interna menor que a janela desktop para reduzir custo de render e evitar canvas instavel em alguns navegadores.
- O audio foi padronizado em OGG para desktop e web, evitando conversao no pipeline e reduzindo o pacote.
- A musica usa `pygame.mixer.music` diretamente, sem camadas duplicadas, para evitar travamentos no mixer WebAssembly.
- Objetos e inimigos fora da camera deixam de ser desenhados, reduzindo trabalho por frame em mapas cheios.
- Os assets do pacote visual foram consolidados em `sprites/post_apocalypse`; a UI fica em `sprites/ui`.
