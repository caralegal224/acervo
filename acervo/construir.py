"""Gera o pacote completo de assets a partir de uma receita JSON + catálogo + galeria."""
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image


def _rel(raiz, caminho):
    return os.path.relpath(caminho, raiz).replace(os.sep, "/")


# ----------------------------------------------------------------------------
# Trabalhos individuais (rodam em processos paralelos)
# ----------------------------------------------------------------------------
def _job_textura(raiz, item, cfg):
    from . import texturas
    t = texturas.gerar(item["gerador"], cfg["tamanho"], item.get("semente", 0), **item.get("params", {}))
    pasta = os.path.join(raiz, "texturas", item["nome"])
    arqs = t.salvar(pasta, item["nome"], mapas=cfg.get("mapas", True), pixel=cfg.get("pixel", [32]))
    info = texturas.REGISTRO[item["gerador"]]
    return {"tipo": "textura", "nome": item["nome"], "categoria": info["categoria"], "descricao": info["descricao"],
            "gerador": item["gerador"], "semente": item.get("semente", 0), "params": item.get("params", {}),
            "arquivos": {k: _rel(raiz, v) for k, v in arqs.items()}}


def _job_modelo(raiz, item):
    from . import modelos, render3d, texturas
    from .cor import para_imagem
    pasta = os.path.join(raiz, "modelos")
    os.makedirs(os.path.join(pasta, "previas"), exist_ok=True)
    if item.get("primitiva"):
        m = modelos.PRIMITIVAS[item["primitiva"]]()
        t = texturas.gerar("uv_teste", 512)
        m.textura = t.imagem()
        desc = f"Primitiva '{item['primitiva']}' com UV (textura de teste)."
    elif item.get("terreno"):
        m = modelos.terreno(resolucao=64, semente=item.get("semente", 1))
        desc = "Terreno 20x20 m com cores por altura/inclinação."
    else:
        m = modelos.gerar(item["objeto"], item.get("semente", 0), **item.get("params", {}))
        desc = modelos.OBJETOS[item["objeto"]]["descricao"]
    nome = item["nome"]
    m.salvar_glb(os.path.join(pasta, nome + ".glb"))
    m.salvar_obj(os.path.join(pasta, nome + ".obj"))
    prev = render3d.renderizar(m, 256)
    prev_path = os.path.join(pasta, "previas", nome + ".png")
    prev.save(prev_path)
    quadros = [render3d.renderizar(m, 160, azimute=0.6 + k * 2 * np.pi / 12) for k in range(12)]
    giro = Image.new("RGBA", (160 * 12, 160))
    for k, q in enumerate(quadros):
        giro.paste(q, (k * 160, 0))
    giro_path = os.path.join(pasta, "previas", nome + "_giro.png")
    giro.save(giro_path)
    arqs = {"glb": nome + ".glb", "obj": nome + ".obj", "mtl": nome + ".mtl", "previa": "previas/" + nome + ".png",
            "giro": "previas/" + nome + "_giro.png"}
    if m.textura is not None:
        arqs["textura"] = nome + "_textura.png"
    return {"tipo": "modelo", "nome": nome, "categoria": "primitiva" if item.get("primitiva") else "objeto",
            "descricao": desc, "triangulos": int(len(m.F)), "params": item.get("params", {}),
            "arquivos": {k: "modelos/" + v for k, v in arqs.items()}}


def _converter_ogg(wav):
    if shutil.which("ffmpeg") is None:
        return None
    ogg = wav[:-4] + ".ogg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", ogg], check=False)
    return ogg if os.path.exists(ogg) else None


def _job_som(raiz, tarefa):
    from .som import sfx, instrumentos, ambiente, musica
    from .som.sintese import salvar_wav
    tipo = tarefa["tipo"]
    out = []
    if tipo == "sfx":
        cat = tarefa["categoria"]
        pasta = os.path.join(raiz, "sons", "sfx_retro", cat)
        os.makedirs(pasta, exist_ok=True)
        for k in range(tarefa["variacoes"]):
            p = sfx.sortear(cat, tarefa["semente"] * 1000 + k)
            x = sfx.sintetizar(p)
            base = os.path.join(pasta, f"{cat}_{k + 1:02d}")
            salvar_wav(base + ".wav", x)
            sfx.salvar_params(base + ".json", p)
            out.append({"tipo": "som", "categoria": "sfx_retro", "grupo": cat, "nome": f"{cat}_{k + 1:02d}",
                        "descricao": sfx.CATEGORIAS[cat][1], "duracao": round(len(x) / 44100, 2), "params": p,
                        "arquivos": {"wav": _rel(raiz, base + ".wav"), "json": _rel(raiz, base + ".json")}})
    elif tipo == "realista":
        fn = sfx.SONS_REALISTAS[tarefa["funcao"]][0]
        pasta = os.path.join(raiz, "sons", "sfx_realistas", tarefa["funcao"])
        os.makedirs(pasta, exist_ok=True)
        for k in range(tarefa["variacoes"]):
            params = dict(tarefa["params"])
            if "semente" in fn.__code__.co_varnames:
                params["semente"] = k + 1
            x = fn(**params)
            nome = tarefa["nome"] + (f"_{k + 1:02d}" if tarefa["variacoes"] > 1 else "")
            base = os.path.join(pasta, nome)
            salvar_wav(base + ".wav", x)
            out.append({"tipo": "som", "categoria": "sfx_realistas", "grupo": tarefa["funcao"], "nome": nome,
                        "descricao": f"{tarefa['funcao']} {tarefa['params']}", "duracao": round(len(x) / 44100, 2),
                        "params": params, "arquivos": {"wav": _rel(raiz, base + ".wav")}})
    elif tipo == "instrumento":
        inst = tarefa["instrumento"]
        pasta = os.path.join(raiz, "sons", "instrumentos", inst)
        os.makedirs(pasta, exist_ok=True)
        arqs = {}
        for nota in tarefa["notas"]:
            x = instrumentos.tocar(inst, nota, tarefa["duracao"], 0.8)
            c = os.path.join(pasta, f"{inst}_{nota}.wav")
            salvar_wav(c, x)
            arqs[nota] = _rel(raiz, c)
        out.append({"tipo": "som", "categoria": "instrumentos", "grupo": inst, "nome": inst,
                    "descricao": instrumentos.INSTRUMENTOS[inst][1], "arquivos": arqs})
    elif tipo == "bateria":
        pasta = os.path.join(raiz, "sons", "bateria")
        os.makedirs(pasta, exist_ok=True)
        for peca in tarefa["pecas"]:
            x = instrumentos.bateria(peca)
            c = os.path.join(pasta, peca + ".wav")
            salvar_wav(c, x)
            out.append({"tipo": "som", "categoria": "bateria", "grupo": "bateria", "nome": peca, "descricao": "Peça de bateria",
                        "duracao": round(len(x) / 44100, 2), "arquivos": {"wav": _rel(raiz, c)}})
    elif tipo == "ambiente":
        pasta = os.path.join(raiz, "sons", "ambientes")
        os.makedirs(pasta, exist_ok=True)
        x = ambiente.gerar(tarefa["nome"], tarefa["duracao"], tarefa["semente"])
        c = os.path.join(pasta, tarefa["nome"] + ".wav")
        salvar_wav(c, x)
        arqs = {"wav": _rel(raiz, c)}
        if tarefa.get("ogg") and (o := _converter_ogg(c)):
            arqs["ogg"] = _rel(raiz, o)
        out.append({"tipo": "som", "categoria": "ambientes", "grupo": "ambiente", "nome": tarefa["nome"],
                    "descricao": ambiente.AMBIENTES[tarefa["nome"]][1] + " (loop perfeito)", "duracao": tarefa["duracao"],
                    "arquivos": arqs})
    elif tipo == "musica":
        pasta = os.path.join(raiz, "sons", "musicas")
        os.makedirs(pasta, exist_ok=True)
        m = musica.compor(tarefa["estilo"], tarefa["semente"], **tarefa.get("mudancas", {}))
        base = os.path.join(pasta, tarefa["nome"])
        musica.salvar(m, base)
        with open(base + "_estilo.json", "w", encoding="utf-8") as f:
            json.dump(m["estilo"], f, ensure_ascii=False, indent=2)
        arqs = {"wav": _rel(raiz, base + ".wav"), "mid": _rel(raiz, base + ".mid"), "json": _rel(raiz, base + "_estilo.json")}
        if tarefa.get("ogg") and (o := _converter_ogg(base + ".wav")):
            arqs["ogg"] = _rel(raiz, o)
        e = m["estilo"]
        out.append({"tipo": "som", "categoria": "musicas", "grupo": tarefa["estilo"], "nome": tarefa["nome"],
                    "descricao": f"{e['bpm']} BPM, {e['tonica']} {e['escala']}, loop de {m['duracao']:.1f}s",
                    "duracao": round(m["duracao"], 2), "arquivos": arqs})
    elif tipo == "jingle":
        pasta = os.path.join(raiz, "sons", "jingles")
        os.makedirs(pasta, exist_ok=True)
        m = musica.jingle(tarefa["jingle"], tarefa["instrumento"], tarefa["acompanhamento"])
        base = os.path.join(pasta, tarefa["nome"])
        x = musica.salvar(m, base, loop=False)
        out.append({"tipo": "som", "categoria": "jingles", "grupo": tarefa["jingle"], "nome": tarefa["nome"],
                    "descricao": f"Jingle '{tarefa['jingle']}' ({tarefa['instrumento']})", "duracao": round(len(x) / 44100, 2),
                    "arquivos": {"wav": _rel(raiz, base + ".wav"), "mid": _rel(raiz, base + ".mid")}})
    return out


# ----------------------------------------------------------------------------
# Seções sequenciais (rápidas)
# ----------------------------------------------------------------------------
def _icones(raiz, cfg):
    from . import sprites
    out = []
    for item in cfg["lista"]:
        arqs = {}
        for tam in cfg["tamanhos"]:
            pasta = os.path.join(raiz, "sprites", "icones", str(tam))
            os.makedirs(pasta, exist_ok=True)
            im = sprites.icone(item["icone"], tam, **item.get("cores", {}))
            c = os.path.join(pasta, item["nome"] + ".png")
            im.save(c)
            arqs[str(tam)] = _rel(raiz, c)
        out.append({"tipo": "sprite", "categoria": "icones", "nome": item["nome"], "descricao": sprites.ICONES[item["icone"]]["descricao"],
                    "params": item.get("cores", {}), "arquivos": arqs, "pixel": True})
    # atlas com todos os ícones 16px
    for tam in cfg["tamanhos"]:
        n = len(cfg["lista"])
        col = 16
        atlas = Image.new("RGBA", (col * tam, ((n + col - 1) // col) * tam))
        mapa = {}
        for i, item in enumerate(cfg["lista"]):
            im = Image.open(os.path.join(raiz, "sprites", "icones", str(tam), item["nome"] + ".png"))
            x, y = (i % col) * tam, (i // col) * tam
            atlas.paste(im, (x, y))
            mapa[item["nome"]] = {"x": x, "y": y, "w": tam, "h": tam}
        c = os.path.join(raiz, "sprites", f"atlas_icones_{tam}.png")
        atlas.save(c)
        with open(c[:-4] + ".json", "w") as f:
            json.dump({"imagem": os.path.basename(c), "quadros": mapa}, f, indent=1)
        out.append({"tipo": "sprite", "categoria": "atlas", "nome": f"atlas_icones_{tam}", "descricao": f"Todos os ícones ({tam}px) num atlas + JSON com coordenadas.",
                    "arquivos": {"png": _rel(raiz, c), "json": _rel(raiz, c[:-4] + ".json")}, "pixel": True})
    return out


def _procedurais(raiz, cfg, personagens_cfg):
    from . import sprites
    out = []
    pasta = os.path.join(raiz, "sprites", "procedurais")
    os.makedirs(pasta, exist_ok=True)
    for nome, c in cfg.items():
        folha = sprites.folha_simetricos(c["molde"], c["semente"], 8, 8, c["quadros"])
        caminho = os.path.join(pasta, nome + ".png")
        folha.save(caminho)
        t = folha.height // 8
        out.append({"tipo": "sprite", "categoria": "procedurais", "nome": nome, "pixel": True,
                    "descricao": f"64 {nome} gerados ({t}x{t}px" + (f", {c['quadros']} quadros de animação lado a lado" if c["quadros"] > 1 else "") + ").",
                    "quadro": [t, t], "quadros": c["quadros"], "arquivos": {"png": _rel(raiz, caminho)}})
    pasta = os.path.join(raiz, "sprites", "personagens")
    os.makedirs(pasta, exist_ok=True)
    n = personagens_cfg["quantidade"]
    folha = Image.new("RGBA", (16 * 4, 16 * n))
    for i in range(n):
        qs = sprites.personagem(personagens_cfg["semente"] * 100 + i)
        tira = Image.new("RGBA", (64, 16))
        for k, q in enumerate(qs):
            tira.paste(q, (k * 16, 0))
            folha.paste(q, (k * 16, i * 16))
        tira.save(os.path.join(pasta, f"personagem_{i + 1:02d}.png"))
    caminho = os.path.join(pasta, "todos.png")
    folha.save(caminho)
    out.append({"tipo": "sprite", "categoria": "personagens", "nome": "personagens", "pixel": True, "quadro": [16, 16], "quadros": 4,
                "descricao": f"{n} personagens 16x16 (4 quadros de caminhada por linha). Arquivos individuais na mesma pasta.",
                "arquivos": {"png": _rel(raiz, caminho)}})
    return out


def _efeitos(raiz, cfg):
    from . import efeitos
    out = []
    for tam in cfg["tamanhos"]:
        pasta = os.path.join(raiz, "efeitos", "particulas", str(tam))
        os.makedirs(pasta, exist_ok=True)
        for nome in cfg["particulas"]:
            c = os.path.join(pasta, nome + ".png")
            efeitos.particula(nome, tam).save(c)
    for nome in cfg["particulas"]:
        out.append({"tipo": "efeito", "categoria": "particulas", "nome": nome, "descricao": efeitos.PARTICULAS[nome]["descricao"] + " (branca: tinja na engine)",
                    "arquivos": {str(t): f"efeitos/particulas/{t}/{nome}.png" for t in cfg["tamanhos"]}})
    for nome in cfg["animacoes"]:
        arqs = {}
        for tam in cfg["tamanhos"]:
            pasta = os.path.join(raiz, "efeitos", "animacoes", str(tam))
            os.makedirs(pasta, exist_ok=True)
            qs = efeitos.animacao(nome, tam, cfg["quadros"])
            c = os.path.join(pasta, nome + ".png")
            efeitos.montar_folha(qs).save(c)
            arqs[str(tam)] = _rel(raiz, c)
        out.append({"tipo": "efeito", "categoria": "animacoes", "nome": nome, "descricao": efeitos.ANIMACOES[nome]["descricao"],
                    "quadros": cfg["quadros"], "arquivos": arqs})
    return out


def _interface(raiz, cfg):
    from . import interface as ui
    out = []
    for est in cfg["estilos"]:
        pasta = os.path.join(raiz, "interface", est)
        os.makedirs(pasta, exist_ok=True)
        arqs = {}
        def s(nome, im):
            c = os.path.join(pasta, nome + ".png")
            im.save(c)
            arqs[nome] = _rel(raiz, c)
        s("painel", ui.painel(48, 48, est, moldura=5))
        for st in ("normal", "foco", "pressionado"):
            s(f"botao_{st}", ui.painel(48, 16, est, st, moldura=3))
        for nome, cor in (("vida", "#e43b44"), ("mana", "#3a7bd5"), ("xp", "#3ac05a"), ("energia", "#e8c43a")):
            fundo, pre, ex = ui.barra(64, 10, cor, est, 0.65)
            if nome == "vida":
                s("barra_fundo", fundo)
            s(f"barra_{nome}", pre)
            s(f"barra_{nome}_exemplo", ex)
        s("caixa_vazia", ui.caixa_selecao(12, est, False))
        s("caixa_marcada", ui.caixa_selecao(12, est, True))
        s("slot", ui.slot(24, est))
        s("slot_selecionado", ui.slot(24, est, True))
        tr, bt = ui.slider(64, est)
        s("slider_trilho", tr)
        s("slider_botao", bt)
        # prévia montada
        prev = Image.new("RGBA", (176, 96), (0, 0, 0, 0))
        prev.alpha_composite(ui.painel(96, 64, est, moldura=5), (0, 0))
        prev.alpha_composite(ui.painel(48, 16, est, "normal", moldura=3), (104, 0))
        prev.alpha_composite(ui.painel(48, 16, est, "foco", moldura=3), (104, 20))
        prev.alpha_composite(ui.painel(48, 16, est, "pressionado", moldura=3), (104, 40))
        prev.alpha_composite(ui.barra(64, 10, "#e43b44", est, 0.7)[2], (104, 62))
        prev.alpha_composite(ui.barra(64, 10, "#3a7bd5", est, 0.4)[2], (104, 76))
        prev.alpha_composite(ui.caixa_selecao(12, est, True), (8, 72))
        prev.alpha_composite(ui.slot(24, est, True), (28, 68))
        prev.alpha_composite(ui.slot(24, est), (54, 68))
        s("_previa", prev)
        out.append({"tipo": "interface", "categoria": "ui", "nome": est, "pixel": True,
                    "descricao": "Painel 9-slice (margem 6px), botões em 3 estados, barras, caixa, slot, slider.", "arquivos": arqs,
                    "margem_9slice": 6})
    return out


def _cenarios(raiz, cfg):
    from . import cenarios
    out = []
    for tema in cfg["tilesets"]:
        arqs = {}
        for T in cfg["tamanhos_tile"]:
            pasta = os.path.join(raiz, "cenarios", "tilesets", str(T))
            os.makedirs(pasta, exist_ok=True)
            folha, mapa = cenarios.tileset(tema, T, 1)
            c = os.path.join(pasta, tema + ".png")
            folha.save(c)
            with open(c[:-4] + ".json", "w") as f:
                json.dump({"tamanho_tile": T, "colunas": 8, "bits": {"N": 1, "NE": 2, "L": 4, "SE": 8, "S": 16, "SO": 32, "O": 64, "NO": 128},
                           "mascara_para_indice": {str(k): v for k, v in mapa.items()},
                           "todas_256_mascaras": {str(k): v for k, v in cenarios.mapa_completo_256(mapa).items()}}, f)
            arqs[str(T)] = _rel(raiz, c)
            arqs[f"{T}_json"] = _rel(raiz, c[:-4] + ".json")
            if T == cfg["tamanhos_tile"][0]:
                G = cenarios.terreno_exemplo(28, 12, 3)
                ex = cenarios.montar_mapa(G, folha, mapa, T)
                c2 = os.path.join(pasta, tema + "_exemplo.png")
                ex.save(c2)
                arqs["exemplo"] = _rel(raiz, c2)
        out.append({"tipo": "cenario", "categoria": "tilesets", "nome": tema, "pixel": True,
                    "descricao": "Tileset autotile de 47 peças (blob) + JSON máscara→índice + mapa de exemplo.", "arquivos": arqs})
    W, H = cfg["resolucao_fundo"]
    for tema in cfg["fundos"]:
        pasta = os.path.join(raiz, "cenarios", "fundos", tema)
        os.makedirs(pasta, exist_ok=True)
        camadas = cenarios.fundo(tema, W, H, 1)
        arqs = {}
        for nome, im in camadas:
            c = os.path.join(pasta, nome + ".png")
            im.save(c)
            arqs[nome] = _rel(raiz, c)
        c = os.path.join(pasta, "_composto.png")
        cenarios.compor(camadas).save(c)
        arqs["composto"] = _rel(raiz, c)
        camadas_p = cenarios.fundo(tema, W // 2, H // 2, 1)
        c = os.path.join(pasta, "_composto_pixel.png")
        from .cor import pixelizar
        cenarios.compor(camadas_p).convert("RGB").quantize(24, dither=Image.Dither.NONE).convert("RGB").save(c)
        arqs["composto_pixel"] = _rel(raiz, c)
        out.append({"tipo": "cenario", "categoria": "fundos", "nome": tema,
                    "descricao": f"Fundo parallax {W}x{H} em {len(camadas)} camadas tileáveis na horizontal.", "arquivos": arqs})
    return out


# ----------------------------------------------------------------------------
def construir(saida="pacote", receita=None, secoes=None, processos=None, verbose=True):
    from .receita import receita_padrao
    t0 = time.time()
    if receita is None:
        r = receita_padrao()
    elif isinstance(receita, str):
        with open(receita, encoding="utf-8") as f:
            r = json.load(f)
    else:
        r = receita
    raiz = os.path.abspath(saida)
    os.makedirs(raiz, exist_ok=True)
    todas = ["texturas", "sprites", "efeitos", "interface", "cenarios", "modelos", "sons"]
    secoes = secoes or todas
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    catalogo_path = os.path.join(raiz, "catalogo.json")
    catalogo = []
    if os.path.exists(catalogo_path) and set(secoes) != set(todas):
        with open(catalogo_path, encoding="utf-8") as f:
            antigo = json.load(f)["itens"]
        tipos_secao = {"texturas": {"textura"}, "sprites": {"sprite"}, "efeitos": {"efeito"}, "interface": {"interface"},
                       "cenarios": {"cenario"}, "modelos": {"modelo"}, "sons": {"som"}}
        remover = set().union(*[tipos_secao[s] for s in secoes])
        catalogo = [i for i in antigo if i["tipo"] not in remover]
    processos = processos or max(1, (os.cpu_count() or 2))
    with ProcessPoolExecutor(processos) as ex:
        if "texturas" in secoes:
            cfg = r["texturas"]
            log(f"[texturas] {len(cfg['lista'])} itens...")
            fut = [ex.submit(_job_textura, raiz, it, cfg) for it in cfg["lista"]]
            catalogo += [f.result() for f in fut]
        if "modelos" in secoes:
            cfg = r["modelos"]
            itens = list(cfg["lista"])
            if cfg.get("primitivas"):
                from . import modelos
                itens += [{"nome": "primitiva_" + p, "primitiva": p} for p in modelos.PRIMITIVAS]
            if cfg.get("terreno"):
                itens.append({"nome": "terreno", "terreno": True, "semente": 1})
            log(f"[modelos] {len(itens)} itens...")
            fut = [ex.submit(_job_modelo, raiz, it) for it in itens]
            catalogo += [f.result() for f in fut]
        if "sons" in secoes:
            s = r["sons"]
            tarefas = [dict(tipo="sfx", **c) for c in s["sfx"]]
            tarefas += [dict(tipo="realista", **c) for c in s["realistas"]]
            tarefas += [dict(tipo="instrumento", instrumento=i, notas=s["instrumentos"]["notas"], duracao=s["instrumentos"]["duracao"])
                        for i in s["instrumentos"]["lista"]]
            tarefas.append(dict(tipo="bateria", pecas=s["bateria"]))
            a = s["ambientes"]
            tarefas += [dict(tipo="ambiente", nome=n, duracao=a["duracao"], semente=a["semente"], ogg=s.get("ogg")) for n in a["lista"]]
            tarefas += [dict(tipo="musica", ogg=s.get("ogg"), **m) for m in s["musicas"]]
            tarefas += [dict(tipo="jingle", **j) for j in s["jingles"]]
            log(f"[sons] {len(tarefas)} tarefas...")
            fut = [ex.submit(_job_som, raiz, t) for t in tarefas]
            for f in fut:
                catalogo += f.result()
    if "sprites" in secoes:
        log("[sprites] ícones, procedurais, personagens...")
        catalogo += _icones(raiz, r["icones"])
        catalogo += _procedurais(raiz, r["procedurais"], r["personagens"])
    if "efeitos" in secoes:
        log("[efeitos] partículas e animações...")
        catalogo += _efeitos(raiz, r["efeitos"])
    if "interface" in secoes:
        log("[interface] estilos de UI...")
        catalogo += _interface(raiz, r["interface"])
    if "cenarios" in secoes:
        log("[cenarios] tilesets e fundos...")
        catalogo += _cenarios(raiz, r["cenarios"])
    with open(catalogo_path, "w", encoding="utf-8") as f:
        json.dump({"gerado_em": time.strftime("%Y-%m-%d %H:%M"), "itens": catalogo}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(raiz, "receita_usada.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    from .galeria import gerar_galeria
    gerar_galeria(raiz, catalogo)
    with open(os.path.join(raiz, "LICENCA.txt"), "w", encoding="utf-8") as f:
        f.write(LICENCA)
    log(f"Pronto: {len(catalogo)} itens em {raiz} ({time.time() - t0:.0f}s). Abra galeria.html no navegador.")
    return catalogo


LICENCA = """Acervo — assets procedurais
==========================

Todos os arquivos deste pacote (imagens, modelos 3D, sons, músicas, MIDI) foram
gerados por código e são dedicados ao DOMÍNIO PÚBLICO sob CC0 1.0 Universal:
https://creativecommons.org/publicdomain/zero/1.0/deed.pt_BR

Você pode copiar, modificar, distribuir e usar em projetos comerciais, sem pedir
permissão e sem precisar dar crédito (embora crédito seja sempre bem-vindo).
"""
