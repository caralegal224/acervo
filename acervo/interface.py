"""Elementos de interface (UI) em pixel art: painéis 9-slice, botões, barras,
caixas de seleção, slots e sliders — em vários estilos.

Todo painel é desenhado de forma que as bordas tenham `margem` pixels: use esse
valor como margem do 9-slice (NinePatchRect no Godot, Sprite Border na Unity...).
"""
import numpy as np
from PIL import Image

from .cor import hex_rgb
from .sprites import clarear, escurecer

ESTILOS = {
    "madeira": dict(borda="#24150c", moldura="#8a5a30", fundo="#c79a64", raio=3, textura=0.08, rebites=False, chanfro=False),
    "pedra": dict(borda="#1c1c22", moldura="#6c6c78", fundo="#9a9aa6", raio=2, textura=0.1, rebites=False, chanfro=False),
    "metal": dict(borda="#14161c", moldura="#8a94a6", fundo="#4a5262", raio=1, textura=0.03, rebites=True, chanfro=False),
    "pergaminho": dict(borda="#3a2414", moldura="#a8743a", fundo="#ecd9aa", raio=4, textura=0.05, rebites=False, chanfro=False),
    "scifi": dict(borda="#04121c", moldura="#1fb8d8", fundo="#0c2a3c", raio=5, textura=0.0, rebites=False, chanfro=True),
    "doce": dict(borda="#5a1a3a", moldura="#ff7ab8", fundo="#ffe0ef", raio=6, textura=0.0, rebites=False, chanfro=False),
    "escuro": dict(borda="#05060a", moldura="#3a3f52", fundo="#1c1f2a", raio=2, textura=0.0, rebites=False, chanfro=False),
    "floresta": dict(borda="#0f1f0c", moldura="#4f7a2a", fundo="#d8cfa0", raio=3, textura=0.05, rebites=False, chanfro=False),
}


def _mascara(w, h, raio, chanfro, recuo=0):
    y, x = np.mgrid[0:h, 0:w].astype(float) + 0.5
    x0, y0, x1, y1 = recuo, recuo, w - recuo, h - recuo
    r = max(0, raio - recuo * 0.5)
    dx = np.maximum(np.maximum(x0 + r - x, x - (x1 - r)), 0)
    dy = np.maximum(np.maximum(y0 + r - y, y - (y1 - r)), 0)
    dentro = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    if r <= 0:
        return dentro
    if chanfro:
        return dentro & (dx + dy <= r)
    return dentro & (dx * dx + dy * dy <= r * r + 0.25)


def painel(largura=48, altura=48, estilo="madeira", estado="normal", moldura=4, semente=0, **sobrescrever):
    """estado: 'normal', 'foco' (hover) ou 'pressionado'."""
    e = dict(ESTILOS[estilo])
    e.update(sobrescrever)
    w, h = int(largura), int(altura)
    img = np.zeros((h, w, 4))
    mold = e["moldura"]
    fundo = e["fundo"]
    if estado == "foco":
        mold, fundo = clarear(mold, 0.25), clarear(fundo, 0.15)
    elif estado == "pressionado":
        mold, fundo = escurecer(mold, 0.15), escurecer(fundo, 0.12)
    m0 = _mascara(w, h, e["raio"], e["chanfro"], 0)
    m1 = _mascara(w, h, e["raio"], e["chanfro"], 1)
    m2 = _mascara(w, h, e["raio"], e["chanfro"], moldura)
    m3 = _mascara(w, h, e["raio"], e["chanfro"], moldura + 1)
    img[m0] = [*hex_rgb(e["borda"]), 1]
    img[m1] = [*hex_rgb(mold), 1]
    # bisel da moldura
    cima = m1 & ~np.roll(m1, 1, 0)
    esq = m1 & ~np.roll(m1, 1, 1)
    baixo = m1 & ~np.roll(m1, -1, 0)
    dir_ = m1 & ~np.roll(m1, -1, 1)
    claro, escuro = hex_rgb(clarear(mold, 0.4)), hex_rgb(escurecer(mold, 0.35))
    if estado == "pressionado":
        claro, escuro = escuro, claro
    img[cima | esq] = [*claro, 1]
    img[(baixo | dir_) & ~(cima | esq)] = [*escuro, 1]
    img[m2] = [*hex_rgb(e["borda"]), 1] if not e["chanfro"] else [*hex_rgb(escurecer(mold, 0.5)), 1]
    rng = np.random.default_rng(semente)
    f = hex_rgb(fundo)
    ruido = (rng.random((h, w)) - 0.5) * e["textura"] * 2
    if e["textura"] > 0:
        listras = np.sin(np.arange(h)[:, None] * 0.9 + rng.random() * 6) * e["textura"] * 0.6 if estilo == "madeira" else 0
        ruido = ruido + listras
    corf = np.clip(f + ruido[..., None], 0, 1)
    img[m3, :3] = corf[m3]
    img[m3, 3] = 0.92 if estilo == "scifi" else 1
    # sombra interna (topo/esquerda do fundo)
    sombra_int = m3 & (~np.roll(m3, 1, 0) | ~np.roll(m3, 1, 1))
    if estado != "pressionado":
        img[sombra_int, :3] = np.clip(img[sombra_int, :3] * 0.85, 0, 1)
    else:
        img[sombra_int, :3] = np.clip(img[sombra_int, :3] * 0.7, 0, 1)
    if e["rebites"] and moldura >= 3:
        c = moldura // 2
        for (x, y) in ((c, c), (w - 1 - c, c), (c, h - 1 - c), (w - 1 - c, h - 1 - c)):
            img[y, x] = [*hex_rgb(clarear(e["moldura"], 0.7)), 1]
            if x + 1 < w and y + 1 < h:
                img[y + 1, x + 1] = [*hex_rgb(escurecer(e["moldura"], 0.5)), 1]
    if e["chanfro"]:
        # detalhe luminoso nos cantos
        img[(m1 & ~m2) & (cima | esq), :3] = hex_rgb(clarear(mold, 0.6))
    return Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA")


def barra(largura=96, altura=12, cor="#e43b44", estilo="escuro", preenchimento=1.0):
    """Barra de progresso: retorna (moldura_vazia, preenchimento) como imagens
    separadas — estique o preenchimento na engine conforme o valor."""
    e = ESTILOS[estilo]
    fundo = painel(largura, altura, estilo, moldura=2)
    w, h = largura - 4, altura - 4
    fill = np.zeros((h, w, 4))
    c = hex_rgb(cor)
    for y in range(h):
        t = y / max(1, h - 1)
        k = 1.25 - 0.5 * t if y > 0 else 1.5
        fill[y, :, :3] = np.clip(c * k, 0, 1)
    fill[..., 3] = 1
    fill[h - 1, :, :3] = hex_rgb(escurecer(cor, 0.35))
    preench = Image.fromarray((fill * 255).astype(np.uint8), "RGBA")
    if preenchimento < 1:
        exemplo = fundo.copy()
        n = int(w * preenchimento)
        if n > 0:
            exemplo.alpha_composite(preench.crop((0, 0, n, h)), (2, 2))
        return fundo, preench, exemplo
    exemplo = fundo.copy()
    exemplo.alpha_composite(preench, (2, 2))
    return fundo, preench, exemplo


def caixa_selecao(tamanho=12, estilo="madeira", marcada=False, cor_marca="#3ad26a"):
    im = painel(tamanho, tamanho, estilo, moldura=2)
    if marcada:
        a = np.array(im).astype(float) / 255
        c = hex_rgb(cor_marca)
        pts = [(3, 6), (4, 7), (5, 8), (6, 7), (7, 6), (8, 5), (9, 4)]
        s = tamanho / 12
        for (x, y) in pts:
            for dy in range(int(np.ceil(s * 1.5))):
                xx, yy = int(x * s), int(y * s) + dy
                if 0 <= xx < tamanho and 0 <= yy < tamanho:
                    a[yy, xx] = [*c, 1]
                    if xx + 1 < tamanho:
                        a[yy, xx + 1] = [*c, 1]
        im = Image.fromarray((a * 255).astype(np.uint8), "RGBA")
    return im


def slot(tamanho=24, estilo="escuro", selecionado=False):
    im = painel(tamanho, tamanho, estilo, "pressionado", moldura=2)
    if selecionado:
        a = np.array(im)
        a[0, :] = a[-1, :] = a[:, 0] = a[:, -1] = [255, 230, 90, 255]
        im = Image.fromarray(a, "RGBA")
    return im


def slider(largura=96, estilo="metal"):
    trilho = painel(largura, 6, estilo, "pressionado", moldura=1)
    botao = painel(10, 14, estilo, moldura=2)
    return trilho, botao


def ampliar(im, escala):
    return im.resize((im.width * escala, im.height * escala), Image.NEAREST) if escala > 1 else im
