# Acervo — biblioteca de assets procedurais

Biblioteca de assets para jogos e projetos multimídia: **texturas PBR, sprites 2D, UI, tilesets, fundos parallax, efeitos animados, modelos 3D, efeitos sonoros, instrumentos, ambientes e músicas**.

Nada aqui é um arquivo "congelado": **tudo é gerado por código a partir de parâmetros**. Se você quer o mesmo tijolo em branco, a mesma poção em verde, o mesmo laser mais grave ou a mesma trilha a 170 BPM, basta mudar um número ou uma cor e gerar de novo.

- **Licença dos assets gerados:** CC0 (domínio público). Pode usar em qualquer projeto, inclusive comercial, sem precisar dar crédito.
- **Dependências:** Python 3.9+, `numpy` e `Pillow`. O `ffmpeg` é opcional e só serve para criar versões `.ogg`.
- **Independente:** não depende de engine nenhuma. Os formatos são universais (PNG, GLB/glTF, OBJ, WAV, OGG, MIDI e JSON).

---

## Começo rápido

```bash
pip install numpy pillow
python -m acervo construir          # gera o pacote completo em ./pacote (~1 min)
python -m acervo galeria            # abre a galeria no navegador
```

Ou instale como comando:

```bash
pip install -e .
acervo listar
```

## O que vem no pacote padrão (496 itens, ~1700 arquivos)

| Seção | Conteúdo |
|---|---|
| **Texturas** (101) | 45 geradores + variações: madeira, tábuas, caixote, casca, tijolo, pedra, paralelepípedo, pedra com musgo, concreto, asfalto, azulejo, hexágonos, telhado, mármore, granito/terrazzo, cristal, grama, terra, areia, neve, gelo, água (cáusticas), lava, folhagem, musgo, metal escovado, chapa xadrez, ferrugem, grade, ouro, tecido, couro, papel, carpete, camuflagem, escamas, pele alienígena, nuvens, espaço/nebulosa, circuito, painel sci-fi, grade de teste UV, ruídos. **Todas tileáveis**, com mapas `normal`, `altura`, `ao`, `rugosidade` (+ `metalico`/`emissao` quando faz sentido) e versão `pixel32`. |
| **Sprites** (78) | 25 ícones de itens (poção, espada, gema, chave, baú...) com variações de cor em 16 e 32 px, atlas + JSON, 4 folhas procedurais com 64 naves/criaturas/invasores/robôs (com animação) e 16 personagens com caminhada. |
| **Efeitos** (19) | 8 animações em spritesheet (explosão, fogo, fumaça, magia, impacto, coleta, portal, respingo) e 11 partículas brancas para tingir. Tudo em 64 e 128 px. |
| **Interface** (8) | 8 estilos (madeira, pedra, metal, pergaminho, sci-fi, doce, escuro, floresta): painel 9-slice, botões em 3 estados, barras de vida/mana/xp/energia, caixa de seleção, slots e slider. |
| **Cenários** (14) | 8 tilesets **autotile de 47 peças** (16 e 32 px, JSON máscara→índice) e 6 fundos parallax em camadas tileáveis na horizontal. |
| **Modelos 3D** (35) | Pinheiro, árvore, rocha, cristal, barril, caixote (PBR), casa, baú, cogumelo, coluna, escada, cerca, moeda, gema, espada, tocha e variações, mais 8 primitivas com UV e um terreno. Formatos **GLB** (validado com o glTF-Validator oficial) e **OBJ+MTL**, com prévias e um giro animado. |
| **Sons** (241) | 90 efeitos retrô em 15 categorias (cada um com JSON editável), 83 efeitos "realistas" (passos em 8 superfícies, impactos, portas, UI, whoosh, splash, trovão, sinos...), 17 instrumentos × 5 notas, 17 peças de bateria, 11 ambientes em **loop perfeito**, 13 músicas em **loop perfeito** (WAV + OGG + **MIDI**) e 10 jingles. |

## Modificando os assets

### 1) Pela linha de comando

```bash
python -m acervo listar                     # tudo que existe
python -m acervo listar texturas --detalhes # parâmetros padrão de cada textura

python -m acervo textura tijolo --tamanho 2048 --semente 7 --p cor_rejunte='#ffffff' --p linhas=12
python -m acervo textura marmore --p cor_base='#202020' --p cor_veio='#d4af37'
python -m acervo textura grama --p flores=0.15 --pixel 16 32 64
python -m acervo icone pocao --tamanho 64 --p cor='#33cc99'
python -m acervo procedural nave --semente 42 --escala 4
python -m acervo personagem --semente 3 --p cabelo='#ff00aa' --escala 4
python -m acervo animacao explosao --tamanho 256 --quadros 12 --p cores='["#001","#03a","#0af","#fff"]'
python -m acervo painel scifi --largura 64 --altura 32 --estado foco --p fundo='#1a0a2a' --p borda='#ff3a8a'
python -m acervo tileset campo --tile 32
python -m acervo fundo noite --largura 1920 --altura 1080
python -m acervo modelo arvore --semente 4 --p cor_folhas='#d8762a'
python -m acervo modelo esfera --textura marmore

python -m acervo sfx laser --variacoes 10
python -m acervo sfx --json pacote/sons/sfx_retro/laser/laser_01.json --p deslize=-3 --p reverb=0.4
python -m acervo realista passo --p superficie=neve --variacoes 6
python -m acervo nota piano C4 E4 G4 --dur 2
python -m acervo ambiente chuva --duracao 60 --p intensidade=1.0
python -m acervo musica batalha --semente 9 --p bpm=170 --p compassos=16
python -m acervo musica --json pacote/sons/musicas/vila_estilo.json --semente 5
python -m acervo jingle vitoria --instrumento cordas --acompanhamento piano
```

Os valores de `--p` são lidos como JSON quando possível (`linhas=12`, `digital=true`, `cores='["#111","#eee"]'`); se não forem JSON válido, viram texto.

### 2) Pela receita (o pacote inteiro)

`acervo/presets/receita.json` descreve **tudo** que o pacote gera: cada textura com seus parâmetros, as variações de cor dos ícones, quantas variações de cada som, quais músicas etc. Edite e reconstrua:

```bash
python -m acervo receita minha_receita.json       # copia a receita padrão
# ...edite cores, sementes, tamanho das texturas (1024/2048), adicione variações...
python -m acervo construir --receita minha_receita.json --saida meu_pacote
python -m acervo construir --secoes texturas,sons  # reconstrói só algumas seções
```

### 3) No navegador (sem Python)

Abra `pacote/galeria.html`. Lá dá para:
- navegar e buscar tudo, ver texturas repetidas 3×3, trocar entre os mapas e ver as animações e os modelos girando;
- ajustar matiz, saturação, brilho e contraste de qualquer imagem e baixar o resultado (para baixar, abra com `python -m acervo galeria`, porque o navegador bloqueia isso em arquivos abertos direto do disco);
- usar o **Editor de SFX**: gerar sons por categoria, mexer em ~27 parâmetros, ver a forma de onda, exportar WAV e copiar/colar o JSON, que é o mesmo formato do Python.

### 4) Em Python

```python
from acervo import texturas, sprites, efeitos, cenarios, modelos
from acervo.som import sfx, instrumentos, ambiente, musica
from acervo.som.sintese import salvar_wav

t = texturas.gerar("pedra", tamanho=1024, semente=5, celulas=10, cores=["#222", "#555", "#888", "#bbb"])
t.salvar("saida", "pedra_escura")                    # cor + normal + altura + ao + rugosidade + pixel32

sprites.icone("espada", 32, cor="#8ae8ff").save("espada_cristal.png")

m = modelos.gerar("cristal", semente=3, cor="#3ad87a", quantidade=8)
m.salvar_glb("cristais.glb")

p = sfx.sortear("moeda", semente=10)
p["freq"] = 1200
salvar_wav("moeda.wav", sfx.sintetizar(p))

trilha = musica.compor("masmorra", semente=2, bpm=72, tonica="E", compassos=16)
musica.salvar(trilha, "masmorra_lenta")              # .wav em loop + .mid

salvar_wav("vento.wav", ambiente.gerar("vento", duracao=45, intensidade=0.9))
```

### 5) Criando um gerador novo

Os registros usam decoradores, então um gerador novo aparece sozinho na CLI, na receita e na galeria:

```python
# em acervo/texturas.py
@material("bolinhas", "Bolinhas coloridas.", "util", cor_fundo="#ffeecc", cor_bolinha="#cc3355", quantidade=8, raio=0.3)
def bolinhas(u, v, s, p):
    n = p["quantidade"]
    lx, ly = (u * n) % 1 - 0.5, (v * n) % 1 - 0.5
    dentro = np.sqrt(lx**2 + ly**2) < p["raio"]
    cor = np.where(dentro[..., None], hex_rgb(p["cor_bolinha"]), hex_rgb(p["cor_fundo"]))
    return Textura(cor, dentro.astype(float), 0.6, 0.0)
```

O mesmo vale para `@icone_def` (sprites), `@particula_def` / `@animacao_def` (efeitos), `@objeto_def` (modelos) e para os dicionários `CATEGORIAS`, `INSTRUMENTOS`, `AMBIENTES` e `ESTILOS` (som).

## Convenções técnicas

- **Texturas:** emendam sem costura em todas as direções (ruídos periódicos). O mapa normal segue o padrão **OpenGL** (verde = +Y), que é o usado por Godot, Blender e Three.js. Na Unreal e em outros programas no padrão DirectX, inverta o canal verde.
- **Modelos:** Y para cima, 1 unidade = 1 m, origem na base do objeto. GLB com cores por vértice (`COLOR_0`) e, no caixote, textura + mapa normal + tangentes embutidos. O OBJ também inclui cores por vértice, no formato que Blender e MeshLab leem.
- **Tilesets:** para cada tile sólido, some os bits dos vizinhos sólidos: `N=1, NE=2, L=4, SE=8, S=16, SO=32, O=64, NO=128`. Os cantos só contam se os dois lados vizinhos forem sólidos. O JSON traz `mascara_para_indice` (47 entradas) e `todas_256_mascaras`.
- **UI 9-slice:** painéis de 48×48 com margem de 6 px e botões de 48×16 com margem de 3 px.
- **Spritesheets:** quadros lado a lado na horizontal, todos do mesmo tamanho.
- **Áudio:** WAV PCM 16 bits, 44,1 kHz. Efeitos são mono (os que têm reverb saem em estéreo). Ambientes e músicas saem em estéreo e fazem **loop sem emenda**: o final é cruzado com o começo e as caudas de reverb voltam para o início.
- **MIDI:** tipo 1, um canal por instrumento com programas General MIDI e a bateria no canal 10.

## Estrutura do código

```
acervo/
  ruido.py        ruídos periódicos: Perlin, fBm, ridged, Worley, warp
  cor.py          hex, rampas de cor, ajustes HSV, paletas, pixelização
  texturas.py     45 geradores de material + classe Textura (mapas PBR)
  sprites.py      ícones por camadas (luz/sombra/contorno automáticos), naves/criaturas, personagens
  efeitos.py      partículas e animações
  interface.py    painéis, botões, barras, slots, sliders
  cenarios.py     tilesets autotile 47 e fundos parallax
  modelos.py      malhas, primitivas, objetos low-poly, exportação OBJ/GLB
  render3d.py     rasterizador em numpy para as prévias
  som/sintese.py  osciladores, envelopes, filtros, reverb por convolução, WAV
  som/sfx.py      motor de SFX parametrizado + sons realistas
  som/instrumentos.py  17 instrumentos (aditivo, Karplus-Strong, FM...) + bateria
  som/ambiente.py      11 ambientes em loop
  som/musica.py        compositor (estrutura A A' B A''), jingles, exportação MIDI
  receita.py / construir.py / galeria.py / __main__.py
testes/teste_rapido.py   teste de fumaça (~5 s)
```

## Licença

O código está sob licença MIT e **os assets gerados estão sob CC0** (domínio público). Veja `LICENSE`.
