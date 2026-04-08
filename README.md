# Jogo em Python
Jogo 2D de sobrevivencia contra zumbis com exploracao, scavenging, crafting em estacoes e gerenciamento de recursos, desenvolvido em Python com Pygame.

## Como rodar

1. Instale dependencias:
   - `python -m pip install -r requirements.txt`
2. Execute:
   - `python main.py`

Controles:
- `WASD` mover
- `Shift` correr (consome stamina)
- `E` vasculhar pontos de interesse
- `Q` consumir `comida` ou `kit_medico`
- `C` craftar receita selecionada quando estiver perto da estacao certa
- `Tab` trocar receita
- `I` abrir/fechar inventario
- `H` abrir/fechar ajuda
- Clique esquerdo ou `Space` atacar
- `1/2/3` equipar lanca/machado/espada
- `F5` salvar
- `F9` carregar
- `ESC` sair

Loop atual:
- Explore o mapa maior e procure `caixotes`, `despensas`, `sucata`, `ervas` e `arsenais`
- Use `bancadas` e `fogueiras` para crafting estrategico
- Controle `vida`, `stamina` e `fome`
- Enfrente grupos pequenos de zumbis em vez de hordas constantes
- Use a base inicial como ponto seguro e o minimapa para se orientar
