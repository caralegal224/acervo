"""Modelos 3D procedurais: primitivas com UV e objetos low-poly com cores por vértice.

Exporta em OBJ (+MTL) e GLB (glTF 2.0 binário, com textura embutida).
Convenção: Y para cima, 1 unidade = 1 metro, frente olhando para +Z.

    from acervo import modelos
    m = modelos.gerar("barril", semente=2)
    m.salvar_glb("barril.glb")
    m.salvar_obj("barril.obj")
"""
import io
import json
import os
import struct
import numpy as np

from .cor import hex_rgb


class Malha:
    def __init__(self, V, F, UV=None, N=None, C=None):
        self.V = np.asarray(V, dtype=np.float64).reshape(-1, 3)
        self.F = np.asarray(F, dtype=np.int64).reshape(-1, 3)
        self.UV = None if UV is None else np.asarray(UV, dtype=np.float64).reshape(-1, 2)
        self.C = None if C is None else np.asarray(C, dtype=np.float64).reshape(-1, 3)
        self.N = np.asarray(N, dtype=np.float64).reshape(-1, 3) if N is not None else self._normais_suaves()
        self.textura = None   # caminho/PIL.Image da cor base (opcional)
        self.textura_normal = None
        self.cor_base = (1.0, 1.0, 1.0)
        self.rugosidade = 0.8
        self.metalico = 0.0

    # --- geometria -----------------------------------------------------------
    def _normais_suaves(self):
        N = np.zeros_like(self.V)
        a, b, c = self.V[self.F[:, 0]], self.V[self.F[:, 1]], self.V[self.F[:, 2]]
        fn = np.cross(b - a, c - a)
        for k in range(3):
            np.add.at(N, self.F[:, k], fn)
        n = np.linalg.norm(N, axis=1, keepdims=True)
        return N / np.where(n == 0, 1, n)

    def limpar(self, eps=1e-12):
        """Remove triângulos degenerados (área ~0), vértices não usados e
        garante normais unitárias."""
        a, b, c = self.V[self.F[:, 0]], self.V[self.F[:, 1]], self.V[self.F[:, 2]]
        area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
        F = self.F[area > eps]
        usados = np.unique(F)
        novo = np.full(len(self.V), -1)
        novo[usados] = np.arange(len(usados))
        self.F = novo[F]
        self.V = self.V[usados]
        self.N = self.N[usados]
        if self.UV is not None:
            self.UV = self.UV[usados]
        if self.C is not None:
            self.C = self.C[usados]
        n = np.linalg.norm(self.N, axis=1, keepdims=True)
        ruins = (n[:, 0] < 1e-8) | ~np.isfinite(n[:, 0])
        self.N = np.where(ruins[:, None], [0.0, 1.0, 0.0], self.N / np.where(n == 0, 1, n))
        return self

    def tangentes(self):
        """Tangentes por vértice (xyz + sinal w), necessárias para mapas normais."""
        T = np.zeros_like(self.V)
        B = np.zeros_like(self.V)
        v0, v1, v2 = (self.V[self.F[:, k]] for k in range(3))
        w0, w1, w2 = (self.UV[self.F[:, k]] for k in range(3))
        e1, e2 = v1 - v0, v2 - v0
        d1, d2 = w1 - w0, w2 - w0
        r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
        r = np.where(np.abs(r) < 1e-12, 1e-12, r)
        t = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
        bt = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None]
        for k in range(3):
            np.add.at(T, self.F[:, k], t)
            np.add.at(B, self.F[:, k], bt)
        T = T - self.N * np.sum(self.N * T, 1, keepdims=True)
        n = np.linalg.norm(T, axis=1, keepdims=True)
        T = np.where(n < 1e-9, np.cross(self.N, [0.0, 0.0, 1.0]) + [1e-6, 0, 0], T)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        w = np.where(np.sum(np.cross(self.N, T) * B, 1) < 0, -1.0, 1.0)
        return np.concatenate([T, w[:, None]], 1)

    def achatar(self):
        """Sombreamento facetado (low-poly): duplica vértices por face."""
        self.limpar()
        idx = self.F.reshape(-1)
        V = self.V[idx]
        UV = None if self.UV is None else self.UV[idx]
        C = None if self.C is None else self.C[idx]
        F = np.arange(len(idx)).reshape(-1, 3)
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        fn = np.cross(b - a, c - a)
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        out = Malha(V, F, UV, np.repeat(fn, 3, 0), C)
        out._copiar_material(self)
        return out

    def _copiar_material(self, o):
        self.textura, self.textura_normal = o.textura, o.textura_normal
        self.cor_base, self.rugosidade, self.metalico = o.cor_base, o.rugosidade, o.metalico

    def colorir(self, cor):
        self.C = np.tile(hex_rgb(cor), (len(self.V), 1))
        return self

    def transformar(self, mover=(0, 0, 0), escala=(1, 1, 1), girar_y=0.0, girar_x=0.0, girar_z=0.0):
        escala = np.broadcast_to(np.asarray(escala, float), (3,))
        def rot(ax, ang):
            c, s = np.cos(ang), np.sin(ang)
            if ax == "x":
                return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
            if ax == "y":
                return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
            return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        R = rot("y", girar_y) @ rot("x", girar_x) @ rot("z", girar_z)
        self.V = (self.V * escala) @ R.T + np.asarray(mover, float)
        n = (self.N / escala) @ R.T
        self.N = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        return self

    def copia(self):
        m = Malha(self.V.copy(), self.F.copy(), None if self.UV is None else self.UV.copy(), self.N.copy(),
                  None if self.C is None else self.C.copy())
        m._copiar_material(self)
        return m

    @staticmethod
    def unir(malhas):
        V, F, UV, N, C = [], [], [], [], []
        base = 0
        tem_uv = all(m.UV is not None for m in malhas)
        tem_c = any(m.C is not None for m in malhas)
        for m in malhas:
            V.append(m.V)
            N.append(m.N)
            F.append(m.F + base)
            if tem_uv:
                UV.append(m.UV)
            if tem_c:
                C.append(m.C if m.C is not None else np.ones((len(m.V), 3)))
            base += len(m.V)
        out = Malha(np.concatenate(V), np.concatenate(F), np.concatenate(UV) if tem_uv else None,
                    np.concatenate(N), np.concatenate(C) if tem_c else None)
        out._copiar_material(malhas[0])
        return out

    def limites(self):
        return self.V.min(0), self.V.max(0)

    # --- exportação ----------------------------------------------------------
    def salvar_obj(self, caminho, nome_material=None):
        self.limpar()
        base = os.path.splitext(caminho)[0]
        nome = os.path.basename(base)
        nome_material = nome_material or nome
        os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
        tex_arquivo = None
        if self.textura is not None:
            tex_arquivo = nome + "_textura.png"
            _como_imagem(self.textura).save(os.path.join(os.path.dirname(caminho) or ".", tex_arquivo))
        with open(base + ".mtl", "w") as f:
            f.write(f"# Acervo — material de {nome}\nnewmtl {nome_material}\n")
            f.write("Kd %.4f %.4f %.4f\nKs 0.05 0.05 0.05\nNs 20\nd 1\nillum 2\n" % tuple(self.cor_base))
            if tex_arquivo:
                f.write(f"map_Kd {tex_arquivo}\n")
        with open(caminho, "w") as f:
            f.write(f"# Acervo — {nome} ({len(self.V)} vértices, {len(self.F)} triângulos)\n")
            f.write(f"mtllib {nome}.mtl\no {nome}\n")
            for i, v in enumerate(self.V):
                if self.C is not None:  # cor por vértice (extensão aceita por Blender/MeshLab)
                    c = self.C[i]
                    f.write("v %.5f %.5f %.5f %.4f %.4f %.4f\n" % (v[0], v[1], v[2], c[0], c[1], c[2]))
                else:
                    f.write("v %.5f %.5f %.5f\n" % tuple(v))
            if self.UV is not None:
                for t in self.UV:
                    f.write("vt %.5f %.5f\n" % tuple(t))
            for n in self.N:
                f.write("vn %.4f %.4f %.4f\n" % tuple(n))
            f.write(f"usemtl {nome_material}\ns off\n")
            for a, b, c in self.F + 1:
                if self.UV is not None:
                    f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")
                else:
                    f.write(f"f {a}//{a} {b}//{b} {c}//{c}\n")

    def salvar_glb(self, caminho):
        os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
        with open(caminho, "wb") as f:
            f.write(self.para_glb())

    def para_glb(self):
        self.limpar()
        blobs, views, accessors = [], [], []
        def add(arr, alvo=None):
            dados = arr.tobytes()
            off = sum(len(b) for b in blobs)
            pad = (-len(dados)) % 4
            blobs.append(dados + b"\x00" * pad)
            v = {"buffer": 0, "byteOffset": off, "byteLength": len(dados)}
            if alvo:
                v["target"] = alvo
            views.append(v)
            return len(views) - 1
        def acc(arr, tipo, comp=5126, minmax=False):
            vi = add(arr, 34963 if comp == 5125 else 34962)
            a = {"bufferView": vi, "componentType": comp, "count": int(arr.shape[0]), "type": tipo}
            if minmax:
                a["min"] = arr.min(0).tolist()
                a["max"] = arr.max(0).tolist()
            accessors.append(a)
            return len(accessors) - 1
        attrs = {"POSITION": acc(self.V.astype(np.float32), "VEC3", minmax=True),
                 "NORMAL": acc(self.N.astype(np.float32), "VEC3")}
        if self.UV is not None:
            uv = self.UV.astype(np.float32).copy()
            uv[:, 1] = 1 - uv[:, 1]  # glTF: origem no canto superior esquerdo
            attrs["TEXCOORD_0"] = acc(uv, "VEC2")
        if self.textura_normal is not None and self.UV is not None:
            tg = self.tangentes().astype(np.float32)
            tg[:, 3] *= -1  # V invertido no glTF inverte a bitangente
            attrs["TANGENT"] = acc(tg, "VEC4")
        if self.C is not None:
            attrs["COLOR_0"] = acc(np.clip(self.C, 0, 1).astype(np.float32), "VEC3")
        ind = acc(self.F.astype(np.uint32).reshape(-1), "SCALAR", comp=5125)
        pbr = {"baseColorFactor": [*map(float, self.cor_base), 1.0], "metallicFactor": float(self.metalico),
               "roughnessFactor": float(self.rugosidade)}
        mat = {"name": "material", "pbrMetallicRoughness": pbr, "doubleSided": False}
        gltf_extra = {}
        imagens, texs = [], []
        for chave, img in (("base", self.textura), ("normal", self.textura_normal)):
            if img is None:
                continue
            buf = io.BytesIO()
            _como_imagem(img).save(buf, "PNG")
            vi = add(np.frombuffer(buf.getvalue(), dtype=np.uint8))
            imagens.append({"bufferView": vi, "mimeType": "image/png"})
            texs.append({"source": len(imagens) - 1, "sampler": 0})
            if chave == "base":
                pbr["baseColorTexture"] = {"index": len(texs) - 1}
            else:
                mat["normalTexture"] = {"index": len(texs) - 1}
        if imagens:
            gltf_extra = {"images": imagens, "textures": texs,
                          "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]}
        binario = b"".join(blobs)
        gltf = {"asset": {"version": "2.0", "generator": "Acervo"}, "scene": 0, "scenes": [{"nodes": [0]}],
                "nodes": [{"mesh": 0, "name": "modelo"}],
                "meshes": [{"primitives": [{"attributes": attrs, "indices": ind, "material": 0}]}],
                "materials": [mat], "buffers": [{"byteLength": len(binario)}], "bufferViews": views,
                "accessors": accessors, **gltf_extra}
        js = json.dumps(gltf, separators=(",", ":")).encode()
        js += b" " * ((-len(js)) % 4)
        total = 12 + 8 + len(js) + 8 + len(binario)
        return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js +
                struct.pack("<II", len(binario), 0x004E4942) + binario)


def _como_imagem(img):
    from PIL import Image
    return Image.open(img) if isinstance(img, str) else img


# ----------------------------------------------------------------------------
# Primitivas
# ----------------------------------------------------------------------------
def plano(tamanho=1.0, divisoes=1):
    n = int(divisoes) + 1
    t = np.linspace(-0.5, 0.5, n) * tamanho
    X, Z = np.meshgrid(t, t)
    V = np.stack([X.ravel(), np.zeros(n * n), Z.ravel()], 1)
    s = np.linspace(0, 1, n)
    U, W = np.meshgrid(s, s)
    UV = np.stack([U.ravel(), 1 - W.ravel()], 1)
    F = []
    for j in range(n - 1):
        for i in range(n - 1):
            a = j * n + i
            F += [[a, a + n, a + 1], [a + 1, a + n, a + n + 1]]
    return Malha(V, F, UV, np.tile([0, 1, 0], (n * n, 1)))


def cubo(tamanho=1.0):
    h = tamanho / 2
    faces = [((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
             ((1, 0, 0), (0, 0, -1), (0, 1, 0)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
             ((0, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, -1, 0), (1, 0, 0), (0, 0, 1))]
    V, N, UV, F = [], [], [], []
    for k, (n, uu, vv) in enumerate(faces):
        n, uu, vv = map(np.array, (n, uu, vv))
        for (a, b) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            V.append((n + uu * a + vv * b) * h)
            N.append(n)
            UV.append(((a + 1) / 2, (b + 1) / 2))
        o = k * 4
        F += [[o, o + 1, o + 2], [o, o + 2, o + 3]]
    return Malha(V, F, UV, N)


def caixa(largura=1, altura=1, profundidade=1):
    return cubo(1).transformar(escala=(largura, altura, profundidade))


def esfera(raio=0.5, segmentos=32, aneis=16):
    V, UV = [], []
    for j in range(aneis + 1):
        th = np.pi * j / aneis
        for i in range(segmentos + 1):
            ph = 2 * np.pi * i / segmentos
            V.append((np.sin(th) * np.cos(ph), np.cos(th), -np.sin(th) * np.sin(ph)))
            UV.append((i / segmentos, 1 - j / aneis))
    V = np.array(V)
    F = []
    w = segmentos + 1
    for j in range(aneis):
        for i in range(segmentos):
            a = j * w + i
            if j != 0:
                F.append([a, a + w, a + 1])
            if j != aneis - 1:
                F.append([a + 1, a + w, a + w + 1])
    return Malha(V * raio, F, UV, V)


def icosfera(raio=0.5, subdivisoes=2):
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    for _ in range(int(subdivisoes)):
        cache, F2 = {}, []
        def meio(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = meio(a, b), meio(b, c), meio(c, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = F2
    V = np.array(V)
    UV = np.stack([0.5 + np.arctan2(-V[:, 2], V[:, 0]) / (2 * np.pi), 0.5 + np.arcsin(V[:, 1]) / np.pi], 1)
    return Malha(V * raio, F, UV, V)


def cilindro(raio=0.5, altura=1.0, segmentos=24, tampas=True, raio_topo=None, aneis=1, perfil=None):
    """perfil: função t(0..1)->multiplicador de raio (ex.: barril abaulado)."""
    raio_topo = raio if raio_topo is None else raio_topo
    V, UV, N, F = [], [], [], []
    w = segmentos + 1
    for j in range(aneis + 1):
        t = j / aneis
        r = raio + (raio_topo - raio) * t
        if perfil:
            r *= perfil(t)
        y = -altura / 2 + altura * t
        for i in range(w):
            a = 2 * np.pi * i / segmentos
            V.append((np.cos(a) * r, y, -np.sin(a) * r))
            UV.append((i / segmentos, t))
            N.append((np.cos(a), (raio - raio_topo) / altura, -np.sin(a)))
    for j in range(aneis):
        for i in range(segmentos):
            a = j * w + i
            F += [[a, a + 1, a + w], [a + 1, a + w + 1, a + w]]
    m = Malha(V, F, UV, N)
    m.N = m._normais_suaves()
    partes = [m]
    if tampas:
        for topo in (False, True):
            r = (raio_topo if topo else raio) * (perfil(1.0 if topo else 0.0) if perfil else 1)
            if r <= 1e-6:
                continue
            y = altura / 2 if topo else -altura / 2
            Vt = [(0, y, 0)] + [(np.cos(2 * np.pi * i / segmentos) * r, y, -np.sin(2 * np.pi * i / segmentos) * r) for i in range(segmentos)]
            UVt = [(0.5, 0.5)] + [(0.5 + 0.5 * np.cos(2 * np.pi * i / segmentos), 0.5 + 0.5 * np.sin(2 * np.pi * i / segmentos)) for i in range(segmentos)]
            Ft = [[0, 1 + i, 1 + (i + 1) % segmentos] if topo else [0, 1 + (i + 1) % segmentos, 1 + i] for i in range(segmentos)]
            partes.append(Malha(Vt, Ft, UVt, np.tile([0, 1 if topo else -1, 0], (segmentos + 1, 1))))
    return Malha.unir(partes)


def cone(raio=0.5, altura=1.0, segmentos=24):
    return cilindro(raio, altura, segmentos, True, raio_topo=0.0)


def toro(raio=0.5, espessura=0.18, segmentos=32, lados=16):
    V, UV, N, F = [], [], [], []
    for j in range(segmentos + 1):
        a = 2 * np.pi * j / segmentos
        for i in range(lados + 1):
            b = 2 * np.pi * i / lados
            n = np.array([np.cos(a) * np.cos(b), np.sin(b), -np.sin(a) * np.cos(b)])
            c = np.array([np.cos(a) * raio, 0, -np.sin(a) * raio])
            V.append(c + n * espessura)
            N.append(n)
            UV.append((j / segmentos, i / lados))
    w = lados + 1
    for j in range(segmentos):
        for i in range(lados):
            a = j * w + i
            F += [[a, a + w, a + 1], [a + 1, a + w, a + w + 1]]
    return Malha(V, F, UV, N)


def capsula(raio=0.3, altura=1.2, segmentos=24, aneis=8):
    V, UV = [], []
    meio = altura / 2 - raio
    linhas = []
    for j in range(aneis + 1):
        th = (np.pi / 2) * j / aneis
        linhas.append((np.cos(th), np.sin(th), meio))
    for j in range(aneis + 1):
        th = np.pi / 2 + (np.pi / 2) * j / aneis
        linhas.append((np.cos(th), np.sin(th), -meio))
    Nn = []
    for k, (cy, sr, off) in enumerate(linhas):
        for i in range(segmentos + 1):
            ph = 2 * np.pi * i / segmentos
            n = np.array([sr * np.cos(ph), cy, -sr * np.sin(ph)])
            V.append(n * raio + [0, off, 0])
            Nn.append(n)
            UV.append((i / segmentos, 1 - k / (len(linhas) - 1)))
    F = []
    w = segmentos + 1
    for j in range(len(linhas) - 1):
        for i in range(segmentos):
            a = j * w + i
            F += [[a, a + w, a + 1], [a + 1, a + w, a + w + 1]]
    return Malha(V, F, UV, Nn)


def terreno(tamanho=20.0, resolucao=64, altura=4.0, semente=0, cores=True, escala_ruido=3):
    from .ruido import fbm
    n = int(resolucao) + 1
    s = np.linspace(0, 1, n)
    U, W = np.meshgrid(s, s)
    H = fbm(U % 1.0, W % 1.0, int(escala_ruido), 6, semente=semente) * 0.5 + 0.5
    H = H ** 1.6
    m = plano(tamanho, resolucao)
    m.V[:, 1] = H.ravel() * altura
    m.N = m._normais_suaves()
    if cores:
        from .cor import rampa
        inclin = 1 - m.N[:, 1]
        t = H.ravel()
        c = rampa(t, [(0, "#c9b27a"), (0.12, "#c9b27a"), (0.18, "#5f8f3a"), (0.5, "#3f6f2a"), (0.68, "#6f6a60"),
                      (0.82, "#8a857a"), (0.9, "#f0f0f4"), (1, "#ffffff")])
        rocha = np.clip((inclin - 0.25) * 4, 0, 1)[:, None]
        m.C = c * (1 - rocha) + hex_rgb("#6f6a60") * rocha
    return m


# ----------------------------------------------------------------------------
# Objetos low-poly (cores por vértice) e texturizados
# ----------------------------------------------------------------------------
OBJETOS = {}


def objeto_def(nome, descricao, **padrao):
    def deco(fn):
        OBJETOS[nome] = {"fn": fn, "padrao": padrao, "descricao": descricao}
        return fn
    return deco


def _variar_cor(m, rng, amp=0.08):
    m.C = np.clip(m.C * (1 + (rng.random((len(m.C), 1)) - 0.5) * amp * 2), 0, 1)
    return m


@objeto_def("pinheiro", "Pinheiro low-poly.", cor_folhas="#2f6a3a", cor_tronco="#6b4a2a", andares=3, altura=3.0)
def _pinheiro(rng, p):
    h = p["altura"]
    partes = [cilindro(0.12 * h / 3, h * 0.3, 6).transformar((0, h * 0.15, 0)).colorir(p["cor_tronco"])]
    n = int(p["andares"])
    for k in range(n):
        r = (0.75 - k * 0.18) * h / 3
        alt = h * 0.42
        y = h * 0.25 + k * h * 0.22 + alt / 2
        c = cone(r, alt, 7).transformar((0, y, 0), girar_y=rng.random() * 6).colorir(p["cor_folhas"])
        c.C *= 0.85 + 0.12 * k
        partes.append(c)
    return _variar_cor(Malha.unir(partes).achatar(), rng)


@objeto_def("arvore", "Árvore de copa arredondada.", cor_folhas="#4f8f34", cor_tronco="#6b4a2a", altura=3.0)
def _arvore(rng, p):
    h = p["altura"]
    partes = [cilindro(0.13 * h / 3, h * 0.55, 6, raio_topo=0.08 * h / 3).transformar((0, h * 0.27, 0)).colorir(p["cor_tronco"])]
    for k in range(3):
        r = (0.55 + rng.random() * 0.25) * h / 3
        ic = icosfera(r, 1)
        ic.V *= 1 + (rng.random((len(ic.V), 1)) - 0.5) * 0.25
        off = (rng.uniform(-0.3, 0.3) * h / 3, h * (0.62 + rng.random() * 0.2), rng.uniform(-0.3, 0.3) * h / 3)
        partes.append(ic.transformar(off).colorir(p["cor_folhas"]))
    return _variar_cor(Malha.unir(partes).achatar(), rng, 0.12)


@objeto_def("rocha", "Rocha irregular.", cor="#7a756c", tamanho=1.0, irregularidade=0.35)
def _rocha(rng, p):
    ic = icosfera(0.5, 2)
    n = ic.V / np.linalg.norm(ic.V, axis=1, keepdims=True)
    r = np.ones(len(n))
    for _ in range(7):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        r += np.cos(n @ d * rng.uniform(1.5, 4) + rng.random() * 6) * p["irregularidade"] / 3
    ic.V = n * r[:, None] * 0.5 * p["tamanho"]
    ic.V[:, 1] = np.maximum(ic.V[:, 1], -0.2 * p["tamanho"]) + 0.2 * p["tamanho"]
    ic.V *= [rng.uniform(0.9, 1.4), rng.uniform(0.6, 0.9), rng.uniform(0.9, 1.3)]
    ic.colorir(p["cor"])
    return _variar_cor(ic.achatar(), rng, 0.15)


@objeto_def("cristal", "Aglomerado de cristais.", cor="#9a5ae8", quantidade=5)
def _cristal(rng, p):
    partes = []
    for k in range(int(p["quantidade"])):
        h = rng.uniform(0.5, 1.3) if k else 1.5
        corpo = cilindro(0.12, h, 6, tampas=False).transformar((0, h / 2, 0))
        ponta = cone(0.12, 0.25, 6).transformar((0, h + 0.125, 0))
        c = Malha.unir([corpo, ponta]).colorir(p["cor"])
        c.transformar(girar_x=rng.uniform(-0.5, 0.5) if k else 0, girar_z=rng.uniform(-0.6, 0.6) if k else 0, girar_y=rng.random() * 6)
        c.C *= 0.8 + 0.4 * rng.random()
        partes.append(c)
    m = Malha.unir(partes).achatar()
    return m


@objeto_def("barril", "Barril de madeira com aros.", cor_madeira="#8a5a30", cor_aro="#3a3a40")
def _barril(rng, p):
    m = cilindro(0.4, 1.0, 14, True, aneis=8, perfil=lambda t: 1 + 0.15 * np.sin(np.pi * t)).transformar((0, 0.5, 0))
    m.colorir(p["cor_madeira"])
    y = m.V[:, 1]
    aro = (np.abs(y - 0.15) < 0.06) | (np.abs(y - 0.85) < 0.06)
    m.C[aro] = hex_rgb(p["cor_aro"])
    m = m.achatar()
    # faixas de tábuas: alterna o tom por face
    tons = 0.85 + 0.15 * (np.arange(len(m.C)) // 6 % 2)
    m.C *= tons[:, None]
    return m


@objeto_def("caixote", "Caixote de madeira (texturizado, 1x1x1).")
def _caixote(rng, p):
    from . import texturas
    t = texturas.gerar("caixote", 256, int(rng.integers(0, 1000)))
    m = cubo(1).transformar((0, 0.5, 0))
    m.textura = t.imagem()
    from .cor import para_imagem
    m.textura_normal = para_imagem(t.normal())
    return m


@objeto_def("casa", "Casinha com telhado, porta e janelas.", cor_parede="#e8dcc0", cor_telhado="#b3452f",
            cor_porta="#6b3f22", cor_janela="#7ac4e8")
def _casa(rng, p):
    paredes = caixa(2, 1.4, 1.6).transformar((0, 0.7, 0)).colorir(p["cor_parede"])
    # telhado prismático
    V = np.array([[-1.15, 1.4, 0.95], [1.15, 1.4, 0.95], [0, 2.3, 0.95], [-1.15, 1.4, -0.95], [1.15, 1.4, -0.95], [0, 2.3, -0.95]])
    F = [[0, 1, 2], [4, 3, 5], [0, 2, 5], [0, 5, 3], [1, 4, 5], [1, 5, 2], [0, 3, 4], [0, 4, 1]]
    telhado = Malha(V, F).colorir(p["cor_telhado"])
    oitao = Malha([[-1, 1.4, 0.8], [1, 1.4, 0.8], [0, 2.2, 0.8], [1, 1.4, -0.8], [-1, 1.4, -0.8], [0, 2.2, -0.8]],
                  [[0, 1, 2], [3, 4, 5]]).colorir(p["cor_parede"])
    porta = caixa(0.45, 0.8, 0.05).transformar((0, 0.4, 0.81)).colorir(p["cor_porta"])
    j1 = caixa(0.4, 0.35, 0.05).transformar((-0.6, 0.85, 0.81)).colorir(p["cor_janela"])
    j2 = caixa(0.4, 0.35, 0.05).transformar((0.6, 0.85, 0.81)).colorir(p["cor_janela"])
    chamine = caixa(0.25, 0.6, 0.25).transformar((0.55, 2.1, -0.3)).colorir("#8a5040")
    return Malha.unir([paredes, telhado, oitao, porta, j1, j2, chamine]).achatar()


@objeto_def("bau", "Baú de tesouro.", cor_madeira="#8a5228", cor_metal="#d9b24a")
def _bau(rng, p):
    corpo = caixa(1.0, 0.5, 0.6).transformar((0, 0.25, 0)).colorir(p["cor_madeira"])
    tampa = cilindro(0.3, 1.0, 10, True).transformar((0, 0.5, 0), girar_z=np.pi / 2).colorir(p["cor_madeira"])
    keep = tampa.V[:, 1] >= 0.499
    tampa.V[:, 1] = np.maximum(tampa.V[:, 1], 0.5)
    tampa.C *= 1.1
    f1 = caixa(0.08, 0.52, 0.62).transformar((-0.35, 0.25, 0)).colorir(p["cor_metal"])
    f2 = caixa(0.08, 0.52, 0.62).transformar((0.35, 0.25, 0)).colorir(p["cor_metal"])
    tr = caixa(0.15, 0.18, 0.05).transformar((0, 0.45, 0.31)).colorir(p["cor_metal"])
    return Malha.unir([corpo, tampa, f1, f2, tr]).achatar()


@objeto_def("cogumelo", "Cogumelo grande.", cor_chapeu="#d93a3a", cor_caule="#efe2c4")
def _cogumelo(rng, p):
    caule = cilindro(0.15, 0.6, 8, raio_topo=0.12).transformar((0, 0.3, 0)).colorir(p["cor_caule"])
    ch = esfera(0.45, 10, 6)
    ch.V[:, 1] = np.maximum(ch.V[:, 1], 0) * 0.8
    ch.transformar((0, 0.55, 0)).colorir(p["cor_chapeu"])
    return Malha.unir([caule, ch]).achatar()


@objeto_def("coluna", "Coluna de pedra com base e capitel.", cor="#cfc8b8", altura=3.0)
def _coluna(rng, p):
    h = p["altura"]
    base = caixa(0.8, 0.25, 0.8).transformar((0, 0.125, 0))
    fuste = cilindro(0.28, h - 0.5, 12, aneis=1).transformar((0, h / 2, 0))
    capitel = caixa(0.8, 0.25, 0.8).transformar((0, h - 0.125, 0))
    m = Malha.unir([base, fuste, capitel]).colorir(p["cor"])
    return _variar_cor(m.achatar(), rng, 0.05)


@objeto_def("escada", "Escada de degraus.", cor="#9a948a", degraus=5)
def _escada(rng, p):
    n = int(p["degraus"])
    partes = [caixa(1.2, 0.2 * (k + 1), 0.3).transformar((0, 0.1 * (k + 1), -0.3 * k)) for k in range(n)]
    return _variar_cor(Malha.unir(partes).colorir(p["cor"]).achatar(), rng, 0.05)


@objeto_def("cerca", "Trecho de cerca (2 m).", cor="#9a6a3c")
def _cerca(rng, p):
    partes = [caixa(0.12, 1.0, 0.12).transformar((x, 0.5, 0)) for x in (-1, 0, 1)]
    partes += [caixa(2.1, 0.1, 0.06).transformar((0, y, 0.07)) for y in (0.35, 0.75)]
    return _variar_cor(Malha.unir(partes).colorir(p["cor"]).achatar(), rng, 0.1)


@objeto_def("moeda", "Moeda 3D.", cor="#f2c230")
def _moeda(rng, p):
    m = cilindro(0.3, 0.06, 20).transformar((0, 0.3, 0), girar_x=np.pi / 2).colorir(p["cor"])
    m.metalico, m.rugosidade = 1.0, 0.3
    return m.achatar()


@objeto_def("gema", "Gema lapidada.", cor="#3fd0e0")
def _gema(rng, p):
    topo = cilindro(0.3, 0.15, 8, True, raio_topo=0.18).transformar((0, 0.075, 0))
    fundo = cone(0.3, 0.4, 8).transformar((0, -0.2, 0), girar_x=np.pi)
    m = Malha.unir([topo, fundo]).colorir(p["cor"]).transformar((0, 0.4, 0))
    m.rugosidade = 0.1
    return _variar_cor(m.achatar(), rng, 0.2)


@objeto_def("espada", "Espada low-poly.", cor_lamina="#c9d3dd", cor_guarda="#c79a3a", cor_cabo="#6b3f22")
def _espada(rng, p):
    lamina = caixa(0.1, 0.9, 0.02).transformar((0, 0.75, 0)).colorir(p["cor_lamina"])
    ponta = Malha([[-0.05, 1.2, 0.01], [0.05, 1.2, 0.01], [0, 1.32, 0], [-0.05, 1.2, -0.01], [0.05, 1.2, -0.01]],
                  [[0, 1, 2], [4, 3, 2], [1, 4, 2], [3, 0, 2]]).colorir(p["cor_lamina"])
    guarda = caixa(0.36, 0.06, 0.08).transformar((0, 0.3, 0)).colorir(p["cor_guarda"])
    cabo = cilindro(0.03, 0.25, 6).transformar((0, 0.15, 0)).colorir(p["cor_cabo"])
    pomo = icosfera(0.05, 0).transformar((0, 0.01, 0)).colorir(p["cor_guarda"])
    return Malha.unir([lamina, ponta, guarda, cabo, pomo]).achatar()


@objeto_def("tocha", "Tocha de parede/chão.", cor_madeira="#6b4a2a", cor_fogo="#ffa21a")
def _tocha(rng, p):
    cabo = cilindro(0.04, 0.6, 6, raio_topo=0.06).transformar((0, 0.3, 0)).colorir(p["cor_madeira"])
    copo = cilindro(0.09, 0.12, 8, raio_topo=0.11).transformar((0, 0.64, 0)).colorir("#3a3a40")
    fogo = cone(0.09, 0.3, 6).transformar((0, 0.85, 0)).colorir(p["cor_fogo"])
    return Malha.unir([cabo, copo, fogo]).achatar()


def gerar(nome, semente=0, **params):
    info = OBJETOS[nome]
    p = dict(info["padrao"])
    p.update(params)
    return info["fn"](np.random.default_rng(semente), p)


PRIMITIVAS = {
    "plano": lambda: plano(2, 4), "cubo": cubo, "esfera": esfera, "icosfera": icosfera, "cilindro": cilindro,
    "cone": cone, "toro": toro, "capsula": capsula,
}
