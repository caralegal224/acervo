"""Linha de comando do Acervo.  Rode:  python -m acervo ajuda"""
import argparse
import json
import os
import sys


def _valor(v):
    try:
        return json.loads(v)
    except Exception:
        try:
            return json.loads(v.replace("'", '"'))
        except Exception:
            return v


def _params(lista):
    out = {}
    for item in lista or []:
        if "=" not in item:
            sys.exit(f"Parâmetro inválido '{item}'. Use --p chave=valor")
        k, v = item.split("=", 1)
        out[k.strip()] = _valor(v.strip())
    return out


def _saida(args, nome, ext):
    os.makedirs(args.saida, exist_ok=True)
    return os.path.join(args.saida, f"{nome}.{ext}")


def cmd_listar(args):
    from . import texturas, sprites, efeitos, interface, cenarios, modelos
    from .som import sfx, instrumentos, ambiente, musica
    secoes = {
        "texturas": {k: v["descricao"] for k, v in texturas.REGISTRO.items()},
        "icones": {k: v["descricao"] for k, v in sprites.ICONES.items()},
        "procedurais": {k: "molde simétrico" for k in sprites.MOLDES},
        "particulas": {k: v["descricao"] for k, v in efeitos.PARTICULAS.items()},
        "animacoes": {k: v["descricao"] for k, v in efeitos.ANIMACOES.items()},
        "interface": {k: "estilo de UI" for k in interface.ESTILOS},
        "tilesets": {k: "tema" for k in cenarios.TEMAS_TILESET},
        "fundos": {k: "tema" for k in cenarios.TEMAS_FUNDO},
        "modelos": {**{k: v["descricao"] for k, v in modelos.OBJETOS.items()}, **{k: "primitiva" for k in modelos.PRIMITIVAS}},
        "sfx": {k: v[1] for k, v in sfx.CATEGORIAS.items()},
        "realistas": {k: ", ".join(f"{a}={'|'.join(b)}" for a, b in v[1].items()) for k, v in sfx.SONS_REALISTAS.items()},
        "instrumentos": {k: v[1] for k, v in instrumentos.INSTRUMENTOS.items()},
        "bateria": {k: "" for k in instrumentos.BATERIA},
        "ambientes": {k: v[1] for k, v in ambiente.AMBIENTES.items()},
        "musicas": {k: f"{v['bpm']} BPM {v['tonica']} {v['escala']}" for k, v in musica.ESTILOS.items()},
        "jingles": {k: "" for k in musica.JINGLES},
    }
    alvo = [args.secao] if args.secao else list(secoes)
    for s in alvo:
        print(f"\n== {s} ({len(secoes[s])}) ==")
        for k, d in secoes[s].items():
            print(f"  {k:22s} {d}")
    if args.secao in ("texturas", "icones", "animacoes", "modelos") and args.detalhes:
        reg = {"texturas": texturas.REGISTRO, "icones": sprites.ICONES, "animacoes": efeitos.ANIMACOES, "modelos": modelos.OBJETOS}[args.secao]
        print("\nParâmetros padrão:")
        for k, v in reg.items():
            print(f"  {k}: {json.dumps(v['padrao'], ensure_ascii=False)}")


def cmd_textura(args):
    from . import texturas
    p = _params(args.p)
    if args.listar_params:
        print(json.dumps(texturas.REGISTRO[args.nome]["padrao"], ensure_ascii=False, indent=1))
        return
    t = texturas.gerar(args.nome, args.tamanho, args.semente, **p)
    nome = args.como or f"{args.nome}_{args.semente}"
    arqs = t.salvar(os.path.join(args.saida, nome), nome, mapas=not args.sem_mapas, pixel=args.pixel)
    for k, v in arqs.items():
        print(f"  {k:12s} {v}")


def cmd_icone(args):
    from . import sprites
    im = sprites.icone(args.nome, args.tamanho, **_params(args.p))
    c = _saida(args, args.como or f"{args.nome}_{args.tamanho}", "png")
    im.save(c)
    print(c)


def cmd_procedural(args):
    from . import sprites
    folha = sprites.folha_simetricos(args.molde, args.semente, args.colunas, args.linhas, args.quadros, args.escala)
    c = _saida(args, f"{args.molde}s_{args.semente}", "png")
    folha.save(c)
    print(c)


def cmd_personagem(args):
    from . import sprites
    from PIL import Image
    qs = sprites.personagem(args.semente, **_params(args.p))
    tira = Image.new("RGBA", (64, 16))
    for k, q in enumerate(qs):
        tira.paste(q, (k * 16, 0))
    if args.escala > 1:
        tira = tira.resize((64 * args.escala, 16 * args.escala), Image.NEAREST)
    c = _saida(args, f"personagem_{args.semente}", "png")
    tira.save(c)
    print(c)


def cmd_particula(args):
    from . import efeitos
    c = _saida(args, f"{args.nome}_{args.tamanho}", "png")
    efeitos.particula(args.nome, args.tamanho, args.semente).save(c)
    print(c)


def cmd_animacao(args):
    from . import efeitos
    qs = efeitos.animacao(args.nome, args.tamanho, args.quadros, args.semente, **_params(args.p))
    c = _saida(args, f"{args.nome}_{args.tamanho}", "png")
    efeitos.montar_folha(qs).save(c)
    print(c, f"({args.quadros} quadros de {args.tamanho}px)")


def cmd_painel(args):
    from . import interface
    im = interface.painel(args.largura, args.altura, args.estilo, args.estado, args.moldura, **_params(args.p))
    im = interface.ampliar(im, args.escala)
    c = _saida(args, f"painel_{args.estilo}_{args.largura}x{args.altura}_{args.estado}", "png")
    im.save(c)
    print(c)


def cmd_tileset(args):
    from . import cenarios
    tema = dict(cenarios.TEMAS_TILESET[args.tema])
    tema.update(_params(args.p))
    folha, mapa = cenarios.tileset(tema, args.tile, args.semente)
    c = _saida(args, f"tileset_{args.tema}_{args.tile}", "png")
    folha.save(c)
    with open(c[:-4] + ".json", "w") as f:
        json.dump({"mascara_para_indice": mapa, "todas_256_mascaras": cenarios.mapa_completo_256(mapa)}, f)
    print(c)


def cmd_fundo(args):
    from . import cenarios
    camadas = cenarios.fundo(args.tema, args.largura, args.altura, args.semente)
    pasta = os.path.join(args.saida, f"fundo_{args.tema}_{args.semente}")
    os.makedirs(pasta, exist_ok=True)
    for nome, im in camadas:
        im.save(os.path.join(pasta, nome + ".png"))
    cenarios.compor(camadas).save(os.path.join(pasta, "_composto.png"))
    print(pasta)


def cmd_modelo(args):
    from . import modelos, render3d, texturas
    if args.nome in modelos.PRIMITIVAS:
        m = modelos.PRIMITIVAS[args.nome]()
        if args.textura:
            t = texturas.gerar(args.textura, 512, args.semente)
            m.textura = t.imagem()
    elif args.nome == "terreno":
        p = _params(args.p)
        m = modelos.terreno(semente=args.semente, **p)
    else:
        m = modelos.gerar(args.nome, args.semente, **_params(args.p))
    base = os.path.join(args.saida, f"{args.nome}_{args.semente}")
    os.makedirs(args.saida, exist_ok=True)
    m.salvar_glb(base + ".glb")
    m.salvar_obj(base + ".obj")
    render3d.renderizar(m, 256).save(base + "_previa.png")
    print(base + ".glb", base + ".obj", f"({len(m.F)} triângulos)")


def cmd_sfx(args):
    from .som import sfx
    p_extra = _params(args.p)
    if args.json:
        with open(args.json, encoding="utf-8") as f:
            base = json.load(f)
        base.update(p_extra)
        nome = args.como or os.path.splitext(os.path.basename(args.json))[0] + "_editado"
        x = sfx.sintetizar(base)
        c = _saida(args, nome, "wav")
        sfx.salvar(c, x)
        sfx.salvar_params(c[:-4] + ".json", base)
        print(c)
        return
    if not args.categoria:
        sys.exit("Informe uma categoria (python -m acervo listar sfx) ou --json arquivo.json")
    for k in range(args.variacoes):
        p = sfx.sortear(args.categoria, args.semente * 1000 + k)
        p.update(p_extra)
        x = sfx.sintetizar(p)
        c = _saida(args, f"{args.categoria}_{args.semente}_{k + 1:02d}", "wav")
        sfx.salvar(c, x)
        sfx.salvar_params(c[:-4] + ".json", p)
        print(c)


def cmd_realista(args):
    from .som import sfx
    from .som.sintese import salvar_wav
    fn = sfx.SONS_REALISTAS[args.nome][0]
    p = _params(args.p)
    for k in range(args.variacoes):
        if "semente" in fn.__code__.co_varnames:
            p["semente"] = args.semente + k
        x = fn(**p)
        c = _saida(args, f"{args.nome}_{'_'.join(str(v) for kk, v in p.items() if kk != 'semente')}_{k + 1:02d}".replace("__", "_"), "wav")
        salvar_wav(c, x)
        print(c)


def cmd_nota(args):
    from .som import instrumentos
    from .som.sintese import salvar_wav
    for nota in args.notas:
        x = instrumentos.tocar(args.instrumento, nota, args.dur, args.vel)
        c = _saida(args, f"{args.instrumento}_{nota}", "wav")
        salvar_wav(c, x)
        print(c)


def cmd_bateria(args):
    from .som import instrumentos
    from .som.sintese import salvar_wav
    for peca in args.pecas:
        c = _saida(args, peca, "wav")
        salvar_wav(c, instrumentos.bateria(peca, args.semente))
        print(c)


def cmd_ambiente(args):
    from .som import ambiente
    from .som.sintese import salvar_wav
    x = ambiente.gerar(args.nome, args.duracao, args.semente, **_params(args.p))
    c = _saida(args, f"{args.nome}_{args.semente}", "wav")
    salvar_wav(c, x)
    print(c, f"({args.duracao}s, loop)")


def cmd_musica(args):
    from .som import musica
    estilo = args.estilo
    if args.json:
        with open(args.json, encoding="utf-8") as f:
            estilo = json.load(f)
    m = musica.compor(estilo, args.semente, **_params(args.p))
    nome = args.como or f"{args.estilo or 'musica'}_{args.semente}"
    base = os.path.join(args.saida, nome)
    os.makedirs(args.saida, exist_ok=True)
    musica.salvar(m, base, loop=not args.sem_loop)
    with open(base + "_estilo.json", "w", encoding="utf-8") as f:
        json.dump(m["estilo"], f, ensure_ascii=False, indent=2)
    print(base + ".wav", base + ".mid", f"({m['duracao']:.1f}s)")


def cmd_jingle(args):
    from .som import musica
    m = musica.jingle(args.nome, args.instrumento, args.acompanhamento)
    base = os.path.join(args.saida, f"{args.nome}_{args.instrumento}")
    os.makedirs(args.saida, exist_ok=True)
    musica.salvar(m, base, loop=False)
    print(base + ".wav")


def cmd_construir(args):
    from .construir import construir
    secoes = args.secoes.split(",") if args.secoes else None
    construir(args.saida, args.receita, secoes, args.processos)


def cmd_receita(args):
    from .receita import receita_padrao
    with open(args.arquivo, "w", encoding="utf-8") as f:
        json.dump(receita_padrao(), f, ensure_ascii=False, indent=1)
    print(args.arquivo)


def cmd_galeria(args):
    import http.server
    import functools
    import threading
    import webbrowser
    pasta = os.path.abspath(args.pasta)
    if not os.path.exists(os.path.join(pasta, "galeria.html")):
        sys.exit(f"Não achei galeria.html em {pasta}. Gere o pacote com: python -m acervo construir")
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=pasta)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.porta), h)
    url = f"http://127.0.0.1:{args.porta}/galeria.html"
    print(f"Galeria em {url}  (Ctrl+C para sair)")
    if not args.sem_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m acervo", description="Acervo — gerador de assets procedurais (CC0).")
    sub = ap.add_subparsers(dest="cmd")

    def novo(nome, ajuda, fn, saida="saida"):
        s = sub.add_parser(nome, help=ajuda, description=ajuda)
        s.set_defaults(fn=fn)
        if saida:
            s.add_argument("--saida", default=saida, help="pasta de saída (padrão: %(default)s)")
        return s

    s = novo("listar", "lista tudo que pode ser gerado", cmd_listar, None)
    s.add_argument("secao", nargs="?")
    s.add_argument("--detalhes", action="store_true", help="mostra os parâmetros padrão")
    s = novo("construir", "gera o pacote completo + galeria", cmd_construir, "pacote")
    s.add_argument("--receita", help="receita JSON (padrão: embutida)")
    s.add_argument("--secoes", help="ex.: texturas,sons (padrão: todas)")
    s.add_argument("--processos", type=int, default=None)
    s = novo("receita", "salva a receita padrão em JSON para você editar", cmd_receita, None)
    s.add_argument("arquivo", nargs="?", default="receita.json")
    s = novo("galeria", "abre a galeria num servidor local", cmd_galeria, None)
    s.add_argument("--pasta", default="pacote")
    s.add_argument("--porta", type=int, default=8765)
    s.add_argument("--sem-navegador", action="store_true")

    s = novo("textura", "gera uma textura tileável (+ mapas PBR)", cmd_textura)
    s.add_argument("nome")
    s.add_argument("--tamanho", type=int, default=512)
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--p", action="append", help="parâmetro chave=valor (repita)")
    s.add_argument("--como", help="nome do arquivo")
    s.add_argument("--pixel", type=int, nargs="*", default=[32], help="tamanhos de versão pixel art")
    s.add_argument("--sem-mapas", action="store_true")
    s.add_argument("--listar-params", action="store_true")
    s = novo("icone", "gera um ícone em pixel art", cmd_icone)
    s.add_argument("nome")
    s.add_argument("--tamanho", type=int, default=32)
    s.add_argument("--p", action="append")
    s.add_argument("--como")
    s = novo("procedural", "folha de naves/criaturas/invasores/robôs", cmd_procedural)
    s.add_argument("molde", choices=["nave", "criatura", "invasor", "robo"])
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--colunas", type=int, default=8)
    s.add_argument("--linhas", type=int, default=8)
    s.add_argument("--quadros", type=int, default=1)
    s.add_argument("--escala", type=int, default=1)
    s = novo("personagem", "personagem 16x16 com 4 quadros", cmd_personagem)
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--escala", type=int, default=1)
    s.add_argument("--p", action="append", help="pele, cabelo, roupa, calca, bota = '#hex'")
    s = novo("particula", "textura de partícula", cmd_particula)
    s.add_argument("nome")
    s.add_argument("--tamanho", type=int, default=64)
    s.add_argument("--semente", type=int, default=0)
    s = novo("animacao", "spritesheet de efeito animado", cmd_animacao)
    s.add_argument("nome")
    s.add_argument("--tamanho", type=int, default=64)
    s.add_argument("--quadros", type=int, default=8)
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--p", action="append")
    s = novo("painel", "painel/botão de UI", cmd_painel)
    s.add_argument("estilo")
    s.add_argument("--largura", type=int, default=48)
    s.add_argument("--altura", type=int, default=48)
    s.add_argument("--estado", default="normal", choices=["normal", "foco", "pressionado"])
    s.add_argument("--moldura", type=int, default=4)
    s.add_argument("--escala", type=int, default=1)
    s.add_argument("--p", action="append", help="borda, moldura, fundo = '#hex', raio=N ...")
    s = novo("tileset", "tileset autotile (47 peças)", cmd_tileset)
    s.add_argument("tema")
    s.add_argument("--tile", type=int, default=16)
    s.add_argument("--semente", type=int, default=1)
    s.add_argument("--p", action="append", help="cores_preench, cobertura, contorno, textura...")
    s = novo("fundo", "fundo parallax em camadas", cmd_fundo)
    s.add_argument("tema")
    s.add_argument("--largura", type=int, default=640)
    s.add_argument("--altura", type=int, default=360)
    s.add_argument("--semente", type=int, default=1)
    s = novo("modelo", "modelo 3D (GLB + OBJ)", cmd_modelo)
    s.add_argument("nome")
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--textura", help="para primitivas: nome de textura a aplicar")
    s.add_argument("--p", action="append")

    s = novo("sfx", "efeito sonoro retrô parametrizado", cmd_sfx)
    s.add_argument("categoria", nargs="?")
    s.add_argument("--variacoes", type=int, default=5)
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--json", help="regenera a partir de um JSON de parâmetros")
    s.add_argument("--como")
    s.add_argument("--p", action="append")
    s = novo("realista", "efeito realista (passo, impacto, porta, ui...)", cmd_realista)
    s.add_argument("nome")
    s.add_argument("--variacoes", type=int, default=3)
    s.add_argument("--semente", type=int, default=1)
    s.add_argument("--p", action="append")
    s = novo("nota", "amostras de um instrumento", cmd_nota)
    s.add_argument("instrumento")
    s.add_argument("notas", nargs="+", help="ex.: C4 E4 G4 A#3")
    s.add_argument("--dur", type=float, default=0.8)
    s.add_argument("--vel", type=float, default=0.8)
    s = novo("bateria", "peças de bateria", cmd_bateria)
    s.add_argument("pecas", nargs="+")
    s.add_argument("--semente", type=int, default=0)
    s = novo("ambiente", "ambiente em loop", cmd_ambiente)
    s.add_argument("nome")
    s.add_argument("--duracao", type=float, default=30)
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--p", action="append", help="intensidade=0..1 ...")
    s = novo("musica", "trilha em loop (+ MIDI)", cmd_musica)
    s.add_argument("estilo", nargs="?")
    s.add_argument("--json", help="estilo completo em JSON")
    s.add_argument("--semente", type=int, default=0)
    s.add_argument("--como")
    s.add_argument("--sem-loop", action="store_true")
    s.add_argument("--p", action="append", help="bpm=140, tonica='E', escala='menor', compassos=16 ...")
    s = novo("jingle", "jingle curto", cmd_jingle)
    s.add_argument("nome")
    s.add_argument("--instrumento", default="chip_quadrada")
    s.add_argument("--acompanhamento", default="chip_triangulo")

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return
    args.fn(args)


if __name__ == "__main__":
    main()
