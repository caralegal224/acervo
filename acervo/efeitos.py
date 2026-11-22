"""Partículas e animações de efeitos (explosão, fogo, fumaça, magia, impacto...).

As partículas são geradas em BRANCO com transparência, para você tingir com
qualquer cor na engine (multiplicação de cor). As animações saem coloridas,
como spritesheet horizontal (todos os quadros lado a lado).
"""
import numpy as np
from PIL import Image

from .ruido import grade, fbm, worley, perlin, suave, normalizar
from .cor import rampa, para_imagem


def _polar(n):
    u, v = grade(n)
    x, y = (u - 0.5 + 0.5 / n) * 2, (v - 0.5 + 0.5 / n) * 2
    return x, y, np.sqrt(x * x + y * y), np.arctan2(y, x)


def _branco(a):
    a = np.clip(a, 0, 1)
    return Image.fromarray((np.stack([np.ones_like(a)] * 3 + [a], -1) * 255 + 0.5).astype(np.uint8), "RGBA")


PARTICULAS = {}


def particula_def(nome, descricao):
    def deco(fn):
        PARTICULAS[nome] = {"fn": fn, "descricao": descricao}
        return fn
    return deco


@particula_def("circulo_suave", "Disco com borda suave (base para quase tudo).")
def _p_circulo(n, s):
    x, y, r, a = _polar(n)
    return _branco((1 - suave(0.0, 1.0, r)) ** 1.5)


@particula_def("brilho", "Brilho com raios em cruz (lens flare/estrela).")
def _p_brilho(n, s):
    x, y, r, a = _polar(n)
    nucleo = np.exp(-r * r * 40)
    raios = np.exp(-np.abs(x) * 30) * np.exp(-np.abs(y) * 2.2) + np.exp(-np.abs(y) * 30) * np.exp(-np.abs(x) * 2.2)
    diag = (np.exp(-np.abs(x - y) * 40) + np.exp(-np.abs(x + y) * 40)) * np.exp(-r * 4) * 0.4
    return _branco(nucleo + raios * 0.8 + diag + np.exp(-r * 6) * 0.3)


@particula_def("faisca", "Risco alongado (faísca, tiro, chuva).")
def _p_faisca(n, s):
    x, y, r, a = _polar(n)
    return _branco(np.exp(-(x * x) * 400) * (1 - suave(0.0, 1.0, np.abs(y))) ** 2)


@particula_def("anel", "Anel (onda de choque, seleção).")
def _p_anel(n, s):
    x, y, r, a = _polar(n)
    return _branco(np.exp(-((r - 0.75) ** 2) * 300))


@particula_def("fumaca", "Puff de fumaça/nuvem com bordas irregulares.")
def _p_fumaca(n, s):
    u, v = grade(n)
    x, y, r, a = _polar(n)
    nz = fbm(u, v, 4, 5, semente=s) * 0.5 + 0.5
    return _branco((1 - suave(0.3, 1.0, r + (nz - 0.5) * 0.6)) * (0.6 + 0.4 * nz))


@particula_def("estrela", "Estrela de 5 pontas suave.")
def _p_estrela(n, s):
    from PIL import ImageDraw
    k = 4
    im = Image.new("L", (n * k, n * k), 0)
    pts = []
    for i in range(10):
        ang = np.radians(-90 + i * 36)
        rr = (0.48 if i % 2 == 0 else 0.2) * n * k
        pts.append((n * k / 2 + np.cos(ang) * rr, n * k / 2 + 0.04 * n * k + np.sin(ang) * rr))
    ImageDraw.Draw(im).polygon(pts, fill=255)
    a = np.asarray(im.resize((n, n), Image.LANCZOS), dtype=float) / 255
    return _branco(a)


@particula_def("bolha", "Bolha (borda clara e centro translúcido).")
def _p_bolha(n, s):
    x, y, r, a = _polar(n)
    borda = np.exp(-((r - 0.85) ** 2) * 200)
    reflexo = np.exp(-((x + 0.35) ** 2 + (y + 0.35) ** 2) * 60)
    return _branco(np.where(r < 0.95, 0.12, 0) + borda * 0.8 + reflexo)


@particula_def("gota", "Gota d'água.")
def _p_gota(n, s):
    x, y, r, a = _polar(n)
    yy = -y
    forma = np.sqrt(x * x / np.clip((1 - yy) / 2, 0.01, 1) ** 1.2 + (yy - 0.25) ** 2 * 1.6)
    return _branco(1 - suave(0.55, 0.65, forma))


@particula_def("fagulha", "Ponto quente com halo (brasa, vagalume).")
def _p_fagulha(n, s):
    x, y, r, a = _polar(n)
    return _branco(np.exp(-r * r * 60) + np.exp(-r * 5) * 0.35)


@particula_def("folha", "Folha (outono, vento).")
def _p_folha(n, s):
    x, y, r, a = _polar(n)
    c, sn = np.cos(0.6), np.sin(0.6)
    xr, yr = x * c - y * sn, x * sn + y * c
    forma = (xr / 0.9) ** 2 + (yr / 0.42) ** 2
    nerv = np.exp(-yr * yr * 600) * (np.abs(xr) < 0.85)
    return _branco((1 - suave(0.85, 1.0, forma)) * (1 - nerv * 0.5))


@particula_def("raio", "Raio elétrico ramificado.")
def _p_raio(n, s):
    rng = np.random.default_rng(s)
    im = np.zeros((n, n))
    def galho(x, y, ang, comp, larg):
        pts = []
        for _ in range(int(comp)):
            ang += rng.normal(0, 0.5)
            x += np.cos(ang) * 2
            y += np.sin(ang) * 2
            pts.append((x, y))
            if rng.random() < 0.04 and larg > 0.6:
                galho(x, y, ang + rng.choice([-0.8, 0.8]), comp * 0.4, larg * 0.6)
        for px, py in pts:
            ix, iy = int(px), int(py)
            if 0 <= ix < n and 0 <= iy < n:
                im[iy, ix] = max(im[iy, ix], larg)
    galho(n / 2, 0, np.pi / 2, n / 2, 1.0)
    from .texturas import desfocar
    return _branco(np.clip(im + desfocar(im, 1.2) * 4 + desfocar(im, 4) * 6, 0, 1))


def particula(nome, tamanho=64, semente=0):
    return PARTICULAS[nome]["fn"](int(tamanho), int(semente))


# ----------------------------------------------------------------------------
# Animações (spritesheets)
# ----------------------------------------------------------------------------
ANIMACOES = {}


def animacao_def(nome, descricao, **padrao):
    def deco(fn):
        ANIMACOES[nome] = {"fn": fn, "padrao": padrao, "descricao": descricao}
        return fn
    return deco


def _rgba(cor, alfa):
    return np.concatenate([cor, np.clip(alfa, 0, 1)[..., None]], -1)


@animacao_def("explosao", "Explosão com bola de fogo e fumaça.",
              cores=["#2a1a14", "#5a2a14", "#c23a0a", "#ff8a1a", "#ffd34a", "#fff6d0"])
def _a_explosao(n, quadros, s, p):
    u, v = grade(n)
    x, y, r, a = _polar(n)
    out = []
    for q in range(quadros):
        t = q / max(1, quadros - 1)
        raio = 0.38 + 0.6 * (1 - (1 - t) ** 2.2)
        nz = fbm(u, v, 3, 5, semente=s + q * 3) * 0.5 + 0.5
        nz2 = fbm(u, v, 5, 4, semente=s + 100) * 0.5 + 0.5
        d = r / raio + (nz - 0.5) * 0.55
        dens = 1 - suave(0.55, 1.0, d)
        calor = np.clip((1 - d * 0.9) * (1 - t * 1.25) * 1.6 + nz2 * 0.2 - 0.1, 0, 1)
        cor = rampa(calor, p["cores"])
        buraco = suave(0.2, 0.9, t) * (1 - suave(0.0, 0.6, d + (nz - 0.5) * 0.5))
        alfa = dens * (1 - buraco * 0.9) * (1 - suave(0.7, 1.0, t))
        out.append(_rgba(cor, alfa))
    return out


@animacao_def("fogo", "Fogo em loop (fogueira, tocha).",
              cores=["#3a0a00", "#a21e00", "#ff5a0a", "#ffa21a", "#ffe58a", "#ffffff"])
def _a_fogo(n, quadros, s, p):
    u, v = grade(n)
    out = []
    for q in range(quadros):
        fase = q / quadros
        # rolagem vertical periódica -> loop perfeito
        vv = (v + fase) % 1.0
        nz = fbm(u, vv, (4, 4), 5, semente=s) * 0.5 + 0.5
        nz2 = fbm(u, (v + fase * 2) % 1.0, (6, 6), 4, semente=s + 9) * 0.5 + 0.5
        x = (u - 0.5) * 2
        forma = (1 - np.abs(x) * (1.25 + (1 - v) * 1.6)) * (v ** 0.7)
        intens = np.clip(forma * 1.35 + (nz * 0.7 + nz2 * 0.3 - 0.55) * 1.2, 0, 1)
        cor = rampa(intens, p["cores"])
        out.append(_rgba(cor, suave(0.08, 0.35, intens)))
    return out


@animacao_def("fumaca", "Fumaça subindo e se dissipando.", cores=["#2b2b2e", "#55555a", "#8a8a90", "#c4c4c8"])
def _a_fumaca(n, quadros, s, p):
    u, v = grade(n)
    out = []
    for q in range(quadros):
        t = q / max(1, quadros - 1)
        cy = 0.75 - t * 0.35
        raio = 0.18 + t * 0.3
        nz = fbm(u, (v + t * 0.3) % 1, 4, 5, semente=s) * 0.5 + 0.5
        d = np.sqrt((u - 0.5) ** 2 + (v - cy) ** 2) / raio + (nz - 0.5) * 0.7
        dens = (1 - suave(0.5, 1.0, d)) * (1 - t) ** 0.8
        cor = rampa(np.clip(nz * 0.8 + (1 - v) * 0.3, 0, 1), p["cores"])
        out.append(_rgba(cor, dens))
    return out


@animacao_def("magia", "Círculo mágico/brilho pulsante girando.", cores=["#1a0a4a", "#5a2ad8", "#9a6aff", "#d8c8ff", "#ffffff"])
def _a_magia(n, quadros, s, p):
    x, y, r, a = _polar(n)
    out = []
    for q in range(quadros):
        f = q / quadros * 2 * np.pi
        anel = np.exp(-((r - 0.7) ** 2) * 400) + np.exp(-((r - 0.55) ** 2) * 900) * 0.6
        runas = (np.cos(a * 8 + f) > 0.6) * np.exp(-((r - 0.62) ** 2) * 1500)
        raios = np.clip(np.cos(a * 6 - f * 2), 0, 1) ** 6 * np.exp(-r * 2.5) * (0.6 + 0.4 * np.sin(f * 2))
        nucleo = np.exp(-r * r * (25 + 10 * np.sin(f * 2)))
        i = np.clip(anel + runas + raios + nucleo, 0, 1)
        out.append(_rgba(rampa(i, p["cores"]), suave(0.03, 0.4, i)))
    return out


@animacao_def("impacto", "Impacto/golpe (hit spark).", cores=["#ff6a00", "#ffd34a", "#ffffff"])
def _a_impacto(n, quadros, s, p):
    x, y, r, a = _polar(n)
    rng = np.random.default_rng(s)
    angs = rng.random(9) * 2 * np.pi
    out = []
    for q in range(quadros):
        t = q / max(1, quadros - 1)
        i = np.zeros_like(r)
        for ang in angs:
            dirx, diry = np.cos(ang), np.sin(ang)
            ao_longo = x * dirx + y * diry
            perp = np.abs(-x * diry + y * dirx)
            ini, fim = t * 0.7, 0.25 + t * 0.75
            seg = (ao_longo > ini) & (ao_longo < fim)
            larg = 0.06 * (1 - t) + 0.01
            i = np.maximum(i, seg * np.exp(-(perp / larg) ** 2))
        i = np.maximum(i, np.exp(-r * r * 30) * (1 - t) ** 2 * 1.5)
        i = np.maximum(i, np.exp(-((r - t * 0.9) ** 2) * 300) * (1 - t))
        out.append(_rgba(rampa(np.clip(i, 0, 1), p["cores"]), np.clip(i * 1.3, 0, 1)))
    return out


@animacao_def("coleta", "Brilho de coleta de item (pop + estrelinhas).", cores=["#fff0a0", "#ffffff"])
def _a_coleta(n, quadros, s, p):
    x, y, r, a = _polar(n)
    out = []
    for q in range(quadros):
        t = q / max(1, quadros - 1)
        anel = np.exp(-((r - t * 0.85) ** 2) * 500) * (1 - t)
        i = anel
        for k in range(6):
            ang = k / 6 * 2 * np.pi + t
            cx, cy = np.cos(ang) * t * 0.8, np.sin(ang) * t * 0.8
            dx, dy = np.abs(x - cx), np.abs(y - cy)
            est = np.exp(-dx * 60) * np.exp(-dy * 12) + np.exp(-dy * 60) * np.exp(-dx * 12)
            i = np.maximum(i, est * (1 - t) * 1.2)
        i = np.maximum(i, np.exp(-r * r * 40) * (1 - t) ** 3)
        out.append(_rgba(rampa(np.clip(i, 0, 1), p["cores"]), np.clip(i, 0, 1)))
    return out


@animacao_def("portal", "Portal giratório em loop.", cores=["#05101a", "#0a4a6a", "#1aa8d8", "#8ae8ff", "#ffffff"])
def _a_portal(n, quadros, s, p):
    x, y, r, a = _polar(n)
    out = []
    for q in range(quadros):
        f = q / quadros
        espiral = np.cos(a * 3 + np.log(r + 0.05) * 6 - f * 2 * np.pi) * 0.5 + 0.5
        borda = np.exp(-((r - 0.85) ** 2) * 200)
        dentro = (1 - suave(0.8, 0.9, r))
        i = np.clip(espiral * dentro * (0.4 + r * 0.6) + borda, 0, 1)
        out.append(_rgba(rampa(i, p["cores"]), np.clip(dentro * 0.95 + borda, 0, 1)))
    return out


@animacao_def("agua_respingo", "Respingo de água.", cores=["#1a5a9a", "#5aaee8", "#d8f0ff"])
def _a_respingo(n, quadros, s, p):
    u, v = grade(n)
    rng = np.random.default_rng(s)
    gotas = [(rng.uniform(-0.9, 0.9), rng.uniform(1.4, 2.4), rng.uniform(0.02, 0.05)) for _ in range(14)]
    out = []
    for q in range(quadros):
        t = q / max(1, quadros - 1)
        i = np.zeros_like(u)
        for vx, vy, rr in gotas:
            gx = 0.5 + vx * t * 0.45
            gy = 0.95 - (vy * t - 2.2 * t * t) * 0.45
            d = np.sqrt((u - gx) ** 2 + ((v - gy) * 0.8) ** 2)
            i = np.maximum(i, 1 - suave(rr * 0.6, rr, d))
        coroa = np.exp(-(((u - 0.5) * 2) ** 2) * (4 + t * 10)) * (v > 0.95 - 0.25 * np.sin(np.pi * min(1, t * 1.5))) * (1 - t)
        i = np.maximum(i, coroa)
        out.append(_rgba(rampa(np.clip(i * (1 - t * 0.3), 0, 1), p["cores"]), i * (1 - t ** 3)))
    return out


def animacao(nome, tamanho=64, quadros=8, semente=0, **params):
    info = ANIMACOES[nome]
    p = dict(info["padrao"])
    p.update(params)
    return [para_imagem(q[..., :3], q[..., 3]) for q in info["fn"](int(tamanho), int(quadros), int(semente), p)]


def montar_folha(quadros, colunas=None):
    colunas = colunas or len(quadros)
    w, h = quadros[0].size
    linhas = (len(quadros) + colunas - 1) // colunas
    folha = Image.new("RGBA", (w * colunas, h * linhas), (0, 0, 0, 0))
    for i, q in enumerate(quadros):
        folha.paste(q, ((i % colunas) * w, (i // colunas) * h))
    return folha
