# Jogo em Python

Jogo 2D de sobrevivencia com zumbis, exploracao, loot, crafting e gerenciamento de recursos, desenvolvido em Python com Pygame.

## Estado atual do projeto

O jogo hoje inclui:

- mapa maior com camera seguindo o personagem
- base inicial com zona segura
- minimapa com jogador, zumbis, estacoes e pontos de busca
- sistema de fome, vida e stamina
- inventario na interface
- busca em pontos de interesse e em corpos de zumbis abatidos
- crafting por receita em estacoes especificas
- armas corpo a corpo e de fogo com consumo de municao
- save/load rapido

## Como rodar

1. Instale as dependencias:
   - `python -m pip install -r requirements.txt`
2. Execute o jogo:
   - `python main.py`

Dependencia atual:

- `pygame>=2.5`

## Controles

- `WASD`: mover
- `Shift`: correr, consumindo stamina
- `Clique esquerdo` ou `Space`: atacar
- `E`: vasculhar pontos de interesse ou corpos
- `Q`: consumir `comida` ou usar `kit_medico`
- `C`: craftar a receita selecionada na estacao correta
- `Tab`: trocar a receita selecionada
- `1`: equipar `maos`
- `2`: equipar `taco`
- `3`: equipar `pistola`
- `4`: equipar `escopeta`
- `I`: abrir/fechar inventario
- `H`: abrir/fechar painel de ajuda
- `F5`: salvar em `savegame.json`
- `F9`: carregar o save
- `Esc`: sair

## Loop de jogo

- Explore o mapa e volte para a base quando precisar se reorganizar.
- Vasculhe pontos de interesse para conseguir recursos, comida, ervas, armas e municao.
- Derrote zumbis com cuidado e use `E` para vasculhar os corpos abatidos.
- Gerencie fome e vida para nao morrer por exaustao ou por ataques.
- Use as estacoes para converter recursos em equipamentos e suprimentos.

## Pontos de interesse

Os pontos de busca atuais sao:

- `arvore`: foco em `madeira`
- `caixote`: mistura de `metal`, `pano` e `comida`
- `sucata`: foco em `metal`, com chance de `polvora`
- `despensa`: foco em `comida`, `erva` e `kit_medico`
- `erva`: foco em `erva`
- `carro`: pode render `metal`, `balas`, `polvora` e `pistola`
- `edificio`: pode render `balas`, `polvora`, `pistola` e `escopeta`

Algumas buscas podem gerar emboscadas com novos zumbis.

## Crafting

Receitas atuais:

- `taco`: custa `3 madeira` na `bancada`
- `balas`: custa `1 metal` + `1 polvora` na `bancada` e cria `6 balas`
- `kit_medico`: custa `2 pano` + `2 erva` na `fogueira`

Estacoes disponiveis no mundo:

- `bancada`
- `fogueira`

## Combate e armas

Armas disponiveis atualmente:

- `maos`: dano baixo, alcance curto
- `taco`: arma corpo a corpo mais forte
- `pistola`: alcance alto, consome `1 bala` por ataque
- `escopeta`: dano alto, alcance medio, consome `2 balas` por ataque

Se faltar municao, armas de fogo nao disparam.

## Recursos e inventario

O inventario atual acompanha:

- `madeira`
- `metal`
- `pano`
- `erva`
- `polvora`
- `balas`
- `comida`
- `kit_medico`
- `taco`
- `pistola`
- `escopeta`

O jogador comeca com `maos` equipaveis e `2 comida`.

## Salvamento

O save registra:

- vida
- fome
- posicao do jogador
- inventario
- arma equipada
- tempo de jogo

## Objetivo atual

O loop principal do projeto hoje e sobreviver o maximo possivel, explorar, coletar recursos, melhorar seu equipamento e voltar para a base vivo.
