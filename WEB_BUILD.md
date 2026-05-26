# Build web com Pygbag

O jogo continua sendo desenvolvido em Python/Pygame. Para web, o Pygbag empacota o projeto em WebAssembly.

## Preparacao

1. Instale dependencias web:

```powershell
python -m pip install -r requirements-web.txt
```

2. Converta audio para OGG antes do build. O codigo ja procura `.ogg` no navegador, mantendo `.wav` e `.mp3` no desktop.

Exemplo com ffmpeg:

```powershell
Get-ChildItem musics -Recurse -Include *.wav,*.mp3 | ForEach-Object {
  ffmpeg -y -i $_.FullName ([System.IO.Path]::ChangeExtension($_.FullName, ".ogg"))
}
```

3. Os mapas usados pelo build web ficam em `maps/`. Para adicionar mapas novos, copie o `.tmj` para `maps/` e deixe seus tilesets em `maps/Sprites/`.

O arquivo `pygbag.ini` ignora os audios `.wav/.mp3` no pacote web. Quando existirem arquivos `.ogg` com o mesmo nome base, eles serao incluidos.

## Rodar local

```powershell
python -m pygbag --ume_block 0 main.py
```

Abra a URL que o Pygbag mostrar, normalmente `http://localhost:8000`.

Para gerar somente a pasta publicavel:

```powershell
python -m pygbag --build .
```

## Publicar

O Pygbag gera a pasta `build/web`. Essa pasta pode ir para GitHub Pages, itch.io ou hospedagem estatica.

### GitHub Pages

Este repositorio ja tem um workflow em `.github/workflows/pages.yml`.

1. No GitHub, abra `Settings > Pages`.
2. Em `Build and deployment`, selecione `Source: GitHub Actions`.
3. Faça push na branch `main`, ou rode manualmente `Publish web build` na aba `Actions`.
4. Ao terminar, o GitHub mostra a URL do jogo no resumo do deploy.

O workflow:

- instala Python e dependencias de `requirements-web.txt`;
- instala `ffmpeg`;
- converte `.wav` e `.mp3` para `.ogg` durante o CI;
- roda `python -m pygbag --build .`;
- publica `build/web` no GitHub Pages.

Como os `.ogg` sao gerados no CI, voce nao precisa commitar audio convertido. Se quiser testar audio localmente no navegador, rode a conversao da secao de preparacao antes do build local.

## Manutencao

E razoavelmente facil manter se seguirmos estas regras:

- gameplay, mapas e mecanicas continuam em Python;
- assets de web precisam estar dentro do projeto;
- audio novo deve ter versao `.ogg`;
- saves/configuracoes usam arquivo no desktop e `localStorage` no navegador;
- para progresso por mapas, chefao e dificuldade por mapa, o ideal e criar metadados por mapa e um contador de mapas concluidos, em vez de amarrar tudo ao tempo de jogo.

## DualSense

O jogo ja le entrada de controle via `pygame.joystick`:

- analogico esquerdo: movimento;
- analogico direito: mira;
- L3: correr;
- L1/R1: trocar item rapido;
- direcional esquerda/direita: trocar item rapido;
- X: interagir;
- quadrado: abrir/fechar crafting;
- triangulo: usar item/cura;
- R3: abrir/fechar inventario;
- R2: atacar;
- Options/Share: abrir ou voltar menu.

No navegador, o DualSense depende do suporte do browser/sistema via Gamepad API. USB tende a ser mais consistente; Bluetooth tambem pode funcionar, mas recursos especiais do DualSense, como gatilhos adaptaveis, nao ficam garantidos nesse caminho.
