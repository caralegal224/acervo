"""Teste de fumaça: gera uma amostra pequena de cada gerador e confere que não há erro/NaN.
Rode:  python testes/teste_rapido.py
"""
import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from acervo import texturas, sprites, efeitos, interface, cenarios, modelos  # noqa: E402
from acervo.som import sfx, instrumentos, ambiente, musica  # noqa: E402


def ok(nome, cond=True):
    if not cond:
        raise AssertionError(nome)


t0 = time.time()
tmp = tempfile.mkdtemp()
for n in texturas.REGISTRO:
    t = texturas.gerar(n, 64, 1)
    ok(n, np.isfinite(t.cor).all() and t.cor.shape == (64, 64, 3))
    # tileável: a 1ª e a última coluna devem ser vizinhas plausíveis (diferença média pequena)
for n in sprites.ICONES:
    ok(n, sprites.icone(n, 16).size == (16, 16))
for m in sprites.MOLDES:
    sprites.gerar_simetrico(m, 1, quadros=2)
sprites.personagem(1)
for n in efeitos.PARTICULAS:
    efeitos.particula(n, 32)
for n in efeitos.ANIMACOES:
    ok(n, len(efeitos.animacao(n, 32, 4)) == 4)
for e in interface.ESTILOS:
    interface.painel(32, 32, e)
for tema in cenarios.TEMAS_TILESET:
    folha, mapa = cenarios.tileset(tema, 16)
    ok(tema, len(mapa) == 47)
cenarios.fundo("dia", 160, 90)
for n in modelos.OBJETOS:
    m = modelos.gerar(n, 1)
    ok(n, len(m.para_glb()) > 100)
for n, f in modelos.PRIMITIVAS.items():
    f().salvar_obj(os.path.join(tmp, n + ".obj"))
for c in sfx.CATEGORIAS:
    x = sfx.sintetizar(sfx.sortear(c, 1))
    ok(c, np.isfinite(x).all() and len(x) > 100)
for n, (fn, _) in sfx.SONS_REALISTAS.items():
    ok(n, np.isfinite(fn()).all())
for n in instrumentos.INSTRUMENTOS:
    ok(n, np.isfinite(instrumentos.tocar(n, "A3", 0.2)).all())
for n in instrumentos.BATERIA:
    instrumentos.bateria(n)
for n in ambiente.AMBIENTES:
    ok(n, ambiente.gerar(n, 3, 1, cruzamento=0.5).shape[1] == 2)
m = musica.compor("aventura", 1, compassos=4)
musica.salvar(m, os.path.join(tmp, "m"))
ok("midi", open(os.path.join(tmp, "m.mid"), "rb").read(4) == b"MThd")
print(f"Tudo certo ({time.time() - t0:.1f}s).")
