"""Ruídos procedurais *periódicos* (tileáveis): Perlin, fBm, ridged, Worley e warp.

Todas as funções recebem coordenadas normalizadas (u, v) em [0, 1) e uma
frequência inteira. Como a rede de gradientes se repete a cada `freq` células,
o resultado emenda perfeitamente nas bordas (textura sem costura).
"""
import numpy as np


def grade(largura, altura=None):
    """Coordenadas (u, v) de cada pixel, em [0, 1)."""
    altura = altura or largura
    u = np.arange(largura) / largura
    v = np.arange(altura) / altura
    return np.meshgrid(u, v)


def _freq(freq):
    if np.isscalar(freq):
        return int(freq), int(freq)
    return int(freq[0]), int(freq[1])


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin(u, v, freq=4, semente=0):
    """Ruído Perlin de gradiente, saída aproximadamente em [-1, 1]."""
    fx, fy = _freq(freq)
    rng = np.random.default_rng(semente)
    ang = rng.random((fy, fx)) * 2 * np.pi
    gx, gy = np.cos(ang), np.sin(ang)
    X, Y = u * fx, v * fy
    x0, y0 = np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64)
    tx, ty = X - x0, Y - y0
    xa, xb = x0 % fx, (x0 + 1) % fx
    ya, yb = y0 % fy, (y0 + 1) % fy
    n00 = gx[ya, xa] * tx + gy[ya, xa] * ty
    n10 = gx[ya, xb] * (tx - 1) + gy[ya, xb] * ty
    n01 = gx[yb, xa] * tx + gy[yb, xa] * (ty - 1)
    n11 = gx[yb, xb] * (tx - 1) + gy[yb, xb] * (ty - 1)
    sx, sy = _fade(tx), _fade(ty)
    a = n00 + sx * (n10 - n00)
    b = n01 + sx * (n11 - n01)
    return np.clip((a + sy * (b - a)) * 1.41421356, -1, 1)


def valor(u, v, freq=4, semente=0):
    """Ruído de valor (blocos suavizados), saída em [0, 1]."""
    fx, fy = _freq(freq)
    rng = np.random.default_rng(semente)
    tab = rng.random((fy, fx))
    X, Y = u * fx, v * fy
    x0, y0 = np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64)
    sx, sy = _fade(X - x0), _fade(Y - y0)
    xa, xb, ya, yb = x0 % fx, (x0 + 1) % fx, y0 % fy, (y0 + 1) % fy
    a = tab[ya, xa] + sx * (tab[ya, xb] - tab[ya, xa])
    b = tab[yb, xa] + sx * (tab[yb, xb] - tab[yb, xa])
    return a + sy * (b - a)


def fbm(u, v, freq=4, oitavas=5, ganho=0.5, lacunaridade=2, semente=0, tipo="perlin"):
    """Soma fractal de oitavas. tipo: 'perlin', 'ridged' ou 'turbulencia'.
    Saída: perlin -> [-1, 1]; ridged/turbulencia -> [0, 1]."""
    fx, fy = _freq(freq)
    lac = max(1, int(round(lacunaridade)))  # inteiro para continuar tileável
    total = np.zeros_like(u, dtype=np.float64)
    amp, soma = 1.0, 0.0
    for i in range(int(oitavas)):
        n = perlin(u, v, (fx, fy), semente + i * 1013)
        if tipo == "ridged":
            n = (1 - np.abs(n)) ** 2
        elif tipo == "turbulencia":
            n = np.abs(n)
        total += n * amp
        soma += amp
        amp *= ganho
        fx, fy = fx * lac, fy * lac
    return total / soma


def worley(u, v, freq=6, semente=0, jitter=1.0, pontos=None, metrica="euclidiana"):
    """Ruído celular (Voronoi). Retorna dict com f1, f2 (distâncias em unidades
    de célula), id (inteiro por célula) e (px, py) do ponto mais próximo."""
    fx, fy = _freq(freq)
    if pontos is None:
        rng = np.random.default_rng(semente)
        pontos = rng.random((fy, fx, 2)) * jitter + (1 - jitter) / 2
    X, Y = u * fx, v * fy
    cx, cy = np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64)
    f1 = np.full(X.shape, np.inf)
    f2 = np.full(X.shape, np.inf)
    ident = np.zeros(X.shape, dtype=np.int64)
    qx = np.zeros(X.shape)
    qy = np.zeros(X.shape)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            nx, ny = cx + ox, cy + oy
            ix, iy = nx % fx, ny % fy
            px = nx + pontos[iy, ix, 0]
            py = ny + pontos[iy, ix, 1]
            dx, dy = X - px, Y - py
            if metrica == "manhattan":
                d = np.abs(dx) + np.abs(dy)
            elif metrica == "chebyshev":
                d = np.maximum(np.abs(dx), np.abs(dy))
            else:
                d = np.sqrt(dx * dx + dy * dy)
            m = d < f1
            f2 = np.where(m, f1, np.minimum(f2, d))
            ident = np.where(m, iy * fx + ix, ident)
            qx = np.where(m, px, qx)
            qy = np.where(m, py, qy)
            f1 = np.where(m, d, f1)
    return {"f1": f1, "f2": f2, "id": ident, "px": qx / fx, "py": qy / fy}


def warp(u, v, forca=0.1, freq=3, oitavas=3, semente=0):
    """Distorce as coordenadas com fBm (domain warping) — mantém o tiling."""
    du = fbm(u, v, freq, oitavas, semente=semente + 71)
    dv = fbm(u, v, freq, oitavas, semente=semente + 137)
    return u + du * forca, v + dv * forca


def aleatorio_celula(ident, semente=0, n=1):
    """Valor pseudoaleatório estável em [0,1) para cada id de célula."""
    h = (ident.astype(np.uint64) * np.uint64(2654435761) + np.uint64(semente * 97531 + 12345 * n))
    h ^= h >> np.uint64(13)
    h *= np.uint64(1274126177)
    h ^= h >> np.uint64(16)
    return (h % np.uint64(1 << 24)).astype(np.float64) / float(1 << 24)


def normalizar(a):
    lo, hi = float(np.min(a)), float(np.max(a))
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def suave(a, b, x):
    """smoothstep(a, b, x)."""
    t = np.clip((x - a) / (b - a + 1e-12), 0, 1)
    return t * t * (3 - 2 * t)
