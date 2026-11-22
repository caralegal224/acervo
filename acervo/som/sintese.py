"""Núcleo de síntese e DSP em numpy: osciladores, envelopes, filtros, efeitos e WAV.

Convenção: sinais mono são arrays 1D float em [-1, 1]; estéreo é (n, 2).
"""
import wave
import numpy as np

TAXA = 44100


def tempo(dur, taxa=TAXA):
    return np.arange(int(round(dur * taxa))) / taxa


def nota_freq(nota):
    """'A4' -> 440.0 ; aceita sustenido '#' e bemol 'b'. Também aceita número MIDI."""
    if isinstance(nota, (int, float)):
        return 440.0 * 2 ** ((nota - 69) / 12)
    nomes = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = nomes[nota[0].upper()]
    i = 1
    if len(nota) > 2 or (len(nota) == 2 and not nota[1].isdigit() and nota[1] != "-"):
        if nota[1] == "#":
            n += 1
            i = 2
        elif nota[1] == "b":
            n -= 1
            i = 2
    oit = int(nota[i:])
    return 440.0 * 2 ** ((n + (oit + 1) * 12 - 69) / 12)


# ----------------------------------------------------------------------------
# Osciladores (aceitam frequência constante ou array por amostra)
# ----------------------------------------------------------------------------
def fase(freq, n, taxa=TAXA, fase0=0.0):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    return (fase0 + np.cumsum(f) / taxa) % 1.0


def _n(freq, dur, taxa):
    """Número de amostras: usa o comprimento do array de frequência, se houver."""
    return len(freq) if np.ndim(freq) else int(round(dur * taxa))


def seno(freq, dur, taxa=TAXA):
    n = _n(freq, dur, taxa)
    return np.sin(2 * np.pi * fase(freq, n, taxa))


def quadrada(freq, dur, duty=0.5, taxa=TAXA):
    n = _n(freq, dur, taxa)
    return np.where(fase(freq, n, taxa) < np.broadcast_to(duty, (n,)), 1.0, -1.0)


def serra(freq, dur, taxa=TAXA):
    n = _n(freq, dur, taxa)
    return fase(freq, n, taxa) * 2 - 1


def triangulo(freq, dur, taxa=TAXA):
    n = _n(freq, dur, taxa)
    p = fase(freq, n, taxa)
    return 1 - 4 * np.abs(p - 0.5)


def serra_suave(freq, dur, harmonicos=24, taxa=TAXA):
    """Serra com banda limitada (aditiva) — sem aliasing, timbre mais 'analógico'."""
    n = _n(freq, dur, taxa)
    p = fase(freq, n, taxa)
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    s = np.zeros(n)
    for k in range(1, harmonicos + 1):
        ganho = (f * k < taxa / 2).astype(float)
        s += ganho * np.sin(2 * np.pi * k * p) / k
    return s * (2 / np.pi)


def ruido(dur, semente=0, taxa=TAXA, cor="branco"):
    rng = np.random.default_rng(semente)
    n = int(round(dur * taxa))
    w = rng.standard_normal(n)
    if cor == "branco":
        return w / 3
    W = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / taxa)
    f[0] = f[1] if n > 1 else 1
    if cor == "rosa":
        W /= np.sqrt(f)
    elif cor == "marrom":
        W /= f
    elif cor == "azul":
        W *= np.sqrt(f)
    s = np.fft.irfft(W, n)
    return s / (np.max(np.abs(s)) + 1e-12)


# ----------------------------------------------------------------------------
# Envelopes
# ----------------------------------------------------------------------------
def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2, taxa=TAXA, sustentar=None):
    """Envelope ADSR com n amostras. `sustentar` = duração (s) antes do release
    (padrão: o que sobrar depois de A+D, reservando R no fim)."""
    A, D, R = int(a * taxa), int(d * taxa), int(r * taxa)
    if sustentar is None:
        S = max(0, n - A - D - R)
    else:
        S = max(0, int(sustentar * taxa) - A - D)
    env = np.concatenate([np.linspace(0, 1, A, endpoint=False), np.linspace(1, s, D, endpoint=False),
                          np.full(S, s), np.linspace(s, 0, R)])
    if len(env) < n:
        env = np.concatenate([env, np.zeros(n - len(env))])
    return env[:n]


def decaimento(n, tau=0.3, taxa=TAXA, ataque=0.002):
    t = np.arange(n) / taxa
    env = np.exp(-t / max(tau, 1e-4))
    A = int(ataque * taxa)
    if A > 0:
        env[:A] *= np.linspace(0, 1, A)
    return env


# ----------------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------------
def filtro(x, tipo="passa_baixa", corte=1000.0, q=0.707, taxa=TAXA, ordem=2):
    """Filtro estático no domínio da frequência (rápido). tipo: passa_baixa,
    passa_alta, passa_banda, rejeita_banda. `ordem` controla a inclinação."""
    x = np.asarray(x, float)
    estereo = x.ndim == 2
    n = x.shape[0]
    pad = int(min(taxa, n) * 0.1)
    xp = np.pad(x, ((0, pad),) + (((0, 0),) if estereo else ()))
    X = np.fft.rfft(xp, axis=0)
    f = np.fft.rfftfreq(xp.shape[0], 1 / taxa)
    r = f / max(corte, 1e-3)
    if tipo == "passa_baixa":
        H = 1 / np.sqrt(1 + r ** (2 * ordem))
        if q > 0.75:
            H *= 1 + (q - 0.707) * np.exp(-((r - 1) ** 2) * 30)
    elif tipo == "passa_alta":
        r = np.where(r == 0, 1e-9, r)
        H = 1 / np.sqrt(1 + (1 / r) ** (2 * ordem))
    elif tipo == "passa_banda":
        largura = 1 / max(q, 0.1)
        H = np.exp(-(np.log2(np.maximum(r, 1e-9)) ** 2) / (2 * (largura * 0.6) ** 2))
    else:
        largura = 1 / max(q, 0.1)
        H = 1 - np.exp(-(np.log2(np.maximum(r, 1e-9)) ** 2) / (2 * (largura * 0.3) ** 2))
    if estereo:
        H = H[:, None]
    return np.fft.irfft(X * H, xp.shape[0], axis=0)[:n]


def passa_baixa_variavel(x, cortes, taxa=TAXA, ressonancia=0.0):
    """Filtro de estado variável (SVF) com corte variando por amostra (laço Python;
    use em sons curtos)."""
    cortes = np.broadcast_to(np.asarray(cortes, float), x.shape)
    g = np.tan(np.pi * np.clip(cortes, 10, taxa * 0.45) / taxa)
    k = 2 - 2 * np.clip(ressonancia, 0, 0.98)
    a1 = 1 / (1 + g * (g + k))
    ic1 = ic2 = 0.0
    out = np.empty_like(x)
    for i in range(len(x)):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + g[i] * a1[i] * v3
        v2 = ic2 + g[i] * v1
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        out[i] = v2
    return out


# ----------------------------------------------------------------------------
# Efeitos
# ----------------------------------------------------------------------------
def distorcer(x, ganho=3.0):
    return np.tanh(x * ganho) / np.tanh(ganho)


def bitcrush(x, bits=8, reduzir=1):
    if reduzir > 1:
        x = np.repeat(x[::int(reduzir)], int(reduzir), axis=0)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(x * q) / q


def eco(x, atraso=0.25, retorno=0.4, repeticoes=4, taxa=TAXA, ping_pong=False):
    d = int(atraso * taxa)
    estereo = x.ndim == 2
    n = len(x) + d * repeticoes
    out = np.zeros((n,) + x.shape[1:])
    out[:len(x)] += x
    g = 1.0
    for k in range(1, repeticoes + 1):
        g *= retorno
        trecho = x * g
        if ping_pong and estereo:
            trecho = trecho[:, ::-1] if k % 2 else trecho
        out[k * d:k * d + len(x)] += trecho
    return out


def resposta_reverb(dur=1.8, taxa=TAXA, semente=7, brilho=0.5, estereo=True, pre_atraso=0.012):
    n = int(round(dur * taxa))
    rng = np.random.default_rng(semente)
    t = np.arange(n) / taxa
    canais = []
    for c in range(2 if estereo else 1):
        r = rng.standard_normal(n) * np.exp(-t * 6.9 / dur)
        r = filtro(r, "passa_baixa", 2000 + 9000 * brilho, taxa=taxa, ordem=1)
        pre = int(pre_atraso * taxa)
        r = np.concatenate([np.zeros(pre), r])[:n]
        canais.append(r)
    r = np.stack(canais, 1) if estereo else canais[0]
    return r / np.sqrt(np.sum(r ** 2, axis=0) + 1e-12)


def convoluir(x, h):
    n = len(x) + len(h) - 1
    N = 1 << int(np.ceil(np.log2(n)))
    if x.ndim == 1 and h.ndim == 2:
        x = np.stack([x, x], 1)
    if x.ndim == 2 and h.ndim == 1:
        h = np.stack([h, h], 1)
    X = np.fft.rfft(x, N, axis=0)
    H = np.fft.rfft(h, N, axis=0)
    return np.fft.irfft(X * H, N, axis=0)[:n]


def reverb(x, mistura=0.25, tamanho=1.8, brilho=0.5, taxa=TAXA):
    h = resposta_reverb(tamanho, taxa, brilho=brilho)
    molhado = convoluir(x, h)
    seco = np.stack([x, x], 1) if x.ndim == 1 else x
    seco = np.pad(seco, ((0, len(molhado) - len(seco)), (0, 0)))
    return seco * (1 - mistura) + molhado * mistura * 0.9


def tremolo(x, vel=6.0, prof=0.5, taxa=TAXA):
    t = np.arange(len(x)) / taxa
    m = 1 - prof * (0.5 + 0.5 * np.sin(2 * np.pi * vel * t))
    return x * (m[:, None] if x.ndim == 2 else m)


def panorama(x, pan=0.0):
    """pan em [-1 (esq), 1 (dir)], lei de potência constante."""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def estereo_largo(x, atraso_ms=12, taxa=TAXA):
    d = int(atraso_ms / 1000 * taxa)
    if x.ndim == 2:
        x = x.mean(1)
    dir_ = np.concatenate([np.zeros(d), x])[:len(x)]
    return np.stack([x, dir_], 1)


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def normalizar(x, pico=0.89):
    m = np.max(np.abs(x))
    return x * (pico / m) if m > 0 else x


def fade(x, entrada=0.005, saida=0.01, taxa=TAXA):
    x = x.copy()
    a, b = int(entrada * taxa), int(saida * taxa)
    if a > 0:
        r = np.linspace(0, 1, min(a, len(x)))
        x[:len(r)] *= r[:, None] if x.ndim == 2 else r
    if b > 0:
        r = np.linspace(1, 0, min(b, len(x)))
        x[len(x) - len(r):] *= r[:, None] if x.ndim == 2 else r
    return x


def cortar_silencio(x, limiar=0.002, margem=0.02, taxa=TAXA):
    env = np.abs(x) if x.ndim == 1 else np.abs(x).max(1)
    idx = np.nonzero(env > limiar)[0]
    if len(idx) == 0:
        return x[:1]
    fim = min(len(x), idx[-1] + int(margem * taxa))
    return x[:fim]


def tornar_loop(x, cruzamento=1.0, taxa=TAXA):
    """Transforma um sinal (gerado mais longo que o necessário) em loop sem emenda:
    o final é misturado ao começo com cross-fade de potência constante."""
    c = int(cruzamento * taxa)
    corpo = x[:-c].copy()
    cauda = x[-c:]
    t = np.linspace(0, np.pi / 2, c)
    fi, fo = np.sin(t), np.cos(t)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    corpo[:c] = corpo[:c] * fi + cauda * fo
    return corpo


def mixar(*faixas):
    n = max(len(f) for f in faixas)
    est = any(f.ndim == 2 for f in faixas)
    out = np.zeros((n, 2)) if est else np.zeros(n)
    for f in faixas:
        if est and f.ndim == 1:
            f = np.stack([f, f], 1)
        out[:len(f)] += f
    return out


def salvar_wav(caminho, x, taxa=TAXA, bits=16):
    x = np.clip(np.asarray(x, float), -1, 1)
    canais = 1 if x.ndim == 1 else x.shape[1]
    if bits == 16:
        dados = (x * 32767).astype("<i2").tobytes()
    else:
        dados = ((x * 127) + 128).astype(np.uint8).tobytes()
    with wave.open(caminho, "wb") as w:
        w.setnchannels(canais)
        w.setsampwidth(bits // 8)
        w.setframerate(taxa)
        w.writeframes(dados)


def ler_wav(caminho):
    with wave.open(caminho, "rb") as w:
        n, c, sw, taxa = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        d = np.frombuffer(w.readframes(n), dtype="<i2" if sw == 2 else np.uint8).astype(float)
    d = d / 32768 if sw == 2 else (d - 128) / 128
    return (d.reshape(-1, c) if c > 1 else d), taxa
