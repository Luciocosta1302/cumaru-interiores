import struct, base64, json, math, io, re
from PIL import Image

UP = "/mnt/user-data/uploads/"

# ---------- 1. comprimir texturas para base64 ----------
# mapeamento: arquivo -> uso
TEX = {
    "model":   "db7c4320c0da462c00a3caf8f0665f58.jpg",  # escura avermelhada = cumaru (modelo 3D)
    "guama":   "a1995144b5821d9ff490fd734effde36.jpg",  # marrom-avermelhada
    "combu":   "299c6143172b21a2ae84f81d3bb15d96.jpg",  # média lisa
    "varanda": "01ef4e5102537a5bc87092b2a2d3a868.jpg",  # dourada com veios fortes
    "mesa":    "6daeffe37242e38a7dc5f10f21bb4054.jpg",  # clara (carvalho)
}

def to_b64_jpeg(path, maxdim, quality):
    im = Image.open(path).convert("RGB")
    im.thumbnail((maxdim, maxdim), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), im.size

datauris = {}
for key, fname in TEX.items():
    maxdim = 768 if key == "model" else 560
    q = 72 if key == "model" else 68
    b64, size = to_b64_jpeg(UP + fname, maxdim, q)
    datauris[key] = "data:image/jpeg;base64," + b64
    print(key, fname, size, f"{len(b64)/1024:.0f}KB")

# ---------- 2. regenerar modelo SEM índice, com UV por box-mapping ----------
SRC = UP + "wood_table.obj"
verts, objects, cur = [], {}, None
with open(SRC) as f:
    for line in f:
        if line.startswith("v "):
            _, x, y, z = line.split()[:4]
            verts.append((float(x), float(y), float(z)))
        elif line.startswith("o "):
            cur = line[2:].strip(); objects.setdefault(cur, [])
        elif line.startswith("f "):
            idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
            objects.setdefault(cur or "d", []).append(idx)

faces = [f for name, fl in objects.items() if not name.lower().startswith("plane") for f in fl]
used = set(i for face in faces for i in face)

xs=[verts[i][0] for i in used]; ys=[verts[i][1] for i in used]; zs=[verts[i][2] for i in used]
diag = math.dist((min(xs),min(ys),min(zs)), (max(xs),max(ys),max(zs)))
cell = diag / 220
cmap, cacc, remap = {}, [], {}
for i in used:
    x,y,z = verts[i]
    key = (int(x//cell), int(y//cell), int(z//cell))
    if key not in cmap:
        cmap[key] = len(cacc); cacc.append([0,0,0,0])
    ci = cmap[key]; a = cacc[ci]
    a[0]+=x; a[1]+=y; a[2]+=z; a[3]+=1
    remap[i] = ci
nv = [(a[0]/a[3], a[1]/a[3], a[2]/a[3]) for a in cacc]

# normalizar
xs=[v[0] for v in nv]; ys=[v[1] for v in nv]; zs=[v[2] for v in nv]
cx, cz = (min(xs)+max(xs))/2, (min(zs)+max(zs))/2
miny = min(ys)
scale = 3.4 / max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
nv = [((x-cx)*scale, (y-miny)*scale, (z-cz)*scale) for x,y,z in nv]

# triangular + UV box-mapping por face (sem índice: vértices duplicados por face)
TEXSCALE = 0.55  # repetições da textura por unidade
pos_out, uv_out = [], []
def face_uv(p, axis):
    x,y,z = p
    if axis == 0:  return (z*TEXSCALE, y*TEXSCALE)   # projeta em ZY
    if axis == 1:  return (x*TEXSCALE, z*TEXSCALE)   # projeta em XZ (tampo)
    return (x*TEXSCALE, y*TEXSCALE)                  # projeta em XY

tris = 0
for face in faces:
    m = [remap[i] for i in face]
    for k in range(1, len(m)-1):
        a,b,c = m[0], m[k], m[k+1]
        if a==b or b==c or a==c: continue
        pa,pb,pc = nv[a], nv[b], nv[c]
        # normal da face
        ux,uy,uz = pb[0]-pa[0], pb[1]-pa[1], pb[2]-pa[2]
        vx,vy,vz = pc[0]-pa[0], pc[1]-pa[1], pc[2]-pa[2]
        nx,ny,nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        axis = max(range(3), key=lambda i: abs((nx,ny,nz)[i]))
        for p in (pa,pb,pc):
            pos_out.extend(p)
            uv_out.extend(face_uv(p, axis))
        tris += 1

print("tris:", tris, "| floats pos:", len(pos_out), "| floats uv:", len(uv_out))
pos_b = struct.pack("<%df" % len(pos_out), *pos_out)
uv_b  = struct.pack("<%df" % len(uv_out), *uv_out)
payload = json.dumps({
    "p": base64.b64encode(pos_b).decode(),
    "u": base64.b64encode(uv_b).decode(),
    "nt": tris,
})
print("payload modelo KB:", round(len(payload)/1024))

# ---------- 3. editar o HTML ----------
with open("/home/claude/cumaru-interiores.html") as f:
    html = f.read()

# 3a. substituir payload do modelo
html = re.sub(r"<script>window\.TABLE_MODEL = \{.*?\};</script>",
              "<script>window.TABLE_MODEL = " + payload + ";\nwindow.WOOD_TEX = '" + datauris["model"] + "';</script>",
              html, count=1, flags=re.S)

# 3b. substituir o builder JS (indexado -> não-indexado com UV + textura)
old_builder = re.search(r"  const M = window\.TABLE_MODEL;.*?  void woodDark; // material reservado para variações futuras", html, re.S)
assert old_builder, "builder não encontrado"
new_builder = """  const M = window.TABLE_MODEL;
  if (M) {
    const posBytes = b64ToBytes(M.p);
    const uvBytes  = b64ToBytes(M.u);
    const positions3d = new Float32Array(posBytes.buffer);
    const uvs = new Float32Array(uvBytes.buffer);

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions3d, 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    geo.computeVertexNormals();

    const tex = new THREE.TextureLoader().load(window.WOOD_TEX);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = 4;

    const woodMat = new THREE.MeshStandardMaterial({
      map: tex, roughness: 0.58, metalness: 0.04,
    });
    const tableMesh = new THREE.Mesh(geo, woodMat);
    bench.add(tableMesh);
  } else {
    const seat = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.28, 1.15), woodLight);
    seat.position.y = 0.9;
    bench.add(seat);
  }
  void woodDark; void woodLight;"""
html = html.replace(old_builder.group(0), new_builder, 1)

# 3c. output encoding do renderer (para a textura sRGB não lavar)
html = html.replace(
  "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));",
  "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));\n  renderer.outputEncoding = THREE.sRGBEncoding;",
  1)

# 3d. cards de coleção: trocar fotos por amostras de textura do cliente
swaps = [
    ("photo-1549497538-303791108f95?w=800&q=70\" alt=\"Aparador de madeira maciça com veio aparente\"", "guama",   "Amostra de madeira avermelhada da Linha Guamá"),
    ("photo-1567016432779-094069958ea5?w=800&q=70\" alt=\"Quarto com cabeceira de madeira\"",           "combu",   "Amostra de madeira média da Linha Combu"),
    ("photo-1470770903676-69b98201ea1c?w=800&q=70\" alt=\"Deck de madeira ao ar livre\"",               "varanda", "Amostra de madeira dourada da Linha Varanda"),
    ("photo-1519710164239-da123dc03ef4?w=800&q=70\" alt=\"Mesa de jantar em madeira rústica\"",         "mesa",    "Amostra de madeira clara da Linha Mesa Posta"),
]
for old_frag, key, alt in swaps:
    old_full = 'src="https://images.unsplash.com/' + old_frag
    assert old_full in html, "não achei: " + old_frag[:40]
    new_full = 'src="' + datauris[key] + '" alt="' + alt + '"'
    html = html.replace(old_full, new_full, 1)

with open("/home/claude/cumaru-interiores.html", "w") as f:
    f.write(html)
print("HTML atualizado:", round(len(html)/1024), "KB")
