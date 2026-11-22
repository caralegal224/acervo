"""Ambientes sonoros em loop perfeito (estéreo): vento, chuva, fogo, oceano...

    from acervo.som import ambiente
    x = ambiente.gerar("chuva", duracao=30, semente=1, intensidade=0.8)
"""
import numpy as np

from .sintese import (TAXA, ruido, filtro, passa_baixa_variavel, normalizar, tornar_loop, reverb, decaimento,
                      convoluir, resposta_reverb)


def _lfo_lento(n, semente, vel=0.2, suave=True):
    """Curva aleatória suave em [0,1] (ruído de valor interpolado)."""
    rng = np.random.default_rng(semente)
    pontos = max(4, int(n / TAXA * vel) + 2)
    v = rng.random(pontos)
    x = np.linspace(0, pontos - 1, n)
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f) if suave else f
    i2 = np.minimum(i + 1, pontos - 1)
    return v[i] * (1 - f) + v[i2] * f


def _estereo(gerar_canal, semente):
    return np.stack([gerar_canal(semente), gerar_canal(semente + 1000)], 1)


def _espalhar(n, quantidade, som_fn, rng, pan_amp=0.8):
    out = np.zeros((n, 2))
    for _ in range(int(quantidade)):
        s = som_fn(rng)
        ini = int(rng.integers(0, max(1, n - len(s))))
        pan = rng.uniform(-pan_amp, pan_amp)
        a = (pan + 1) * np.pi / 4
        m = min(len(s), n - ini)
        out[ini:ini + m, 0] += s[:m] * np.cos(a)
        out[ini:ini + m, 1] += s[:m] * np.sin(a)
    return out


def vento(dur, semente=0, intensidade=0.6, **_):
    n = int(round(dur * TAXA))
    def canal(s):
        base = ruido(dur, s, cor="rosa")
        mod = _lfo_lento(n, s + 1, 0.25)
        rajada = _lfo_lento(n, s + 2, 0.08) ** 2
        cortes = 250 + (600 + 1400 * intensidade) * (mod * 0.6 + rajada * 0.8)
        x = passa_baixa_variavel(base, cortes, ressonancia=0.6)
        return x * (0.35 + 0.65 * (0.4 * mod + 0.6 * rajada))
    return _estereo(canal, semente)


def _pingo(rng):
    m = int(rng.uniform(0.004, 0.02) * TAXA)
    t = np.arange(m) / TAXA
    f = rng.uniform(1500, 6000)
    return np.sin(2 * np.pi * f * t * (1 + t * 20)) * np.exp(-t / (m / TAXA / 4)) * rng.uniform(0.05, 0.3)


def chuva(dur, semente=0, intensidade=0.6, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    chiado = np.stack([filtro(ruido(dur, semente + k, cor="rosa"), "passa_banda", 3500, 0.4) for k in (0, 1)], 1)
    chiado *= 0.25 + 0.5 * intensidade
    grave = np.stack([filtro(ruido(dur, semente + 5 + k, cor="marrom"), "passa_baixa", 180) for k in (0, 1)], 1) * 0.4
    pingos = _espalhar(n, dur * (150 + 900 * intensidade), _pingo, rng)
    return chiado + grave + pingos


def _estalo_fogo(rng):
    m = int(rng.uniform(0.002, 0.012) * TAXA)
    s = rng.uniform(-1, 1, m) * np.exp(-np.arange(m) / (m / 3))
    return s * rng.uniform(0.1, 1.0) ** 2


def fogo(dur, semente=0, intensidade=0.6, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    ronco = np.stack([filtro(ruido(dur, semente + k, cor="marrom"), "passa_baixa", 300) for k in (0, 1)], 1)
    ronco *= (0.5 + 0.5 * _lfo_lento(n, semente + 3, 1.5))[:, None] * 0.8
    sopro = np.stack([filtro(ruido(dur, semente + 7 + k), "passa_banda", 1200, 0.5) for k in (0, 1)], 1) * 0.08
    estalos = _espalhar(n, dur * (25 + 70 * intensidade), _estalo_fogo, rng, 0.5)
    estalos = filtro(estalos, "passa_alta", 800)
    return ronco + sopro + estalos * 1.8


def oceano(dur, semente=0, intensidade=0.6, periodo=8.0, **_):
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    rng = np.random.default_rng(semente)
    def canal(s):
        fase = rng.random() * 2 * np.pi
        onda = np.sin(np.pi * t / periodo + fase) ** 2
        onda = onda ** 1.5 * (0.6 + 0.4 * _lfo_lento(n, s, 0.1))
        cortes = 300 + 3500 * onda * (0.5 + 0.5 * intensidade)
        x = passa_baixa_variavel(ruido(dur, s, cor="rosa"), cortes)
        return x * (0.25 + 0.75 * onda)
    return _estereo(canal, semente)


def _passaro(rng):
    notas = int(rng.integers(2, 7))
    f0 = rng.uniform(2200, 4800)
    partes = []
    for _ in range(notas):
        m = int(rng.uniform(0.04, 0.12) * TAXA)
        t = np.arange(m) / TAXA
        desl = rng.uniform(-1, 1) * f0 * 0.4
        f = f0 + desl * t / (m / TAXA) + 300 * np.sin(2 * np.pi * rng.uniform(20, 60) * t)
        s = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.sin(np.pi * t / (m / TAXA)) ** 2
        partes += [s, np.zeros(int(rng.uniform(0.02, 0.08) * TAXA))]
    return np.concatenate(partes) * rng.uniform(0.05, 0.25)


def floresta(dur, semente=0, intensidade=0.5, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    v = vento(dur, semente, 0.25) * 0.35
    folhas = np.stack([filtro(ruido(dur, semente + 20 + k), "passa_alta", 3000) for k in (0, 1)], 1)
    folhas *= _lfo_lento(n, semente + 21, 0.4)[:, None] ** 2 * 0.06
    aves = _espalhar(n, dur * (0.4 + 1.2 * intensidade), _passaro, rng)
    aves = convoluir(aves, resposta_reverb(1.2, brilho=0.6))[:n] * 0.6 + aves
    return v + folhas + aves


def _grilo(rng):
    f = rng.uniform(4200, 5200)
    pulsos = int(rng.integers(3, 6))
    partes = []
    for _ in range(int(rng.integers(2, 5))):
        for _ in range(pulsos):
            m = int(0.012 * TAXA)
            t = np.arange(m) / TAXA
            partes += [np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / 0.012), np.zeros(int(0.008 * TAXA))]
        partes.append(np.zeros(int(rng.uniform(0.15, 0.3) * TAXA)))
    return np.concatenate(partes) * rng.uniform(0.03, 0.12)


def _coruja(rng):
    m = int(0.5 * TAXA)
    t = np.arange(m) / TAXA
    f = 380 + 30 * np.sin(np.pi * t / 0.5)
    s = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.sin(np.pi * t / 0.5) ** 3
    return np.concatenate([s * 0.5, np.zeros(int(0.25 * TAXA)), s]) * 0.12


def noite(dur, semente=0, intensidade=0.5, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    base = vento(dur, semente, 0.15) * 0.2
    grilos = _espalhar(n, dur * (1.5 + 4 * intensidade), _grilo, rng)
    corujas = _espalhar(n, max(1, dur / 15), _coruja, rng, 0.6)
    corujas = convoluir(corujas, resposta_reverb(2.0, brilho=0.3))[:n]
    return base + grilos + corujas


def _gota_caverna(rng):
    m = int(0.12 * TAXA)
    t = np.arange(m) / TAXA
    f0 = rng.uniform(700, 1600)
    return np.sin(2 * np.pi * np.cumsum(f0 * (1 + t * 12)) / TAXA) * np.exp(-t / 0.02) * rng.uniform(0.2, 0.6)


def caverna(dur, semente=0, intensidade=0.5, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    drone = np.stack([filtro(ruido(dur, semente + k, cor="marrom"), "passa_baixa", 120) for k in (0, 1)], 1)
    drone *= (0.6 + 0.4 * _lfo_lento(n, semente + 2, 0.1))[:, None]
    gotas = _espalhar(n, dur * (0.5 + 1.5 * intensidade), _gota_caverna, rng)
    gotas = convoluir(gotas, resposta_reverb(3.5, brilho=0.4))[:n] * 1.2 + gotas * 0.3
    return drone * 0.8 + gotas


def _bolha(rng):
    m = int(rng.uniform(0.01, 0.04) * TAXA)
    t = np.arange(m) / TAXA
    f0 = rng.uniform(400, 1400)
    return np.sin(2 * np.pi * np.cumsum(f0 * (1 + t * 30)) / TAXA) * np.sin(np.pi * t / (m / TAXA)) * rng.uniform(0.02, 0.12)


def riacho(dur, semente=0, intensidade=0.6, **_):
    n = int(round(dur * TAXA))
    rng = np.random.default_rng(semente)
    agua = np.stack([filtro(ruido(dur, semente + k, cor="rosa"), "passa_banda", 1800, 0.5) for k in (0, 1)], 1) * 0.25
    bolhas = _espalhar(n, dur * (60 + 140 * intensidade), _bolha, rng)
    return agua + bolhas


def espaco(dur, semente=0, intensidade=0.5, **_):
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    rng = np.random.default_rng(semente)
    out = np.zeros((n, 2))
    base = rng.choice([55.0, 65.4, 73.4])
    for k, r in enumerate((1, 1.5, 2, 3, 4.01)):
        for c in (0, 1):
            f = base * r * (1 + 0.003 * (c - 0.5))
            lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / rng.uniform(6, 15) + rng.random() * 6)
            out[:, c] += np.sin(2 * np.pi * f * t + rng.random() * 6) * lfo / (k + 1)
    ar = np.stack([filtro(ruido(dur, semente + k, cor="rosa"), "passa_banda", 600, 0.3) for k in (0, 1)], 1) * 0.15
    return out * 0.4 + ar


def nave(dur, semente=0, intensidade=0.5, **_):
    n = int(round(dur * TAXA))
    t = np.arange(n) / TAXA
    rng = np.random.default_rng(semente)
    zumbido = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((50, 1), (100, 0.5), (150, 0.25), (200, 0.12)))
    zumbido = zumbido * (0.9 + 0.1 * np.sin(2 * np.pi * 0.3 * t))
    ventil = filtro(ruido(dur, semente, cor="rosa"), "passa_baixa", 900) * 0.6
    def bip(r):
        m = int(0.08 * TAXA)
        tt = np.arange(m) / TAXA
        return np.sin(2 * np.pi * r.choice([880, 1320, 1760, 2093]) * tt) * np.exp(-tt / 0.03) * 0.12
    bips = _espalhar(n, dur * 0.3 * (0.5 + intensidade), bip, rng)
    return np.stack([zumbido, zumbido], 1) * 0.35 + np.stack([ventil, np.roll(ventil, 1500)], 1) * 0.5 + bips


def tempestade(dur, semente=0, intensidade=0.9, **_):
    from .sfx import trovao
    n = int(round(dur * TAXA))
    x = chuva(dur, semente, intensidade) + vento(dur, semente + 3, 0.8) * 0.5
    rng = np.random.default_rng(semente)
    for k in range(max(1, int(dur / 12))):
        tr = trovao(semente + k, rng.uniform(0.2, 0.8))
        ini = int(rng.uniform(0.05, 0.8) * n)
        m = min(len(tr), n - ini)
        x[ini:ini + m] += tr[:m] * 0.8
    return x


AMBIENTES = {
    "vento": (vento, "Vento com rajadas"), "chuva": (chuva, "Chuva com pingos espalhados"), "fogo": (fogo, "Fogueira/lareira crepitando"),
    "oceano": (oceano, "Ondas do mar"), "floresta": (floresta, "Floresta diurna com pássaros"), "noite": (noite, "Noite com grilos e coruja"),
    "caverna": (caverna, "Caverna com gotas e eco"), "riacho": (riacho, "Riacho/córrego"), "espaco": (espaco, "Drone espacial"),
    "nave": (nave, "Interior de nave (zumbido + bipes)"), "tempestade": (tempestade, "Tempestade com trovões"),
}


def gerar(nome, duracao=30.0, semente=0, intensidade=0.6, cruzamento=2.0, **params):
    fn = AMBIENTES[nome][0]
    x = fn(duracao + cruzamento, semente=semente, intensidade=intensidade, **params)
    x = tornar_loop(x, cruzamento)
    return normalizar(x, 0.8)
