# Dynamo Python (CPython3) – Adjacent Room Pairs from Rooms
# RSL-only sampling + Wall-overlap exclusion (Revit 2024)

import clr, math
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager

doc = DocumentManager.Instance.CurrentDBDocument
ZAXIS = XYZ.BasisZ

# ---------- 単位 ----------
def mm_to_internal(mm):
    return UnitUtils.ConvertToInternalUnits(mm, UnitTypeId.Millimeters)

# ---------- パラメータ（既定値） ----------
offset_mm      = 350.0
sample_step_mm = 500.0
overlap_pad_mm = 30.0   # 壁重なり許容（±mm）
parallel_tol_deg = 10.0 # 平行判定

if 'IN' in globals():
    if len(IN) >= 2 and IN[1] is not None:
        try: offset_mm = float(IN[1])
        except: pass
    if len(IN) >= 3 and IN[2] is not None:
        try: sample_step_mm = float(IN[2])
        except: pass

OFFSET      = mm_to_internal(offset_mm)
STEP        = mm_to_internal(sample_step_mm)
BB_PAD      = mm_to_internal(400.0)
OVERLAP_PAD = mm_to_internal(overlap_pad_mm)
COS_TOL     = math.cos(math.radians(parallel_tol_deg))

# ---------- ユーティリティ ----------
def to_db(elem):
    api = getattr(elem, 'InternalElement', None)
    if api: return api
    try:
        return UnwrapElement(elem)
    except:
        return elem

def is_room(e):
    try:
        return isinstance(e, SpatialElement) and e.Category and \
               e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)
    except:
        return False

def norm_vec(v):
    if not v or v.GetLength() < 1e-12:
        return XYZ.BasisX
    return v.Normalize()

def tangent_xy(curve, param, normalized=False):
    try:
        deriv = curve.ComputeDerivatives(param, normalized)
        tvec  = norm_vec(deriv.BasisX)
    except:
        p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)
        tvec = norm_vec(p1.Subtract(p0))
    return tvec

def normal_xy_from_tangent(tvec):
    n = ZAXIS.CrossProduct(tvec)
    return norm_vec(n) if n.GetLength() >= 1e-12 else XYZ.BasisX

def expand_bbox_xy(bb, pad):
    if bb is None: return None
    mn, mx = bb.Min, bb.Max
    mn2 = XYZ(mn.X - pad, mn.Y - pad, mn.Z)
    mx2 = XYZ(mx.X + pad, mx.Y + pad, mx.Z)
    bb2 = BoundingBoxXYZ(); bb2.Min = mn2; bb2.Max = mx2
    return bb2

def bbox2d_contains(bb, pt):
    if bb is None: return True
    mn, mx = bb.Min, bb.Max
    x, y = pt.X, pt.Y
    return (mn.X <= x <= mx.X) and (mn.Y <= y <= mx.Y)

def candidate_rooms(pt, room_bbs):
    return [r for (r, bb) in room_bbs if bbox2d_contains(bb, pt)]

def room_at_point_prefiltered(pt, room_bbs):
    for r in candidate_rooms(pt, room_bbs):
        try:
            if r.IsPointInRoom(pt):
                return r
        except: pass
    return None

# 弧長 STEP ピッチでサンプリング
def length_uniform_samples(curve, step_len):
    pts = []
    poly = curve.Tessellate()
    if not poly or len(poly) < 2:
        try: pts.append(curve.Evaluate(0.5, True))
        except: pass
        return pts

    cum = [0.0]
    for i in range(1, len(poly)):
        seg_len = poly[i].DistanceTo(poly[i-1])
        cum.append(cum[-1] + seg_len)
    total = cum[-1]
    if total < 1e-8:
        try: pts.append(curve.Evaluate(0.5, True))
        except: pass
        return pts

    n = max(1, int(total / step_len))
    targets = [total * (k / float(n + 1)) for k in range(1, n + 1)]

    j = 1
    for d in targets:
        while j < len(cum) and cum[j] < d:
            j += 1
        if j >= len(cum): break
        d0, d1 = cum[j-1], cum[j]
        t = 0.5 if (d1 - d0) < 1e-12 else (d - d0) / (d1 - d0)
        vec = poly[j].Subtract(poly[j-1])
        p = poly[j-1].Add(vec.Multiply(t))
        pts.append(p)

    if not pts:
        try: pts.append(curve.Evaluate(0.5, True))
        except: pass
    return pts

# ---------- 壁データ ----------
def wall_half_thickness(wall):
    try:
        wt = wall.WallType
        if wt: return 0.5 * float(wt.Width)
    except: pass
    try:
        p = wall.WallType.get_Parameter(BuiltInParameter.WALL_ATTR_WIDTH_PARAM)
        if p: return 0.5 * float(p.AsDouble())
    except: pass
    return mm_to_internal(50.0)

walls = list(FilteredElementCollector(doc).OfClass(Wall).WhereElementIsNotElementType())
walls_data = []
for w in walls:
    try:
        loc = w.Location
        if isinstance(loc, LocationCurve):
            c = loc.Curve
            if c and c.Length > 1e-6:
                walls_data.append((w, c, wall_half_thickness(w)))
    except: pass

def is_overlapped_with_wall(pm, rsl_tangent, walls_data):
    for w, wc, half_t in walls_data:
        prj = wc.Project(pm)
        if not prj: 
            continue
        q = prj.XYZPoint
        dx = pm.X - q.X; dy = pm.Y - q.Y
        dist_xy = (dx*dx + dy*dy) ** 0.5
        if dist_xy > (half_t + OVERLAP_PAD):
            continue
        w_tan = tangent_xy(wc, prj.Parameter, normalized=False)
        if abs(rsl_tangent.DotProduct(w_tan)) >= COS_TOL:
            return True
    return False

# ---------- 入力の Rooms ----------
rooms_input = None
if 'IN' in globals() and len(IN) >= 1 and IN[0] is not None:
    elems_in = IN[0] if isinstance(IN[0], list) else [IN[0]]
    rooms_input = [to_db(e) for e in elems_in if e is not None]

if rooms_input and all(is_room(r) for r in rooms_input):
    rooms = rooms_input
else:
    rooms = list(
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_Rooms)
        .WhereElementIsNotElementType()
    )

# ---------- 近傍探索用に Room の膨張BBox ----------
room_bbs = []
for r in rooms:
    try:
        bb = r.get_BoundingBox(None)
        bb = expand_bbox_xy(bb, BB_PAD) if bb else None
    except:
        bb = None
    room_bbs.append((r, bb))

# ---------- メイン（RSLのみを対象） ----------
opt = SpatialElementBoundaryOptions()
opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish

pair_flags = {}  # key -> {"clean":bool, "dirty":bool}

def mark_pair(a, b, clean_sample):
    ida = a.Id.IntegerValue; idb = b.Id.IntegerValue
    key = (ida, idb) if ida < idb else (idb, ida)
    flags = pair_flags.get(key, {"clean": False, "dirty": False})
    if clean_sample: flags["clean"] = True
    else:            flags["dirty"] = True
    pair_flags[key] = flags

for rm in rooms:
    segloops = rm.GetBoundarySegments(opt)
    if not segloops: 
        continue

    for loop in segloops:
        for seg in loop:
            # ★ ここで RSL（部屋分割線）以外の境界は完全に除外 ★
            eid = seg.ElementId
            if not eid or eid == ElementId.InvalidElementId:
                continue
            host = doc.GetElement(eid)
            if not isinstance(host, CurveElement):
                continue
            cat = host.Category
            if not cat or cat.Id.IntegerValue != int(BuiltInCategory.OST_RoomSeparationLines):
                continue

            # RSL の実曲線で判定
            c = seg.GetCurve() if hasattr(seg, "GetCurve") else getattr(seg, "Curve", None)
            if c is None or c.Length < 1e-8:
                continue

            for pm in length_uniform_samples(c, STEP):
                prj = c.Project(pm)
                tparam = prj.Parameter if prj else 0.5
                tvec = tangent_xy(c, tparam, normalized=False)
                nvec = normal_xy_from_tangent(tvec)

                pL = pm.Add(nvec.Multiply(OFFSET))
                pR = pm.Add(nvec.Negate().Multiply(OFFSET))

                left  = room_at_point_prefiltered(pL, room_bbs)
                right = room_at_point_prefiltered(pR, room_bbs)

                # rm と向かい合う相手が見つかった場合のみ、壁重なりを評価
                if left is rm and right is not None and right.Id != rm.Id:
                    overlapped = is_overlapped_with_wall(pm, tvec, walls_data)
                    mark_pair(rm, right, clean_sample=(not overlapped))
                elif right is rm and left is not None and left.Id != rm.Id:
                    overlapped = is_overlapped_with_wall(pm, tvec, walls_data)
                    mark_pair(rm, left, clean_sample=(not overlapped))

# ---------- 出力 ----------
pairs = []
for (ida, idb), flags in pair_flags.items():
    if flags.get("clean", False):  # RSL単独で接している点が1箇所でもある
        a = doc.GetElement(ElementId(ida))
        b = doc.GetElement(ElementId(idb))
        if a and b:
            pairs.append([a, b])

if not pairs:
    pairs = [[None, None]]

OUT = pairs
