"""Sprites 2D em pixel art: ícones de itens, naves/criaturas procedurais e personagens.

Os ícones são descritos por camadas de formas geométricas num grid 16x16
lógico. A renderização aplica luz (canto superior esquerdo), sombra e contorno
automaticamente — então você pode mudar cores e tamanho (16, 32, 64...) à vontade.

    from acervo import sprites
    im = sprites.icone("pocao", tamanho=32, cor="#3a7bd5")
    im.save("pocao_azul.png")
"""
import colorsys
import numpy as np
from PIL import Image, ImageDraw

from .cor import hex_rgb, rgb_hex


# ----------------------------------------------------------------------------
# Cor
# ----------------------------------------------------------------------------
def clarear(h, k=0.3):
    r, g, b = hex_rgb(h)
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    hh = hh + (0.1667 - hh) * 0.08 * k  # puxa levemente para o amarelo (luz quente)
    return rgb_hex(colorsys.hsv_to_rgb(hh % 1, max(0, s - 0.25 * k), min(1, v + (1 - v) * k * 1.4 + 0.05 * k)))


def escurecer(h, k=0.3):
    r, g, b = hex_rgb(h)
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    alvo = 0.7  # puxa para o azul/roxo (sombra fria)
    hh = hh + ((alvo - hh + 0.5) % 1 - 0.5) * 0.12 * k
    return rgb_hex(colorsys.hsv_to_rgb(hh % 1, min(1, s + 0.15 * k), v * (1 - k)))


# ----------------------------------------------------------------------------
# Motor de ícones por camadas
# ----------------------------------------------------------------------------
def _ret_px(c, esc):
    x0, y0, x1, y1 = c
    return [round(x0 * esc), round(y0 * esc), round(x1 * esc) - 1, round(y1 * esc) - 1]


def _desenhar_op(d, op, esc):
    tipo = op[0]
    if tipo == "e":  # elipse cheia
        d.ellipse(_ret_px(op[1:5], esc), fill=255)
    elif tipo == "eo":  # contorno de elipse
        d.ellipse(_ret_px(op[1:5], esc), outline=255, width=max(1, round(esc * (op[5] if len(op) > 5 else 1))))
    elif tipo == "r":
        d.rectangle(_ret_px(op[1:5], esc), fill=255)
    elif tipo == "p":
        d.polygon([(x * esc, y * esc) for x, y in op[1]], fill=255)
    elif tipo == "l":
        d.line([(x * esc, y * esc) for x, y in op[1]], fill=255, width=max(1, round(op[2] * esc)))
    elif tipo == "c":  # corda (segmento de elipse) — ângulos em graus, sentido horário a partir das 3h
        d.chord(_ret_px(op[1:5], esc), op[5], op[6], fill=255)
    elif tipo == "pie":
        d.pieslice(_ret_px(op[1:5], esc), op[5], op[6], fill=255)


def renderizar_camadas(camadas, tamanho=16, contorno="auto", sombreado=True):
    """camadas: lista de (cor_hex ou None para apagar, [operações]). Grid lógico 16x16."""
    esc = tamanho / 16.0
    idx = np.full((tamanho, tamanho), -1, dtype=int)
    cores = []
    for i, (cor, ops) in enumerate(camadas):
        m = Image.new("L", (tamanho, tamanho), 0)
        d = ImageDraw.Draw(m)
        for op in ops:
            _desenhar_op(d, op, esc)
        mask = np.asarray(m) > 127
        idx[mask] = -1 if cor is None else len(cores)
        if cor is not None:
            cores.append(cor)
    out = np.zeros((tamanho, tamanho, 4))
    cheio = idx >= 0
    for k, c in enumerate(cores):
        M = idx == k
        if not M.any():
            continue
        base = hex_rgb(c)
        out[M, :3] = base
        out[M, 3] = 1
        if sombreado:
            px = max(1, tamanho // 16)
            cima = np.roll(M, px, 0)
            cima[:px] = False
            esq = np.roll(M, px, 1)
            esq[:, :px] = False
            baixo = np.roll(M, -px, 0)
            baixo[-px:] = False
            dir_ = np.roll(M, -px, 1)
            dir_[:, -px:] = False
            luz = M & (~cima | ~esq)
            sombra = M & (~baixo | ~dir_) & ~luz
            out[luz, :3] = hex_rgb(clarear(c, 0.35))
            out[sombra, :3] = hex_rgb(escurecer(c, 0.3))
    if contorno:
        viz = np.zeros_like(cheio)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            viz |= np.roll(np.roll(cheio, dy, 0), dx, 1)
        borda = viz & ~cheio
        if contorno == "auto":
            # contorno escuro da cor vizinha (estilo "selout" suave)
            soma = np.zeros((tamanho, tamanho, 3))
            cnt = np.zeros((tamanho, tamanho))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c2 = np.roll(np.roll(out[..., :3], dy, 0), dx, 1)
                m2 = np.roll(np.roll(cheio, dy, 0), dx, 1)
                soma += c2 * m2[..., None]
                cnt += m2
            media = soma / np.maximum(cnt, 1)[..., None]
            out[borda, :3] = media[borda] * 0.22 + np.array([0.06, 0.04, 0.1]) * 0.78
        else:
            out[borda, :3] = hex_rgb(contorno)
        out[borda, 3] = 1
    return Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA")


def _estrela_pts(cx, cy, R, r, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        a = np.radians(rot + i * 180 / n)
        rr = R if i % 2 == 0 else r
        pts.append((cx + np.cos(a) * rr, cy + np.sin(a) * rr))
    return pts


# Cada ícone: função (p) -> camadas. `p` traz as cores (padrões abaixo).
ICONES = {}


def icone_def(nome, descricao, **padrao):
    def deco(fn):
        ICONES[nome] = {"fn": fn, "padrao": padrao, "descricao": descricao}
        return fn
    return deco


@icone_def("moeda", "Moeda", cor="#f2c230")
def _moeda(p):
    c = p["cor"]
    return [(c, [("e", 2, 2, 14, 14)]), (escurecer(c, 0.25), [("eo", 4, 4, 12, 12)]), (clarear(c, 0.4), [("r", 7, 5, 9, 11)])]


@icone_def("gema", "Gema / diamante", cor="#3fd0e0")
def _gema(p):
    c = p["cor"]
    return [(c, [("p", [(8, 1.5), (14.5, 6), (8, 14.8), (1.5, 6)])]),
            (clarear(c, 0.3), [("p", [(8, 1.5), (14.5, 6), (1.5, 6)])]),
            (escurecer(c, 0.2), [("p", [(8, 6), (14.5, 6), (8, 14.8)])]),
            ("#ffffff", [("r", 5, 4, 7, 5)])]


@icone_def("coracao", "Coração (vida)", cor="#e43b44")
def _coracao(p):
    c = p["cor"]
    return [(c, [("e", 1.5, 2.5, 8.8, 9.8), ("e", 7.2, 2.5, 14.5, 9.8), ("p", [(2, 7.6), (14, 7.6), (8, 14.2)])]),
            (clarear(c, 0.6), [("r", 3.5, 4.5, 5.5, 6.5)])]


@icone_def("estrela", "Estrela", cor="#ffd23f")
def _estrela(p):
    c = p["cor"]
    return [(c, [("p", _estrela_pts(8, 8.6, 7.2, 3.1))]), (clarear(c, 0.5), [("r", 6, 6, 8, 8)])]


@icone_def("pocao", "Poção", cor="#d6336c", vidro="#cfe7ef", rolha="#8a5a32")
def _pocao(p):
    return [(p["vidro"], [("r", 6.5, 3, 9.5, 7), ("e", 2.5, 5.5, 13.5, 15.2)]),
            (p["cor"], [("c", 3.5, 6.5, 12.5, 14.5, -15, 195)]),
            (p["rolha"], [("r", 6, 1, 10, 3.5)]),
            ("#ffffff", [("r", 5, 8, 6, 10)])]


@icone_def("chave", "Chave", cor="#e0b13a")
def _chave(p):
    c = p["cor"]
    return [(c, [("e", 1, 4, 8.5, 11.5), ("r", 7.5, 6.8, 15, 9.2), ("r", 11, 9, 12.5, 12.5), ("r", 13.5, 9, 15, 11.5)]),
            (None, [("e", 3, 6, 6.5, 9.5)])]


@icone_def("espada", "Espada", cor="#c9d3dd", guarda="#c79a3a", cabo="#6b3f22")
def _espada(p):
    return [(p["cor"], [("p", [(13.6, 1.2), (14.8, 2.4), (6.6, 10.6), (5.4, 9.4)])]),
            (p["cabo"], [("l", [(5.2, 10.8), (2.6, 13.4)], 1.8)]),
            (p["guarda"], [("l", [(3.4, 8.6), (7.4, 12.6)], 1.9), ("e", 0.8, 12.8, 3.6, 15.4)])]


@icone_def("escudo", "Escudo", cor="#3a64c8", emblema="#f0d060")
def _escudo(p):
    return [(p["cor"], [("p", [(2, 1.8), (14, 1.8), (14, 8), (8, 14.8), (2, 8)])]),
            (p["emblema"], [("r", 7, 3.5, 9, 12), ("r", 3.8, 5.6, 12.2, 7.6)])]


@icone_def("bau", "Baú de tesouro", cor="#8a5228", metal="#d9b24a")
def _bau(p):
    c = p["cor"]
    return [(c, [("r", 1.5, 7, 14.5, 14.5)]),
            (clarear(c, 0.15), [("c", 1.5, 2, 14.5, 12, 180, 360)]),
            (p["metal"], [("r", 3, 3, 4.5, 14.5), ("r", 11.5, 3, 13, 14.5), ("r", 6.8, 6, 9.2, 10)])]


@icone_def("bomba", "Bomba", cor="#2b2d42", pavio="#b08850", faisca="#ffb030")
def _bomba(p):
    return [(p["cor"], [("e", 1.8, 4, 13.5, 15.5)]),
            ("#5c6070", [("r", 6, 2.6, 9.5, 5)]),
            (p["pavio"], [("l", [(8, 3), (10, 1.6), (11.5, 1.4)], 1)]),
            (p["faisca"], [("p", _estrela_pts(13, 1.8, 2.2, 0.9, 4, -45))]),
            ("#9aa0b5", [("e", 4, 6.5, 6.5, 9)])]


@icone_def("cogumelo", "Cogumelo", cor="#d93a3a", caule="#efe2c4", pintas="#ffffff")
def _cogumelo(p):
    return [(p["caule"], [("r", 5, 8, 11, 14.8)]),
            (p["cor"], [("c", 1, 1.8, 15, 14, 180, 360)]),
            (p["pintas"], [("e", 3.5, 4, 6, 6.5), ("e", 8.5, 3, 11, 5.5), ("e", 11.8, 5.6, 13.6, 7.4)])]


@icone_def("maca", "Maçã", cor="#d42b2b", folha="#4caf3a", cabo="#6b4222")
def _maca(p):
    return [(p["cor"], [("e", 1.8, 4, 14.2, 15.2)]),
            (p["cabo"], [("l", [(8, 5), (8.6, 1.6)], 1.2)]),
            (p["folha"], [("e", 9, 1.6, 13.4, 4.4)]),
            ("#ffffff", [("r", 4, 6.5, 5.5, 8.5)])]


@icone_def("pergaminho", "Pergaminho", cor="#e8d3a0", tinta="#6b4a2a")
def _pergaminho(p):
    c = p["cor"]
    return [(c, [("r", 3, 3, 13, 13)]),
            (escurecer(c, 0.15), [("e", 1.8, 1.4, 14.2, 4.6), ("e", 1.8, 11.4, 14.2, 14.6)]),
            (p["tinta"], [("r", 5, 6, 11, 6.9), ("r", 5, 8, 10, 8.9)])]


@icone_def("caveira", "Caveira", cor="#e9e4d4", olhos="#1e1622")
def _caveira(p):
    return [(p["cor"], [("e", 2, 1.5, 14, 12.2), ("r", 4.5, 10, 11.5, 14.8)]),
            (p["olhos"], [("e", 4, 5.5, 7.2, 9), ("e", 8.8, 5.5, 12, 9), ("p", [(8, 9.2), (7, 11), (9, 11)]),
                          ("r", 6.2, 12.6, 7, 14.8), ("r", 9, 12.6, 9.8, 14.8)])]


@icone_def("anel", "Anel", cor="#e3b341", gema="#e0304e")
def _anel(p):
    return [(p["cor"], [("e", 2, 5, 14, 15.2)]), (None, [("e", 4.6, 7.6, 11.4, 12.6)]),
            (p["gema"], [("e", 5.5, 1.4, 10.5, 6.6)])]


@icone_def("livro", "Livro / grimório", cor="#6b2fa3", paginas="#f1e9d2", detalhe="#e8c04a")
def _livro(p):
    c = p["cor"]
    return [(p["paginas"], [("r", 4, 3, 14.5, 14.2)]),
            (c, [("r", 2, 1.8, 12.8, 14.8)]),
            (escurecer(c, 0.25), [("r", 2, 1.8, 4, 14.8)]),
            (p["detalhe"], [("r", 6.5, 5.5, 10, 9)])]


@icone_def("machado", "Machado", cor="#c9d3dd", cabo="#7a4a26")
def _machado(p):
    return [(p["cabo"], [("r", 6.8, 2, 9, 15.4)]),
            (p["cor"], [("p", [(8.6, 2.4), (13.6, 0.8), (15.4, 6), (13.6, 10.2), (8.6, 7.4)])])]


@icone_def("cajado", "Cajado mágico", cor="#47c6ff", madeira="#7a4a26")
def _cajado(p):
    return [(p["madeira"], [("l", [(2.5, 14.8), (10.5, 5.2)], 1.7)]),
            (p["cor"], [("e", 9, 1, 14.8, 6.8)]),
            ("#ffffff", [("r", 10.5, 2.5, 12, 4)])]


@icone_def("chama", "Chama / fogo", cor="#ff7a1a", miolo="#ffd84a")
def _chama(p):
    return [(p["cor"], [("p", [(8, 0.8), (12.5, 6.5), (13.8, 10.5), (11.5, 14.6), (4.5, 14.6), (2.2, 10.5), (4, 6), (6, 8), (6.5, 3.5)])]),
            (p["miolo"], [("p", [(8.5, 6), (11, 10), (10, 13.5), (6, 13.5), (5, 10.8), (7, 9)])])]


@icone_def("raio", "Raio / energia", cor="#ffe14a")
def _raio(p):
    return [(p["cor"], [("p", [(10, 0.8), (3, 9), (7.5, 9), (5.5, 15.2), (13, 6.2), (8.5, 6.2), (10.8, 0.8)])])]


@icone_def("gota", "Gota (água, mana)", cor="#3a8fe0")
def _gota(p):
    return [(p["cor"], [("e", 3, 6, 13, 15.4), ("p", [(8, 0.8), (12.6, 9), (3.4, 9)])]), ("#ffffff", [("r", 5, 9, 6.5, 11.5)])]


@icone_def("folha", "Folha / erva", cor="#4caf3a")
def _folha(p):
    c = p["cor"]
    return [(c, [("p", [(2, 14), (3, 7), (7, 3), (14.5, 1.5), (13, 9), (9, 13)])]),
            (escurecer(c, 0.3), [("l", [(2.5, 13.5), (11, 5)], 1)])]


@icone_def("carne", "Carne / coxa", cor="#b8552e", osso="#efe6d0")
def _carne(p):
    return [(p["osso"], [("l", [(9, 9), (13.5, 13.5)], 2), ("e", 12, 11.5, 15, 14.5), ("e", 11.5, 12, 14.5, 15)]),
            (p["cor"], [("e", 1.2, 1.2, 11.5, 11.5)])]


@icone_def("bandeira", "Bandeira / checkpoint", cor="#e0344a", mastro="#9aa0b5")
def _bandeira(p):
    return [(p["mastro"], [("r", 3, 1, 4.6, 15.5)]), (p["cor"], [("p", [(4.6, 1.5), (14.5, 4.2), (4.6, 8.5)])])]


@icone_def("relogio", "Relógio / tempo", cor="#e8e0cc", aro="#c79a3a")
def _relogio(p):
    return [(p["aro"], [("e", 1.5, 1.5, 14.5, 14.5)]), (p["cor"], [("e", 3, 3, 13, 13)]),
            ("#2a2030", [("r", 7.4, 4.5, 8.6, 8.6), ("r", 7.4, 7.4, 11, 8.6)])]


def icone(nome, tamanho=16, contorno="auto", **cores):
    info = ICONES[nome]
    p = dict(info["padrao"])
    p.update(cores)
    return renderizar_camadas(info["fn"](p), tamanho, contorno)


# ----------------------------------------------------------------------------
# Geradores procedurais simétricos (naves, criaturas, invasores)
# ----------------------------------------------------------------------------
# 0 = vazio, 1 = corpo ou vazio, 2 = corpo ou borda, -1 = sempre borda
MOLDES = {
    "nave": [
        [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1], [0, 0, 0, 0, 1, -1], [0, 0, 0, 1, 1, -1],
        [0, 0, 0, 1, 1, -1], [0, 0, 1, 1, 1, -1], [0, 1, 1, 1, 2, 2], [0, 1, 1, 1, 2, 2],
        [0, 1, 1, 1, 2, 2], [0, 1, 1, 1, 1, -1], [0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 0, 0]],
    "criatura": [
        [0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1], [0, 0, 1, 1, 2, 2], [0, 0, 1, 2, 2, 2],
        [0, 1, 1, 2, 2, 2], [0, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2], [0, 1, 1, 1, 2, 2],
        [0, 0, 1, 1, 1, 1], [0, 0, 1, 1, 0, 0], [0, 1, 1, 0, 1, 1], [0, 1, 0, 0, 1, 0]],
    "invasor": [
        [0, 0, 1, 1], [0, 1, 1, 2], [1, 1, 2, 2], [1, 2, 2, 2], [1, 1, 1, 1], [0, 1, 1, 1], [1, 1, 0, 1], [1, 0, 0, 0]],
    "robo": [
        [0, 0, 1, 1, 1, 1], [0, 0, 1, 2, 2, 2], [0, 0, 1, 2, 2, 2], [0, 0, 0, 1, 1, 1],
        [1, 1, 1, 2, 2, 2], [1, 0, 1, 2, 2, 2], [1, 0, 1, 2, 2, 2], [0, 0, 1, 1, 1, 1],
        [0, 0, 1, 1, 0, 1], [0, 0, 1, 1, 0, 1], [0, 1, 1, 1, 0, 1], [0, 0, 0, 0, 0, 0]],
}


def gerar_simetrico(molde="nave", semente=0, cor=None, quadros=1, olhos=None):
    """Gera um sprite espelhado a partir de um molde. Retorna lista de imagens RGBA
    (um item por quadro de animação)."""
    rng = np.random.default_rng(semente)
    M = np.array(MOLDES[molde])
    h, w2 = M.shape
    if cor is None:
        matiz = rng.random()
        cor = rgb_hex(colorsys.hsv_to_rgb(matiz, 0.55 + rng.random() * 0.35, 0.75 + rng.random() * 0.2))
    cor2 = rgb_hex(colorsys.hsv_to_rgb((colorsys.rgb_to_hsv(*hex_rgb(cor))[0] + 0.45 + rng.random() * 0.2) % 1, 0.6, 0.9))
    if olhos is None:
        olhos = molde in ("criatura", "invasor", "robo")
    sorteio = rng.random(M.shape)
    sorteio2 = rng.random(M.shape)
    quadros_out = []
    for q in range(quadros):
        s1 = sorteio.copy()
        if q > 0:  # anima apenas as linhas de baixo (pernas/tentáculos/propulsores)
            r2 = np.random.default_rng(semente * 31 + q).random(M.shape)
            s1[-3:] = r2[-3:]
        corpo = np.zeros(M.shape, bool)
        borda = np.zeros(M.shape, bool)
        corpo |= (M == 1) & (s1 < 0.5)
        corpo |= (M == 2) & (s1 >= 0.5)
        borda |= (M == 2) & (s1 < 0.5)
        borda |= M == -1
        cheio_meio = np.concatenate([corpo, corpo[:, ::-1]], 1)
        borda_meio = np.concatenate([borda, borda[:, ::-1]], 1)
        Hh, W = cheio_meio.shape
        pad = 2
        tam = max(Hh, W) + pad * 2
        img = np.zeros((tam, tam, 4))
        oy, ox = (tam - Hh) // 2, (tam - W) // 2
        base, sec = hex_rgb(cor), hex_rgb(cor2)
        for y in range(Hh):
            for x in range(W):
                if cheio_meio[y, x]:
                    # gradiente vertical + leve variação: base no meio, secundária nas pontas
                    t = (np.sin(y / Hh * np.pi) * 0.6 + 0.4)
                    c = base * t + sec * (1 - t) * 0.6 + base * (1 - t) * 0.4
                    c = c * (0.85 + 0.3 * sorteio2[y, min(x, W - 1 - x)])
                    img[oy + y, ox + x] = [*np.clip(c, 0, 1), 1]
                elif borda_meio[y, x]:
                    img[oy + y, ox + x] = [*(base * 0.25 + 0.03), 1]
        cheio = img[..., 3] > 0
        viz = np.zeros_like(cheio)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            viz |= np.roll(np.roll(cheio, dy, 0), dx, 1)
        contorno = viz & ~cheio
        img[contorno] = [0.07, 0.05, 0.1, 1]
        # luz no topo
        topo = cheio & ~np.roll(cheio, 1, 0)
        img[topo & (img[..., :3].sum(-1) > 0.6), :3] = np.clip(img[topo & (img[..., :3].sum(-1) > 0.6), :3] * 1.25 + 0.05, 0, 1)
        if olhos:
            linhas = [y for y in range(2, Hh // 2 + 1) if cheio_meio[y, W // 2 - 2] or cheio_meio[y, W // 2 - 1]]
            if linhas:
                ey = linhas[len(linhas) // 2] if molde != "invasor" else min(linhas)
                ex = W // 2 - 2 if W >= 8 else W // 2 - 1
                for xx in (ex, W - 1 - ex):
                    img[oy + ey, ox + xx] = [1, 1, 1, 1]
                    if ey + 1 < Hh:
                        img[oy + ey + 1, ox + xx] = [0.1, 0.05, 0.15, 1]
        quadros_out.append(Image.fromarray((img * 255).astype(np.uint8), "RGBA"))
    return quadros_out


def folha_simetricos(molde="nave", semente=0, colunas=8, linhas=8, quadros=1, escala=1):
    """Gera uma folha (spritesheet) com colunas*linhas variações. Se quadros>1,
    cada variação ocupa `quadros` células lado a lado."""
    exemplo = gerar_simetrico(molde, 0)[0]
    t = exemplo.size[0]
    folha = Image.new("RGBA", (t * colunas * quadros, t * linhas), (0, 0, 0, 0))
    for j in range(linhas):
        for i in range(colunas):
            qs = gerar_simetrico(molde, semente * 10007 + j * colunas + i, quadros=quadros)
            for q, im in enumerate(qs):
                folha.paste(im, ((i * quadros + q) * t, j * t))
    if escala > 1:
        folha = folha.resize((folha.width * escala, folha.height * escala), Image.NEAREST)
    return folha


# ----------------------------------------------------------------------------
# Personagem 16x16 recolorível (frente, 4 quadros de caminhada)
# ----------------------------------------------------------------------------
_CORPO = [
    "................",
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "...KHHHHHHHHK...",
    "...KHHSSSSHHK...",
    "...KHSESSESHK...",
    "...KHSSSSSSHK...",
    "....KSSMMSSK....",
    ".....KKSSKK.....",
    "....KCCCCCCK....",
    "...KSKCCCCKSK...",
    "...KSKCCCCKSK...",
    "....KKPPPPKK....",
]
_PERNAS = [
    ["....KPPKKPPK....", "....KBBKKBBK....", "....KKKKKKKK...."],
    ["....KPPKKPPK....", "....KBBKKKKK....", "....KKKK........"],
    ["....KPPKKPPK....", "....KBBKKBBK....", "....KKKKKKKK...."],
    ["....KPPKKPPK....", "....KKKKKBBK....", "........KKKK...."],
]
PALETAS_PERSONAGEM = {
    "pele": ["#f5d0b0", "#e0ac84", "#c68660", "#8d5a3b", "#5c3a24"],
    "cabelo": ["#2b1d14", "#5a3620", "#c58b3a", "#e8d070", "#b8402c", "#d8d8e0", "#3a6ad8", "#d65aa8"],
    "roupa": ["#3a64c8", "#c83a3a", "#3aa856", "#d8a83a", "#8a3ac8", "#3ab8c8", "#444a58", "#e07030"],
    "calca": ["#2c3a5c", "#4a3424", "#2e2e34", "#5c5c64", "#3c5a2c"],
    "bota": ["#3a2418", "#1e1e24", "#6a4a2a"],
}


def personagem(semente=0, pele=None, cabelo=None, roupa=None, calca=None, bota=None, olhos="#1e1622",
               boca="#a05050", contorno="#1a1420"):
    """Retorna lista de 4 quadros (16x16) de um personagem de frente andando."""
    rng = np.random.default_rng(semente)
    esc = lambda k: PALETAS_PERSONAGEM[k][rng.integers(0, len(PALETAS_PERSONAGEM[k]))]
    cores = {"S": pele or esc("pele"), "H": cabelo or esc("cabelo"), "C": roupa or esc("roupa"),
             "P": calca or esc("calca"), "B": bota or esc("bota"), "E": olhos, "M": boca, "K": contorno}
    quadros = []
    for k in range(4):
        linhas = _CORPO + _PERNAS[k]
        bob = 1 if k in (1, 3) else 0
        img = np.zeros((16, 16, 4), np.uint8)
        for y, linha in enumerate(linhas):
            yy = y + bob
            if yy >= 16:
                continue
            for x, ch in enumerate(linha):
                if ch in cores:
                    c = hex_rgb(cores[ch])
                    if ch in "HSCPB" and y + 1 < len(linhas) and (x == 0 or linha[x - 1] == "K"):
                        c = hex_rgb(clarear(cores[ch], 0.3))
                    elif ch in "HSCPB" and x + 1 < 16 and linha[x + 1] == "K":
                        c = hex_rgb(escurecer(cores[ch], 0.25))
                    img[yy, x] = [*(c * 255).astype(np.uint8), 255]
        quadros.append(Image.fromarray(img, "RGBA"))
    return quadros
