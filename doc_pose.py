import bpy, math
from mathutils import Vector, Matrix

X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
CURLS = {"1": (8, 14, 10), "2": (18, 28, 18), "3": (22, 32, 20), "4": (26, 36, 22), "5": (30, 40, 24)}

def _update():
    bpy.context.view_layer.update()

def rot_world(arm, pb, axis, deg):
    _update()
    head = arm.matrix_world @ pb.head
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix

def aim(arm, pb, d):
    _update()
    M = arm.matrix_world @ pb.matrix
    q = (M.to_3x3() @ Vector((0, 1, 0))).normalized().rotation_difference(d.normalized())
    h = M.translation.copy()
    pb.matrix = arm.matrix_world.inverted() @ Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M

def relaxed_hands(arm, twist=35):
    P = arm.pose.bones
    for side, s in (("L", 1), ("R", -1)):
        for f, angs in CURLS.items():
            for j, a in zip((1, 2, 3), angs):
                pb = P.get(f"finger{f}-{j}.{side}")
                if pb:
                    pb.rotation_mode = "XYZ"
                    pb.rotation_euler = (math.radians(a), 0, 0)
        w = P.get(f"wrist.{side}")
        if w:
            w.rotation_mode = "XYZ"
            w.rotation_euler = (math.radians(-8), 0, 0)
        la2 = P.get(f"lowerarm02.{side}")
        if la2:
            la2.rotation_mode = "XYZ"
            la2.rotation_euler = (0, math.radians(s * twist), 0)

def arm_dirs(yaw_deg=0.0, swing=0.0, elbow=12.0, up_fwd=0.0, fore_fwd=0.0, side=1, out=0.16, fore_out=0.10):
    Rz = Matrix.Rotation(math.radians(yaw_deg), 3, Z)
    up = Matrix.Rotation(math.radians(swing - up_fwd), 3, X) @ Vector((side * out, 0.0, -1.0))
    fa = Matrix.Rotation(math.radians(swing - up_fwd - elbow - fore_fwd), 3, X) @ Vector((side * fore_out, 0.0, -1.0))
    return Rz @ up, Rz @ fa

def pose_arms(arm, yaw_deg=0.0, swing_L=0.0, swing_R=0.0, elbow=12.0, up_fwd=0.0, fore_fwd=0.0, shoulder_drop=8.0, out=0.16, fore_out=0.10):
    P = arm.pose.bones
    for side, s, sw in (("L", 1, swing_L), ("R", -1, swing_R)):
        rot_world(arm, P["shoulder01." + side], Matrix.Rotation(math.radians(yaw_deg), 3, Z) @ Y, s * shoulder_drop)
        up, fa = arm_dirs(yaw_deg, sw, elbow, up_fwd, fore_fwd, s, out, fore_out)
        aim(arm, P["upperarm01." + side], up)
        aim(arm, P["upperarm02." + side], up)
        aim(arm, P["lowerarm01." + side], fa)
