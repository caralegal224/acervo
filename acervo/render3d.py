"""Rasterizador de software minúsculo (numpy) para gerar miniaturas PNG dos modelos."""
import numpy as np
from PIL import Image


def renderizar(m, tamanho=256, fundo=(0, 0, 0, 0), azimute=0.6, elevacao=0.45, superamostra=2):
    S = tamanho * superamostra
    V = m.V.copy()
    lo, hi = V.min(0), V.max(0)
    centro = (lo + hi) / 2
    V -= centro
    ca, sa = np.cos(azimute), np.sin(azimute)
    ce, se = np.cos(elevacao), np.sin(elevacao)
    Ry = np.array([[ca, 0, -sa], [0, 1, 0], [sa, 0, ca]])
    Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    R = Rx @ Ry
    P = V @ R.T
    N = m.N @ R.T
    raio = np.max(np.abs(P[:, :2])) * 1.12 + 1e-9
    xs = (P[:, 0] / raio * 0.5 + 0.5) * S
    ys = (0.5 - P[:, 1] / raio * 0.5) * S
    zs = P[:, 2]
    zbuf = np.full((S, S), -np.inf)
    cor = np.zeros((S, S, 3))
    alfa = np.zeros((S, S))
    luz = np.array([-0.4, 0.75, 0.55])
    luz /= np.linalg.norm(luz)
    tex = None
    if m.textura is not None and m.UV is not None:
        tex = np.asarray(m.textura.convert("RGB"), float) / 255
    base = np.ones((len(V), 3)) * np.asarray(m.cor_base) if m.C is None else m.C * np.asarray(m.cor_base)
    for f in m.F:
        a, b, c = f
        x0, y0, x1, y1, x2, y2 = xs[a], ys[a], xs[b], ys[b], xs[c], ys[c]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area >= 0:  # descarta faces de costas (sentido anti-horário visto de frente)
            continue
        minx, maxx = int(max(0, np.floor(min(x0, x1, x2)))), int(min(S - 1, np.ceil(max(x0, x1, x2))))
        miny, maxy = int(max(0, np.floor(min(y0, y1, y2)))), int(min(S - 1, np.ceil(max(y0, y1, y2))))
        if minx > maxx or miny > maxy:
            continue
        py, px = np.mgrid[miny:maxy + 1, minx:maxx + 1] + 0.5
        w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area
        w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area
        w2 = 1 - w0 - w1
        dentro = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not dentro.any():
            continue
        z = w0 * zs[a] + w1 * zs[b] + w2 * zs[c]
        sub_z = zbuf[miny:maxy + 1, minx:maxx + 1]
        vis = dentro & (z > sub_z)
        if not vis.any():
            continue
        n = w0[..., None] * N[a] + w1[..., None] * N[b] + w2[..., None] * N[c]
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
        dif = np.clip(n @ luz, 0, 1)
        if tex is not None:
            uv = w0[..., None] * m.UV[a] + w1[..., None] * m.UV[b] + w2[..., None] * m.UV[c]
            th, tw = tex.shape[:2]
            tx = (np.mod(uv[..., 0], 1) * (tw - 1)).astype(int)
            ty = ((1 - np.mod(uv[..., 1], 1)) * (th - 1)).astype(int)
            alb = tex[ty, tx]
        else:
            alb = w0[..., None] * base[a] + w1[..., None] * base[b] + w2[..., None] * base[c]
        shade = alb * (0.32 + 0.78 * dif[..., None]) + 0.04 * (n[..., 1:2] * 0.5 + 0.5)
        sub_z[vis] = z[vis]
        cor[miny:maxy + 1, minx:maxx + 1][vis] = shade[vis]
        alfa[miny:maxy + 1, minx:maxx + 1][vis] = 1
    img = np.concatenate([np.clip(cor, 0, 1), alfa[..., None]], -1)
    im = Image.fromarray((img * 255).astype(np.uint8), "RGBA")
    return im.resize((tamanho, tamanho), Image.LANCZOS)
