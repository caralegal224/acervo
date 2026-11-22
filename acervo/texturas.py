"""Texturas procedurais tileáveis com mapas PBR (cor, normal, altura, rugosidade...).

Uso rápido:
    from acervo import texturas
    t = texturas.gerar("tijolo", tamanho=512, semente=3, linhas=10, cor_rejunte="#ddd")
    t.salvar("saida", "meu_tijolo")

Cada gerador recebe (u, v, semente, p) onde `p` são os parâmetros (padrões
listados em REGISTRO[nome]["padrao"]). Cores são sempre strings hex, para que
os presets em JSON fiquem fáceis de editar.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .ruido import grade, perlin, fbm, worley, warp, aleatorio_celula, normalizar, suave, valor
from .cor import rampa, hex_rgb, misturar, para_imagem, pixelizar, ajustar

REGISTRO = {}


def material(nome, descricao, categoria="geral", **padrao):
    def deco(fn):
        REGISTRO[nome] = {"fn": fn, "padrao": padrao, "descricao": descricao, "categoria": categoria}
        return fn
    return deco


# ----------------------------------------------------------------------------
# Classe de resultado
# ----------------------------------------------------------------------------
class Textura:
    def __init__(self, cor, altura=None, rugosidade=None, metalico=None, alfa=None, emissao=None):
        self.cor = np.clip(cor, 0, 1)
        forma = self.cor.shape[:2]
        cheio = lambda a: None if a is None else np.clip(np.broadcast_to(np.asarray(a, float), forma), 0, 1).copy()
        self.altura = cheio(altura)
        self.rugosidade = cheio(rugosidade)
        self.metalico = metalico
        self.alfa = cheio(alfa)
        self.emissao = cheio(emissao)

    def normal(self, forca=2.0):
        """Mapa normal no padrão OpenGL (verde = +Y). Para DirectX, inverta o verde."""
        h = self.altura if self.altura is not None else np.zeros(self.cor.shape[:2])
        k = forca * h.shape[1] / 128.0
        gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * k
        gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * k
        n = np.stack([-gx, gy, np.ones_like(h)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return n * 0.5 + 0.5

    def oclusao(self, raio=6.0, forca=1.2):
        """Oclusão ambiente aproximada a partir da altura (cavidades escurecem)."""
        if self.altura is None:
            return np.ones(self.cor.shape[:2])
        media = desfocar(self.altura, raio)
        return np.clip(1 - np.maximum(media - self.altura, 0) * forca * 4, 0, 1)

    def imagem(self):
        return para_imagem(self.cor, self.alfa)

    def salvar(self, pasta, nome, mapas=True, pixel=(32,), forca_normal=2.0, formato="png"):
        os.makedirs(pasta, exist_ok=True)
        arquivos = {}

        def grava(sufixo, img):
            caminho = os.path.join(pasta, f"{nome}{sufixo}.{formato}")
            img.save(caminho)
            arquivos[sufixo.strip("_") or "cor"] = caminho

        grava("", self.imagem())
        if mapas:
            if self.altura is not None:
                grava("_altura", para_imagem(self.altura))
                grava("_normal", para_imagem(self.normal(forca_normal)))
                grava("_ao", para_imagem(self.oclusao()))
            if self.rugosidade is not None:
                grava("_rugosidade", para_imagem(self.rugosidade))
            if self.metalico is not None and not np.isscalar(self.metalico):
                grava("_metalico", para_imagem(self.metalico))
            if self.emissao is not None:
                grava("_emissao", para_imagem(self.emissao))
        for tam in pixel or ():
            im = pixelizar(para_imagem(self.cor), tam, cores=16)
            if self.alfa is not None:
                a = para_imagem(self.alfa).resize((tam, tam), Image.BOX).point(lambda x: 255 if x > 127 else 0)
                im = im.convert("RGBA")
                im.putalpha(a)
            grava(f"_pixel{tam}", im)
        return arquivos


def gerar(nome, tamanho=512, semente=0, **params):
    if nome not in REGISTRO:
        raise KeyError(f"Textura desconhecida: {nome}. Opções: {', '.join(sorted(REGISTRO))}")
    info = REGISTRO[nome]
    p = dict(info["padrao"])
    p.update(params)
    u, v = grade(int(tamanho))
    t = info["fn"](u, v, int(semente), p)
    if any(k in p for k in ("matiz", "saturacao", "brilho", "contraste")):
        t.cor = ajustar(t.cor, p.get("matiz", 0), p.get("saturacao", 1), p.get("brilho", 1), p.get("contraste", 1))
    return t


# ----------------------------------------------------------------------------
# Auxiliares
# ----------------------------------------------------------------------------
def desfocar(a, sigma):
    """Desfoque gaussiano circular (via FFT) — preserva o tiling."""
    if sigma <= 0:
        return a
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    if a.ndim == 3:
        return np.real(np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * g[..., None], axes=(0, 1)))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def _frac(x):
    return x - np.floor(x)


def _ruido_fino(u, s, amp=1.0):
    rng = np.random.default_rng(s + 999)
    return (rng.random(u.shape) - 0.5) * amp


def _desenho_tileavel(tamanho, desenhar, modo="L", fundo=0):
    """Executa `desenhar(draw, ox, oy)` em 9 deslocamentos para emendar nas bordas."""
    im = Image.new(modo, (tamanho, tamanho), fundo)
    d = ImageDraw.Draw(im)
    for oy in (-tamanho, 0, tamanho):
        for ox in (-tamanho, 0, tamanho):
            desenhar(d, ox, oy)
    return im


def _arr(im):
    return np.asarray(im, dtype=np.float64) / 255.0


# ----------------------------------------------------------------------------
# Madeira
# ----------------------------------------------------------------------------
def _veio_madeira(u, v, s, aneis, distorcao, fibras):
    n = fbm(u, v, (2, 3), 4, semente=s)
    t = v * aneis + n * distorcao * 2.0
    f = _frac(t)
    anel = suave(0.0, 0.8, f) * (1 - suave(0.8, 1.0, f))  # sobe devagar, cai rápido
    f1 = perlin(u, v, (4, 96), s + 5) * 0.5 + 0.5
    f2 = perlin(u, v, (8, 256), s + 6) * 0.5 + 0.5
    nos = fbm(u, v, (6, 12), 3, semente=s + 7) * 0.5 + 0.5
    return np.clip(0.5 * anel + fibras * (0.65 * f1 + 0.35 * f2) + 0.25 * nos - 0.05, 0, 1), anel


@material("madeira", "Veios de madeira contínuos (tronco serrado).", "madeira",
          cores=["#3b2212", "#6b4122", "#9a6a3c", "#c39260"], aneis=10, distorcao=0.7, fibras=0.35,
          direcao="horizontal")
def madeira(u, v, s, p):
    if p["direcao"] == "vertical":
        u, v = v, u
    tom, anel = _veio_madeira(u, v, s, int(p["aneis"]), p["distorcao"], p["fibras"])
    cor = rampa(normalizar(tom), p["cores"])
    alt = 1 - anel * 0.4 + (tom - 0.5) * 0.2
    t = Textura(cor, alt, 0.55 + 0.3 * anel, 0.0)
    return t


@material("tabuas", "Assoalho/parede de tábuas com emendas e frestas.", "madeira",
          cores=["#3b2212", "#6b4122", "#9a6a3c", "#c39260"], tabuas=5, emendas=2, aneis=4,
          fresta=0.004, variacao=0.25, cor_fresta="#1a0f08", direcao="horizontal")
def tabuas(u, v, s, p):
    if p["direcao"] == "vertical":
        u, v = v, u
    rng = np.random.default_rng(s)
    n, m = int(p["tabuas"]), max(1, int(p["emendas"]))
    linha = np.floor(v * n).astype(int) % n
    desloc = rng.random(n)
    uu = _frac(u + desloc[linha])
    seg = np.floor(uu * m).astype(int)
    ident = linha * m + seg
    lv, lu = _frac(v * n), _frac(uu * m)
    dv = np.minimum(lv, 1 - lv) / n
    du = np.minimum(lu, 1 - lu) / m
    d = np.minimum(du, dv)
    borda = suave(0, p["fresta"] * 2.5 + 1e-4, d)
    veio, anel = _veio_madeira(uu, lv / n + aleatorio_celula(ident, s), s + 3, int(p["aneis"]) * n, 0.5, 0.35)
    var = (aleatorio_celula(ident, s, 2) - 0.5) * p["variacao"]
    cor = rampa(np.clip(veio + var, 0, 1), p["cores"])
    cor = misturar(hex_rgb(p["cor_fresta"]) * np.ones_like(cor), cor, borda)
    alt = borda * (0.75 + veio * 0.25)
    out = Textura(cor, alt, 0.6 + 0.25 * (1 - borda), 0.0)
    if p["direcao"] == "vertical":
        out = _transpor(out)
    return out


def _transpor(t):
    tr = lambda a: None if a is None or np.isscalar(a) else np.swapaxes(a, 0, 1)
    return Textura(tr(t.cor), tr(t.altura), tr(t.rugosidade), t.metalico if np.isscalar(t.metalico) else tr(t.metalico),
                   tr(t.alfa), tr(t.emissao))


@material("casca", "Casca de árvore com sulcos verticais.", "madeira",
          cores=["#1e140c", "#3d2a1a", "#5f4630", "#7d6449"], sulcos=8, profundidade=1.0)
def casca(u, v, s, p):
    uu, vv = warp(u, v, 0.08, 3, 3, s)
    r = fbm(uu, vv, (int(p["sulcos"]), 2), 5, semente=s, tipo="ridged")
    fino = fbm(u, v, (32, 8), 3, semente=s + 9) * 0.5 + 0.5
    alt = normalizar(r * 0.8 + fino * 0.2) ** p["profundidade"]
    cor = rampa(alt, p["cores"])
    return Textura(cor, alt, 0.85 + 0.1 * (1 - alt), 0.0)


# ----------------------------------------------------------------------------
# Alvenaria
# ----------------------------------------------------------------------------
@material("tijolo", "Parede de tijolos com rejunte, desgaste e variação por peça.", "alvenaria",
          cores=["#5c2318", "#8a3524", "#a8492f", "#c0664a"], cor_rejunte="#b3aa9b", linhas=8, colunas=4,
          rejunte=0.08, chanfro=0.12, variacao=0.6, desgaste=0.4, sujeira=0.25)
def tijolo(u, v, s, p):
    linhas = max(2, int(p["linhas"]) // 2 * 2)
    col = int(p["colunas"])
    row = np.floor(v * linhas).astype(int)
    x = u * col + (row % 2) * 0.5
    c = np.floor(x).astype(int) % col
    lx, ly = _frac(x), _frac(v * linhas)
    ident = row * col + c
    asp = linhas / col
    d = np.minimum(np.minimum(lx, 1 - lx) * asp, np.minimum(ly, 1 - ly))
    ru = fbm(u, v, 16, 4, semente=s + 1)
    d = d + ru * 0.04 * p["desgaste"]
    meio = p["rejunte"] / 2
    peca = suave(meio, meio + p["chanfro"], d)
    tom = aleatorio_celula(ident, s) * p["variacao"] + (fbm(u, v, 12, 4, semente=s + 2) * 0.5 + 0.5) * (1 - p["variacao"] * 0.5)
    cor_t = rampa(np.clip(tom, 0, 1), p["cores"])
    manchas = suave(0.2, 0.7, fbm(u, v, 4, 4, semente=s + 3) * 0.5 + 0.5) * p["sujeira"]
    cor_t = cor_t * (1 - manchas[..., None] * 0.5)
    cor_r = hex_rgb(p["cor_rejunte"]) * (0.85 + 0.15 * (ru[..., None] * 0.5 + 0.5))
    cor = misturar(cor_r * np.ones_like(cor_t), cor_t, peca)
    alt = peca * (0.8 + 0.2 * (ru * 0.5 + 0.5)) + _ruido_fino(u, s, 0.03)
    return Textura(cor, alt, 0.8 + 0.15 * (1 - peca), 0.0)


def _pedras(u, v, s, p, jitter):
    uu, vv = warp(u, v, 0.04, 4, 3, s)
    w = worley(uu, vv, int(p["celulas"]), s, jitter=jitter)
    borda = w["f2"] - w["f1"]
    j = p["junta"]
    forma = suave(j, j + p["abaulado"], borda)
    det = fbm(u, v, 24, 4, semente=s + 4) * 0.5 + 0.5
    rnd = aleatorio_celula(w["id"], s)
    tom = np.clip(rnd * 0.6 + det * 0.5 - 0.05, 0, 1)
    cor_p = rampa(tom, p["cores"])
    cor = misturar(hex_rgb(p["cor_junta"]) * np.ones_like(cor_p), cor_p, forma)
    alt = forma * (0.75 + 0.25 * rnd) * (0.85 + 0.15 * det)
    return Textura(cor, alt, 0.75 + 0.2 * (1 - forma), 0.0), forma, w


@material("pedra", "Muro de pedras irregulares (Voronoi).", "alvenaria",
          cores=["#3f3d3a", "#5f5c57", "#827d74", "#a39d91"], cor_junta="#22201e", celulas=6,
          junta=0.04, abaulado=0.25)
def pedra(u, v, s, p):
    return _pedras(u, v, s, p, 1.0)[0]


@material("paralelepipedo", "Calçamento de paralelepípedos arredondados.", "alvenaria",
          cores=["#4a4744", "#6a655e", "#8b847a", "#a69f93"], cor_junta="#2b2925", celulas=8,
          junta=0.06, abaulado=0.45)
def paralelepipedo(u, v, s, p):
    return _pedras(u, v, s, p, 0.45)[0]


@material("pedra_musgo", "Pedras com musgo crescendo nas juntas.", "alvenaria",
          cores=["#3f3d3a", "#5f5c57", "#827d74", "#a39d91"], cor_junta="#1f2a14", celulas=6, junta=0.04,
          abaulado=0.3, cores_musgo=["#1d3310", "#2f5216", "#4f7a24", "#7aa33a"], musgo=0.5)
def pedra_musgo(u, v, s, p):
    t, forma, w = _pedras(u, v, s, p, 0.9)
    n = fbm(u, v, 5, 5, semente=s + 20) * 0.5 + 0.5
    mascara = suave(1 - p["musgo"], 1.05 - p["musgo"] + 0.25, n + (1 - forma) * 0.45)
    fino = fbm(u, v, 64, 3, semente=s + 21) * 0.5 + 0.5
    cor_m = rampa(fino * 0.7 + n * 0.3, p["cores_musgo"])
    t.cor = misturar(t.cor, cor_m, mascara)
    t.altura = np.maximum(t.altura, mascara * (0.55 + 0.2 * fino))
    t.rugosidade = np.clip(t.rugosidade + mascara * 0.2, 0, 1)
    return t


@material("concreto", "Concreto liso com poros e manchas.", "alvenaria",
          cores=["#6d6b67", "#8a8781", "#a4a19a", "#b9b6ae"], poros=0.5, manchas=0.5)
def concreto(u, v, s, p):
    base = fbm(u, v, 6, 6, semente=s) * 0.5 + 0.5
    w = worley(u, v, 72, s + 1)
    rnd = aleatorio_celula(w["id"], s)
    poro = (w["f1"] < 0.18) & (rnd < p["poros"] * 0.6)
    mancha = suave(0.45, 0.8, fbm(u, v, 3, 4, semente=s + 2) * 0.5 + 0.5) * p["manchas"]
    tom = np.clip(base * 0.7 + 0.2 + _ruido_fino(u, s, 0.08) - mancha * 0.35, 0, 1)
    cor = rampa(tom, p["cores"])
    cor = np.where(poro[..., None], cor * 0.55, cor)
    alt = 0.6 + base * 0.2 - poro * 0.4
    return Textura(cor, alt, 0.9 - mancha * 0.2, 0.0)


@material("asfalto", "Asfalto com agregado claro.", "alvenaria",
          cores=["#1c1c1e", "#2a2a2c", "#3b3a3a", "#57534e"], agregado=0.35, desgaste=0.3)
def asfalto(u, v, s, p):
    w = worley(u, v, 96, s)
    rnd = aleatorio_celula(w["id"], s)
    pedrinha = (w["f1"] < 0.33) & (rnd < p["agregado"])
    base = fbm(u, v, 8, 5, semente=s + 1) * 0.5 + 0.5
    tom = np.clip(base * 0.5 + rnd * 0.3 * pedrinha + _ruido_fino(u, s, 0.15), 0, 1)
    gasto = suave(0.5, 0.8, fbm(u, v, 2, 4, semente=s + 2) * 0.5 + 0.5) * p["desgaste"]
    cor = rampa(np.clip(tom + gasto * 0.3, 0, 1), p["cores"])
    alt = 0.5 + pedrinha * 0.3 * (1 - w["f1"] * 2) + base * 0.1
    return Textura(cor, alt, 0.92, 0.0)


@material("azulejo", "Azulejos/ladrilhos quadrados com rejunte.", "piso",
          cores=["#e9e6df"], cor_rejunte="#9c968c", quantidade=8, rejunte=0.05, chanfro=0.05, variacao=0.06,
          padrao="liso")
def azulejo(u, v, s, p):
    n = int(p["quantidade"])
    cx, cy = np.floor(u * n).astype(int), np.floor(v * n).astype(int)
    lx, ly = _frac(u * n), _frac(v * n)
    ident = cy * n + cx
    d = np.minimum(np.minimum(lx, 1 - lx), np.minimum(ly, 1 - ly))
    m = p["rejunte"] / 2
    peca = suave(m, m + p["chanfro"], d)
    cores = [hex_rgb(c) for c in p["cores"]]
    if p["padrao"] == "xadrez" and len(cores) >= 2:
        idx = (cx + cy) % 2
    elif p["padrao"] == "listras":
        idx = cy % len(cores)
    else:
        idx = (aleatorio_celula(ident, s, 3) * len(cores)).astype(int) % len(cores)
    base = np.stack(cores)[idx]
    var = (aleatorio_celula(ident, s) - 0.5) * p["variacao"]
    nuvem = fbm(u, v, n * 2, 3, semente=s) * 0.03
    cor_p = np.clip(base + (var + nuvem)[..., None], 0, 1)
    cor_r = hex_rgb(p["cor_rejunte"]) * (0.9 + 0.1 * (fbm(u, v, 32, 3, semente=s + 1)[..., None] * 0.5 + 0.5))
    cor = misturar(cor_r * np.ones_like(cor_p), cor_p, peca)
    return Textura(cor, peca * 0.9 + 0.05, 0.85 - peca * 0.7, 0.0)


@material("hexagonos", "Piso de ladrilhos hexagonais.", "piso",
          cores=["#d7d2c8", "#c9c2b5", "#b8b0a1"], cor_rejunte="#5b5750", colunas=8, rejunte=0.08,
          chanfro=0.1)
def hexagonos(u, v, s, p):
    fx = int(p["colunas"])
    fy = max(2, int(round(fx * 1.1547)) // 2 * 2)
    pts = np.zeros((fy, fx, 2))
    pts[..., 1] = 0.5
    pts[..., 0] = 0.5
    pts[1::2, :, 0] = 1.0
    w = worley(u, v, (fx, fy), s, pontos=pts)
    borda = w["f2"] - w["f1"]
    peca = suave(p["rejunte"], p["rejunte"] + p["chanfro"], borda)
    cores = np.stack([hex_rgb(c) for c in p["cores"]])
    idx = (aleatorio_celula(w["id"], s) * len(cores)).astype(int) % len(cores)
    cor_p = cores[idx] + (fbm(u, v, 24, 3, semente=s)[..., None] * 0.03)
    cor = misturar(hex_rgb(p["cor_rejunte"]) * np.ones_like(cor_p), cor_p, peca)
    return Textura(cor, peca * 0.9, 0.85 - peca * 0.6, 0.0)


@material("telhado", "Telhas cerâmicas arredondadas sobrepostas.", "alvenaria",
          cores=["#6b2a17", "#93412a", "#b3583a", "#c97b55"], colunas=8, linhas=10, sombra=0.55, variacao=0.5)
def telhado(u, v, s, p):
    return _escamas(u, v, s, p)


@material("escamas", "Escamas (peixe, dragão, réptil).", "organico",
          cores=["#0f3b3a", "#1d6b5c", "#3c9a73", "#8fd19e"], colunas=16, linhas=20, sombra=0.7, variacao=0.3)
def escamas(u, v, s, p):
    return _escamas(u, v, s, p)


def _escamas(u, v, s, p):
    nc = int(p["colunas"])
    nr = max(2, int(p["linhas"]) // 2 * 2)
    X, Y = u * nc, v * nr
    raio = 0.5 * 1.05
    melhor_j = np.full(X.shape, 10 ** 6)
    dist = np.zeros(X.shape)
    dyv = np.zeros(X.shape)
    ident = np.zeros(X.shape, dtype=np.int64)
    base_j = np.floor(Y).astype(int)
    for dj in (1, 0, -1):
        j = base_j + dj
        off = (j % 2) * 0.5
        i = np.floor(X - off + 0.5).astype(int)
        cx = i + off
        dx = X - cx
        dy = (Y - j) * (nc / nr) * 0.85
        dentro = (dx * dx + dy * dy <= raio * raio) | ((dy <= 0) & (dy > -1.2) & (np.abs(dx) <= raio))
        sel = dentro & (j <= melhor_j)
        melhor_j = np.where(sel, j, melhor_j)
        r = np.sqrt(dx * dx + np.maximum(dy, 0) ** 2)
        dist = np.where(sel, r / raio, dist)
        dyv = np.where(sel, dy, dyv)
        ident = np.where(sel, (j % nr) * nc + (i % nc), ident)
    rnd = aleatorio_celula(ident, s)
    borda = 1 - suave(0.75, 1.0, dist)
    sombra = 1 - p["sombra"] * suave(0.2, -1.0, dyv)
    det = fbm(u, v, 32, 3, semente=s) * 0.5 + 0.5
    tom = np.clip(0.35 + (rnd - 0.5) * p["variacao"] + det * 0.3 + dyv * 0.15, 0, 1)
    cor = rampa(tom, p["cores"]) * (sombra * (0.55 + 0.45 * borda))[..., None]
    alt = np.clip(borda * 0.6 + (dyv + 1.2) / 2.2 * 0.4, 0, 1)
    return Textura(cor, alt, 0.6 - 0.2 * borda, 0.0)


# ----------------------------------------------------------------------------
# Pedras nobres
# ----------------------------------------------------------------------------
@material("marmore", "Mármore polido com veios.", "pedra",
          cor_base="#ebe7df", cor_nuvem="#d6d0c4", cor_veio="#4f4a44", cor_veio2="#9e978b", veios=3, nitidez=10.0,
          distorcao=0.35)
def marmore(u, v, s, p):
    uu, vv = warp(u, v, p["distorcao"], 2, 5, s)
    n1 = fbm(uu, vv, int(p["veios"]), 5, semente=s + 1)
    n2 = fbm(uu, vv, int(p["veios"]) * 2, 4, semente=s + 2)
    veio = np.exp(-np.abs(n1) * p["nitidez"] * 3)
    veio2 = np.exp(-np.abs(n2) * p["nitidez"] * 4)
    nuvem = fbm(u, v, 3, 5, semente=s + 3) * 0.5 + 0.5
    cor = misturar(hex_rgb(p["cor_base"]) * np.ones(u.shape + (3,)), hex_rgb(p["cor_nuvem"]), nuvem * 0.8)
    cor = misturar(cor, hex_rgb(p["cor_veio2"]), veio2 * 0.6)
    cor = misturar(cor, hex_rgb(p["cor_veio"]), veio)
    return Textura(cor, 0.5 - veio * 0.05, 0.12 + veio * 0.15, 0.0)


@material("granito", "Granito salpicado (também serve para terrazzo).", "pedra",
          cores=["#2b2a2a", "#575250", "#8d8580", "#c9c1b8", "#7a4b3a"], pesos=[0.25, 0.3, 0.2, 0.15, 0.1], graos=64)
def granito(u, v, s, p):
    w = worley(u, v, int(p["graos"]), s, jitter=0.9)
    w2 = worley(u, v, int(p["graos"]) * 2, s + 7)
    pesos = np.cumsum(np.array(p["pesos"], dtype=float))
    pesos /= pesos[-1]
    r1 = aleatorio_celula(w["id"], s)
    r2 = aleatorio_celula(w2["id"], s + 1)
    r = np.where(w2["f1"] < 0.35, r2, r1)
    idx = np.searchsorted(pesos, r)
    cores = np.stack([hex_rgb(c) for c in p["cores"]])
    cor = cores[np.clip(idx, 0, len(cores) - 1)]
    cor = cor * (0.9 + 0.1 * (fbm(u, v, 8, 3, semente=s)[..., None] * 0.5 + 0.5))
    return Textura(cor, 0.5 + (w["f2"] - w["f1"]) * 0.1, 0.2 + r * 0.2, 0.0)


@material("cristal", "Facetas cristalinas brilhantes (gema, gelo mágico).", "pedra",
          cores=["#1a0b3d", "#4a1d8f", "#8a4fe0", "#d7b8ff", "#ffffff"], facetas=6)
def cristal(u, v, s, p):
    w = worley(u, v, int(p["facetas"]), s)
    rnd = aleatorio_celula(w["id"], s)
    ang = rnd * 2 * np.pi
    dx, dy = u - w["px"], v - w["py"]
    dx, dy = dx - np.round(dx), dy - np.round(dy)
    plano = (np.cos(ang) * dx + np.sin(ang) * dy) * int(p["facetas"]) * 1.5
    borda = suave(0.0, 0.06, w["f2"] - w["f1"])
    tom = np.clip(0.45 + plano + (rnd - 0.5) * 0.4, 0, 1) * borda + (1 - borda) * 0.95
    cor = rampa(tom, p["cores"])
    return Textura(cor, np.clip(0.5 + plano, 0, 1) * borda, 0.08, 0.0)


# ----------------------------------------------------------------------------
# Natureza
# ----------------------------------------------------------------------------
@material("grama", "Grama vista de cima, com tufos e flores opcionais.", "natureza",
          cores=["#18320d", "#2a5115", "#41741f", "#66992f", "#97c04c"], tufos=6, flores=0.0,
          cores_flores=["#f4f1e8", "#f2d24b", "#d9506c"])
def grama(u, v, s, p):
    base = fbm(u, v, int(p["tufos"]), 4, semente=s) * 0.5 + 0.5
    w = worley(u, v, (64, 16), s + 1)
    folha = np.clip(1 - w["f1"] * 1.4, 0, 1)
    w2 = worley(u, v, (128, 32), s + 2)
    folha2 = np.clip(1 - w2["f1"] * 1.4, 0, 1)
    tom = np.clip(0.4 * base + 0.35 * folha + 0.25 * folha2 + _ruido_fino(u, s, 0.06), 0, 1)
    cor = rampa(tom, p["cores"])
    alt = tom
    if p["flores"] > 0:
        wf = worley(u, v, 24, s + 3)
        r = aleatorio_celula(wf["id"], s)
        flor = (wf["f1"] < 0.12) & (r < p["flores"])
        cores = np.stack([hex_rgb(c) for c in p["cores_flores"]])
        cf = cores[(aleatorio_celula(wf["id"], s, 2) * len(cores)).astype(int) % len(cores)]
        miolo = wf["f1"] < 0.04
        cf = np.where(miolo[..., None], hex_rgb("#f2c230"), cf)
        cor = np.where(flor[..., None], cf, cor)
        alt = np.where(flor, 1.0, alt)
    return Textura(cor, alt, 0.9, 0.0)


@material("terra", "Terra/solo com pedrinhas e umidade.", "natureza",
          cores=["#2e1f14", "#4a3322", "#664832", "#866448"], pedrinhas=0.35, umidade=0.4,
          cor_pedrinha="#8d8478")
def terra(u, v, s, p):
    base = fbm(u, v, 8, 6, semente=s) * 0.5 + 0.5
    umido = suave(0.45, 0.75, fbm(u, v, 3, 4, semente=s + 1) * 0.5 + 0.5) * p["umidade"]
    tom = np.clip(base * 0.8 + 0.15 + _ruido_fino(u, s, 0.12) - umido * 0.3, 0, 1)
    cor = rampa(tom, p["cores"])
    w = worley(u, v, 20, s + 2, jitter=0.8)
    r = aleatorio_celula(w["id"], s)
    raio = 0.2 + r * 0.25
    pedra_m = (w["f1"] < raio) & (r < p["pedrinhas"])
    sombreado = np.clip(1 - w["f1"] / raio, 0, 1)
    cp = hex_rgb(p["cor_pedrinha"]) * (0.6 + 0.5 * sombreado[..., None]) * (0.8 + 0.4 * r[..., None])
    cor = np.where(pedra_m[..., None], cp, cor)
    alt = np.where(pedra_m, 0.6 + 0.4 * np.sqrt(sombreado), base * 0.5)
    return Textura(cor, alt, 0.95 - umido * 0.4, 0.0)


@material("areia", "Areia com ondulações de vento.", "natureza",
          cores=["#a8875a", "#c9a874", "#dcc08d", "#ecd7aa"], ondas=14, ondulacao=0.8, grao=0.15)
def areia(u, v, s, p):
    n = fbm(u, v, 2, 4, semente=s)
    t = v * int(p["ondas"]) + n * p["ondulacao"] * 2 + perlin(u, v, (3, 1), s + 1) * 0.5
    f = _frac(t)
    onda = np.where(f < 0.75, f / 0.75, (1 - f) / 0.25)
    grao = _ruido_fino(u, s, p["grao"] * 2)
    tom = np.clip(onda * 0.45 + (fbm(u, v, 8, 4, semente=s + 2) * 0.5 + 0.5) * 0.4 + grao + 0.1, 0, 1)
    return Textura(rampa(tom, p["cores"]), onda * 0.7 + grao + 0.15, 0.95, 0.0)


@material("neve", "Neve fofa com brilhos.", "natureza",
          cores=["#a9b8cc", "#d3deea", "#eef3f8", "#ffffff"], brilhos=0.004)
def neve(u, v, s, p):
    base = fbm(u, v, 4, 6, semente=s) * 0.5 + 0.5
    det = fbm(u, v, 24, 3, semente=s + 1) * 0.5 + 0.5
    tom = np.clip(base * 0.6 + det * 0.3 + 0.15, 0, 1)
    cor = rampa(tom, p["cores"])
    rng = np.random.default_rng(s)
    br = rng.random(u.shape) < p["brilhos"]
    cor = np.where(br[..., None], 1.0, cor)
    return Textura(cor, base * 0.8 + det * 0.2, 0.75, 0.0)


@material("gelo", "Gelo com rachaduras e profundidade.", "natureza",
          cores=["#0d3a5c", "#2c78a8", "#79b9dd", "#d4ecf7"], rachaduras=5, espessura=0.025)
def gelo(u, v, s, p):
    uu, vv = warp(u, v, 0.05, 4, 3, s)
    base = fbm(u, v, 3, 5, semente=s) * 0.5 + 0.5
    w1 = worley(uu, vv, int(p["rachaduras"]), s + 1)
    w2 = worley(uu, vv, int(p["rachaduras"]) * 3, s + 2)
    r1 = 1 - suave(0, p["espessura"], w1["f2"] - w1["f1"])
    r2 = (1 - suave(0, p["espessura"] * 0.6, w2["f2"] - w2["f1"])) * 0.5
    rach = np.maximum(r1, r2)
    cor = rampa(np.clip(base * 0.7 + 0.2, 0, 1), p["cores"])
    cor = misturar(cor, np.ones(3), rach * 0.85)
    return Textura(cor, 0.6 - rach * 0.4 + base * 0.1, 0.05 + rach * 0.4, 0.0)


@material("agua", "Água com cáusticas (fundo de piscina/lago raso).", "natureza",
          cores=["#063a5c", "#0f6b8f", "#2aa3c0", "#9de3ef"], celulas=6, intensidade=1.0)
def agua(u, v, s, p):
    uu, vv = warp(u, v, 0.12, 2, 3, s)
    w1 = worley(uu, vv, int(p["celulas"]), s + 1)
    uu2, vv2 = warp(u, v, 0.1, 3, 3, s + 5)
    w2 = worley(uu2, vv2, int(p["celulas"]) + 2, s + 2)
    c = np.exp(-(w1["f2"] - w1["f1"]) * 10) + np.exp(-(w2["f2"] - w2["f1"]) * 10) * 0.7
    base = fbm(u, v, 3, 4, semente=s + 3) * 0.5 + 0.5
    tom = np.clip(base * 0.45 + c * 0.55 * p["intensidade"], 0, 1)
    ondas = fbm(u, v, 4, 5, semente=s + 4) * 0.5 + 0.5
    return Textura(rampa(tom, p["cores"]), ondas, 0.05, 0.0)


@material("lava", "Lava com crosta escura e fissuras incandescentes.", "natureza",
          cores_crosta=["#0e0b0a", "#241a16", "#3d2c24"], cores_brasa=["#5a0a00", "#c22a00", "#ff7a00", "#ffd34d"],
          celulas=6, crosta=0.6)
def lava(u, v, s, p):
    uu, vv = warp(u, v, 0.1, 3, 4, s)
    w = worley(uu, vv, int(p["celulas"]), s + 1)
    borda = w["f2"] - w["f1"]
    n = fbm(u, v, 8, 4, semente=s + 2) * 0.5 + 0.5
    crosta = suave(0.02, 0.02 + 0.3 * p["crosta"], borda) * suave(0.25, 0.55, n + p["crosta"] * 0.3)
    brasa = 1 - crosta
    cor_c = rampa(n, p["cores_crosta"])
    cor_b = rampa(np.clip(brasa * 0.9 + n * 0.2, 0, 1), p["cores_brasa"])
    cor = misturar(cor_b, cor_c, crosta)
    return Textura(cor, crosta * (0.6 + 0.4 * n), 0.4 + crosta * 0.5, 0.0, emissao=brasa ** 1.5)


@material("folhagem", "Folhas sobrepostas (cerca viva, copa de árvore).", "natureza",
          cores=["#14300e", "#22501a", "#36722a", "#5c9a3b", "#8cc256"], folhas=450, tamanho_folha=0.06)
def folhagem(u, v, s, p):
    N = u.shape[0]
    rng = np.random.default_rng(s)
    cores = [hex_rgb(c) for c in p["cores"]]
    folhas = []
    for _ in range(int(p["folhas"] * (N / 512) ** 0)):
        x, y = rng.random() * N, rng.random() * N
        a = rng.random() * 2 * np.pi
        L = N * p["tamanho_folha"] * (0.7 + rng.random() * 0.6)
        W = L * (0.35 + rng.random() * 0.15)
        folhas.append((x, y, a, L, W, rng.random()))
    folhas.sort(key=lambda f: f[5])
    im = Image.new("RGB", (N, N), tuple(int(c * 255) for c in cores[0]))
    ha = Image.new("L", (N, N), 0)
    d, dh = ImageDraw.Draw(im), ImageDraw.Draw(ha)
    for (x, y, a, L, W, z) in folhas:
        ca, sa = np.cos(a), np.sin(a)
        k = int(z * (len(cores) - 1))
        c1 = cores[min(len(cores) - 1, k + 1)] * (0.75 + 0.25 * z)
        c0 = cores[k] * 0.9
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                pts_a, pts_b = [], []
                for t in np.linspace(0, 1, 9):
                    lx = (t - 0.5) * L
                    ly = np.sin(t * np.pi) * W / 2
                    pts_a.append((x + ox + lx * ca - ly * sa, y + oy + lx * sa + ly * ca))
                    pts_b.append((x + ox + lx * ca + ly * sa, y + oy + lx * sa - ly * ca))
                metade1 = pts_a + pts_b[::-1][:1]
                d.polygon(pts_a + [pts_a[0]], fill=tuple(int(c * 255) for c in c1))
                d.polygon(pts_b + [pts_b[0]], fill=tuple(int(c * 255) for c in c0))
                dh.polygon(pts_a + pts_b[::-1], fill=int(60 + 195 * z))
                d.line([pts_a[0], pts_a[-1]], fill=tuple(int(c * 255 * 0.7) for c in c0), width=max(1, N // 512))
    cor = _arr(im)
    alt = desfocar(_arr(ha), 1.0)
    return Textura(cor, alt, 0.7, 0.0)


@material("musgo", "Tapete de musgo denso.", "natureza",
          cores=["#152a0c", "#25461a", "#3b6b25", "#5e8f30", "#8fb84a"])
def musgo(u, v, s, p):
    w = worley(u, v, 48, s)
    bolinha = np.clip(1 - w["f1"], 0, 1) ** 1.5
    base = fbm(u, v, 6, 5, semente=s + 1) * 0.5 + 0.5
    tom = np.clip(bolinha * 0.5 + base * 0.5 + _ruido_fino(u, s, 0.1), 0, 1)
    return Textura(rampa(tom, p["cores"]), tom, 0.95, 0.0)


# ----------------------------------------------------------------------------
# Metais
# ----------------------------------------------------------------------------
@material("metal_escovado", "Metal escovado (aço, alumínio).", "metal",
          cores=["#6f7378", "#8d9196", "#a9adb2", "#c4c7cb"], riscos=0.6)
def metal_escovado(u, v, s, p):
    a = perlin(u, v, (4, 256), s) * 0.5 + 0.5
    b = perlin(u, v, (2, 512), s + 1) * 0.5 + 0.5
    rng = np.random.default_rng(s)
    linhas = rng.random(u.shape[0])[:, None] * np.ones_like(u)
    tom = np.clip(0.5 * a + 0.25 * b + 0.25 * linhas * p["riscos"] + fbm(u, v, 3, 3, semente=s + 2) * 0.1, 0, 1)
    return Textura(rampa(tom, p["cores"]), 0.5 + (tom - 0.5) * 0.05, 0.3 + tom * 0.15, 1.0)


@material("chapa_xadrez", "Chapa de piso antiderrapante (diamond plate).", "metal",
          cores=["#5d6166", "#80858b", "#a3a8ae", "#cdd1d5"], quantidade=10)
def chapa_xadrez(u, v, s, p):
    n = int(p["quantidade"])
    cx, cy = np.floor(u * n).astype(int), np.floor(v * n).astype(int)
    lx, ly = _frac(u * n) - 0.5, _frac(v * n) - 0.5
    par = (cx + cy) % 2 == 0
    a = np.where(par, lx + ly, lx - ly) / np.sqrt(2)
    b = np.where(par, lx - ly, lx + ly) / np.sqrt(2)
    e = (a / 0.36) ** 2 + (b / 0.085) ** 2
    bump = np.sqrt(np.clip(1 - e, 0, 1))
    base = perlin(u, v, (4, 128), s) * 0.5 + 0.5
    tom = np.clip(0.35 + base * 0.2 + bump * 0.45, 0, 1)
    return Textura(rampa(tom, p["cores"]), bump * 0.8 + base * 0.05, 0.4 - bump * 0.15, 1.0)


@material("ferrugem", "Metal enferrujado com corrosão e pites.", "metal",
          cores_metal=["#4c4f52", "#6d7174", "#8b8f92"], cores_ferrugem=["#3a1a0b", "#6b2f12", "#9a4a1c", "#c46e2e", "#d99a52"],
          quantidade=0.55)
def ferrugem(u, v, s, p):
    uu, vv = warp(u, v, 0.15, 3, 4, s)
    n = fbm(uu, vv, 4, 6, semente=s) * 0.5 + 0.5
    q = p["quantidade"]
    mascara = suave(1 - q - 0.08, 1 - q + 0.08, n)
    det = fbm(u, v, 32, 4, semente=s + 1) * 0.5 + 0.5
    w = worley(u, v, 40, s + 2)
    pite = (w["f1"] < 0.15) & (aleatorio_celula(w["id"], s) < 0.4)
    metal = rampa(perlin(u, v, (4, 128), s + 3) * 0.5 + 0.5, p["cores_metal"])
    ferr = rampa(np.clip(det * 0.7 + n * 0.3, 0, 1), p["cores_ferrugem"])
    cor = misturar(metal, ferr, mascara)
    cor = np.where((pite & (mascara > 0.5))[..., None], cor * 0.45, cor)
    alt = 0.4 + mascara * (0.2 + det * 0.3) - pite * mascara * 0.3
    return Textura(cor, alt, 0.35 + mascara * 0.6, 1 - mascara)


@material("grade_metal", "Grade metálica com furos (tem transparência).", "metal",
          cores=["#3d4044", "#6a6e73", "#9a9ea3"], quantidade=8, barra=0.22, furo="quadrado")
def grade_metal(u, v, s, p):
    n = int(p["quantidade"])
    lx, ly = _frac(u * n) - 0.5, _frac(v * n) - 0.5
    if p["furo"] == "redondo":
        d = 0.5 - np.sqrt(lx * lx + ly * ly)
    else:
        d = 0.5 - np.maximum(np.abs(lx), np.abs(ly))
    barra = d < p["barra"] / 2
    perfil = np.clip(d / (p["barra"] / 2), 0, 1)
    alt = np.where(barra, np.sin(perfil * np.pi * 0.5 + 0.5) , 0)
    tom = np.clip(alt * 0.6 + perlin(u, v, (8, 64), s) * 0.15 + 0.3, 0, 1)
    return Textura(rampa(tom, p["cores"]), alt, 0.4, 1.0, alfa=barra.astype(float))


@material("ouro", "Ouro martelado / folheado.", "metal",
          cores=["#6b4a0f", "#a8791e", "#d6a73a", "#f3d27a", "#fff0bf"], marteladas=24)
def ouro(u, v, s, p):
    w = worley(u, v, int(p["marteladas"]), s)
    cova = w["f1"] ** 2
    ang = aleatorio_celula(w["id"], s) * 0.3
    tom = np.clip(0.75 - cova * 0.6 + ang + fbm(u, v, 6, 3, semente=s) * 0.1, 0, 1)
    return Textura(rampa(tom, p["cores"]), 1 - cova, 0.25 + cova * 0.2, 1.0)


# ----------------------------------------------------------------------------
# Tecidos e orgânicos
# ----------------------------------------------------------------------------
@material("tecido", "Tecido em trama (lona, linho, jeans).", "tecido",
          cor_fio1="#2f4a73", cor_fio2="#c9c3b2", fios=48, relevo=0.6, felpa=0.3)
def tecido(u, v, s, p):
    n = int(p["fios"])
    X, Y = u * n, v * n
    cx, cy = np.floor(X).astype(int), np.floor(Y).astype(int)
    fx, fy = _frac(X), _frac(Y)
    sobre = (cx + cy) % 2 == 0
    pv = np.sin(np.pi * fx)
    ph = np.sin(np.pi * fy)
    curva_v = 0.55 + 0.45 * np.sin(np.pi * fy)
    curva_h = 0.55 + 0.45 * np.sin(np.pi * fx)
    alt = np.where(sobre, pv * curva_v, ph * curva_h)
    fibra_v = perlin(u, v, (n * 4, n // 4 or 1), s) * 0.5 + 0.5
    fibra_h = perlin(u, v, (n // 4 or 1, n * 4), s + 1) * 0.5 + 0.5
    fibra = np.where(sobre, fibra_v, fibra_h)
    base = np.where(sobre[..., None], hex_rgb(p["cor_fio1"]), hex_rgb(p["cor_fio2"]))
    luz = (1 - p["relevo"]) + p["relevo"] * alt
    cor = base * (luz * (1 - p["felpa"] * 0.5 + p["felpa"] * fibra))[..., None]
    return Textura(cor, alt, 0.95, 0.0)


@material("couro", "Couro com poros e vincos.", "tecido",
          cores=["#2a160b", "#4a2814", "#6b3d20", "#8c5634"], granulado=28)
def couro(u, v, s, p):
    g = int(p["granulado"])
    w = worley(u, v, g, s)
    w2 = worley(u, v, g * 2, s + 1)
    vinco = suave(0.0, 0.12, w["f2"] - w["f1"]) * 0.7 + suave(0, 0.1, w2["f2"] - w2["f1"]) * 0.3
    base = fbm(u, v, 4, 5, semente=s + 2) * 0.5 + 0.5
    tom = np.clip(base * 0.5 + vinco * 0.45 + _ruido_fino(u, s, 0.05), 0, 1)
    return Textura(rampa(tom, p["cores"]), vinco * 0.8 + base * 0.2, 0.55 + (1 - vinco) * 0.3, 0.0)


@material("papel", "Papel/pergaminho envelhecido.", "tecido",
          cores=["#b89b6c", "#d4bc8e", "#e6d4ab", "#f2e6c8"], manchas=0.4, fibras=0.5)
def papel(u, v, s, p):
    base = fbm(u, v, 4, 6, semente=s) * 0.5 + 0.5
    fib = fbm(u, v, (64, 16), 3, semente=s + 1) * 0.5 + 0.5
    mancha = suave(0.55, 0.85, fbm(u, v, 3, 5, semente=s + 2) * 0.5 + 0.5) * p["manchas"]
    tom = np.clip(0.55 + (base - 0.5) * 0.5 + (fib - 0.5) * 0.3 * p["fibras"] - mancha * 0.6 + _ruido_fino(u, s, 0.04), 0, 1)
    return Textura(rampa(tom, p["cores"]), base * 0.3 + fib * 0.2, 0.9, 0.0)


@material("carpete", "Carpete/tapete felpudo com estampa de losangos.", "tecido",
          cor1="#7a1f2b", cor2="#d9b35a", cor3="#1f2a4a", losangos=4, felpa=0.35)
def carpete(u, v, s, p):
    n = int(p["losangos"])
    lx, ly = _frac(u * n) - 0.5, _frac(v * n) - 0.5
    d = np.abs(lx) + np.abs(ly)
    faixa = np.where(d < 0.18, 2, np.where((d > 0.3) & (d < 0.36), 1, 0))
    paleta = np.stack([hex_rgb(p["cor1"]), hex_rgb(p["cor2"]), hex_rgb(p["cor3"])])
    cor = paleta[faixa]
    pelo = _ruido_fino(u, s, 1.0) + 0.5
    pelo = desfocar(pelo, 0.6)
    cor = cor * (1 - p["felpa"] + p["felpa"] * normalizar(pelo)[..., None] * 1.3)
    return Textura(cor, normalizar(pelo), 1.0, 0.0)


@material("camuflagem", "Camuflagem orgânica ou digital (pixelada).", "tecido",
          cores=["#4b5320", "#2e3317", "#76693f", "#1c1c12"], escala=3, digital=False, blocos=64)
def camuflagem(u, v, s, p):
    if p["digital"]:
        b = int(p["blocos"])
        u, v = np.floor(u * b) / b, np.floor(v * b) / b
    cores = [hex_rgb(c) for c in p["cores"]]
    cor = np.ones(u.shape + (3,)) * cores[0]
    uu, vv = warp(u, v, 0.08, 4, 3, s)
    for k, c in enumerate(cores[1:]):
        n = fbm(uu, vv, int(p["escala"]) + k, 4, semente=s + k * 31)
        cor = np.where((n > 0.12)[..., None], c, cor)
    return Textura(cor, 0.5 + _ruido_fino(u, s, 0.05), 0.9, 0.0)


@material("pele_alien", "Pele orgânica com veias e manchas (monstros, alien).", "organico",
          cores=["#1b2b12", "#3d5a1f", "#6f8f2f", "#b6c95a"], cor_veia="#5a1030", veias=0.6, manchas=0.5)
def pele_alien(u, v, s, p):
    uu, vv = warp(u, v, 0.2, 2, 4, s)
    base = fbm(uu, vv, 4, 5, semente=s) * 0.5 + 0.5
    w = worley(uu, vv, 5, s + 1)
    veia = np.exp(-(w["f2"] - w["f1"]) * 25) * p["veias"]
    wm = worley(u, v, 12, s + 2)
    mancha = (1 - suave(0.2, 0.45, wm["f1"])) * (aleatorio_celula(wm["id"], s) < p["manchas"])
    tom = np.clip(base * 0.8 - mancha * 0.35 + 0.15, 0, 1)
    cor = misturar(rampa(tom, p["cores"]), hex_rgb(p["cor_veia"]), veia)
    return Textura(cor, base * 0.6 + veia * 0.4, 0.35, 0.0)


# ----------------------------------------------------------------------------
# Céu, espaço, sci-fi
# ----------------------------------------------------------------------------
@material("nuvens", "Nuvens sobre o céu (inclui mapa alfa para sobrepor).", "ceu",
          cor_ceu="#4d8fd6", cor_ceu2="#9cc7f0", cor_nuvem="#ffffff", cor_sombra="#9aa7b8", cobertura=0.5,
          suavidade=0.25, escala=3)
def nuvens(u, v, s, p):
    n = fbm(u, v, int(p["escala"]), 7, semente=s) * 0.5 + 0.5
    lim = 1 - p["cobertura"]
    a = suave(lim - p["suavidade"] * 0.5, lim + p["suavidade"] * 0.5, n)
    n2 = fbm(_frac(u - 0.01), _frac(v - 0.015), int(p["escala"]), 7, semente=s) * 0.5 + 0.5
    sombra = np.clip((n2 - n) * 8 + 0.5, 0, 1)
    ceu = misturar(hex_rgb(p["cor_ceu"]) * np.ones(u.shape + (3,)), hex_rgb(p["cor_ceu2"]), fbm(u, v, 2, 3, semente=s + 4) * 0.5 + 0.5)
    nuvem = misturar(hex_rgb(p["cor_nuvem"]) * np.ones_like(ceu), hex_rgb(p["cor_sombra"]), sombra * 0.8)
    return Textura(misturar(ceu, nuvem, a), a, 1.0, 0.0, alfa=None if not p.get("so_alfa") else a)


@material("espaco", "Espaço com nebulosa colorida e estrelas.", "ceu",
          cores_nebulosa=["#05030c", "#1a0f3d", "#5a1f6e", "#c2386f", "#ffb36b"], estrelas=0.0015, nebulosa=0.8)
def espaco(u, v, s, p):
    uu, vv = warp(u, v, 0.3, 2, 5, s)
    n = fbm(uu, vv, 3, 7, semente=s) * 0.5 + 0.5
    mascara = suave(0.3, 0.8, fbm(u, v, 2, 4, semente=s + 1) * 0.5 + 0.5)
    tom = np.clip(n * mascara * p["nebulosa"] * 1.4, 0, 1)
    cor = rampa(tom, p["cores_nebulosa"])
    rng = np.random.default_rng(s)
    brilho = (rng.random(u.shape) < p["estrelas"]) * (rng.random(u.shape) ** 3 * 0.8 + 0.2)
    grandes = (rng.random(u.shape) < p["estrelas"] * 0.05).astype(float)
    halo = desfocar(grandes, 1.5) * 30 + desfocar(brilho, 0.6) * 4
    estrelas = np.clip(brilho + halo, 0, 1)
    tinta = rampa(rng.random(u.shape), ["#a9c4ff", "#ffffff", "#ffe1b0"])
    cor = 1 - (1 - cor) * (1 - tinta * estrelas[..., None])
    return Textura(cor, estrelas, 1.0, 0.0, emissao=np.clip(estrelas + tom * 0.3, 0, 1))


@material("circuito", "Placa de circuito impresso (sci-fi, hacker).", "scifi",
          cor_placa="#0d3b1e", cor_trilha="#2f8a45", cor_metal="#d9b44a", cor_chip="#141414", grade=32, trilhas=70, chips=5)
def circuito(u, v, s, p):
    N = u.shape[0]
    g = int(p["grade"])
    passo = N / g
    rng = np.random.default_rng(s)
    caminhos = []
    for _ in range(int(p["trilhas"])):
        x, y = rng.integers(0, g), rng.integers(0, g)
        pts = [(x, y)]
        dx, dy = [(1, 0), (0, 1), (1, 1), (1, -1)][rng.integers(0, 4)]
        for _ in range(rng.integers(3, 12)):
            if rng.random() < 0.3:
                dx, dy = [(1, 0), (0, 1), (1, 1), (1, -1)][rng.integers(0, 4)]
            x, y = x + dx, y + dy
            pts.append((x, y))
        caminhos.append(pts)
    chips = [(rng.integers(0, g), rng.integers(0, g), rng.integers(3, 7), rng.integers(2, 5)) for _ in range(int(p["chips"]))]
    larg = max(1, int(passo * 0.28))
    rpad = passo * 0.38

    def trilhas_fn(d, ox, oy):
        for pts in caminhos:
            xy = [(ox + (a + 0.5) * passo, oy + (b + 0.5) * passo) for a, b in pts]
            d.line(xy, fill=255, width=larg, joint="curve")

    def pads_fn(d, ox, oy):
        for pts in caminhos:
            for a, b in (pts[0], pts[-1]):
                cx, cy = ox + (a + 0.5) * passo, oy + (b + 0.5) * passo
                d.ellipse([cx - rpad, cy - rpad, cx + rpad, cy + rpad], fill=255)
        for (a, b, w, h) in chips:
            for k in range(w):
                for lado in (-0.6, h - 0.4):
                    cx, cy = ox + (a + k + 0.5) * passo, oy + (b + lado + 0.5) * passo
                    d.rectangle([cx - passo * 0.18, cy - passo * 0.3, cx + passo * 0.18, cy + passo * 0.3], fill=255)

    def chips_fn(d, ox, oy):
        for (a, b, w, h) in chips:
            d.rectangle([ox + a * passo + 2, oy + b * passo + 2, ox + (a + w) * passo - 2, oy + (b + h) * passo - 2], fill=255)

    tri = _arr(_desenho_tileavel(N, trilhas_fn))
    pad = _arr(_desenho_tileavel(N, pads_fn))
    chp = _arr(_desenho_tileavel(N, chips_fn))
    base = fbm(u, v, 16, 3, semente=s) * 0.5 + 0.5
    cor = hex_rgb(p["cor_placa"]) * (0.85 + 0.3 * base[..., None])
    cor = misturar(cor, hex_rgb(p["cor_trilha"]), tri)
    cor = misturar(cor, hex_rgb(p["cor_metal"]) * (0.85 + 0.15 * base[..., None]), pad)
    cor = misturar(cor, hex_rgb(p["cor_chip"]), chp)
    alt = np.clip(0.3 + tri * 0.25 + pad * 0.3 + chp * 0.6, 0, 1)
    metal = np.clip(pad, 0, 1)
    return Textura(cor, desfocar(alt, 0.7), 0.7 - pad * 0.4 - chp * 0.2, metal)


@material("painel_scifi", "Painéis de nave com rebites e frisos.", "scifi",
          cores=["#3a3f47", "#555c66", "#737b86", "#959da8"], cor_luz="#38e1ff", divisoes=3, luzes=0.3)
def painel_scifi(u, v, s, p):
    rng = np.random.default_rng(s)
    N = u.shape[0]
    rects = [(0.0, 0.0, 1.0, 1.0)]
    for _ in range(int(p["divisoes"]) * 3):
        rects.sort(key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))
        x0, y0, x1, y1 = rects.pop(0)
        if (x1 - x0) > (y1 - y0):
            c = x0 + (x1 - x0) * rng.uniform(0.3, 0.7)
            rects += [(x0, y0, c, y1), (c, y0, x1, y1)]
        else:
            c = y0 + (y1 - y0) * rng.uniform(0.3, 0.7)
            rects += [(x0, y0, x1, c), (x0, c, x1, y1)]
    alt = np.zeros(u.shape)
    tom = np.zeros(u.shape)
    luz = np.zeros(u.shape)
    for i, (x0, y0, x1, y1) in enumerate(rects):
        dentro = (u >= x0) & (u < x1) & (v >= y0) & (v < y1)
        d = np.minimum(np.minimum(u - x0, x1 - u), np.minimum(v - y0, y1 - v))
        bev = suave(0.002, 0.012, d)
        nivel = rng.uniform(0.4, 1.0)
        alt = np.where(dentro, bev * nivel, alt)
        tom = np.where(dentro, rng.uniform(0.3, 0.8), tom)
        # rebites nos cantos
        for cx, cy in ((x0 + 0.02, y0 + 0.02), (x1 - 0.02, y0 + 0.02), (x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)):
            r = np.sqrt((u - cx) ** 2 + (v - cy) ** 2)
            reb = dentro & (r < 0.007)
            alt = np.where(reb, alt + 0.2 * (1 - r / 0.007), alt)
        if rng.random() < p["luzes"] and (x1 - x0) > 0.1:
            ly = y0 + (y1 - y0) * 0.5
            faixa = dentro & (np.abs(v - ly) < 0.006) & (u > x0 + 0.05) & (u < x1 - 0.05)
            luz = np.where(faixa, 1.0, luz)
    det = perlin(u, v, (8, 64), s) * 0.05
    cor = rampa(np.clip(tom * 0.6 + alt * 0.3 + det, 0, 1), p["cores"])
    halo = np.clip(desfocar(luz, 3) * 3, 0, 1)
    cor = misturar(cor, hex_rgb(p["cor_luz"]), np.maximum(luz, halo * 0.5))
    return Textura(cor, alt, 0.45, 0.8, emissao=np.maximum(luz, halo * 0.6))


# ----------------------------------------------------------------------------
# Utilitárias
# ----------------------------------------------------------------------------
@material("uv_teste", "Grade de teste de UV com coordenadas (para modelos 3D).", "util",
          quantidade=8)
def uv_teste(u, v, s, p):
    N = u.shape[0]
    n = int(p["quantidade"])
    cx, cy = np.floor(u * n).astype(int), np.floor(v * n).astype(int)
    matiz = (cx / n + cy / n * 0.5) % 1.0
    cor = rampa(matiz, ["#e34b4b", "#e3b34b", "#7be34b", "#4be3c4", "#4b7be3", "#b34be3", "#e34b4b"])
    xad = ((cx + cy) % 2 == 0)
    cor = np.where(xad[..., None], cor, cor * 0.55)
    lx, ly = _frac(u * n * 4), _frac(v * n * 4)
    fina = (lx < 0.04) | (ly < 0.04)
    cor = np.where(fina[..., None], cor * 0.8, cor)
    im = para_imagem(cor)
    d = ImageDraw.Draw(im)
    try:
        fonte = ImageFont.load_default(size=max(8, N // n // 3))
    except TypeError:
        fonte = ImageFont.load_default()
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for j in range(n):
        for i in range(n):
            txt = f"{letras[i % 26]}{n - j}"
            d.text(((i + 0.5) * N / n, (j + 0.5) * N / n), txt, fill="white", font=fonte, anchor="mm",
                   stroke_width=max(1, N // 512), stroke_fill="black")
    d.line([(0, 0), (N, 0)], fill="white", width=2)
    return Textura(_arr(im), None, None, None)


@material("xadrez", "Xadrez simples de duas cores.", "util", cor1="#202020", cor2="#e0e0e0", quantidade=8)
def xadrez(u, v, s, p):
    n = int(p["quantidade"])
    m = (np.floor(u * n) + np.floor(v * n)) % 2 == 0
    cor = np.where(m[..., None], hex_rgb(p["cor1"]), hex_rgb(p["cor2"]))
    return Textura(cor, m.astype(float), 0.5, 0.0)


@material("ruido_perlin", "Ruído fBm cinza (para máscaras, displacement, shaders).", "util",
          escala=4, oitavas=6, tipo="perlin")
def ruido_perlin(u, v, s, p):
    n = fbm(u, v, int(p["escala"]), int(p["oitavas"]), semente=s, tipo=p["tipo"])
    if p["tipo"] == "perlin":
        n = n * 0.5 + 0.5
    n = normalizar(n)
    return Textura(np.stack([n] * 3, -1), n, None, None)


@material("ruido_celular", "Ruído Worley/Voronoi cinza (f1, f2-f1 ou células).", "util",
          escala=8, modo="f1")
def ruido_celular(u, v, s, p):
    w = worley(u, v, int(p["escala"]), s)
    if p["modo"] == "bordas":
        n = normalizar(w["f2"] - w["f1"])
    elif p["modo"] == "celulas":
        n = aleatorio_celula(w["id"], s)
    else:
        n = normalizar(w["f1"])
    return Textura(np.stack([n] * 3, -1), n, None, None)


@material("caixote", "Face de caixote de madeira com moldura e travessa diagonal.", "madeira",
          cores=["#4a2c15", "#7a4e28", "#a3703e", "#c89660"], cor_prego="#9aa0a8", moldura=0.13, tabuas=4)
def caixote(u, v, s, p):
    tab = tabuas(u, v, s, {"cores": p["cores"], "tabuas": int(p["tabuas"]), "emendas": 1, "aneis": 3,
                           "fresta": 0.004, "variacao": 0.25, "cor_fresta": "#1a0f08", "direcao": "vertical"})
    m = p["moldura"]
    borda = (u < m) | (u > 1 - m) | (v < m) | (v > 1 - m)
    diag = np.abs(u - v) < m * 0.55
    alvo = borda | diag
    veio, _ = _veio_madeira(u, v, s + 50, 3, 0.4, 0.4)
    veio_d, _ = _veio_madeira((u + v) / 2 % 1, (u - v) % 1, s + 51, 2, 0.4, 0.4)
    tom = np.where(borda, veio, veio_d)
    cor_f = rampa(np.clip(tom * 0.8 + 0.25, 0, 1), p["cores"])
    db = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    bev_b = suave(0, 0.012, np.where(borda, m - db, 1)) * suave(0, 0.01, db)
    bev_d = suave(0, 0.012, m * 0.55 - np.abs(u - v))
    bev = np.where(borda, bev_b, bev_d)
    cor = np.where(alvo[..., None], cor_f * (0.55 + 0.45 * bev[..., None]), tab.cor * 0.8)
    alt = np.where(alvo, 0.7 + 0.3 * bev, tab.altura * 0.5)
    # pregos nos cantos da moldura
    for cx in (m / 2, 1 - m / 2):
        for cy in (m / 2, 1 - m / 2):
            r = np.sqrt((u - cx) ** 2 + (v - cy) ** 2)
            prego = r < 0.012
            cor = np.where(prego[..., None], hex_rgb(p["cor_prego"]) * (1.2 - r[..., None] / 0.012 * 0.6), cor)
            alt = np.where(prego, 1.0, alt)
    return Textura(cor, alt, 0.7, 0.0)
