"""Receita padrão do pacote: tudo que `python -m acervo construir` gera.

A receita é salva em presets/receita.json. Edite o JSON (mude cores, sementes,
tamanhos, adicione variações) e rode o construtor de novo.
"""


def receita_padrao():
    from . import texturas, sprites, efeitos, modelos
    from .som import sfx, instrumentos, ambiente, musica

    tex = [{"nome": n, "gerador": n, "semente": 1, "params": {}} for n in sorted(texturas.REGISTRO)]
    V = lambda nome, ger, **p: {"nome": nome, "gerador": ger, "semente": p.pop("semente", 2), "params": p}
    tex += [
        V("tijolo_branco", "tijolo", cores=["#b9b4ab", "#d3cec4", "#e6e1d7", "#f3efe7"], cor_rejunte="#8a857c", sujeira=0.15),
        V("tijolo_castelo", "tijolo", cores=["#4a4a52", "#5f5f68", "#76767f", "#8c8c94"], cor_rejunte="#2a2a30", linhas=6, colunas=3, desgaste=0.8),
        V("tijolo_amarelo", "tijolo", cores=["#a8743a", "#c89048", "#d8a860", "#e6c07a"], cor_rejunte="#e8e0d0"),
        V("pedra_masmorra", "pedra", cores=["#22232a", "#33343c", "#45464f", "#575862"], cor_junta="#0e0e12", celulas=5),
        V("pedra_arenito", "pedra", cores=["#8a6a44", "#a88658", "#c4a070", "#d8ba8a"], cor_junta="#4a3420", celulas=7),
        V("paralelepipedo_quente", "paralelepipedo", cores=["#6a5444", "#86705c", "#a08a74", "#b8a28a"], cor_junta="#3a2e24"),
        V("madeira_clara", "madeira", cores=["#a8845a", "#c4a070", "#dcbc8c", "#ecd6ac"]),
        V("madeira_escura", "madeira", cores=["#1e0f08", "#3a1d10", "#5a2e18", "#7a4424"]),
        V("tabuas_cinza", "tabuas", cores=["#4a4a48", "#6a6864", "#8a8680", "#aaa59c"], cor_fresta="#1e1e1c"),
        V("tabuas_vermelhas", "tabuas", cores=["#4a1410", "#7a2418", "#9a3420", "#b04830"], tabuas=6),
        V("tabuas_verticais", "tabuas", direcao="vertical", tabuas=6),
        V("grama_florida", "grama", flores=0.12),
        V("grama_seca", "grama", cores=["#4a4018", "#6a5a22", "#8a7a30", "#aa9a48", "#c8b868"]),
        V("grama_alienigena", "grama", cores=["#1a0a3a", "#3a1a6a", "#5a2a9a", "#8a4ac8", "#c08aff"], flores=0.06,
          cores_flores=["#7affea", "#ffea7a"]),
        V("terra_seca", "terra", cores=["#6a4a2e", "#8a6640", "#a88454", "#c4a06c"], umidade=0.0, pedrinhas=0.2),
        V("terra_vermelha", "terra", cores=["#4a1a0e", "#6e2a16", "#8e3c20", "#ae5430"], cor_pedrinha="#a8988a"),
        V("marmore_preto", "marmore", cor_base="#1a1a1c", cor_nuvem="#2a2a2e", cor_veio="#e8e4dc", cor_veio2="#7a7672"),
        V("marmore_verde", "marmore", cor_base="#1e4a3a", cor_nuvem="#2a5e4a", cor_veio="#dfeee6", cor_veio2="#6a9a84"),
        V("terrazzo", "granito", cores=["#efe9df", "#d84a3a", "#3a7ad8", "#f0c040", "#3a9a5a"], pesos=[0.7, 0.08, 0.08, 0.07, 0.07], graos=24),
        V("azulejo_xadrez", "azulejo", cores=["#f0ede6", "#1e1e22"], padrao="xadrez", rejunte=0.02),
        V("azulejo_portugues", "azulejo", cores=["#f4f1ea", "#2a5aa8", "#e6ecf6"], quantidade=6, variacao=0.04),
        V("azulejo_piscina", "azulejo", cores=["#5ac8e0", "#4ab8d8", "#6ad4e8"], quantidade=16, cor_rejunte="#d8f0f4"),
        V("favo_de_mel", "hexagonos", cores=["#e8a420", "#f0b830", "#d89418"], cor_rejunte="#7a4a08", colunas=10),
        V("tecido_vermelho", "tecido", cor_fio1="#a8201e", cor_fio2="#7a1414", fios=64),
        V("linho", "tecido", cor_fio1="#d8ccb0", cor_fio2="#c4b898", fios=72, felpa=0.5),
        V("couro_preto", "couro", cores=["#08080a", "#16161a", "#24242a", "#34343c"]),
        V("camuflagem_deserto", "camuflagem", cores=["#c8a878", "#a88458", "#8a6a44", "#6a5038"]),
        V("camuflagem_digital", "camuflagem", digital=True, cores=["#5a6a4a", "#3a4a2e", "#8a9a6a", "#2a2a1e"]),
        V("camuflagem_neve", "camuflagem", cores=["#eef2f6", "#b8c0ca", "#8a94a0", "#5a646e"]),
        V("nuvens_tempestade", "nuvens", cor_ceu="#2a3440", cor_ceu2="#4a5664", cor_nuvem="#6a7480", cor_sombra="#1a2028", cobertura=0.75),
        V("nuvens_por_do_sol", "nuvens", cor_ceu="#3a2a6a", cor_ceu2="#e86a5a", cor_nuvem="#ffcc8a", cor_sombra="#a83a5a", cobertura=0.45),
        V("espaco_azul", "espaco", cores_nebulosa=["#02040a", "#0a1a3a", "#1a4a8a", "#3aa8d8", "#c8f4ff"]),
        V("espaco_verde", "espaco", cores_nebulosa=["#020a06", "#0a2a1a", "#1a6a3a", "#6ac86a", "#e8ffc8"]),
        V("cristal_verde", "cristal", cores=["#022a14", "#0a6a3a", "#2ac86a", "#a8ffcc", "#ffffff"]),
        V("cristal_rubi", "cristal", cores=["#2a0208", "#7a0a1a", "#d82a3a", "#ffa8b4", "#ffffff"]),
        V("cobre", "metal_escovado", cores=["#5a2a14", "#8a4424", "#b46a3a", "#d89464"]),
        V("aco_escuro", "metal_escovado", cores=["#1e2024", "#2e3136", "#3e4248", "#50555c"]),
        V("ferrugem_total", "ferrugem", quantidade=0.9),
        V("circuito_azul", "circuito", cor_placa="#0a1a3a", cor_trilha="#2a5aa8", cor_metal="#c8d8e8", cor_chip="#0a0a10"),
        V("painel_branco", "painel_scifi", cores=["#9aa0a8", "#b8bec6", "#d4d8de", "#eef0f2"], cor_luz="#ff7a3a"),
        V("escamas_dragao", "escamas", cores=["#3a0a0a", "#7a1414", "#b82a1e", "#f06a3a"]),
        V("telhado_ardosia", "telhado", cores=["#1e2228", "#2e343c", "#40474f", "#555d66"]),
        V("telhado_verde", "telhado", cores=["#1a3a2a", "#2a5a3a", "#3a7a4a", "#5a9a62"]),
        V("carpete_azul", "carpete", cor1="#1e3a7a", cor2="#e8d8a8", cor3="#7a1e2a"),
        V("pele_alien_roxa", "pele_alien", cores=["#1a0a2a", "#3a1a5a", "#6a3a8a", "#a87ac8"], cor_veia="#0a6a5a"),
        V("lava_azul", "lava", cores_brasa=["#00103a", "#0a3aa8", "#2a8aff", "#a8e8ff"]),
        V("agua_pantano", "agua", cores=["#0e1e0a", "#1e3a14", "#3a5a22", "#7a8a4a"], intensidade=0.5),
        V("ruido_ridged", "ruido_perlin", tipo="ridged"),
        V("ruido_turbulencia", "ruido_perlin", tipo="turbulencia"),
        V("ruido_celular_bordas", "ruido_celular", modo="bordas"),
        V("ruido_celular_mosaico", "ruido_celular", modo="celulas", escala=12),
        V("grade_redonda", "grade_metal", furo="redondo"),
        V("musgo_seco", "musgo", cores=["#2a2a0e", "#4a4a18", "#6a6a24", "#8a8a3a", "#aaa858"]),
        V("ouro_branco", "ouro", cores=["#6a6a6e", "#a8a8ae", "#d4d4da", "#ececf0", "#ffffff"]),
        V("papel_branco", "papel", cores=["#c8c4bc", "#dcd8d0", "#ece8e0", "#f8f6f2"], manchas=0.1),
        V("caixote_escuro", "caixote", cores=["#2a1a0e", "#4a2e18", "#6a4426", "#8a5e38"]),
    ]

    icones = []
    for nome in sprites.ICONES:
        icones.append({"nome": nome, "icone": nome, "cores": {}})
    variacoes = {
        "pocao": [("vermelha", "#d6336c"), ("azul", "#3a7bd5"), ("verde", "#3ab85a"), ("roxa", "#9a4ad8"), ("amarela", "#e8c43a")],
        "gema": [("ciano", "#3fd0e0"), ("rubi", "#e0304e"), ("esmeralda", "#2ec46a"), ("ametista", "#a04ae0"), ("topazio", "#f0b030")],
        "chave": [("ouro", "#e0b13a"), ("prata", "#c0c8d0"), ("bronze", "#c07a3a"), ("rubi", "#d83a4a")],
        "moeda": [("ouro", "#f2c230"), ("prata", "#c8d0d8"), ("bronze", "#c8803a")],
        "escudo": [("azul", "#3a64c8"), ("vermelho", "#c83a3a"), ("verde", "#3a8a4a"), ("ferro", "#7a828c")],
        "coracao": [("vermelho", "#e43b44"), ("azul", "#3a8ae4"), ("dourado", "#f0c040"), ("preto", "#3a3040")],
        "livro": [("roxo", "#6b2fa3"), ("vermelho", "#a32f2f"), ("verde", "#2f7a3a"), ("azul", "#2f4aa3")],
        "cajado": [("gelo", "#47c6ff"), ("fogo", "#ff6a2a"), ("natureza", "#5ad84a"), ("sombra", "#9a4ae0")],
        "espada": [("ferro", "#c9d3dd"), ("ouro", "#f0d070"), ("rubi", "#e0505a"), ("cristal", "#8ae8ff")],
        "estrela": [("amarela", "#ffd23f"), ("azul", "#6ab8ff"), ("rosa", "#ff7ac8")],
        "chama": [("laranja", "#ff7a1a"), ("azul", "#3a8aff"), ("verde", "#4ae05a")],
        "bandeira": [("vermelha", "#e0344a"), ("azul", "#3a6ae0"), ("verde", "#3ac05a")],
    }
    for nome, vs in variacoes.items():
        for sufixo, cor in vs:
            icones.append({"nome": f"{nome}_{sufixo}", "icone": nome, "cores": {"cor": cor}})

    sfx_lista = [{"categoria": c, "variacoes": 6, "semente": 1} for c in sfx.CATEGORIAS]
    realistas = []
    for s in ["terra", "pedra", "madeira", "grama", "neve", "metal", "agua", "cascalho"]:
        realistas.append({"nome": f"passo_{s}", "funcao": "passo", "params": {"superficie": s}, "variacoes": 4})
    for m in ["madeira", "metal", "pedra", "vidro", "carne", "terra"]:
        realistas.append({"nome": f"impacto_{m}", "funcao": "impacto", "params": {"material": m}, "variacoes": 3})
    for t in ["abrir", "fechar", "ranger"]:
        realistas.append({"nome": f"porta_{t}", "funcao": "porta", "params": {"tipo": t}, "variacoes": 1})
    for t in ["clique", "hover", "confirmar", "cancelar", "notificacao", "digitar"]:
        realistas.append({"nome": f"ui_{t}", "funcao": "ui", "params": {"tipo": t}, "variacoes": 1 if t != "digitar" else 4})
    realistas += [
        {"nome": "whoosh", "funcao": "whoosh", "params": {}, "variacoes": 3},
        {"nome": "whoosh_rapido", "funcao": "whoosh", "params": {"dur": 0.3, "agudo": 1.5}, "variacoes": 2},
        {"nome": "splash", "funcao": "splash", "params": {}, "variacoes": 2},
        {"nome": "splash_pequeno", "funcao": "splash", "params": {"tamanho": 0.5}, "variacoes": 2},
        {"nome": "gota", "funcao": "gota", "params": {}, "variacoes": 4},
        {"nome": "trovao_perto", "funcao": "trovao", "params": {"distancia": 0.1}, "variacoes": 1},
        {"nome": "trovao_longe", "funcao": "trovao", "params": {"distancia": 0.8}, "variacoes": 1},
        {"nome": "sino_agudo", "funcao": "sino", "params": {"freq": 880.0}, "variacoes": 1},
        {"nome": "sino_medio", "funcao": "sino", "params": {"freq": 523.25}, "variacoes": 1},
        {"nome": "sino_grave", "funcao": "sino", "params": {"freq": 196.0, "dur": 5.0}, "variacoes": 1},
        {"nome": "batimento", "funcao": "batimento", "params": {}, "variacoes": 1},
        {"nome": "batimento_rapido", "funcao": "batimento", "params": {"bpm": 130, "batidas": 6}, "variacoes": 1},
        {"nome": "relogio", "funcao": "relogio", "params": {}, "variacoes": 1},
    ]

    modelos_lista = [{"nome": n, "objeto": n, "semente": 1, "params": {}} for n in modelos.OBJETOS]
    modelos_lista += [
        {"nome": "pinheiro_neve", "objeto": "pinheiro", "semente": 2, "params": {"cor_folhas": "#d8e4ee"}},
        {"nome": "arvore_outono", "objeto": "arvore", "semente": 3, "params": {"cor_folhas": "#d8762a"}},
        {"nome": "arvore_cerejeira", "objeto": "arvore", "semente": 4, "params": {"cor_folhas": "#f4a8c8"}},
        {"nome": "rocha_grande", "objeto": "rocha", "semente": 5, "params": {"tamanho": 2.5}},
        {"nome": "rocha_arenito", "objeto": "rocha", "semente": 6, "params": {"cor": "#b8925e"}},
        {"nome": "cristal_verde", "objeto": "cristal", "semente": 7, "params": {"cor": "#3ad87a"}},
        {"nome": "cristal_gelo", "objeto": "cristal", "semente": 8, "params": {"cor": "#9ae4ff"}},
        {"nome": "casa_azul", "objeto": "casa", "semente": 1, "params": {"cor_parede": "#a8c4e0", "cor_telhado": "#3a4a6a"}},
        {"nome": "cogumelo_azul", "objeto": "cogumelo", "semente": 1, "params": {"cor_chapeu": "#3a7ad8"}},
        {"nome": "gema_rubi", "objeto": "gema", "semente": 1, "params": {"cor": "#e0304e"}},
    ]

    return {
        "_ajuda": "Edite este arquivo e rode: python -m acervo construir --receita presets/receita.json",
        "texturas": {"tamanho": 512, "pixel": [32], "mapas": True, "lista": tex},
        "icones": {"tamanhos": [16, 32], "lista": icones},
        "procedurais": {"naves": {"molde": "nave", "semente": 1, "quadros": 1}, "criaturas": {"molde": "criatura", "semente": 2, "quadros": 2},
                        "invasores": {"molde": "invasor", "semente": 3, "quadros": 2}, "robos": {"molde": "robo", "semente": 4, "quadros": 2}},
        "personagens": {"quantidade": 16, "semente": 1},
        "efeitos": {"tamanhos": [64, 128], "quadros": 8, "particulas": list(efeitos.PARTICULAS), "animacoes": list(efeitos.ANIMACOES)},
        "interface": {"estilos": ["madeira", "pedra", "metal", "pergaminho", "scifi", "doce", "escuro", "floresta"]},
        "cenarios": {"tilesets": ["campo", "neve", "deserto", "caverna", "castelo", "vulcao", "floresta", "doce"], "tamanhos_tile": [16, 32],
                     "fundos": ["dia", "entardecer", "noite", "inverno", "deserto", "alienigena"], "resolucao_fundo": [640, 360]},
        "modelos": {"lista": modelos_lista, "primitivas": True, "terreno": True},
        "sons": {
            "sfx": sfx_lista, "realistas": realistas,
            "instrumentos": {"lista": list(instrumentos.INSTRUMENTOS), "notas": ["C2", "C3", "C4", "C5", "C6"], "duracao": 0.8},
            "bateria": list(instrumentos.BATERIA),
            "ambientes": {"lista": list(ambiente.AMBIENTES), "duracao": 30, "semente": 1},
            "musicas": [{"nome": e, "estilo": e, "semente": 1} for e in musica.ESTILOS] +
                       [{"nome": "aventura_2", "estilo": "aventura", "semente": 7},
                        {"nome": "batalha_orquestral", "estilo": "batalha", "semente": 3,
                         "mudancas": {"instrumentos": {"melodia": "cordas", "acordes": "cordas", "baixo": "baixo", "arpejo": "harpa"}}},
                        {"nome": "menu_chiptune", "estilo": "menu", "semente": 2,
                         "mudancas": {"instrumentos": {"melodia": "chip_pulso", "acordes": "chip_quadrada", "baixo": "chip_triangulo", "arpejo": None},
                                      "acordes": "arpejo", "bateria": {"chip_bumbo": "x.......x.......", "chip_chimbal": "..x...x...x...x."}}}],
            "jingles": [{"nome": j, "jingle": j, "instrumento": "chip_quadrada", "acompanhamento": "chip_triangulo"} for j in musica.JINGLES] +
                       [{"nome": f"{j}_orquestra", "jingle": j, "instrumento": "cordas", "acompanhamento": "piano"} for j in ("vitoria", "derrota", "missao")],
            "ogg": True,
        },
    }
