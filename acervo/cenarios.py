"""Cenários 2D: tilesets com autotile (47 peças "blob") e fundos parallax.

Tileset: as 47 peças cobrem todas as combinações de vizinhos. O arquivo JSON
gerado junto traz o mapa máscara->índice. Bits da máscara (vizinho sólido):
    N=1, NE=2, L=4, SE=8, S=16, SO=32, O=64, NO=128
(cantos só contam se os dois lados adjacentes também forem sólidos).
"""
import numpy as np
from PIL import Image

from .ruido import perlin, fbm, grade
from .cor import hex_rgb, rampa, pixelizar, para_imagem
from . import texturas

N_, NE, E_, SE, S_, SW, W_, NW = 1, 2, 4, 8, 16, 32, 64, 128


def reduzir(m):
    if not (m & N_ and m & E_):
        m &= ~NE
    if not (m & S_ and m & E_):
        m &= ~SE
    if not (m & S_ and m & W_):
        m &= ~SW
    if not (m & N_ and m & W_):
        m &= ~NW
    return m


MASCARAS_47 = sorted({reduzir(m) for m in range(256)})
assert len(MASCARAS_47) == 47

TEMAS_TILESET = {
    "campo": dict(textura="terra", cores_preench=["#3b2617", "#5a3b22", "#7a5232", "#94693f"], cobertura=["#2a6a1e", "#4c9a2a", "#7cc63a", "#b0e85a"], contorno="#1a120c"),
    "neve": dict(textura="pedra", cores_preench=["#3a3d48", "#5a5e6c", "#7d8292", "#9da2b0"], cobertura=["#8aa0c8", "#c4d4ec", "#eef4ff", "#ffffff"], contorno="#151820"),
    "deserto": dict(textura="areia", cores_preench=["#8a5a2e", "#a8743e", "#c48f52", "#d8a868"], cobertura=["#c89a5a", "#e0b878", "#f0d49a", "#fff0c4"], contorno="#3a2210"),
    "caverna": dict(textura="pedra", cores_preench=["#1c1a22", "#2c2934", "#403c4a", "#57525f"], cobertura=None, contorno="#0a090e"),
    "castelo": dict(textura="tijolo", cores_preench=["#3c3c46", "#5a5a66", "#7c7c88", "#9a9aa4"], cobertura=None, contorno="#121218",
                    params={"linhas": 4, "colunas": 2, "cores": ["#5a5a66", "#7c7c88", "#9a9aa4"], "cor_rejunte": "#3c3c46"}),
    "vulcao": dict(textura="pedra", cores_preench=["#1a1210", "#2e201a", "#463026", "#5c4234"], cobertura=["#a21e00", "#ff5a0a", "#ffa21a", "#ffe58a"], contorno="#0a0605"),
    "floresta": dict(textura="terra", cores_preench=["#22180f", "#33241a", "#463426", "#5a4632"], cobertura=["#163a12", "#24561a", "#3a7a26", "#5a9a34"], contorno="#0c0a06"),
    "doce": dict(textura="xadrez", cores_preench=["#c85a8a", "#e07aa8", "#f29ac0", "#ffc4dc"], cobertura=["#5a2a14", "#7a3e22", "#9a5634", "#c07a4c"], contorno="#3a1424",
                 params={"cor1": "#e07aa8", "cor2": "#ffc4dc", "quantidade": 4}),
}


def _preenchimento(tema, T, semente):
    t = texturas.gerar(tema["textura"], 128, semente, **tema.get("params", {}))
    im = t.imagem().convert("RGB").resize((T, T), Image.BOX)
    lum = np.asarray(im, float).mean(-1) / 255
    z = (lum - lum.mean()) / max(1e-6, lum.std())
    cores = np.stack([hex_rgb(c) for c in tema["cores_preench"]])
    k = len(cores)
    idx = np.clip(np.round(z * 0.75 + (k - 1) / 2 + 0.25), 0, k - 1).astype(int)
    return cores[idx]


def renderizar_tile(mascara, tema, T=16, preench=None, semente=0):
    rng = np.random.default_rng(semente)
    if preench is None:
        preench = _preenchimento(tema, T, semente)
    cob = [hex_rgb(c) for c in tema["cobertura"]] if tema.get("cobertura") else None
    alt_cob = 3 + (np.sin(np.arange(T) * 1.7 + 1.3) * 1.2 + np.sin(np.arange(T) * 0.9) * 0.8).round().astype(int)
    alt_cob = np.clip(alt_cob, 2, max(3, T // 3))
    img = np.zeros((T, T, 4))
    inf = 10 ** 6
    y, x = np.mgrid[0:T, 0:T]
    ds = {"N": np.where(mascara & N_, inf, y), "S": np.where(mascara & S_, inf, T - 1 - y),
          "O": np.where(mascara & W_, inf, x), "L": np.where(mascara & E_, inf, T - 1 - x),
          "NO": np.where((mascara & N_) and (mascara & W_) and not (mascara & NW), np.maximum(x, y), inf),
          "NE": np.where((mascara & N_) and (mascara & E_) and not (mascara & NE), np.maximum(T - 1 - x, y), inf),
          "SO": np.where((mascara & S_) and (mascara & W_) and not (mascara & SW), np.maximum(x, T - 1 - y), inf),
          "SE": np.where((mascara & S_) and (mascara & E_) and not (mascara & SE), np.maximum(T - 1 - x, T - 1 - y), inf)}
    nomes = list(ds)
    pilha = np.stack([ds[k] for k in nomes])
    d = pilha.min(0)
    lado = np.array(nomes)[pilha.argmin(0)]
    img[..., :3] = preench
    img[..., 3] = 1
    luz = (d == 1) & np.isin(lado, ["N", "O", "NO"])
    sombra = (d == 1) & np.isin(lado, ["S", "L", "SE", "SO", "NE"])
    img[luz, :3] = np.clip(img[luz, :3] * 1.3 + 0.05, 0, 1)
    img[sombra, :3] = img[sombra, :3] * 0.65
    if cob is not None and not (mascara & N_):
        g = alt_cob[x]
        grama = y < g
        img[grama, :3] = cob[2]
        img[(y == g - 1), :3] = cob[1]
        img[(y == g), :3] = np.array(cob[0]) * 0.8 + img[(y == g), :3] * 0.2
        img[(y == 1) & grama, :3] = cob[3]
        # tufos que escorregam pelas laterais
        if not (mascara & W_):
            img[(x <= 1) & (y < g + 2), :3] = cob[1]
        if not (mascara & E_):
            img[(x >= T - 2) & (y < g + 2), :3] = cob[1]
    img[d == 0, :3] = hex_rgb(tema["contorno"])
    return img


def tileset(tema="campo", T=16, semente=0, colunas=8):
    """Gera folha com as 47 peças. Retorna (imagem, mapa {mascara: indice})."""
    t = TEMAS_TILESET[tema] if isinstance(tema, str) else tema
    preench = _preenchimento(t, T, semente)
    linhas = (47 + colunas - 1) // colunas
    folha = np.zeros((linhas * T, colunas * T, 4))
    mapa = {}
    for i, m in enumerate(MASCARAS_47):
        r, c = divmod(i, colunas)
        folha[r * T:(r + 1) * T, c * T:(c + 1) * T] = renderizar_tile(m, t, T, preench, semente)
        mapa[m] = i
    # último espaço livre: uma variação de preenchimento puro
    if linhas * colunas > 47:
        r, c = divmod(47, colunas)
        p2 = _preenchimento(t, T, semente + 1)
        folha[r * T:(r + 1) * T, c * T:(c + 1) * T, :3] = p2
        folha[r * T:(r + 1) * T, c * T:(c + 1) * T, 3] = 1
    im = Image.fromarray(np.clip(folha * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA")
    return im, mapa


def mapa_completo_256(mapa47):
    return {m: mapa47[reduzir(m)] for m in range(256)}


def montar_mapa(grade_solida, folha, mapa47, T=16):
    """Monta uma imagem a partir de uma matriz booleana (True = sólido)."""
    G = np.asarray(grade_solida, bool)
    h, w = G.shape
    colunas = folha.width // T
    out = Image.new("RGBA", (w * T, h * T), (0, 0, 0, 0))
    def s(yy, xx):
        if xx < 0 or xx >= w:
            return True if 0 <= yy < h and G[yy, min(max(xx, 0), w - 1)] else False
        if yy < 0:
            return False
        if yy >= h:
            return True
        return G[yy, xx]
    for y in range(h):
        for x in range(w):
            if not G[y, x]:
                continue
            m = 0
            for bit, (dy, dx) in ((N_, (-1, 0)), (NE, (-1, 1)), (E_, (0, 1)), (SE, (1, 1)), (S_, (1, 0)),
                                  (SW, (1, -1)), (W_, (0, -1)), (NW, (-1, -1))):
                if s(y + dy, x + dx):
                    m |= bit
            i = mapa47[reduzir(m)]
            r, c = divmod(i, colunas)
            out.paste(folha.crop((c * T, r * T, (c + 1) * T, (r + 1) * T)), (x * T, y * T))
    return out


def terreno_exemplo(largura=32, altura=14, semente=0):
    rng = np.random.default_rng(semente)
    u = np.arange(largura) / largura
    alt = (perlin(u, np.zeros_like(u), 3, semente) * 0.5 + 0.5) * altura * 0.45 + altura * 0.35
    G = np.zeros((altura, largura), bool)
    for x in range(largura):
        G[int(altura - alt[x]):, x] = True
    for _ in range(4):  # plataformas flutuantes
        px, py, pw = rng.integers(0, largura - 5), rng.integers(2, altura // 2), rng.integers(2, 6)
        G[py, px:px + pw] = True
        if rng.random() < 0.5:
            G[py + 1, px + 1:px + pw - 1] = True
    return G


# ----------------------------------------------------------------------------
# Fundos parallax (tileáveis na horizontal)
# ----------------------------------------------------------------------------
TEMAS_FUNDO = {
    "dia": dict(ceu=["#3a7bd5", "#7fb4ee", "#cfe6fa"], camadas=[
        ("montanhas", "#7f9cc4", "#a9c0de", 0.42, 0.18, True), ("colinas", "#5f9a6a", "#7cb886", 0.35, 0.08, False),
        ("arvores", "#2f6a3a", "#3f8a4a", 0.22, 0.0, False)], sol="#fff6c8", estrelas=0, nuvens="#ffffff"),
    "entardecer": dict(ceu=["#2a1d4a", "#c2436a", "#f7a35c"], camadas=[
        ("montanhas", "#6a3a6a", "#8a4a72", 0.55, 0.18, False), ("colinas", "#3e2450", "#56305e", 0.38, 0.08, False),
        ("arvores", "#1e1230", "#2a1a3e", 0.22, 0.0, False)], sol="#ffd27a", estrelas=0.0005, nuvens="#f4a0a0"),
    "noite": dict(ceu=["#03040c", "#0c1430", "#1e2c5a"], camadas=[
        ("montanhas", "#1a2244", "#243060", 0.5, 0.18, True), ("colinas", "#101830", "#162040", 0.35, 0.08, False),
        ("arvores", "#060a16", "#0a1020", 0.22, 0.0, False)], lua="#f0f0e0", estrelas=0.003, nuvens="#4a5a8a"),
    "inverno": dict(ceu=["#8aa4c8", "#c4d4ea", "#eef3fa"], camadas=[
        ("montanhas", "#9aaccc", "#e8eef8", 0.6, 0.2, True), ("colinas", "#c8d6ea", "#f4f8ff", 0.36, 0.08, False),
        ("arvores", "#3a5a5a", "#4a6a6a", 0.24, 0.0, False)], sol="#ffffff", estrelas=0, nuvens="#ffffff"),
    "deserto": dict(ceu=["#e07a3a", "#f4b46a", "#fde0a8"], camadas=[
        ("montanhas", "#c48a5a", "#d8a070", 0.45, 0.12, False), ("dunas", "#d8a060", "#e8b878", 0.3, 0.06, False),
        ("dunas", "#b87a42", "#c88a52", 0.18, 0.0, False)], sol="#fff2c0", estrelas=0, nuvens=None),
    "alienigena": dict(ceu=["#0a1a1a", "#1a5a4a", "#7ae0a0"], camadas=[
        ("montanhas", "#2a4a6a", "#3a6a8a", 0.55, 0.2, False), ("cristais", "#5a2a7a", "#8a4aaa", 0.35, 0.05, False),
        ("cogumelos", "#1a0a2a", "#2a1a3a", 0.22, 0.0, False)], lua="#ffb0f0", estrelas=0.002, nuvens=None),
}


def _altura_1d(u, freq, semente, tipo="perlin", oitavas=5):
    v = np.full_like(u, 0.37)
    n = fbm(u, v, (freq, 1), oitavas, semente=semente, tipo=tipo)
    return n * 0.5 + 0.5 if tipo == "perlin" else n


def fundo(tema="dia", largura=640, altura=360, semente=0):
    """Retorna lista [(nome, imagem RGBA)], do fundo (céu) para a frente."""
    t = TEMAS_FUNDO[tema]
    rng = np.random.default_rng(semente)
    W, H = int(largura), int(altura)
    yy = np.arange(H)[:, None] / H * np.ones((1, W))
    u = np.arange(W) / W
    camadas = []
    ceu = rampa(yy, t["ceu"])
    if t.get("estrelas"):
        est = (rng.random((H, W)) < t["estrelas"]) * (1 - yy) ** 2
        ceu = np.clip(ceu + est[..., None] * rng.random((H, W))[..., None], 0, 1)
    astro = t.get("sol") or t.get("lua")
    if astro:
        cx, cy, r = W * 0.72, H * 0.3, H * (0.08 if t.get("lua") else 0.1)
        X, Y = np.meshgrid(np.arange(W), np.arange(H))
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        disco = np.clip(r - d + 1, 0, 1)
        halo = np.exp(-np.maximum(d - r, 0) / (r * 1.2)) * 0.35
        c = hex_rgb(astro)
        ceu = ceu * (1 - disco[..., None]) + c * disco[..., None]
        ceu = np.clip(ceu + c * halo[..., None] * (1 - disco[..., None]), 0, 1)
    camadas.append(("ceu", para_imagem(ceu)))
    if t.get("nuvens"):
        uu, vv = np.meshgrid(u, np.arange(H) / H)
        n = fbm(uu, vv, (4, 2), 6, semente=semente + 50) * 0.5 + 0.5
        faixa = np.exp(-((yy - 0.3) ** 2) / 0.02)
        a = np.clip((n - 0.42) * 3.5, 0, 1) * faixa
        camadas.append(("nuvens", para_imagem(np.ones((H, W, 3)) * hex_rgb(t["nuvens"]), a * 0.9)))
    for i, (tipo, c1, c2, alt, var, neve) in enumerate(t["camadas"]):
        base = H * (1 - alt)
        if tipo == "montanhas":
            h = _altura_1d(u, 3, semente + i, "ridged", 6) ** 1.5 * H * 0.3 + H * var * 0.1
        elif tipo == "colinas":
            h = _altura_1d(u, 2, semente + i, "perlin", 3) * H * 0.14
        elif tipo == "dunas":
            h = (np.sin(u * 2 * np.pi * 3 + _altura_1d(u, 2, semente + i) * 3) * 0.5 + 0.5) * H * 0.08
        else:
            h = _altura_1d(u, 2, semente + i, "perlin", 3) * H * 0.05
        topo = base - h
        Y = np.arange(H)[:, None]
        massa = Y >= topo[None, :]
        if tipo in ("arvores", "cristais", "cogumelos"):
            X = np.arange(W)[None, :]
            n_obj = int(W / 14)
            for k in range(n_obj):
                cx = rng.random() * W
                hh = H * (0.08 + rng.random() * 0.1)
                ww = hh * (0.35 if tipo == "arvores" else 0.25 if tipo == "cristais" else 0.6)
                chao = base - np.interp(cx, np.arange(W), h)
                for off in (-W, 0, W):
                    dx = np.abs(X - (cx + off))
                    if tipo == "arvores":
                        rel = (Y - (chao - hh)) / hh
                        forma = (rel >= 0) & (rel <= 1) & (dx <= ww * rel * (0.7 + 0.3 * np.abs(np.sin(rel * 14))))
                    elif tipo == "cristais":
                        rel = (Y - (chao - hh)) / hh
                        forma = (rel >= 0) & (rel <= 1) & (dx <= ww * np.minimum(rel * 3, 1))
                    else:
                        cap = ((dx / ww) ** 2 + ((Y - (chao - hh)) / (hh * 0.35)) ** 2 <= 1) & (Y <= chao - hh)
                        caule = (dx <= ww * 0.15) & (Y >= chao - hh) & (Y <= chao)
                        forma = cap | caule
                    massa |= forma
        topo_min = topo.min()
        uu2, vv2 = np.meshgrid(u, np.arange(H) / H)
        textura = fbm(uu2, vv2, (6, 3), 4, semente=semente + i * 7) * 0.08
        sombreado = np.clip((Y - topo_min) / max(1.0, H - topo_min) + textura, 0, 1)
        cor = rampa(1 - sombreado, [c1, c2])
        if neve:
            linha_neve = topo.min() + (base - topo.min()) * 0.35 + _altura_1d(u, 12, semente + 9)[None, :] * H * 0.03
            cobertura = Y < linha_neve
            cor = np.where((cobertura & massa)[..., None], np.ones(3) * 0.95, cor)
        camadas.append((f"{i + 1}_{tipo}", para_imagem(cor, massa.astype(float))))
    return camadas


def compor(camadas):
    base = camadas[0][1].convert("RGBA")
    for _, im in camadas[1:]:
        base.alpha_composite(im.convert("RGBA"))
    return base
