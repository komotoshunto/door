# -*- coding: utf-8 -*-
"""
Revit 2024 / Dynamo (CPython3) 用
グループがいくつあっても、OpenAI API の呼び出しは 1 回だけにする版。

IN[0] : OpenAI API キー（文字列）
IN[1] : プロンプト（今回の長文ルール）
IN[2] : 部屋名称リスト
        例1: [[{'名前':..., 'ID':...}, ...], [...], ...]      ← 二重リスト
        例2: [[[{'名前':..., 'ID':...}, ...], [...], ...]]  ← 三重リスト（前回の例）

OUT  : フラットな 1 本のリスト
       [{'名前':..., 'ID':...}, {'名前':..., 'ID':...}, ...]
"""

import json
import ssl
import urllib.request
import urllib.error

# ---------- 入力 ----------
api_key = IN[0]
base_prompt = IN[1]
raw_input = IN[2]

if raw_input is None:
    raw_input = []

# ---------- OpenAI API 設定 ----------
API_URL = "https://api.openai.com/v1/chat/completions"

# Structured Outputs (response_format.json_schema) が Chat Completions で
# サポートされている gpt-4o スナップショットを利用
MODEL_NAME = "gpt-4o-2024-08-06"

_ssl_context = ssl.create_default_context()


# ---------- IN[2] から「辞書リストのグループ」だけを抜き出す ----------

def extract_groups(obj):
    """
    入れ子構造の中から
      [{'名前':..., 'ID':...}, ...]
    という「辞書のリスト」をすべて拾い出して
    [[{...}, {...}, ...], [...], ...] という 2 次元リストにして返す。
    （三重リストでも四重リストでも対応）
    """
    groups = []

    def _walk(x):
        if isinstance(x, (list, tuple)):
            if x and isinstance(x[0], dict):
                # 1 グループ発見
                groups.append(list(x))
            else:
                for y in x:
                    _walk(y)

    _walk(obj)
    return groups


groups_in = extract_groups(raw_input)
# groups_in: [[{名前,ID},...], [{名前,ID},...], ...]


# ---------- OpenAI 1 回呼び出し ----------

def call_openai_structured_all(api_key, model, prompt_text, groups):
    """
    groups: [[{名前,ID}, ...], [{名前,ID}, ...], ...] を
    まとめて 1 回の Structured Outputs で処理する。

    返り値:
        正常時 : [[{名前,ID}, ...], [{名前,ID}, ...], ...]（入力と同じ形）
        失敗時 : {"error": "...", "body": "...", "input": groups} など
    """
    # モデルに渡すための JSON テキスト
    groups_payload = {
        "groups": [
            {"items": g} for g in groups
        ]
    }

    try:
        groups_json = json.dumps(groups_payload, ensure_ascii=False)
    except Exception as e:
        return {
            "error": "groups json.dumps failed: {0}".format(e),
            "input": str(groups)
        }

    messages = [
        {
            "role": "system",
            "content": (
                "あなたは建築の部屋名称を正規化する専門アシスタントです。"
                "必ず指定された JSON Schema に従って応答し、"
                "各グループ内でのみ名前を比較して処理してください。"
                "異なるグループ間で名称をまとめたり統合しないでください。"
                "ID は入力と同じ値をそのままコピーしてください。"
            )
        },
        {
            "role": "user",
            "content": u"{prompt}\n\n対象のグループ構造:\n{data}".format(
                prompt=prompt_text,
                data=groups_json
            )
        }
    ]

    # ルート: type: "object"
    # 中に groups: array[ { items: array[ {名前,ID} ] } ]
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "room_name_all_groups",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "名前": {"type": "string"},
                                            "ID": {"type": "integer"}
                                        },
                                        "required": ["名前", "ID"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["items"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["groups"],
                "additionalProperties": False
            }
        }
    }

    payload = {
        "model": model,
        "messages": messages,
        "response_format": response_format
    }

    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + str(api_key).strip()
    }

    req = urllib.request.Request(API_URL, data=data_bytes, headers=headers)

    # ---- HTTP 呼び出し ＋ エラーハンドリング ----
    try:
        with urllib.request.urlopen(req, context=_ssl_context) as resp:
            resp_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        return {
            "error": "HTTP error: {0} {1}".format(e.code, e.reason),
            "body": err_body,
            "input": groups
        }
    except Exception as e:
        return {
            "error": "Connection error: {0}".format(e),
            "input": groups
        }

    # ---- レスポンス JSON パース ----
    try:
        resp_json = json.loads(resp_text)
    except Exception as e:
        return {
            "error": "JSON decode error in API response: {0}".format(e),
            "raw_response": resp_text,
            "input": groups
        }

    try:
        content = resp_json["choices"][0]["message"]["content"]
    except Exception as e:
        return {
            "error": "Unexpected API response format: {0}".format(e),
            "response_json": resp_json,
            "input": groups
        }

    # message.content には JSON 文字列が入っている想定
    try:
        body = json.loads(content)
    except Exception as e:
        return {
            "error": "JSON decode error in message.content: {0}".format(e),
            "content": content,
            "input": groups
        }

    # 期待形: {"groups": [ {"items":[{名前,ID},...]}, {"items":[...]}, ... ] }
    if not (isinstance(body, dict) and "groups" in body):
        return {
            "error": "JSON schema mismatch: 'groups' not found in response.",
            "body": body,
            "input": groups
        }

    groups_out = body["groups"]

    # groups_out[i]["items"] が実際の [{名前,ID}, ...]
    results = []
    for g in groups_out:
        if isinstance(g, dict) and "items" in g:
            results.append(g["items"])
        else:
            results.append({
                "error": "group item missing 'items' field",
                "group": g
            })

    return results


# ---------- フラット化 ----------

def flatten_groups(groups_2d):
    """
    [[{...}, {...}], [{...}], ...] を
    1 本の [{...}, {...}, ...] に変換。
    （エラー情報の dict もそのまま要素として残す）
    """
    flat = []
    for g in groups_2d:
        if isinstance(g, (list, tuple)):
            for x in g:
                flat.append(x)
        else:
            flat.append(g)
    return flat


# ---------- メイン処理 ----------
if not groups_in:
    # IN[2] に辞書リストが見つからなかった場合
    OUT = []
else:
    result_groups = call_openai_structured_all(api_key, MODEL_NAME, base_prompt, groups_in)

    if isinstance(result_groups, dict) and "error" in result_groups:
        # まとめて失敗した場合は、そのまま OUT に
        OUT = [result_groups]
    else:
        # 成功した場合は 2 次元 → 1 次元にフラット化して OUT
        OUT = flatten_groups(result_groups)
