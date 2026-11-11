# songs.csv(スプレッドシートのCSV書き出し)→ songs.json に変換する
# 使い方: python convert.py   (CSVを更新したら再実行して、songs.jsonをコミット)
import csv, json, re, hashlib

SRC, OUT = "songs.csv", "songs.json"

# ブランド表示名(順番がそのまま表示順)。コードが違っていたらここを直す
BRANDS = {"765":"765AS","876":"876プロ","961":"961&0936","CIN":"シンデレラガールズ","MIL":"ミリオンライブ",
          "SdM":"SideM","SYC":"シャイニーカラーズ","GKM":"学園アイドルマスター","VLV":"ヴイアライヴ",
          "XNG":"XENOGLOSSIA","RAD":"ラジオ","765+876":"765×876","合同":"合同","TOR":"TOURS","ETC":"その他","???":"不明"}

# 表示名を変えても曲IDが変わらないよう、IDの計算には変更前のブランド名を使う
LEGACY = {"765AS": "765プロ"}

# 自動で決まらない歌唱者名の手動指定(表記 → フルネーム)。「春香]」はシート側の入力ミス
NAME_FIX = {"歩": "舞浜歩", "鈴帆": "上田鈴帆", "春香]": "天海春香"}

# 発売日違いでも1曲にまとめる曲(ブランド, 曲名, 歌唱者)
MERGE = {("シンデレラガールズ", "君の知らない物語", "神谷奈緒")}

def split_brand(raw):
    codes = re.findall(r"[^\[\]]+", raw.replace("][", "+")) if raw.startswith("[") else [raw]
    code = codes[0]
    kind = "original"
    if code.endswith("別"): code = code[:-1]                 # 「別」はオリジナルに統合
    elif code.endswith("C") and code[:-1] in BRANDS: code, kind = code[:-1], "cover"
    elif code.endswith("R") and code[:-1] in BRANDS: code, kind = code[:-1], "remix"
    return code, kind

def clean_singer(s):
    m = re.match(r"^\(([^)]*)\)(.*)$", s.strip())
    return (m.group(2).strip() or m.group(1)) if m else s.strip()

def norm_date(d):
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", d.strip())
    return f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}" if m else "不明"

rows = list(csv.reader(open(SRC, encoding="utf-8")))
head = rows[1]; idx = {h: i for i, h in enumerate(head)}
get = lambda r, k: r[idx[k]].strip() if k in idx and idx[k] < len(r) else ""

songs, seen = [], set()
for r in rows[2:]:
    if not get(r, "楽曲名"): continue
    code, kind = split_brand(get(r, "ブランド"))
    s = dict(b=BRANDS.get(code, code), t=get(r, "楽曲名"), s=clean_singer(get(r, "歌唱者")),
             d=norm_date(get(r, "発売年月日")), a=get(r, "収録アルバム"), k=kind)
    key = (s["b"], s["t"], s["s"], s["d"])
    dk = key[:3] if key[:3] in MERGE else key   # MERGE対象は日付が違っても1曲にまとめる(最初の行を残す)
    if dk in seen: continue
    seen.add(dk)
    s["id"] = get(r, "ID") or hashlib.sha1("|".join((LEGACY.get(key[0], key[0]),) + key[1:]).encode()).hexdigest()[:10]
    songs.append(s)

# 歌唱者の整形 ①「全員曲・アーケード」などを「全体曲」に統一
for s in songs:
    s["s"] = re.sub(r"^全員曲.*$", "全体曲", s["s"])

# ② 名前だけ(例: 春香)を、シート内に出てくるフルネーム(例: 天海春香)に置き換える
SEP = re.compile(r"([,、，／/・&＆+＋])")
def toks(text): return [t for t in SEP.split(text) if t and not SEP.fullmatch(t)]
FAM = {"765AS", "876プロ", "961プロ", "765×876", "XENOGLOSSIA"}   # 同じ世代のブランドは名簿を共有
key = lambda b: "765系" if b in FAM else b
from collections import Counter
roster, world = {}, Counter()
for s in songs:
    for t in toks(s["s"]):
        t = re.sub(r"\s*歌唱版$", "", t)
        if 2 <= len(t) <= 6 and not re.search(r"[A-Za-z0-9]", t):
            roster.setdefault(key(s["b"]), Counter())[t] += 1; world[t] += 1
def full(t, brand):
    m = re.match(r"^(.*?)(\s*歌唱版)?$", t); name, tail = m[1], m[2] or ""
    if name in NAME_FIX: return NAME_FIX[name] + tail
    for pool in (roster.get(key(brand), Counter()), world):
        c = sorted((f for f in pool if len(f) > len(name) and f.endswith(name)), key=lambda f: -pool[f])
        if len(c) == 1 or (len(c) > 1 and pool[c[0]] >= 3 * pool[c[1]]): return c[0] + tail   # 候補が複数なら、圧倒的に多いほうを採用
        if len(c) > 1: return t
    return t
for s in songs:
    s["s"] = "".join(p if SEP.fullmatch(p) else full(p, s["b"]) for p in SEP.split(s["s"]) if p)

order = list(BRANDS.values())
songs.sort(key=lambda s: (order.index(s["b"]) if s["b"] in order else 99, s["d"]))
json.dump({"brands": [b for b in order if any(s["b"] == b for s in songs)], "songs": songs},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
from collections import Counter
print(len(songs), "曲", dict(Counter(s["k"] for s in songs)))
