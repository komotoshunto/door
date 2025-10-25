# -*- coding: utf-8 -*-

import clr

# Revit / Dynamo API 参照（ProtoGeometry 等の重い幾何は未使用なので読込しない）
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import BuiltInParameter

# --- 入力 ---
doors = UnwrapElement(IN[0])  # 単体 or リストどちらでも可

# --- 前処理：ActiveView のフェーズを明示取得（精度向上） ---
doc = DocumentManager.Instance.CurrentDBDocument
av = doc.ActiveView
phase_param = av.get_Parameter(BuiltInParameter.VIEW_PHASE)
phase = doc.GetElement(phase_param.AsElementId()) if phase_param else None


seq = doors if isinstance(doors, (list, tuple)) else [doors]


def get_rooms(inst):
    """FamilyInstance から [FromRoom, ToRoom] を返す。取得不可は None。"""
    if inst is None:
        return [None, None]

    # RevitAPI のメソッドがあれば優先（フェーズを明示して精度確保）
    has_get = hasattr(inst, "get_FromRoom") and hasattr(inst, "get_ToRoom")
    if has_get and phase is not None:
        fr = inst.get_FromRoom(phase)
        tr = inst.get_ToRoom(phase)
        return [fr, tr]

    # フォールバック：Dynamo 側の簡易プロパティ
    fr = inst.FromRoom if hasattr(inst, "FromRoom") else None
    tr = inst.ToRoom if hasattr(inst, "ToRoom") else None
    return [fr, tr]

# ループ最小化（内包表記）
result = [get_rooms(d) for d in seq]

# --- 出力（元コード互換） ---
OUT = result if isinstance(doors, (list, tuple)) else (result[0] if result else [None, None])
