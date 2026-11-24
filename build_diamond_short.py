import bpy, bmesh, sys, os, math, json, time, random, addon_utils
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE         = argv[0] if len(argv) > 0 else "test_sheet"
CHUNK_IDX    = int(argv[1]) if len(argv) > 1 else 0
TOTAL_CHUNKS = int(argv[2]) if len(argv) > 2 else 12
SAMPLES      = int(argv[3]) if len(argv) > 3 else 16
RESW         = int(argv[4]) if len(argv) > 4 else 720
WATERMARK    = argv[5] if len(argv) > 5 else "@always_animate"
WORK_DIR     = os.path.abspath(argv[6] if len(argv) > 6 else "work")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import doc_pose as D

with open(os.path.join(WORK_DIR, "talk_curve.json"), encoding="utf-8") as f:
    td = json.load(f)
FPS = int(td["fps"])
N_FRAMES = int(td["n_frames"])
TALK = td["talk"]

OUT_DIR = os.path.join(WORK_DIR, "chunk_out")
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("bl_ext.blender_org.mpfb", default_set=True)
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.faceservice import FaceService

scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = N_FRAMES

# Fast CPU Cycles tuned for GitHub Actions parallel runners
r = scene.render
r.engine = "CYCLES"
r.resolution_x = RESW
r.resolution_y = int(RESW * 16 / 9) // 2 * 2
r.resolution_percentage = 100
r.image_settings.file_format = "PNG"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 4
try:
    scene.view_settings.view_transform = "Khronos PBR Neutral"
except Exception:
    scene.view_settings.view_transform = "AgX"

# Build 25-Year-Old Indian Man Host
SKIN_VAL, SKIN_SAT = 0.66, 1.18
info = HumanService._create_default_human_info_dict()
info["phenotype"].update({
    "gender": 1.0, "age": 0.50, "muscle": 0.52, "weight": 0.46, "height": 0.52,
    "proportions": 0.58, "race": {"caucasian": 0.45, "asian": 0.40, "african": 0.15}
})
T = lambda n, v: {"target": n, "value": v}
info["targets"] = [
    T("head-oval", 0.35), T("chin-prominent-incr", 0.28), T("chin-width-incr", 0.12),
    T("r-cheek-bones-incr", 0.32), T("l-cheek-bones-incr", 0.32),
    T("r-eye-scale-incr", 0.22), T("l-eye-scale-incr", 0.22), T("nose-hump-decr", 0.18),
]
info["rig"] = "default"
info["eyes"] = "high-poly/high-poly.mhclo"
info["eyebrows"] = "eyebrow001/eyebrow001.mhclo"
info["eyelashes"] = "eyelashes01/eyelashes01.mhclo"
info["teeth"] = "teeth_base/teeth_base.mhclo"
info["tongue"] = "tongue01/tongue01.mhclo"
info["hair"] = "short02/short02.mhclo"
info["clothes"] = ["male_casualsuit06/male_casualsuit06.mhclo", "shoes05/shoes05.mhclo"]
info["skin_mhmat"] = "young_caucasian_male2/young_caucasian_male2.mhmat"
info["skin_material_type"] = "ENHANCED_SSS"

st = HumanService.get_default_deserialization_settings()
st["scale"] = 0.1
body = HumanService.deserialize_from_dict(info, st)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.name = "Host_rig"; body.name = "Host_body"
print("BUILT HOST:", body.name, len(body.data.vertices), "verts", flush=True)

for o in bpy.data.objects:
    if o.type == "MESH" and "casualsuit" in o.name.lower():
        dm = o.modifiers.new("ClothOut", "DISPLACE"); dm.strength = 0.006; dm.mid_level = 0.0

def tune_skin_tree(nt):
    for n in list(nt.nodes):
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Roughness"].default_value = max(n.inputs["Roughness"].default_value, 0.50)
            if "Coat Weight" in n.inputs:
                n.inputs["Coat Weight"].default_value = 0.0
            bc = n.inputs["Base Color"]
            if bc.is_linked:
                src_sock = bc.links[0].from_socket
                nt.links.remove(bc.links[0])
                hsv = nt.nodes.new("ShaderNodeHueSaturation")
                hsv.inputs["Hue"].default_value = 0.496
                hsv.inputs["Saturation"].default_value = SKIN_SAT
                hsv.inputs["Value"].default_value = SKIN_VAL
                nt.links.new(src_sock, hsv.inputs["Color"])
                nt.links.new(hsv.outputs["Color"], bc)
        elif n.type == "GROUP" and n.node_tree:
            tune_skin_tree(n.node_tree)

for sl in body.material_slots:
    if sl.material and sl.material.node_tree:
        tune_skin_tree(sl.material.node_tree)

for o in bpy.data.objects:
    if o.type == "MESH" and any(k in o.name.lower() for k in ("short02", "hair", "eyebrow")):
        for sl in o.material_slots:
            if sl.material and sl.material.node_tree:
                nt = sl.material.node_tree
                for n in list(nt.nodes):
                    if n.type == "BSDF_PRINCIPLED":
                        bc = n.inputs["Base Color"]
                        if bc.is_linked:
                            src_sock = bc.links[0].from_socket
                            nt.links.remove(bc.links[0])
                            hsv = nt.nodes.new("ShaderNodeHueSaturation")
                            hsv.inputs["Value"].default_value = 0.16
                            nt.links.new(src_sock, hsv.inputs["Color"])
                            nt.links.new(hsv.outputs["Color"], bc)

def sym(**kw):
    out = {}
    for k, v in kw.items():
        if k.endswith("_"):
            out[k[:-1] + "Left"] = v; out[k[:-1] + "Right"] = v
        else:
            out[k] = v
    return out

EXPR = {
    "neutral": sym(mouthSmile_=0.18, browOuterUp_=0.12),
    "happy":   sym(mouthSmile_=0.75, cheekSquint_=0.45, eyeSquint_=0.25, browOuterUp_=0.25, jawOpen=0.10),
    "shock":   sym(eyeWide_=0.85, browInnerUp=0.85, browOuterUp_=0.75, jawOpen=0.30, mouthFunnel=0.20),
    "skeptic": sym(browDown_=0.55, eyeSquint_=0.40, noseSneer_=0.45, mouthFrown_=0.45, mouthPress_=0.35),
}
allk = {"eyeBlinkLeft": 0.01, "eyeBlinkRight": 0.01, "mouthFunnel": 0.01, "jawOpen": 0.01}
for e in EXPR.values():
    allk.update({k: 0.01 for k in e})
FaceService.set_expression(body, allk)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
D.relaxed_hands(arm); D.pose_arms(arm)
for sd, sx in (("L", 1), ("R", -1)):
    D.rot_world(arm, arm.pose.bones["upperleg01." + sd], Vector((0, 1, 0)), sx * 4.5)
    D.rot_world(arm, arm.pose.bones["foot." + sd], Vector((0, 1, 0)), -sx * 4.5)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

def make_mat(name, color=(0.8,0.8,0.8,1), metallic=0.0, rough=0.35, trans=0.0, ior=1.45, emit_col=None, emit_str=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = trans
    b.inputs["IOR"].default_value = ior
    if emit_col and emit_str > 0:
        b.inputs["Emission Color"].default_value = emit_col
        b.inputs["Emission Strength"].default_value = emit_str
    return m

M_STEEL   = make_mat("Steel",   (0.22, 0.25, 0.30, 1), metallic=0.92, rough=0.26)
M_DARKMET = make_mat("DarkMet", (0.07, 0.08, 0.10, 1), metallic=0.85, rough=0.38)
M_GLASS   = make_mat("Glass",   (0.88, 0.96, 1.0, 1),  rough=0.04, trans=0.92, ior=1.50)
M_DIAMOND = make_mat("Diamond", (0.96, 0.99, 1.0, 1),  rough=0.01, trans=1.0,  ior=2.417, emit_col=(0.75, 0.92, 1.0, 1), emit_str=0.18)
M_ROUGH   = make_mat("RoughCube",(0.12, 0.11, 0.10, 1), metallic=0.15, rough=0.68)
M_PLASMA  = make_mat("Plasma",  (0.75, 0.25, 1.0, 1),  rough=0.2,  emit_col=(0.72, 0.18, 1.0, 1), emit_str=14.0)
M_MW_GLOW = make_mat("MWGlow",  (1.0, 0.35, 0.08, 1),  emit_col=(1.0, 0.35, 0.08, 1), emit_str=12.0)
M_GAS     = make_mat("GasBall", (0.35, 0.78, 1.0, 1),  rough=0.2,  emit_col=(0.30, 0.75, 1.0, 1), emit_str=3.5)
M_CARBON  = make_mat("Carbon",  (0.95, 0.85, 1.0, 1),  rough=0.15, emit_col=(0.85, 0.45, 1.0, 1), emit_str=5.5)
M_BOND    = make_mat("Bond",    (0.40, 0.88, 1.0, 1),  emit_col=(0.40, 0.88, 1.0, 1), emit_str=3.0)
M_LASER   = make_mat("Laser",   (1.0, 0.12, 0.25, 1),  emit_col=(1.0, 0.15, 0.35, 1), emit_str=25.0)
M_SPARK   = make_mat("Spark",   (1.0, 0.85, 0.35, 1),  emit_col=(1.0, 0.75, 0.20, 1), emit_str=18.0)

bg_m = make_mat("Backdrop", (0.04, 0.16, 0.34, 1), rough=0.95, emit_col=(0.06, 0.25, 0.55, 1), emit_str=0.08)
bm = bmesh.new()
prof = [(-6 + i * 0.5, 0.0) for i in range(12)]
for i in range(13):
    a = math.pi / 2 * i / 12
    prof.append((1.0 + 2.5 * math.sin(a), 2.5 - 2.5 * math.cos(a)))
for i in range(1, 6):
    prof.append((3.5, 2.5 + i * 1.2))
cols = [[bm.verts.new((x, y, z)) for (y, z) in prof] for x in [-6 + i for i in range(24)]]
for a_, b_ in zip(cols, cols[1:]):
    for j in range(len(prof) - 1):
        bm.faces.new((a_[j], b_[j], b_[j + 1], a_[j + 1]))
me = bpy.data.meshes.new("Backdrop"); bm.to_mesh(me); bm.free(); me.shade_smooth()
bd = bpy.data.objects.new("Backdrop", me); scene.collection.objects.link(bd); me.materials.append(bg_m)

def add_area(name, loc, tgt, size, energy, color=(1,1,1)):
    l = bpy.data.lights.new(name, "AREA"); l.size = size; l.energy = energy; l.color = color
    o = bpy.data.objects.new(name, l); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

add_area("HostKey",  (-2.0, -2.5, 2.8), (0, 0, 1.3), 2.0, 420, (1.0, 0.92, 0.84))
add_area("HostFill", ( 2.2, -2.0, 1.6), (0, 0, 1.2), 2.8, 120, (0.82, 0.92, 1.0))
add_area("HostRim",  ( 1.2,  1.8, 2.5), (0, 0, 1.4), 1.2, 190, (0.75, 0.88, 1.0))
add_area("LabKey",   (6.5, -2.2, 2.8), (8, 0, 1.0), 1.8, 380, (1.0, 0.96, 0.92))
add_area("LabFill",  (9.8, -1.8, 1.6), (8, 0, 1.0), 2.2, 140, (0.75, 0.88, 1.0))
add_area("LabRim",   (8.0,  1.8, 2.4), (8, 0, 1.0), 1.4, 240, (0.85, 0.72, 1.0))

world = bpy.data.worlds.new("W"); scene.world = world
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.08, 0.14, 0.25, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

LAB = Vector((8.0, 0.0, 1.0))

def make_brilliant_diamond(name, radius=0.12):
    bm = bmesh.new(); n = 16
    top_r = radius * 0.56; girdle_z = radius * 0.25; crown_z = radius * 0.52; culet_z = -radius * 0.72
    top_v = [bm.verts.new((math.cos(2*math.pi*i/n)*top_r, math.sin(2*math.pi*i/n)*top_r, crown_z)) for i in range(n)]
    mid_v = [bm.verts.new((math.cos(2*math.pi*i/n)*radius, math.sin(2*math.pi*i/n)*radius, girdle_z)) for i in range(n)]
    bot_v = bm.verts.new((0, 0, culet_z))
    bm.faces.new(top_v)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top_v[i], mid_v[i], mid_v[j], top_v[j]))
        bm.faces.new((mid_v[i], bot_v, mid_v[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob); me.materials.append(M_DIAMOND)
    return ob

host_diamond = make_brilliant_diamond("HostDiamond", radius=0.065)
host_diamond.location = (0.28, -0.32, 1.38)
macro_diamond = make_brilliant_diamond("MacroDiamond", radius=0.16)
macro_diamond.location = LAB + Vector((0, 0, 0.18))

bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.65, depth=0.14, location=LAB + Vector((0, 0, -0.07)))
pedestal = bpy.context.active_object; pedestal.name = "Pedestal"; pedestal.data.materials.append(M_DARKMET)

# 3D Watermark Badges (on Host chest + on Lab Pedestal)
def make_badge_tex(path, text, bg=(18, 24, 34, 255), fg=(235, 245, 255, 255), border=(80, 175, 255, 255)):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (1024, 256), bg)
    dr = ImageDraw.Draw(im)
    if border:
        dr.rounded_rectangle([8, 8, 1015, 247], radius=28, outline=border, width=10)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 92)
    except Exception:
        font = ImageFont.load_default()
    bb = dr.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    dr.text(((1024 - tw) // 2, (256 - th) // 2 - 8), text, font=font, fill=fg)
    im.save(path)

def make_tex_mat(name, img_path, metallic=0.15, rough=0.45, emit_str=0.25):
    m = bpy.data.materials.new(name)
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path, check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emit_str > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit_str
    return m

if WATERMARK:
    chest_png = os.path.join(WORK_DIR, "wm_chest.png")
    plate_png = os.path.join(WORK_DIR, "wm_plate.png")
    make_badge_tex(chest_png, WATERMARK, bg=(20, 26, 36, 255), fg=(245, 250, 255, 255), border=(90, 185, 255, 255))
    make_badge_tex(plate_png, WATERMARK, bg=(12, 16, 24, 255), fg=(140, 225, 255, 255), border=(65, 165, 255, 255))

    bpy.context.view_layer.update()
    chest_bone = arm.pose.bones.get("spine01") or arm.pose.bones.get("spine02")
    if chest_bone:
        cp = arm.matrix_world @ chest_bone.head
        hit_pos = Vector((0.0, -0.14, cp.z + 0.04))
        for ob in bpy.data.objects:
            if ob.type == "MESH" and ("casualsuit" in ob.name.lower() or ob == body):
                mi = ob.matrix_world.inverted()
                hit, loc, _, _ = ob.ray_cast(mi @ Vector((0.0, -0.8, cp.z + 0.04)), (mi.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized())
                if hit:
                    wloc = ob.matrix_world @ loc
                    if wloc.y < hit_pos.y:
                        hit_pos = wloc
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=hit_pos + Vector((0.0, -0.008, 0.0)))
        cbadge = bpy.context.active_object; cbadge.name = "HostChestWatermark"
        cbadge.scale = (0.18, 0.045, 1.0); cbadge.rotation_euler = (math.radians(90), 0.0, 0.0)
        cbadge.data.materials.append(make_tex_mat("ChestBadgeMat", chest_png, metallic=0.0, rough=0.72, emit_str=0.05))
        mw = cbadge.matrix_world.copy()
        cbadge.parent = arm; cbadge.parent_type = "BONE"; cbadge.parent_bone = chest_bone.name
        bpy.context.view_layer.update(); cbadge.matrix_world = mw

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=LAB + Vector((0.0, -0.655, -0.065)))
    lbadge = bpy.context.active_object; lbadge.name = "LabPedestalWatermark"
    lbadge.scale = (0.34, 0.085, 1.0); lbadge.rotation_euler = (math.radians(90), 0.0, 0.0)
    lbadge.data.materials.append(make_tex_mat("LabBadgeMat", plate_png, metallic=0.45, rough=0.25, emit_str=0.65))

bpy.ops.mesh.primitive_cube_add(size=1.0, location=LAB + Vector((0, 0, 0.02)))
seed = bpy.context.active_object; seed.scale = (0.09, 0.09, 0.014); seed.data.materials.append(M_DIAMOND)

bpy.ops.mesh.primitive_cube_add(size=1.0, location=LAB + Vector((0.28, 0, 0.22)))
tw1 = bpy.context.active_object; tw1.scale = (0.35, 0.018, 0.012); tw1.rotation_euler = (0, 0.55, 0); tw1.data.materials.append(M_STEEL)

bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.52, depth=0.72, location=LAB + Vector((0, 0, 0.36)))
chamber_glass = bpy.context.active_object; chamber_glass.data.materials.append(M_GLASS)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.58, depth=0.14, location=LAB + Vector((0, 0, 0.78)))
chamber_lid = bpy.context.active_object; chamber_lid.data.materials.append(M_STEEL)

emitters = []
for ang in (-0.9, 0.9):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.07, depth=0.18, location=LAB + Vector((math.sin(ang)*0.56, -math.cos(ang)*0.15, 0.38)))
    em = bpy.context.active_object; em.rotation_euler = (0, math.pi/2, 0); em.data.materials.append(M_MW_GLOW); emitters.append(em)

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=0.26, location=LAB + Vector((0, 0, 0.28)))
plasma = bpy.context.active_object; plasma.data.materials.append(M_PLASMA); bpy.ops.object.shade_smooth()

rng = random.Random(42)
carbon_atoms = []
for i in range(28):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.022,
        location=LAB + Vector((rng.uniform(-0.24, 0.24), rng.uniform(-0.18, 0.18), rng.uniform(0.08, 0.58))))
    at = bpy.context.active_object; at.data.materials.append(M_CARBON if i % 2 == 0 else M_GAS)
    carbon_atoms.append((at, at.location.copy(), rng.uniform(0, 6.28)))

lattice_objs = []
for ix in (-1, 0, 1):
    for iy in (-1, 0, 1):
        for iz in range(3):
            p = LAB + Vector((ix * 0.085, iy * 0.085, 0.07 + iz * 0.085))
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.022, location=p)
            nd = bpy.context.active_object; nd.data.materials.append(M_BOND)
            lattice_objs.append((nd, iz))

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.17, location=LAB + Vector((0, 0, 0.17)))
rough_cube = bpy.context.active_object; rough_cube.data.materials.append(M_ROUGH)
for v in rough_cube.data.vertices:
    v.co *= (0.85 + 0.30 * rng.random())

bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.008, depth=0.90, location=LAB + Vector((0.28, -0.05, 0.42)))
laser = bpy.context.active_object; laser.rotation_euler = (0, -0.58, 0); laser.data.materials.append(M_LASER)
sparks = []
for i in range(12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.011, location=LAB + Vector((0.06, -0.05, 0.20)))
    sp = bpy.context.active_object; sp.data.materials.append(M_SPARK)
    sparks.append((sp, Vector((rng.uniform(-0.18, 0.22), rng.uniform(-0.15, 0.05), rng.uniform(0.05, 0.24)))))

cam_d = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam

SHOT_FRACS = [
    (0.00, 0.11, "01_hook_host"), (0.11, 0.19, "02_seed_tweezers"), (0.19, 0.27, "03_chamber_seal"),
    (0.27, 0.35, "04_gas_fill"), (0.35, 0.43, "05_host_pizza_joke"), (0.43, 0.53, "06_purple_plasma"),
    (0.53, 0.64, "07_carbon_rain"), (0.64, 0.74, "08_crystal_lattice"), (0.74, 0.81, "09_rough_cube"),
    (0.81, 0.88, "10_host_not_romantic"), (0.88, 0.94, "11_laser_cut"), (0.94, 1.00, "12_sparkling_finale"),
]

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

head_z = (arm.matrix_world @ arm.pose.bones["head"].head).z + 0.05
jaw_pb = arm.pose.bones.get("jaw")

def set_host_expr(name, talk_val=0.0, blink=0.0):
    want = EXPR[name]
    for k in body.data.shape_keys.key_blocks:
        if not k.name.startswith("!ex-"):
            continue
        uk = k.name[4:]
        if uk in ("eyeBlinkLeft", "eyeBlinkRight"):
            k.value = blink
        elif uk == "jawOpen":
            k.value = min(1.0, want.get(uk, 0.0) + talk_val * 0.25)
        elif uk == "mouthFunnel":
            k.value = min(1.0, want.get(uk, 0.0) + talk_val * 0.15)
        else:
            k.value = min(1.0, want.get(uk, 0.0) * 1.45)
    if jaw_pb:
        jaw_pb.rotation_mode = "XYZ"
        jaw_pb.rotation_euler = (math.radians(15.0 * talk_val), 0, 0)

def hide_all_macro():
    for o in [host_diamond, macro_diamond, seed, tw1, chamber_glass, chamber_lid, plasma, rough_cube, laser] + emitters + [a[0] for a in carbon_atoms] + [l[0] for l in lattice_objs] + [s[0] for s in sparks]:
        o.hide_render = True

def setup_frame(f_idx):
    frac = (f_idx - 1) / max(1, N_FRAMES - 1)
    shot_i = 0
    for idx, (a, b, _) in enumerate(SHOT_FRACS):
        if a <= frac <= b or idx == len(SHOT_FRACS) - 1:
            shot_i = idx; s0, s1, sname = a, b, SHOT_FRACS[idx][2]
            break
    u = ease((frac - s0) / max(1e-5, s1 - s0))
    talk = TALK[min(len(TALK) - 1, f_idx - 1)]
    blink = 1.0 if (f_idx % 78) in (70, 71, 72) else 0.0
    hide_all_macro()

    if shot_i == 0:
        host_diamond.hide_render = False; host_diamond.rotation_euler = (0.2, 0.1, f_idx * 0.08)
        set_host_expr("shock" if u < 0.45 else "happy", talk, blink)
        loc = Vector((0.08, -1.65 + 0.18 * u, head_z - 0.05)); tgt = Vector((0.05, 0.0, head_z - 0.06)); cam_d.lens = 75
    elif shot_i == 1:
        seed.hide_render = False; tw1.hide_render = False
        seed.location = LAB + Vector((0, 0, 0.14 - 0.12 * u)); tw1.location = LAB + Vector((0.22, 0, 0.28 - 0.10 * u))
        loc = LAB + Vector((0.0, -0.78 + 0.12 * u, 0.24)); tgt = LAB + Vector((0.0, 0.0, 0.06)); cam_d.lens = 65
    elif shot_i == 2:
        seed.hide_render = False; chamber_glass.hide_render = False; chamber_lid.hide_render = False
        seed.location = LAB + Vector((0, 0, 0.02)); chamber_lid.location = LAB + Vector((0, 0, 1.08 - 0.30 * u))
        loc = LAB + Vector((0.0, -2.1 - 0.22 * u, 0.55)); tgt = LAB + Vector((0.0, 0.0, 0.40)); cam_d.lens = 55
    elif shot_i == 3:
        seed.hide_render = False; chamber_glass.hide_render = False; chamber_lid.hide_render = False
        chamber_lid.location = LAB + Vector((0, 0, 0.78))
        for em in emitters: em.hide_render = False
        for at, p0, ph in carbon_atoms[:14]:
            at.hide_render = False
            at.location = p0 + Vector((0.05 * math.sin(f_idx * 0.15 + ph), 0, 0.04 * math.cos(f_idx * 0.12 + ph)))
        loc = LAB + Vector((0.0, -1.95 + 0.25 * u, 0.45)); tgt = LAB + Vector((0.0, 0.0, 0.34)); cam_d.lens = 58
    elif shot_i == 4:
        set_host_expr("shock", talk, blink)
        loc = Vector((-0.10, -1.35 + 0.12 * u, head_z)); tgt = Vector((0.0, 0.0, head_z - 0.02)); cam_d.lens = 85
    elif shot_i == 5:
        seed.hide_render = False; chamber_glass.hide_render = False; chamber_lid.hide_render = False; plasma.hide_render = False
        for em in emitters: em.hide_render = False
        sc = 0.45 + 0.65 * u + 0.04 * math.sin(f_idx * 0.6); plasma.scale = (sc, sc, sc)
        loc = LAB + Vector((0.0, -1.80 + 0.25 * u, 0.42)); tgt = LAB + Vector((0.0, 0.0, 0.30)); cam_d.lens = 60
    elif shot_i == 6:
        seed.hide_render = False; plasma.hide_render = False; plasma.scale = (0.95, 0.95, 0.95)
        for at, p0, ph in carbon_atoms:
            at.hide_render = False; drop = ((f_idx * 0.025 + ph) % 0.48)
            at.location = Vector((p0.x, p0.y, LAB.z + 0.52 - drop))
        loc = LAB + Vector((0.0, -1.05 + 0.14 * u, 0.32)); tgt = LAB + Vector((0.0, 0.0, 0.18)); cam_d.lens = 68
    elif shot_i == 7:
        seed.hide_render = False
        for nd, iz in lattice_objs:
            if u >= iz * 0.28: nd.hide_render = False
        loc = LAB + Vector((0.0, -0.92 + 0.16 * u, 0.26)); tgt = LAB + Vector((0.0, 0.0, 0.16)); cam_d.lens = 70
    elif shot_i == 8:
        rough_cube.hide_render = False; rough_cube.rotation_euler = (0, 0, u * 0.8)
        loc = LAB + Vector((0.0, -0.95 - 0.18 * u, 0.28)); tgt = LAB + Vector((0.0, 0.0, 0.17)); cam_d.lens = 65
    elif shot_i == 9:
        set_host_expr("skeptic", talk, blink)
        loc = Vector((0.10, -1.32 + 0.10 * u, head_z)); tgt = Vector((0.0, 0.0, head_z - 0.02)); cam_d.lens = 85
    elif shot_i == 10:
        rough_cube.hide_render = False; macro_diamond.hide_render = False; laser.hide_render = False
        rough_cube.location = LAB + Vector((-0.08 * u, 0, 0.17)); laser.location = LAB + Vector((0.30 - 0.12 * u, -0.05, 0.42))
        for sp, vel in sparks:
            sp.hide_render = False; t_sp = (f_idx % 8) / 8.0
            sp.location = LAB + Vector((0.04, -0.04, 0.20)) + vel * t_sp
        loc = LAB + Vector((0.0, -1.05 + 0.15 * u, 0.30)); tgt = LAB + Vector((0.0, 0.0, 0.18)); cam_d.lens = 68
    else:
        host_diamond.hide_render = False; host_diamond.location = (0.24, -0.34, 1.40); host_diamond.rotation_euler = (0.15, 0.1, f_idx * 0.10)
        set_host_expr("happy", talk, blink)
        loc = Vector((0.06, -1.48 + 0.16 * u, head_z - 0.03)); tgt = Vector((0.04, 0.0, head_z - 0.04)); cam_d.lens = 80

    cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    return sname

t_all = time.time()
if MODE == "test_sheet":
    a, b, sname = SHOT_FRACS[CHUNK_IDX]
    f_mid = max(1, min(N_FRAMES, int(((a + b) * 0.5) * N_FRAMES)))
    setup_frame(f_mid)
    r.filepath = os.path.join(OUT_DIR, f"shot_{CHUNK_IDX+1:02d}_{sname}.png")
    bpy.ops.render.render(write_still=True)
    print(f"TEST SHOT {CHUNK_IDX+1}/12 DONE in {time.time() - t_all:.1f}s", flush=True)
else:
    per = math.ceil(N_FRAMES / TOTAL_CHUNKS)
    f0 = CHUNK_IDX * per + 1
    f1 = min(N_FRAMES, (CHUNK_IDX + 1) * per)
    print(f"Chunk {CHUNK_IDX}: rendering frames {f0}..{f1} of {N_FRAMES}", flush=True)
    for f_idx in range(f0, f1 + 1):
        setup_frame(f_idx)
        r.filepath = os.path.join(OUT_DIR, f"frame_{f_idx:04d}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        if f_idx == f0 or f_idx % 10 == 0 or f_idx == f1:
            print(f"FRAME {f_idx}/{f1} ({time.time() - t0:.1f}s)", flush=True)
    print(f"Chunk {CHUNK_IDX} DONE in {(time.time() - t_all)/60:.1f} min", flush=True)
