"""Instrumentos sintetizados (melódicos) e kit de bateria.

    from acervo.som import instrumentos as ins
    x = ins.tocar("piano", "C4", dur=1.0, vel=0.8)    # array mono
    b = ins.bateria("caixa")
"""
import numpy as np

from .sintese import (TAXA, nota_freq, filtro, ruido, decaimento, normalizar, fade, serra_suave, passa_baixa_variavel,
                      bitcrush, adsr)


def _t(n):
    return np.arange(n) / TAXA


def _amostras(dur):
    return max(1, int(round(dur * TAXA)))


def piano(f, dur, vel):
    n = _amostras(dur + 1.5)
    t = _t(n)
    B = 0.0004
    tau0 = 2.8 * (220 / f) ** 0.5
    x = np.zeros(n)
    for k in range(1, 14):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > TAXA / 2.2:
            break
        a = (1 / k ** (1.4 - 0.5 * vel)) * (1 if k > 1 else 1.2)
        x += a * np.sin(2 * np.pi * fk * t + k) * np.exp(-t * (1 + k * 0.45) / tau0)
    x += filtro(ruido(n / TAXA, int(f)) * decaimento(n, 0.008), "passa_banda", f * 4, 1.0) * 0.15 * vel
    solta = np.ones(n)
    i = _amostras(dur)
    solta[i:] = np.exp(-_t(n - i) / 0.12)
    return x * solta * decaimento(n, 99, ataque=0.002)


def _karplus(f, dur, brilho=0.5, amort=0.996, semente=0):
    N = max(2, int(round(TAXA / f)))
    n = _amostras(dur)
    blocos = n // N + 2
    rng = np.random.default_rng(semente)
    exc = rng.uniform(-1, 1, N)
    exc = filtro(exc, "passa_baixa", 2000 + 10000 * brilho) if N > 16 else exc
    out = np.empty(blocos * N)
    out[:N] = exc
    prev = exc
    for b in range(1, blocos):
        cur = amort * 0.5 * (prev + np.roll(prev, 1))
        out[b * N:(b + 1) * N] = cur
        prev = cur
    # corrige afinação (N inteiro) por reamostragem
    real = TAXA / N
    razao = f / real
    idx = np.arange(int(len(out) / razao)) * razao
    out = np.interp(idx, np.arange(len(out)), out)
    return out[:n]


def violao(f, dur, vel):
    n_total = dur + 1.2
    x = _karplus(f, n_total, 0.35 + 0.5 * vel, 0.997 if f < 400 else 0.995, int(f))
    i = _amostras(dur)
    x[i:] *= np.exp(-_t(len(x) - i) / 0.15)
    return filtro(x, "passa_alta", 60)


def harpa(f, dur, vel):
    x = _karplus(f, dur + 2.0, 0.8, 0.998, int(f) + 1)
    return x * decaimento(len(x), 99, ataque=0.001)


def baixo(f, dur, vel):
    n = _amostras(dur + 0.25)
    x = serra_suave(f, n / TAXA, 10) * 0.6 + np.sin(2 * np.pi * f * _t(n)) * 0.8
    x = filtro(x, "passa_baixa", min(5000, f * (3 + 4 * vel)))
    env = adsr(n, 0.004, 0.25, 0.55, 0.12, sustentar=dur)
    return x * env


def baixo_synth(f, dur, vel):
    n = _amostras(dur + 0.15)
    t = _t(n)
    x = serra_suave(f, n / TAXA, 30) + np.sign(np.sin(2 * np.pi * f * 0.5 * t)) * 0.3
    cortes = f * 1.5 + 3000 * vel * np.exp(-t / 0.08)
    x = passa_baixa_variavel(x, cortes, ressonancia=0.55)
    return x * adsr(n, 0.003, 0.1, 0.7, 0.1, sustentar=dur)


def pad(f, dur, vel):
    n = _amostras(dur + 1.0)
    x = sum(serra_suave(f * d, n / TAXA, 16) for d in (0.995, 1.0, 1.006)) / 3
    x += np.sin(2 * np.pi * f * 0.5 * _t(n)) * 0.3
    x = filtro(x, "passa_baixa", 1800 + 600 * vel)
    return x * adsr(n, 0.45, 0.3, 0.8, 0.9, sustentar=dur)


def cordas(f, dur, vel):
    n = _amostras(dur + 0.5)
    t = _t(n)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.4, 0, 1)
    x = sum(serra_suave(f * d * vib, n / TAXA, 30) for d in (0.997, 1.0, 1.004)) / 3
    x = filtro(x, "passa_baixa", 3500 + 2000 * vel)
    x = filtro(x, "passa_alta", 150)
    return x * adsr(n, 0.12, 0.2, 0.85, 0.4, sustentar=dur)


def orgao(f, dur, vel):
    n = _amostras(dur + 0.08)
    t = _t(n)
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in ((0.5, 0.5), (1, 1), (2, 0.6), (3, 0.4), (4, 0.3), (6, 0.15), (8, 0.12)))
    x *= 1 - 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * 6.5 * t))
    return x * adsr(n, 0.01, 0.05, 0.95, 0.06, sustentar=dur)


def flauta(f, dur, vel):
    n = _amostras(dur + 0.15)
    t = _t(n)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    fase = np.cumsum(f * vib) / TAXA
    x = np.sin(2 * np.pi * fase) + 0.18 * np.sin(4 * np.pi * fase) + 0.05 * np.sin(6 * np.pi * fase)
    sopro = filtro(ruido(n / TAXA, int(f)), "passa_banda", f * 2, 1.5) * 0.12
    return (x + sopro) * adsr(n, 0.06, 0.1, 0.85, 0.12, sustentar=dur)


def sinos(f, dur, vel):
    n = _amostras(dur + 2.5)
    t = _t(n)
    indice = 2.5 * vel * np.exp(-t / 0.6)
    x = np.sin(2 * np.pi * f * t + indice * np.sin(2 * np.pi * f * 3.5 * t))
    return x * decaimento(n, 1.2, ataque=0.002)


def marimba(f, dur, vel):
    n = _amostras(max(dur, 0.2) + 0.8)
    t = _t(n)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / (0.5 * (300 / f) ** 0.4))
    x += 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.05)
    x += 0.15 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.015)
    return x * decaimento(n, 99, ataque=0.001)


def kalimba(f, dur, vel):
    n = _amostras(max(dur, 0.2) + 1.2)
    t = _t(n)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7) + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.04)
    x += 0.1 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.2)
    return x * decaimento(n, 99, ataque=0.0015)


def chip_quadrada(f, dur, vel, duty=0.5):
    n = _amostras(dur + 0.05)
    t = _t(n)
    x = np.where((f * t) % 1 < duty, 0.5, -0.5)
    x = x - (duty - 0.5)  # remove o nível DC de pulsos assimétricos
    return x * adsr(n, 0.002, 0.08, 0.7, 0.04, sustentar=dur)


def chip_pulso(f, dur, vel):
    return chip_quadrada(f, dur, vel, 0.125)


def chip_triangulo(f, dur, vel):
    n = _amostras(dur + 0.03)
    t = _t(n)
    p = (f * t) % 1
    x = np.round((1 - 4 * np.abs(p - 0.5)) * 8) / 8  # 4 bits, como chips antigos
    return x * adsr(n, 0.002, 0.02, 1.0, 0.02, sustentar=dur)


def lead(f, dur, vel):
    n = _amostras(dur + 0.2)
    t = _t(n)
    vib = 1 + 0.008 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) / 0.2, 0, 1)
    x = (serra_suave(f * vib, n / TAXA, 30) + serra_suave(f * vib * 1.007, n / TAXA, 30)) / 2
    x = filtro(x, "passa_baixa", 2500 + 3000 * vel)
    return x * adsr(n, 0.01, 0.15, 0.75, 0.15, sustentar=dur)


def voz(f, dur, vel):
    """Coro 'aah' com formantes."""
    n = _amostras(dur + 0.6)
    t = _t(n)
    vib = 1 + 0.01 * np.sin(2 * np.pi * 5 * t)
    fonte = sum(serra_suave(f * d * vib, n / TAXA, 40) for d in (0.996, 1.0, 1.005)) / 3
    x = sum(filtro(fonte, "passa_banda", fc, q) * g for fc, q, g in ((730, 3, 1.0), (1090, 4, 0.5), (2440, 5, 0.25)))
    return x * adsr(n, 0.25, 0.2, 0.9, 0.5, sustentar=dur)


INSTRUMENTOS = {
    "piano": (piano, "Piano"), "violao": (violao, "Violão (cordas dedilhadas)"), "harpa": (harpa, "Harpa"),
    "baixo": (baixo, "Baixo"), "baixo_synth": (baixo_synth, "Baixo sintetizado com filtro"), "pad": (pad, "Pad (fundo atmosférico)"),
    "cordas": (cordas, "Orquestra de cordas"), "orgao": (orgao, "Órgão"), "flauta": (flauta, "Flauta"),
    "sinos": (sinos, "Sinos FM / celesta"), "marimba": (marimba, "Marimba"), "kalimba": (kalimba, "Kalimba"),
    "chip_quadrada": (chip_quadrada, "Chiptune onda quadrada"), "chip_pulso": (chip_pulso, "Chiptune pulso estreito"),
    "chip_triangulo": (chip_triangulo, "Chiptune triângulo (baixo 8-bit)"), "lead": (lead, "Lead de sintetizador"),
    "voz": (voz, "Coro 'aah'"),
}


def tocar(instrumento, nota, dur=0.5, vel=0.8):
    f = nota_freq(nota) if not isinstance(nota, float) else nota
    x = INSTRUMENTOS[instrumento][0](f, dur, vel)
    return normalizar(fade(x, 0.001, 0.01), 0.9) * (0.4 + 0.6 * vel)


# ----------------------------------------------------------------------------
# Bateria
# ----------------------------------------------------------------------------
def _metalico(dur, freqs=(205.3, 304.4, 369.6, 522.7, 540, 800), semente=0):
    n = _amostras(dur)
    t = _t(n)
    return sum(np.sign(np.sin(2 * np.pi * f * t + i)) for i, f in enumerate(freqs)) / len(freqs)


def bumbo(tom=1.0, dur=0.5, semente=0):
    n = _amostras(dur)
    t = _t(n)
    f = 45 * tom + 110 * tom * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.exp(-t / 0.18)
    clique = filtro(ruido(dur, semente) * np.exp(-t / 0.003), "passa_baixa", 5000) * 0.4
    return x + clique


def bumbo_808(tom=1.0, dur=1.2, semente=0):
    n = _amostras(dur)
    t = _t(n)
    f = 48 * tom + 60 * tom * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.exp(-t / 0.45)
    return np.tanh(x * 1.6)


def caixa(tom=1.0, dur=0.35, semente=0):
    n = _amostras(dur)
    t = _t(n)
    corpo = np.sin(2 * np.pi * 185 * tom * t) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * 330 * tom * t) * np.exp(-t / 0.03)
    esteira = filtro(ruido(dur, semente), "passa_banda", 4000, 0.6) * np.exp(-t / 0.09)
    return corpo * 0.6 + esteira * 1.2


def aro(tom=1.0, dur=0.1, semente=0):
    n = _amostras(dur)
    t = _t(n)
    return (np.sin(2 * np.pi * 1700 * tom * t) * 0.5 + filtro(ruido(dur, semente), "passa_alta", 2000)) * np.exp(-t / 0.012)


def chimbal(aberto=False, dur=None, semente=0):
    dur = dur or (0.6 if aberto else 0.09)
    n = _amostras(dur)
    t = _t(n)
    x = _metalico(dur, semente=semente) * 0.6 + ruido(dur, semente) * 0.4
    x = filtro(x, "passa_alta", 7000, ordem=3)
    return x * np.exp(-t / (0.18 if aberto else 0.022))


def prato(dur=2.2, semente=0, tipo="ataque"):
    n = _amostras(dur)
    t = _t(n)
    x = _metalico(dur, (293, 371, 467, 539, 622, 811, 1063), semente) * 0.5 + ruido(dur, semente) * 0.5
    x = filtro(x, "passa_alta", 4000 if tipo == "ataque" else 2500, ordem=2)
    return x * np.exp(-t / (0.7 if tipo == "ataque" else 1.2)) * decaimento(n, 99, ataque=0.002)


def palmas(dur=0.3, semente=0):
    n = _amostras(dur)
    t = _t(n)
    env = np.zeros(n)
    for k, off in enumerate((0, 0.011, 0.023, 0.034)):
        i = int(off * TAXA)
        env[i:] += np.exp(-_t(n - i) / (0.008 if k < 3 else 0.09))
    return filtro(ruido(dur, semente), "passa_banda", 1200, 1.2) * env


def tambor(tom=1.0, dur=0.6, semente=0):
    n = _amostras(dur)
    t = _t(n)
    f = 110 * tom * (1 + 0.4 * np.exp(-t / 0.05))
    return np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.exp(-t / 0.22) + filtro(ruido(dur, semente) * np.exp(-t / 0.01), "passa_baixa", 3000) * 0.2


def chocalho(dur=0.12, semente=0):
    n = _amostras(dur)
    t = _t(n)
    return filtro(ruido(dur, semente), "passa_alta", 5000) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2


def cowbell(dur=0.4, semente=0):
    n = _amostras(dur)
    t = _t(n)
    x = np.sign(np.sin(2 * np.pi * 540 * t)) + np.sign(np.sin(2 * np.pi * 800 * t))
    return filtro(x, "passa_banda", 900, 1.0) * np.exp(-t / 0.08)


def chip_bumbo(dur=0.2, semente=0):
    n = _amostras(dur)
    t = _t(n)
    f = 60 + 300 * np.exp(-t / 0.02)
    x = np.where((np.cumsum(f) / TAXA) % 1 < 0.5, 1.0, -1.0) * np.exp(-t / 0.06)
    return bitcrush(x, 4)


def chip_caixa(dur=0.2, semente=0):
    n = _amostras(dur)
    t = _t(n)
    return bitcrush(ruido(dur, semente) * 3 * np.exp(-t / 0.05), 4, 4)


def chip_chimbal(dur=0.05, semente=0):
    n = _amostras(dur)
    t = _t(n)
    return bitcrush(filtro(ruido(dur, semente) * 3, "passa_alta", 6000) * np.exp(-t / 0.012), 4, 2)


BATERIA = {
    "bumbo": lambda s=0: bumbo(semente=s), "bumbo_808": lambda s=0: bumbo_808(semente=s), "caixa": lambda s=0: caixa(semente=s),
    "aro": lambda s=0: aro(semente=s), "chimbal_fechado": lambda s=0: chimbal(False, semente=s),
    "chimbal_aberto": lambda s=0: chimbal(True, semente=s), "prato_ataque": lambda s=0: prato(semente=s),
    "prato_conducao": lambda s=0: prato(2.5, s, "conducao"), "palmas": lambda s=0: palmas(semente=s),
    "tom_grave": lambda s=0: tambor(0.75, semente=s), "tom_medio": lambda s=0: tambor(1.0, semente=s),
    "tom_agudo": lambda s=0: tambor(1.35, semente=s), "chocalho": lambda s=0: chocalho(semente=s),
    "cowbell": lambda s=0: cowbell(semente=s), "chip_bumbo": lambda s=0: chip_bumbo(semente=s),
    "chip_caixa": lambda s=0: chip_caixa(semente=s), "chip_chimbal": lambda s=0: chip_chimbal(semente=s),
}


def bateria(peca, semente=0, vel=1.0):
    return normalizar(fade(BATERIA[peca](semente), 0.0005, 0.01), 0.9) * vel
