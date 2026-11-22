"""Utilidades de cor: hex, rampas (gradientes), ajustes, paletas e pixelização."""
import colorsys
import numpy as np
from PIL import Image


def hex_rgb(h):
    """'#ff8800' ou 'f80' -> array float [r, g, b] em [0, 1]."""
    if isinstance(h, (list, tuple, np.ndarray)):
        a = np.asarray(h, dtype=np.float64)
        return a / 255.0 if a.max() > 1 else a
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255.0


def rgb_hex(c):
    c = np.clip(np.asarray(c) * 255 + 0.5, 0, 255).astype(int)
    return "#%02x%02x%02x" % tuple(c[:3])


def rampa(t, cores):
    """Mapeia t (array em [0,1]) para cores. `cores` é lista de hex (espaçadas
    igualmente) ou de pares [posição, hex]."""
    if not isinstance(cores[0], (list, tuple)) or isinstance(cores[0], str):
        cores = [(i / (len(cores) - 1), c) for i, c in enumerate(cores)]
    pos = np.array([p for p, _ in cores], dtype=np.float64)
    rgb = np.array([hex_rgb(c) for _, c in cores])
    t = np.clip(t, 0, 1)
    out = np.empty(t.shape + (3,))
    for k in range(3):
        out[..., k] = np.interp(t, pos, rgb[:, k])
    return out


def misturar(a, b, t):
    t = np.asarray(t)
    if t.ndim == a.ndim - 1:
        t = t[..., None]
    return a * (1 - t) + b * t


def cor_solida(shape, h):
    return np.broadcast_to(hex_rgb(h), tuple(shape) + (3,)).copy()


def ajustar(img, matiz=0.0, saturacao=1.0, brilho=1.0, contraste=1.0):
    """Ajuste HSV/contraste em imagem float (H,W,3). matiz em graus."""
    out = img
    if matiz or saturacao != 1.0:
        r, g, b = out[..., 0], out[..., 1], out[..., 2]
        mx, mn = np.max(out, -1), np.min(out, -1)
        lum = (mx + mn) / 2
        cinza = np.stack([lum] * 3, -1)
        out = cinza + (out - cinza) * saturacao
        if matiz:
            a = np.radians(matiz)
            # rotação de matiz no espaço YIQ
            yiq = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]])
            rot = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            m = np.linalg.inv(yiq) @ rot @ yiq
            out = out @ m.T
    out = (out - 0.5) * contraste + 0.5
    return np.clip(out * brilho, 0, 1)


def variar_hex(h, dh=0.0, ds=0.0, dv=0.0):
    r, g, b = hex_rgb(h)
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    return rgb_hex(colorsys.hsv_to_rgb((hh + dh) % 1.0, min(1, max(0, s + ds)), min(1, max(0, v + dv))))


def para_uint8(img):
    return np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)


def para_imagem(img, alfa=None):
    if img.ndim == 2:
        return Image.fromarray(para_uint8(img), "L")
    if alfa is not None:
        img = np.concatenate([img, alfa[..., None]], -1)
        return Image.fromarray(para_uint8(img), "RGBA")
    return Image.fromarray(para_uint8(img), "RGB" if img.shape[-1] == 3 else "RGBA")


def pixelizar(im, tamanho=32, cores=16, dither=False):
    """Reduz uma imagem para pixel art: redimensiona (média) e limita a paleta."""
    pequeno = im.convert("RGB").resize((tamanho, tamanho), Image.BOX)
    q = pequeno.quantize(colors=cores, method=Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
    return q.convert("RGB")


# Algumas paletas populares/neutras para pixel art (livres para uso).
PALETAS = {
    "pico8": ["#000000", "#1d2b53", "#7e2553", "#008751", "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8",
              "#ff004d", "#ffa300", "#ffec27", "#00e436", "#29adff", "#83769c", "#ff77a8", "#ffccaa"],
    "gameboy": ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"],
    "cinza": ["#000000", "#333333", "#666666", "#999999", "#cccccc", "#ffffff"],
    "terra": ["#2b1d14", "#4a3020", "#6e4a2e", "#94693f", "#b88f5a", "#d9b98a", "#3a4a24", "#5b7334", "#86a04a"],
}


def aplicar_paleta(im, paleta):
    """Converte uma imagem PIL para a paleta dada (lista de hex), sem dither."""
    pal = []
    for h in paleta:
        pal.extend(int(x * 255 + 0.5) for x in hex_rgb(h))
    pal += pal[:3] * (256 - len(paleta))
    pim = Image.new("P", (1, 1))
    pim.putpalette(pal)
    rgba = im.convert("RGBA")
    q = rgba.convert("RGB").quantize(palette=pim, dither=Image.Dither.NONE).convert("RGBA")
    q.putalpha(rgba.getchannel("A"))
    return q
