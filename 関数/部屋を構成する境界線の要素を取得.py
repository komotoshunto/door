# Dynamo Python (CPython3) – Rooms → all boundary elements (Revit 2024)
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager

doc = DocumentManager.Instance.CurrentDBDocument

# ---- helper: unwrap Dynamo element to Revit API element ----
def to_db(elem):
    api = getattr(elem, 'InternalElement', None)
    if api:
        return api
    try:
        return UnwrapElement(elem)
    except:
        return elem

# ---- normalize input: accept single room or list of rooms ----
inp = IN[0]
rooms_in = inp if isinstance(inp, list) else [inp]
rooms_db = [to_db(r) for r in rooms_in]

# 仕上げ面基準（必要に応じて Center / CoreCenter 等に変更可）
opt = SpatialElementBoundaryOptions()
opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish

results = []
for r in rooms_db:
    # 部屋が無効／未確定の場合に備えて空配列で返す
    if r is None:
        results.append([])
        continue

    segloops = r.GetBoundarySegments(opt)  # 部屋の境界セグメントを取得
    if not segloops:
        results.append([])
        continue

    unique_ids = set()
    boundary_elements = []

    for loop in segloops:
        for seg in loop:
            # ホストモデル側の要素ID
            eid = seg.ElementId
            if eid and eid != ElementId.InvalidElementId:
                if eid.IntegerValue not in unique_ids:
                    elem = doc.GetElement(eid)
                    if elem:  # 壁・床・柱・部屋境界線(CurveElement) など全て含める
                        unique_ids.add(eid.IntegerValue)
                        boundary_elements.append(elem)

            # （参考）リンク要素に由来する境界への対応
            # RevitLinkInstance を経由してリンクDocの要素を取りに行くことも可能ですが、
            # Dynamoの環境ではリンクDoc要素のラップに制約があるため、ここでは
            # 「リンクインスタンス自体」を境界要素として挙げる方が安定します。
            # 必要な場合は下のコメントアウトを有効化してください。
            #
            # if hasattr(seg, 'LinkElementId'):
            #     leid = seg.LinkElementId
            #     if leid and leid != ElementId.InvalidElementId:
            #         link_inst = doc.GetElement(eid)  # seg.ElementId はリンクインスタンス
            #         if link_inst and link_inst.Id.IntegerValue not in unique_ids:
            #             unique_ids.add(link_inst.Id.IntegerValue)
            #             boundary_elements.append(link_inst)

    results.append(boundary_elements)

# 入力が単一なら単一で返す
OUT = results if isinstance(inp, list) else (results[0] if results else [])
