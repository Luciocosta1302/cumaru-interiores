import struct, base64, json, math

SRC = "/mnt/user-data/uploads/wood_table.obj"

# ---------- parse ----------
verts = []          # global vertex list (OBJ indices are global)
objects = {}        # name -> list of faces (each face = list of global vert indices)
cur = None
with open(SRC) as f:
    for line in f:
        if line.startswith("v "):
            _, x, y, z = line.split()[:4]
            verts.append((float(x), float(y), float(z)))
        elif line.startswith("o "):
            cur = line[2:].strip()
            objects.setdefault(cur, [])
        elif line.startswith("f "):
            idx = []
            for part in line.split()[1:]:
                i = part.split("/")[0]
                i = int(i)
                if i < 0:
                    i = len(verts) + 1 + i
                idx.append(i - 1)
            objects.setdefault(cur or "default", []).append(idx)

print("objetos:", {k: len(v) for k, v in objects.items()})
print("total verts:", len(verts))

# ---------- filtrar fundo ----------
faces = []
for name, fl in objects.items():
    if name.lower().startswith("plane"):
        print("descartando fundo:", name, f"({len(fl)} faces)")
        continue
    faces.extend(fl)
print("faces mantidas:", len(faces))

# ---------- bounding box ----------
used = set(i for face in faces for i in face)
xs = [verts[i][0] for i in used]; ys = [verts[i][1] for i in used]; zs = [verts[i][2] for i in used]
bbox = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
diag = math.dist(bbox[:3], bbox[3:])
print("bbox:", bbox, "diag:", round(diag, 2))

# ---------- decimação por clustering ----------
# células da grade: diag/N — N maior = mais detalhe
N = 220
cell = diag / N

cluster_map = {}   # cell key -> new index
cluster_acc = []   # accumulate sums for averaging: [sx,sy,sz,count]
remap = {}         # old global idx -> new idx

for i in used:
    x, y, z = verts[i]
    key = (int(x // cell), int(y // cell), int(z // cell))
    if key not in cluster_map:
        cluster_map[key] = len(cluster_acc)
        cluster_acc.append([0.0, 0.0, 0.0, 0])
    ci = cluster_map[key]
    acc = cluster_acc[ci]
    acc[0] += x; acc[1] += y; acc[2] += z; acc[3] += 1
    remap[i] = ci

new_verts = [(a[0]/a[3], a[1]/a[3], a[2]/a[3]) for a in cluster_acc]
print("verts após clustering:", len(new_verts))

# ---------- triangulação + remoção de degeneradas ----------
tris = []
for face in faces:
    m = [remap[i] for i in face]
    # fan triangulation
    for k in range(1, len(m) - 1):
        a, b, c = m[0], m[k], m[k+1]
        if a != b and b != c and a != c:
            tris.append((a, b, c))
print("triângulos:", len(tris))

# ---------- centralizar e normalizar escala ----------
xs = [v[0] for v in new_verts]; ys = [v[1] for v in new_verts]; zs = [v[2] for v in new_verts]
cx, cz = (min(xs)+max(xs))/2, (min(zs)+max(zs))/2
miny = min(ys)
sx, sy, sz = max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)
scale = 3.4 / max(sx, sy, sz)   # maior dimensão vira ~3.4 unidades (como o banco antigo)
norm = [((x-cx)*scale, (y-miny)*scale, (z-cz)*scale) for x, y, z in new_verts]

# ---------- empacotar ----------
pos = struct.pack("<%df" % (len(norm)*3), *[c for v in norm for c in v])
use32 = len(norm) > 65535
fmt = "I" if use32 else "H"
idx = struct.pack("<%d%s" % (len(tris)*3, fmt), *[i for t in tris for i in t])

payload = {
    "v": base64.b64encode(pos).decode(),
    "i": base64.b64encode(idx).decode(),
    "i32": use32,
    "nv": len(norm),
    "nt": len(tris),
}
out = json.dumps(payload)
with open("/home/claude/table_model.json", "w") as f:
    f.write(out)
print("payload KB:", round(len(out)/1024, 1), "| verts:", len(norm), "| tris:", len(tris), "| index 32-bit:", use32)
