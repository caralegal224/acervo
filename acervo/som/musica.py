"""Compositor procedural de trilhas em loop + jingles, com exportação WAV e MIDI.

Um estilo é um dicionário (veja ESTILOS, ou presets/musica.json):
    bpm, tonica ('D'), escala ('menor'), progressao (graus, 0 = I), compassos,
    instrumentos {melodia, acordes, baixo, arpejo}, acordes ('bloco'|'arpejo'|'pad'|'violao'),
    bateria {peça: "padrão de 16 passos com x/X/."}, swing, reverb, oitava_melodia, densidade.

    from acervo.som import musica
    m = musica.compor("aventura", semente=4)
    musica.salvar(m, "trilha")      # trilha.wav + trilha.mid
"""
import copy
import struct
import numpy as np

from .sintese import TAXA, reverb, normalizar, panorama, salvar_wav, filtro, fade
from . import instrumentos as ins

ESCALAS = {
    "maior": [0, 2, 4, 5, 7, 9, 11], "menor": [0, 2, 3, 5, 7, 8, 10], "menor_harmonica": [0, 2, 3, 5, 7, 8, 11],
    "dorico": [0, 2, 3, 5, 7, 9, 10], "frigio": [0, 1, 3, 5, 7, 8, 10], "lidio": [0, 2, 4, 6, 7, 9, 11],
    "mixolidio": [0, 2, 4, 5, 7, 9, 10], "pentatonica": [0, 2, 4, 7, 9], "pentatonica_menor": [0, 3, 5, 7, 10],
}
NOTAS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
         "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

ESTILOS = {
    "aventura": dict(bpm=128, tonica="D", escala="maior", progressao=[0, 4, 5, 3], compassos=8,
                     instrumentos=dict(melodia="chip_quadrada", acordes="chip_pulso", baixo="chip_triangulo", arpejo=None),
                     acordes="arpejo", bateria=dict(chip_bumbo="x...x...x...x...", chip_caixa="....x.......x...", chip_chimbal="..x...x...x...xx"),
                     swing=0.0, reverb=0.12, oitava_melodia=5, densidade=0.65),
    "masmorra": dict(bpm=84, tonica="A", escala="menor_harmonica", progressao=[0, 5, 3, 4], compassos=8,
                     instrumentos=dict(melodia="flauta", acordes="pad", baixo="baixo", arpejo="harpa"),
                     acordes="pad", bateria=dict(tom_grave="x.......x..x....", chocalho="....x.......x..."),
                     swing=0.0, reverb=0.4, oitava_melodia=5, densidade=0.4),
    "batalha": dict(bpm=150, tonica="E", escala="menor", progressao=[0, 5, 2, 6], compassos=8,
                    instrumentos=dict(melodia="lead", acordes="cordas", baixo="baixo_synth", arpejo=None),
                    acordes="bloco", bateria=dict(bumbo="x..x..x.x..x..x.", caixa="....X.......X..x", chimbal_fechado="x.x.x.x.x.x.x.x.",
                                                  prato_ataque="x..............."),
                    swing=0.0, reverb=0.18, oitava_melodia=5, densidade=0.8),
    "menu": dict(bpm=92, tonica="F", escala="maior", progressao=[0, 5, 3, 4], compassos=8,
                 instrumentos=dict(melodia="kalimba", acordes="pad", baixo="baixo", arpejo="marimba"),
                 acordes="pad", bateria=dict(chocalho="..x...x...x...x.", aro="....x.......x..."),
                 swing=0.15, reverb=0.35, oitava_melodia=5, densidade=0.45),
    "vila": dict(bpm=104, tonica="G", escala="maior", progressao=[0, 3, 0, 4], compassos=8,
                 instrumentos=dict(melodia="flauta", acordes="violao", baixo="baixo", arpejo=None),
                 acordes="violao", bateria=dict(tambor="x.....x.x.......", chocalho="..x...x...x...x."),
                 swing=0.2, reverb=0.25, oitava_melodia=5, densidade=0.55),
    "misterio": dict(bpm=70, tonica="C", escala="frigio", progressao=[0, 1, 0, 6], compassos=8,
                     instrumentos=dict(melodia="sinos", acordes="pad", baixo="baixo", arpejo=None),
                     acordes="pad", bateria=dict(), swing=0.0, reverb=0.55, oitava_melodia=5, densidade=0.3),
    "espacial": dict(bpm=110, tonica="A", escala="dorico", progressao=[0, 5, 3, 6], compassos=8,
                     instrumentos=dict(melodia="lead", acordes="pad", baixo="baixo_synth", arpejo="sinos"),
                     acordes="pad", bateria=dict(bumbo_808="x.......x.......", palmas="....x.......x...", chimbal_fechado="..x...x...x...x."),
                     swing=0.0, reverb=0.35, oitava_melodia=5, densidade=0.5),
    "chefe": dict(bpm=160, tonica="D", escala="menor_harmonica", progressao=[0, 0, 5, 4], compassos=8,
                  instrumentos=dict(melodia="orgao", acordes="cordas", baixo="baixo_synth", arpejo=None),
                  acordes="bloco", bateria=dict(bumbo="x.x.x.x.x.x.x.x.", caixa="....x.......x.x.", chimbal_fechado="xxxxxxxxxxxxxxxx",
                                                prato_ataque="x.......x......."),
                  swing=0.0, reverb=0.25, oitava_melodia=5, densidade=0.85),
    "tranquilo": dict(bpm=76, tonica="E", escala="pentatonica", progressao=[0, 3, 1, 4], compassos=8,
                      instrumentos=dict(melodia="piano", acordes="piano", baixo="baixo", arpejo=None),
                      acordes="arpejo", bateria=dict(), swing=0.1, reverb=0.4, oitava_melodia=5, densidade=0.4),
    "deserto": dict(bpm=96, tonica="D", escala="menor_harmonica", progressao=[0, 1, 0, 6], compassos=8,
                    instrumentos=dict(melodia="flauta", acordes="violao", baixo="baixo", arpejo=None),
                    acordes="violao", bateria=dict(tambor="x..x..x.x..x....", chocalho="x.xxx.xxx.xxx.xx"),
                    swing=0.0, reverb=0.3, oitava_melodia=5, densidade=0.6),
}

# Ritmos de melodia (16 passos por compasso): 'x' = nota nova, '-' = segura, '.' = pausa
RITMOS = ["x-x-x-x-x---x---", "x---x-x-x---x-x-", "x-x-x---x-x-x---", "x--x--x-x-x-x---", "x---x---x-x-x-x-",
          "x-xxx-x-x---x---", "x---x-----x-x---", "x-x-x-x-x-x-x---", "x--x--x---x-x-x-", "x---------x-x---",
          "x-------x-------", "x-x---x---x-x---"]


def _grau_para_midi(grau, escala, tonica_midi):
    n = len(escala)
    oit, idx = divmod(grau, n)
    return tonica_midi + 12 * oit + escala[idx]


def _acorde(raiz, escala, tonica_midi):
    passo = 2 if len(escala) == 7 else 1
    return [_grau_para_midi(raiz + k * passo, escala, tonica_midi) for k in range(3)]


def compor(estilo="aventura", semente=0, **mudancas):
    """Retorna dict com 'eventos' (lista de notas), metadados e o estilo usado."""
    e = copy.deepcopy(ESTILOS[estilo] if isinstance(estilo, str) else estilo)
    e.update(mudancas)
    rng = np.random.default_rng(semente)
    escala = ESCALAS[e["escala"]]
    tonica = NOTAS[e["tonica"]]
    passo_s = 60 / e["bpm"] / 4
    comp_n = int(e["compassos"])
    prog = e["progressao"]
    eventos = []  # (inicio_s, dur_s, parte, instrumento, nota_midi, vel)

    def t(passo):
        sw = e.get("swing", 0) * passo_s * 0.5 if passo % 2 == 1 else 0
        return passo * passo_s + sw

    oit_m = (int(e["oitava_melodia"]) + 1) * 12 + tonica
    raiz_baixo = 3 * 12 + tonica + 12 if tonica < 5 else 3 * 12 + tonica
    raiz_acordes = 4 * 12 + tonica

    # --- melodia com estrutura A A' B A'' --------------------------------
    def frase(n_comp, inicio_comp, grau0):
        notas = []
        g = grau0
        for c in range(n_comp):
            ritmo = RITMOS[int(rng.integers(0, len(RITMOS)))]
            if rng.random() > e["densidade"]:
                ritmo = ritmo.replace("x-x-", "x---")
            acorde_graus = [prog[(inicio_comp + c) % len(prog)] + k * (2 if len(escala) == 7 else 1) for k in range(3)]
            for i, ch in enumerate(ritmo):
                if ch != "x":
                    continue
                d = 1
                while i + d < 16 and ritmo[i + d] == "-":
                    d += 1
                if i % 4 == 0:  # tempo forte: nota do acorde mais próxima
                    alvos = [a + o * len(escala) for a in acorde_graus for o in (-1, 0, 1)]
                    g = min(alvos, key=lambda a: abs(a - g) + rng.random() * 1.5)
                else:
                    g += int(rng.choice([-2, -1, -1, 1, 1, 2, 0]))
                g = int(np.clip(g, -3, len(escala) + 4))
                notas.append([c, i, d, g])
        return notas

    A = frase(2, 0, 0)
    B = frase(2, 4, 2)
    def terminar(fr, grau):
        fr = copy.deepcopy(fr)
        if fr:
            fr[-1][3] = grau
        return fr
    estrutura = [(A, 0), (terminar(A, 4), 2), (B, 4), (terminar(A, 0), 6)]
    vezes = max(1, comp_n // 8)
    for rep in range(vezes):
        for fr, base in estrutura:
            for (c, i, d, g) in fr:
                comp = rep * 8 + base + c
                if comp >= comp_n:
                    continue
                passo = comp * 16 + i
                eventos.append((t(passo), d * passo_s * 0.95, "melodia", e["instrumentos"]["melodia"],
                                _grau_para_midi(g, escala, oit_m), 0.75 + 0.15 * (i % 4 == 0)))

    # --- harmonia, baixo, arpejo -------------------------------------------
    for comp in range(comp_n):
        raiz = prog[comp % len(prog)]
        ac = _acorde(raiz, escala, raiz_acordes)
        ini = comp * 16
        estilo_ac = e["acordes"]
        inst_ac = e["instrumentos"]["acordes"]
        if inst_ac:
            if estilo_ac == "pad" or estilo_ac == "bloco":
                batidas = [0] if estilo_ac == "pad" else [0, 6, 8, 14] if rng.random() < 0.5 else [0, 4, 8, 12]
                dur = 16 if estilo_ac == "pad" else 3
                for b in batidas:
                    for nmidi in ac:
                        eventos.append((t(ini + b), dur * passo_s * 0.98, "acordes", inst_ac, nmidi, 0.5))
            elif estilo_ac == "violao":
                for b in (0, 3, 6, 8, 10, 12, 14):
                    for k, nmidi in enumerate(ac + [ac[0] + 12]):
                        eventos.append((t(ini + b) + k * 0.012, 2 * passo_s, "acordes", inst_ac, nmidi, 0.45 if b % 4 else 0.6))
            else:  # arpejo
                padrao = [0, 1, 2, 1] if rng.random() < 0.5 else [0, 1, 2, 3]
                notas_arp = ac + [ac[0] + 12]
                for k in range(8):
                    eventos.append((t(ini + k * 2), 2 * passo_s * 0.9, "acordes", inst_ac, notas_arp[padrao[k % 4]], 0.5))
        inst_b = e["instrumentos"]["baixo"]
        if inst_b:
            rb = _grau_para_midi(raiz, escala, raiz_baixo - 12)
            padrao_b = [(0, 4, rb), (6, 2, rb), (8, 4, rb + 7 if (rb + 7) % 12 in [(tonica + s) % 12 for s in escala] else rb), (12, 4, rb)]
            if e["bpm"] < 90:
                padrao_b = [(0, 8, rb), (8, 8, rb)]
            for (p0, d, nm) in padrao_b:
                eventos.append((t(ini + p0), d * passo_s * 0.9, "baixo", inst_b, nm, 0.8))
        inst_a = e["instrumentos"].get("arpejo")
        if inst_a:
            notas_arp = [n_ + 12 for n_ in ac] + [ac[0] + 24]
            for k in range(0, 16, 2):
                if rng.random() < 0.7:
                    eventos.append((t(ini + k), passo_s * 1.8, "arpejo", inst_a, notas_arp[int(rng.integers(0, 4))], 0.35))

    # --- bateria ------------------------------------------------------------
    for peca, padrao in e.get("bateria", {}).items():
        for comp in range(comp_n):
            p = padrao
            if comp % 4 == 3 and peca in ("caixa", "chip_caixa", "tom_grave", "tambor"):
                p = p[:12] + "x.xx"  # virada no fim da frase
            for i, ch in enumerate(p):
                if ch in "xX":
                    peca_real = "tom_medio" if peca == "tambor" else peca
                    eventos.append((t(comp * 16 + i), 0.1, "bateria", peca_real, 0, 1.0 if ch == "X" else 0.8))

    duracao = comp_n * 16 * passo_s
    return {"eventos": sorted(eventos), "duracao": duracao, "estilo": e, "semente": semente, "bpm": e["bpm"]}


_PAN = {"melodia": 0.0, "acordes": -0.3, "baixo": 0.0, "arpejo": 0.35, "bateria": 0.0}
_VOL = {"melodia": 0.55, "acordes": 0.3, "baixo": 0.55, "arpejo": 0.28, "bateria": 0.55}
_VOL_PECA = {"chimbal_fechado": 0.35, "chimbal_aberto": 0.35, "chocalho": 0.3, "prato_ataque": 0.4, "chip_chimbal": 0.3,
             "aro": 0.5, "palmas": 0.6, "caixa": 0.75}


def renderizar(musica, loop=True):
    cache = {}
    dur = musica["duracao"]
    cauda = 4.0
    n = int((dur + cauda) * TAXA)
    out = np.zeros((n, 2))
    for (ini, d, parte, inst, nota, vel) in musica["eventos"]:
        chave = (parte, inst, nota, round(d, 3), round(vel, 2))
        if chave not in cache:
            if parte == "bateria":
                s = ins.bateria(inst, semente=nota) * _VOL_PECA.get(inst, 1.0)
            else:
                s = ins.tocar(inst, float(440 * 2 ** ((nota - 69) / 12)), d, vel)
            cache[chave] = s * _VOL[parte]
        s = cache[chave]
        i = int(ini * TAXA)
        m = min(len(s), n - i)
        if m <= 0:
            continue
        pan = _PAN[parte]
        a = (pan + 1) * np.pi / 4
        out[i:i + m, 0] += s[:m] * np.cos(a)
        out[i:i + m, 1] += s[:m] * np.sin(a)
    mr = musica["estilo"].get("reverb", 0.2)
    if mr > 0:
        out = reverb(out, mr, 2.2)[:n]
    corpo = int(round(dur * TAXA))
    if loop:
        res = out[:corpo].copy()
        resto = out[corpo:]
        res[:len(resto)] += resto  # o que soa depois do fim volta para o começo -> loop perfeito
    else:
        res = fade(out, 0, 0.5)
    res = np.tanh(res * 1.2)
    return normalizar(res, 0.85)


# ----------------------------------------------------------------------------
# MIDI
# ----------------------------------------------------------------------------
GM_PROGRAMA = {"piano": 0, "violao": 24, "harpa": 46, "baixo": 33, "baixo_synth": 38, "pad": 89, "cordas": 48, "orgao": 16,
               "flauta": 73, "sinos": 14, "marimba": 12, "kalimba": 108, "chip_quadrada": 80, "chip_pulso": 80,
               "chip_triangulo": 80, "lead": 81, "voz": 52}
GM_BATERIA = {"bumbo": 36, "bumbo_808": 35, "chip_bumbo": 36, "caixa": 38, "chip_caixa": 38, "aro": 37, "palmas": 39,
              "chimbal_fechado": 42, "chip_chimbal": 42, "chimbal_aberto": 46, "prato_ataque": 49, "prato_conducao": 51,
              "tom_grave": 45, "tom_medio": 47, "tom_agudo": 50, "chocalho": 70, "cowbell": 56}


def _vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def salvar_midi(musica, caminho):
    ppq = 480
    bpm = musica["bpm"]
    seg_por_tick = 60 / bpm / ppq
    partes = {}
    for ev in musica["eventos"]:
        partes.setdefault((ev[2], ev[3]), []).append(ev)
    faixas = []
    tempo_us = int(60_000_000 / bpm)
    faixas.append(b"\x00\xff\x51\x03" + tempo_us.to_bytes(3, "big") + b"\x00\xff\x58\x04\x04\x02\x18\x08" + b"\x00\xff\x2f\x00")
    canal = 0
    for (parte, inst), evs in partes.items():
        if parte == "bateria":
            ch = 9
        else:
            ch = canal
            canal += 1
            if canal == 9:
                canal = 10
        msgs = []
        for (ini, d, _, peca, nota, vel) in evs:
            nm = GM_BATERIA.get(peca, 38) if parte == "bateria" else nota
            v = int(np.clip(vel * 110, 1, 127))
            t0 = int(round(ini / seg_por_tick))
            t1 = int(round((ini + d) / seg_por_tick))
            msgs.append((t0, 1, bytes([0x90 | ch, nm, v])))
            msgs.append((t1, 0, bytes([0x80 | ch, nm, 0])))
        msgs.sort(key=lambda m: (m[0], m[1]))
        nome = f"{parte} ({inst})".encode()
        dados = b"\x00\xff\x03" + _vlq(len(nome)) + nome
        if parte != "bateria":
            dados += b"\x00" + bytes([0xC0 | ch, GM_PROGRAMA.get(inst, 0)])
        ultimo = 0
        for (tk, _, msg) in msgs:
            dados += _vlq(tk - ultimo) + msg
            ultimo = tk
        dados += b"\x00\xff\x2f\x00"
        faixas.append(dados)
    with open(caminho, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 1, len(faixas), ppq))
        for d in faixas:
            f.write(b"MTrk" + struct.pack(">I", len(d)) + d)


def salvar(musica, caminho_base, loop=True):
    x = renderizar(musica, loop)
    salvar_wav(caminho_base + ".wav", x)
    salvar_midi(musica, caminho_base + ".mid")
    return x


# ----------------------------------------------------------------------------
# Jingles (curtos, sem loop)
# ----------------------------------------------------------------------------
JINGLES = {
    # (notas [(passo, duracao_passos, midi)], bpm, instrumentos)
    "vitoria": ([(0, 2, 72), (2, 2, 76), (4, 2, 79), (6, 2, 84), (8, 2, 79), (10, 6, 84)], 150, [72, 76, 79]),
    "derrota": ([(0, 4, 67), (4, 4, 66), (8, 4, 65), (12, 12, 64)], 100, [52, 55, 58]),
    "item": ([(0, 1, 76), (1, 1, 79), (2, 1, 84), (3, 4, 88)], 160, None),
    "nivel": ([(0, 1, 72), (1, 1, 74), (2, 1, 76), (3, 1, 77), (4, 1, 79), (5, 1, 81), (6, 1, 83), (7, 6, 84)], 180, [60, 64, 67]),
    "fim_de_jogo": ([(0, 3, 72), (3, 3, 67), (6, 3, 64), (9, 2, 69), (11, 2, 71), (13, 2, 69), (15, 2, 68), (17, 2, 70),
                     (19, 2, 68), (21, 8, 67)], 120, [48, 55]),
    "segredo": ([(0, 1, 79), (1, 1, 78), (2, 1, 75), (3, 1, 69), (4, 1, 68), (5, 1, 76), (6, 1, 80), (7, 4, 84)], 170, None),
    "missao": ([(0, 2, 67), (2, 2, 72), (4, 2, 74), (6, 6, 76), (12, 2, 74), (14, 8, 79)], 130, [60, 64, 67]),
}


def jingle(nome, instrumento="chip_quadrada", acompanhamento="chip_triangulo", reverb_mix=0.2):
    notas, bpm, acorde = JINGLES[nome]
    passo_s = 60 / bpm / 4
    eventos = [(p * passo_s, d * passo_s, "melodia", instrumento, nm, 0.85) for p, d, nm in notas]
    fim = max(p + d for p, d, _ in notas)
    if acorde and acompanhamento:
        ultimo = max(p for p, d, _ in notas)
        for nm in acorde:
            eventos.append((ultimo * passo_s, (fim - ultimo) * passo_s, "acordes", acompanhamento, nm - 12, 0.6))
    m = {"eventos": eventos, "duracao": fim * passo_s + 1.0, "estilo": {"reverb": reverb_mix}, "bpm": bpm}
    return m
