"""Efeitos sonoros.

1) Motor "retrô" parametrizado (inspirado em geradores do tipo sfxr, mas próprio):
   todo som é um dicionário de parâmetros (salvo em JSON ao lado do WAV), então
   você pode abrir o .json, mudar um número e gerar de novo.

       from acervo.som import sfx
       p = sfx.sortear("moeda", semente=3)      # parâmetros aleatórios da categoria
       x = sfx.sintetizar(p)                    # array de áudio
       sfx.salvar("moeda.wav", x)

2) Sons "realistas" sintetizados por modelos físicos simples (passos, porta,
   impacto, chuva...): funções em SONS_REALISTAS, também com parâmetros.
"""
import json
import numpy as np

from .sintese import (TAXA, passa_baixa_variavel, filtro, ruido, normalizar, fade, cortar_silencio, reverb,
                      eco, decaimento, seno, salvar_wav, distorcer, bitcrush)

PADRAO = {
    "onda": "quadrada",        # quadrada | serra | seno | triangulo | ruido | ruido_rosa | ruido_metalico
    "freq": 440.0,             # frequência inicial (Hz)
    "freq_min": 20.0,          # abaixo disso o som corta (útil com deslize negativo)
    "deslize": 0.0,            # oitavas por segundo (+ sobe, - desce)
    "deslize_aceleracao": 0.0, # oitavas/s² (curva o deslize)
    "vibrato_prof": 0.0,       # em semitons
    "vibrato_vel": 6.0,        # Hz
    "ataque": 0.0,             # s
    "sustentacao": 0.1,        # s
    "soco": 0.0,               # 0..1 — pico extra no início da sustentação
    "decaimento": 0.2,         # s
    "duty": 0.5,               # largura de pulso da quadrada (0..1)
    "duty_deslize": 0.0,       # variação do duty por segundo
    "arpejo_mult": 1.0,        # multiplicador de frequência depois de arpejo_tempo (ex.: 1.5 = quinta)
    "arpejo_tempo": 0.0,       # s (0 = desligado)
    "repetir": 0.0,            # reinicia a altura a cada N segundos (0 = desligado)
    "passa_baixa": 22000.0,    # Hz
    "passa_baixa_deslize": 0.0,# oitavas por segundo
    "ressonancia": 0.0,        # 0..0.95
    "passa_alta": 0.0,         # Hz
    "distorcao": 0.0,          # 0..1
    "bits": 16,                # 16 = sem bitcrush; 4..8 = sujo/retrô
    "reduzir_taxa": 1,         # 1 = normal; 2..8 = aliasing retrô
    "eco": 0.0,                # 0..1 retorno do eco
    "eco_atraso": 0.12,        # s
    "reverb": 0.0,             # 0..1
    "volume": 0.8,
    "semente": 0,
}


def _onda(p, fase, n):
    tipo = p["onda"]
    if tipo == "quadrada":
        t = np.arange(n) / TAXA
        duty = np.clip(p["duty"] + p["duty_deslize"] * t, 0.05, 0.95)
        return np.where(fase < duty, 0.6, -0.6)
    if tipo == "serra":
        return (fase * 2 - 1) * 0.7
    if tipo == "seno":
        return np.sin(2 * np.pi * fase)
    if tipo == "triangulo":
        return 1 - 4 * np.abs(fase - 0.5)
    rng = np.random.default_rng(int(p.get("semente", 0)))
    if tipo in ("ruido", "ruido_rosa", "ruido_metalico"):
        # ruído "afinado": novo valor a cada ciclo (como chips antigos), tom segue a frequência
        ciclo = np.floor(np.cumsum(np.clip(_freq_cache[0], 1, None) * 32 / TAXA)).astype(np.int64)
        tabela = rng.uniform(-1, 1, int(ciclo.max()) + 2)
        if tipo == "ruido_metalico":
            tabela = np.sign(np.sin(np.arange(len(tabela)) * 0.731) + rng.uniform(-0.3, 0.3, len(tabela)))
        s = tabela[ciclo]
        if tipo == "ruido_rosa":
            s = filtro(s, "passa_baixa", 3000, ordem=1) * 2
        return s
    raise ValueError(f"onda desconhecida: {tipo}")


_freq_cache = [None]


def sintetizar(params):
    p = dict(PADRAO)
    p.update(params or {})
    dur = p["ataque"] + p["sustentacao"] + p["decaimento"]
    n = max(1, int(round(dur * TAXA)))
    t = np.arange(n) / TAXA
    tr = np.mod(t, p["repetir"]) if p["repetir"] > 0 else t
    oit = p["deslize"] * tr + 0.5 * p["deslize_aceleracao"] * tr ** 2
    if p["vibrato_prof"]:
        oit = oit + p["vibrato_prof"] / 12 * np.sin(2 * np.pi * p["vibrato_vel"] * t)
    f = p["freq"] * 2.0 ** oit
    if p["arpejo_tempo"] > 0:
        f = np.where(tr >= p["arpejo_tempo"], f * p["arpejo_mult"], f)
    vivo = f >= p["freq_min"]
    if not vivo.all():
        corte = np.argmin(vivo)
        n = max(corte, 1)
        f, t = f[:n], t[:n]
    f = np.clip(f, 1, TAXA / 2.2)
    _freq_cache[0] = f
    fase = np.cumsum(f) / TAXA % 1.0
    x = _onda(p, fase, n)
    # envelope
    A, S, D = int(p["ataque"] * TAXA), int(p["sustentacao"] * TAXA), int(p["decaimento"] * TAXA)
    env = np.concatenate([np.linspace(0, 1, A, endpoint=False),
                          np.ones(S) * (1 + p["soco"] * np.linspace(1, 0, S) if S else np.ones(0)),
                          np.linspace(1, 0, D) ** 1.5])[:n]
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    x = x * env
    # filtros
    if p["passa_baixa"] < 20000 or p["passa_baixa_deslize"]:
        cortes = p["passa_baixa"] * 2.0 ** (p["passa_baixa_deslize"] * t)
        x = passa_baixa_variavel(x, cortes, ressonancia=p["ressonancia"])
    if p["passa_alta"] > 0:
        x = filtro(x, "passa_alta", p["passa_alta"], ordem=1)
    if p["distorcao"] > 0:
        x = distorcer(x, 1 + p["distorcao"] * 8)
    if p["bits"] < 16 or p["reduzir_taxa"] > 1:
        x = bitcrush(x, int(p["bits"]), int(p["reduzir_taxa"]))
    if p["eco"] > 0:
        x = eco(x, p["eco_atraso"], p["eco"], 4)
    x = fade(x, 0.001, 0.004)
    if p["reverb"] > 0:
        x = reverb(x, p["reverb"] * 0.5, 1.2)
        x = cortar_silencio(x, 0.001)
    return normalizar(x, 0.95) * p["volume"]


# ----------------------------------------------------------------------------
# Categorias com sorteio de parâmetros
# ----------------------------------------------------------------------------
def _u(rng, a, b):
    return float(rng.uniform(a, b))


def _ch(rng, xs):
    return xs[int(rng.integers(0, len(xs)))]


def _cat_moeda(r):
    return dict(onda=_ch(r, ["quadrada", "quadrada", "seno", "triangulo"]), freq=_u(r, 700, 1400), sustentacao=_u(r, 0.03, 0.09),
                decaimento=_u(r, 0.12, 0.35), soco=_u(r, 0.2, 0.6), duty=_u(r, 0.3, 0.5),
                arpejo_mult=_ch(r, [1.335, 1.5, 1.26, 2.0]), arpejo_tempo=_u(r, 0.04, 0.09))


def _cat_pulo(r):
    return dict(onda=_ch(r, ["quadrada", "quadrada", "triangulo"]), freq=_u(r, 250, 500), deslize=_u(r, 2.5, 5),
                sustentacao=_u(r, 0.06, 0.15), decaimento=_u(r, 0.08, 0.2), duty=_u(r, 0.2, 0.5),
                passa_baixa=_u(r, 3000, 12000))


def _cat_laser(r):
    return dict(onda=_ch(r, ["serra", "quadrada", "seno"]), freq=_u(r, 900, 2200), deslize=-_u(r, 6, 14),
                deslize_aceleracao=_u(r, -10, 10), sustentacao=_u(r, 0.04, 0.12), decaimento=_u(r, 0.05, 0.2),
                duty=_u(r, 0.1, 0.5), duty_deslize=_u(r, -1, 1), passa_alta=_u(r, 0, 400), freq_min=60)


def _cat_tiro(r):
    return dict(onda="ruido", freq=_u(r, 400, 1500), deslize=-_u(r, 2, 6), sustentacao=_u(r, 0.02, 0.08),
                decaimento=_u(r, 0.12, 0.3), soco=_u(r, 0.4, 0.9), passa_baixa=_u(r, 3000, 9000),
                passa_baixa_deslize=-_u(r, 1, 4), distorcao=_u(r, 0, 0.5))


def _cat_explosao(r):
    return dict(onda=_ch(r, ["ruido", "ruido_rosa"]), freq=_u(r, 60, 300), deslize=-_u(r, 0.5, 2.5),
                sustentacao=_u(r, 0.1, 0.35), decaimento=_u(r, 0.4, 1.2), soco=_u(r, 0.4, 1.0),
                passa_baixa=_u(r, 1500, 6000), passa_baixa_deslize=-_u(r, 0.5, 2.5), distorcao=_u(r, 0.2, 0.7),
                repetir=_ch(r, [0.0, 0.0, _u(r, 0.15, 0.4)]), reverb=_u(r, 0, 0.4))


def _cat_dano(r):
    return dict(onda=_ch(r, ["quadrada", "serra", "ruido"]), freq=_u(r, 150, 600), deslize=-_u(r, 3, 8),
                sustentacao=_u(r, 0.02, 0.06), decaimento=_u(r, 0.08, 0.2), soco=_u(r, 0.2, 0.6),
                passa_baixa=_u(r, 2000, 8000), distorcao=_u(r, 0.0, 0.6), freq_min=40)


def _cat_powerup(r):
    rep = _ch(r, [0.0, _u(r, 0.07, 0.15)])
    return dict(onda=_ch(r, ["quadrada", "triangulo", "serra", "seno"]), freq=_u(r, 200, 500), deslize=_u(r, 1.5, 5),
                sustentacao=_u(r, 0.2, 0.4), decaimento=_u(r, 0.15, 0.4), repetir=rep, vibrato_prof=_ch(r, [0, _u(r, 0.2, 1)]),
                vibrato_vel=_u(r, 8, 16), duty=_u(r, 0.25, 0.5))


def _cat_blip(r):
    return dict(onda=_ch(r, ["quadrada", "seno", "triangulo"]), freq=_u(r, 400, 1500), sustentacao=_u(r, 0.02, 0.05),
                decaimento=_u(r, 0.01, 0.06), duty=_u(r, 0.25, 0.5), passa_baixa=_u(r, 4000, 16000))


def _cat_selecao(r):
    return dict(onda=_ch(r, ["quadrada", "triangulo"]), freq=_u(r, 500, 900), sustentacao=0.05, decaimento=_u(r, 0.08, 0.15),
                arpejo_mult=_ch(r, [1.5, 2.0, 1.335]), arpejo_tempo=0.05, duty=0.5)


def _cat_teleporte(r):
    return dict(onda=_ch(r, ["seno", "triangulo", "quadrada"]), freq=_u(r, 300, 700), deslize=_u(r, 2, 4),
                repetir=_u(r, 0.05, 0.1), sustentacao=_u(r, 0.3, 0.5), decaimento=_u(r, 0.2, 0.4),
                vibrato_prof=_u(r, 0.5, 2), vibrato_vel=_u(r, 10, 25), eco=_u(r, 0.2, 0.5), eco_atraso=0.08)


def _cat_queda(r):
    return dict(onda=_ch(r, ["quadrada", "triangulo", "seno"]), freq=_u(r, 600, 1200), deslize=-_u(r, 1.2, 3),
                sustentacao=_u(r, 0.4, 0.8), decaimento=_u(r, 0.1, 0.3), vibrato_prof=_u(r, 0, 0.6), vibrato_vel=8)


def _cat_alarme(r):
    return dict(onda=_ch(r, ["quadrada", "serra"]), freq=_u(r, 500, 900), vibrato_prof=_u(r, 3, 7), vibrato_vel=_u(r, 3, 8),
                sustentacao=_u(r, 0.6, 1.0), decaimento=0.1, passa_baixa=_u(r, 3000, 7000))


def _cat_erro(r):
    return dict(onda=_ch(r, ["quadrada", "serra"]), freq=_u(r, 110, 220), sustentacao=_u(r, 0.15, 0.25), decaimento=0.05,
                arpejo_mult=_ch(r, [0.94, 0.89, 0.75]), arpejo_tempo=_u(r, 0.08, 0.12), passa_baixa=_u(r, 1500, 3500), duty=0.5)


def _cat_robo(r):
    return dict(onda=_ch(r, ["quadrada", "serra"]), freq=_u(r, 80, 300), sustentacao=_u(r, 0.2, 0.5), decaimento=0.1,
                vibrato_prof=_u(r, 2, 12), vibrato_vel=_u(r, 15, 45), bits=int(r.integers(4, 8)), reduzir_taxa=int(r.integers(1, 4)))


def _cat_magia(r):
    return dict(onda=_ch(r, ["seno", "triangulo"]), freq=_u(r, 600, 1400), deslize=_u(r, -1, 2), sustentacao=_u(r, 0.25, 0.5),
                decaimento=_u(r, 0.3, 0.6), vibrato_prof=_u(r, 0.3, 1.2), vibrato_vel=_u(r, 12, 30), repetir=_u(r, 0.04, 0.09),
                arpejo_mult=_ch(r, [1.5, 1.26]), arpejo_tempo=0.02, reverb=_u(r, 0.3, 0.7), ataque=0.01)


CATEGORIAS = {
    "moeda": (_cat_moeda, "Coletar moeda/item"), "pulo": (_cat_pulo, "Pulo"), "laser": (_cat_laser, "Tiro laser/blaster"),
    "tiro": (_cat_tiro, "Tiro com ruído (arma)"), "explosao": (_cat_explosao, "Explosão"), "dano": (_cat_dano, "Levar dano/acerto"),
    "powerup": (_cat_powerup, "Power-up/level up"), "blip": (_cat_blip, "Blip de menu/texto"), "selecao": (_cat_selecao, "Confirmar/selecionar"),
    "teleporte": (_cat_teleporte, "Teleporte/portal"), "queda": (_cat_queda, "Cair/perder"), "alarme": (_cat_alarme, "Alarme/sirene"),
    "erro": (_cat_erro, "Erro/negado"), "robo": (_cat_robo, "Voz/ruído de robô"), "magia": (_cat_magia, "Feitiço/brilho mágico"),
}


def sortear(categoria, semente=0):
    rng = np.random.default_rng(semente)
    p = dict(PADRAO)
    p.update(CATEGORIAS[categoria][0](rng))
    p["semente"] = int(semente)
    return p


def mutar(params, intensidade=0.1, semente=0):
    """Pequenas variações aleatórias de um som existente (ótimo para variações de passos/tiros)."""
    rng = np.random.default_rng(semente)
    p = dict(params)
    for k, v in params.items():
        if isinstance(v, float) and k not in ("volume",):
            p[k] = v * (1 + rng.uniform(-intensidade, intensidade)) if v != 0 else v
    p["semente"] = int(semente)
    return p


def salvar(caminho, x):
    salvar_wav(caminho, x)


def salvar_params(caminho, p):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------------
# Sons "realistas" (modelos simples de ruído filtrado, ressonadores e impactos)
# ----------------------------------------------------------------------------
def _ressonador(x, freqs, decs, ganhos=None):
    """Banco de modos ressonantes (soma de senoides amortecidas excitadas por x)."""
    n = len(x)
    t = np.arange(n) / TAXA
    out = np.zeros(n)
    ganhos = ganhos or [1.0] * len(freqs)
    from .sintese import convoluir
    for f, d, g in zip(freqs, decs, ganhos):
        h = np.sin(2 * np.pi * f * t[:int(min(n, d * 6 * TAXA))]) * np.exp(-t[:int(min(n, d * 6 * TAXA))] / d)
        out += convoluir(x, h)[:n] * g
    return out


def _estalo(dur, semente, corte=3000, tau=0.01):
    n = int(round(dur * TAXA))
    return ruido(dur, semente) * decaimento(n, tau, ataque=0.0005) if corte >= 20000 else \
        filtro(ruido(dur, semente) * decaimento(n, tau, ataque=0.0005), "passa_baixa", corte)


def passo(superficie="terra", semente=0, peso=1.0):
    """Passo em: terra, pedra, madeira, grama, neve, metal, agua, cascalho."""
    rng = np.random.default_rng(semente)
    dur = 0.35
    n = int(round(dur * TAXA))
    calc = _estalo(dur, semente, 900 + rng.uniform(-100, 100), 0.025 * peso)
    if superficie == "pedra":
        x = _estalo(dur, semente, 4000, 0.012) + _estalo(dur, semente + 1, 700, 0.03) * 0.6
    elif superficie == "madeira":
        x = _ressonador(_estalo(dur, semente, 6000, 0.004), [180 + rng.uniform(-20, 20), 410, 820], [0.05, 0.03, 0.015], [1, 0.5, 0.3]) * 0.4 + calc * 0.3
    elif superficie == "grama":
        x = filtro(ruido(dur, semente) * decaimento(n, 0.06, ataque=0.01), "passa_banda", 3500, 0.8) + calc * 0.4
    elif superficie == "neve":
        crunch = ruido(dur, semente) * (rng.random(n) < 0.08) * decaimento(n, 0.08, ataque=0.015)
        x = filtro(crunch, "passa_banda", 2500, 0.6) * 2 + calc * 0.5
    elif superficie == "metal":
        x = _ressonador(_estalo(dur, semente, 8000, 0.003), [520, 1340, 2210, 3480], [0.12, 0.08, 0.05, 0.04], [1, 0.6, 0.4, 0.3]) * 0.2 + calc * 0.4
    elif superficie == "agua":
        x = filtro(ruido(dur, semente) * decaimento(n, 0.09, ataque=0.008), "passa_banda", 1200, 0.7) + \
            seno(np.linspace(600, 1400, n), dur) * decaimento(n, 0.03, ataque=0.003) * 0.3
    elif superficie == "cascalho":
        graos = ruido(dur, semente) * (rng.random(n) < 0.15) * decaimento(n, 0.07, ataque=0.01)
        x = filtro(graos, "passa_alta", 1500) * 2 + calc * 0.6
    else:  # terra
        x = calc + filtro(ruido(dur, semente + 3) * decaimento(n, 0.05, ataque=0.005), "passa_banda", 1800, 0.7) * 0.4
    return normalizar(cortar_silencio(fade(x, 0.0005, 0.02)), 0.8)


def impacto(material="madeira", semente=0, tamanho=1.0):
    """Batida em: madeira, metal, pedra, vidro, carne (soco), terra."""
    rng = np.random.default_rng(semente)
    dur = 1.2
    exc = _estalo(dur, semente, 9000, 0.004 * tamanho)
    if material == "metal":
        f0 = 300 / tamanho * rng.uniform(0.9, 1.1)
        x = _ressonador(exc, [f0, f0 * 2.76, f0 * 5.4, f0 * 8.93], [0.5, 0.35, 0.2, 0.12], [1, 0.7, 0.5, 0.3])
    elif material == "vidro":
        f0 = 1800 / tamanho
        x = _ressonador(exc, [f0, f0 * 2.32, f0 * 4.25, f0 * 6.63], [0.25, 0.15, 0.1, 0.06], [1, 0.8, 0.5, 0.4])
    elif material == "pedra":
        x = filtro(exc * 2, "passa_baixa", 2500) + _estalo(dur, semente + 1, 400, 0.05 * tamanho)
    elif material == "carne":
        x = _estalo(dur, semente, 1200, 0.03 * tamanho) * 1.5 + seno(np.linspace(140, 60, int(round(dur * TAXA))), dur) * decaimento(int(round(dur * TAXA)), 0.06)
    elif material == "terra":
        x = _estalo(dur, semente, 600, 0.08 * tamanho)
    else:
        f0 = 220 / tamanho
        x = _ressonador(exc, [f0, f0 * 2.4, f0 * 4.1], [0.08, 0.05, 0.03], [1, 0.5, 0.3]) + exc * 0.2
    return normalizar(cortar_silencio(fade(x, 0.0, 0.05)), 0.9)


def porta(tipo="abrir", semente=0):
    rng = np.random.default_rng(semente)
    if tipo == "ranger":
        dur = 1.4
        n = int(round(dur * TAXA))
        t = np.arange(n) / TAXA
        f = 420 + 160 * np.sin(t * 2.1 + rng.random()) + 60 * np.sin(t * 7.3)
        # fricção: trem de pulsos irregulares filtrado por ressonador
        pulsos = (np.diff(np.floor(np.cumsum(f / TAXA)), prepend=0) > 0).astype(float) * rng.uniform(0.5, 1, n)
        x = _ressonador(pulsos, [900, 1750, 2600], [0.01, 0.008, 0.006]) * adsr_simples(n, 0.15, 0.3)
        return normalizar(x, 0.8)
    if tipo == "fechar":
        from .sintese import mixar
        x = mixar(impacto("madeira", semente, 1.8), np.pad(impacto("metal", semente + 1, 0.5) * 0.15, (int(0.01 * TAXA), 0)))
        return normalizar(x, 0.9)
    # abrir: trinco + rangido curto
    trinco = impacto("metal", semente, 0.4) * 0.5
    r = porta("ranger", semente)[: int(0.7 * TAXA)]
    return normalizar(np.concatenate([trinco[:int(0.15 * TAXA)], fade(r, 0.02, 0.2)]), 0.85)


def adsr_simples(n, a, r):
    A, R = int(a * TAXA), int(r * TAXA)
    env = np.ones(n)
    env[:A] = np.linspace(0, 1, A)
    env[n - R:] = np.linspace(1, 0, R)
    return env


def whoosh(semente=0, dur=0.6, agudo=1.0):
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    env = np.sin(np.pi * t / dur) ** 2
    cortes = (500 + 3500 * env) * agudo
    x = passa_baixa_variavel(ruido(dur, semente), cortes, ressonancia=0.5) * env
    return normalizar(x, 0.8)


def splash(semente=0, tamanho=1.0):
    dur = 1.0
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    corpo = filtro(ruido(dur, semente) * decaimento(n, 0.15 * tamanho, ataque=0.005), "passa_banda", 1500 / tamanho, 0.5)
    bolhas = np.zeros(n)
    for _ in range(int(14 * tamanho)):
        ini = int(rng.uniform(0.02, 0.5) * TAXA)
        d = rng.uniform(0.02, 0.06)
        m = int(d * TAXA)
        f0 = rng.uniform(500, 2000)
        tt = np.arange(m) / TAXA
        b = np.sin(2 * np.pi * np.cumsum(f0 * (1 + tt * 8)) / TAXA) * np.exp(-tt / (d / 3))
        bolhas[ini:ini + m] += b[:max(0, min(m, n - ini))] * rng.uniform(0.2, 0.5)
    return normalizar(corpo + bolhas, 0.85)


def gota(semente=0):
    rng = np.random.default_rng(semente)
    dur = 0.25
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    f0 = rng.uniform(900, 1700)
    f = f0 * (1 + t * rng.uniform(6, 14))
    x = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.exp(-t / 0.03)
    return normalizar(fade(x, 0.001, 0.02), 0.7)


def trovao(semente=0, distancia=0.5):
    dur = 5.0
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    x = ruido(dur, semente, cor="marrom")
    env = np.zeros(n)
    for _ in range(int(rng.integers(3, 7))):
        ini = rng.uniform(0, 1.2)
        env += decaimento(n, rng.uniform(0.5, 1.5), ataque=0.02) * np.concatenate([np.zeros(int(ini * TAXA)), np.ones(n)])[:n] * rng.uniform(0.4, 1)
    estalo = _estalo(dur, semente, 6000, 0.05) * (1 - distancia) * 2
    x = filtro(x * env, "passa_baixa", 400 + 2000 * (1 - distancia)) + estalo
    return normalizar(reverb(x, 0.35, 3.0)[:n], 0.9)


def sino(freq=660.0, semente=0, dur=3.0):
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    parciais = [(0.5, 1.0, 1.0), (1.0, 0.7, 0.8), (1.19, 0.5, 0.6), (1.56, 0.4, 0.5), (2.0, 0.35, 0.4), (2.74, 0.25, 0.3), (3.76, 0.15, 0.2)]
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / (dur * d)) for r, a, d in parciais)
    return normalizar(fade(x, 0.001, 0.2), 0.8)


def ui(tipo="clique", semente=0):
    """Sons de interface limpos: clique, hover, confirmar, cancelar, notificacao, digitar."""
    def tom(f, d, forma="seno", tau=None):
        n = int(d * TAXA)
        tt = np.arange(n) / TAXA
        s = np.sin(2 * np.pi * f * tt) if forma == "seno" else np.sign(np.sin(2 * np.pi * f * tt)) * 0.4
        return s * np.exp(-tt / (tau or d / 4))
    if tipo == "clique":
        x = tom(1800, 0.04, tau=0.006) + _estalo(0.04, semente, 8000, 0.002)[:int(0.04 * TAXA)] * 0.4
    elif tipo == "hover":
        x = tom(1200, 0.05, tau=0.01) * 0.5
    elif tipo == "confirmar":
        x = np.concatenate([tom(880, 0.08), tom(1320, 0.18)])
    elif tipo == "cancelar":
        x = np.concatenate([tom(660, 0.08), tom(440, 0.18)])
    elif tipo == "notificacao":
        x = np.concatenate([tom(1046, 0.12, tau=0.06), tom(1568, 0.4, tau=0.12)])
        x = reverb(x, 0.2, 0.8).mean(1)
    elif tipo == "digitar":
        x = _estalo(0.05, semente, 5000, 0.004) + np.pad(tom(2400 + semente % 5 * 100, 0.03, tau=0.004) * 0.3, (0, int(0.02 * TAXA)))[:int(0.05 * TAXA)]
    else:
        raise ValueError(tipo)
    return normalizar(fade(x, 0.0005, 0.01), 0.7)


def batimento(bpm=70, batidas=4):
    periodo = 60 / bpm
    n = int(periodo * batidas * TAXA)
    out = np.zeros(n)
    for k in range(batidas):
        for off, a in ((0.0, 1.0), (0.16, 0.7)):
            ini = int((k * periodo + off) * TAXA)
            m = int(0.15 * TAXA)
            tt = np.arange(m) / TAXA
            b = np.sin(2 * np.pi * (55 - tt * 80) * tt) * np.exp(-tt / 0.04) * a
            out[ini:ini + m] += b[:max(0, min(m, n - ini))]
    return normalizar(filtro(out, "passa_baixa", 200), 0.9)


def relogio(batidas=4, bpm=60):
    periodo = 60 / bpm
    n = int(periodo * batidas * TAXA)
    out = np.zeros(n)
    for k in range(batidas):
        tic = impacto("metal", k % 2, 0.15)[: int(0.08 * TAXA)] * (1 if k % 2 == 0 else 0.7)
        ini = int(k * periodo * TAXA)
        out[ini:ini + len(tic)] += tic[: max(0, n - ini)]
    return normalizar(out, 0.7)


SONS_REALISTAS = {
    "passo": (passo, {"superficie": ["terra", "pedra", "madeira", "grama", "neve", "metal", "agua", "cascalho"]}),
    "impacto": (impacto, {"material": ["madeira", "metal", "pedra", "vidro", "carne", "terra"]}),
    "porta": (porta, {"tipo": ["abrir", "fechar", "ranger"]}),
    "ui": (ui, {"tipo": ["clique", "hover", "confirmar", "cancelar", "notificacao", "digitar"]}),
    "whoosh": (whoosh, {}), "splash": (splash, {}), "gota": (gota, {}), "trovao": (trovao, {}),
    "sino": (sino, {}), "batimento": (batimento, {}), "relogio": (relogio, {}),
}
