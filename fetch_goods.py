#!/usr/bin/env python3
"""r1b.jp の商品をカテゴリ別に取得し、実ブランドを付与して goods.json に保存する。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "http://r1b.jp"
OUT = Path(__file__).with_name("goods.json")

CATEGORIES = [
    {"id": 1, "name": "ボール", "key": "ball"},
    {"id": 2, "name": "シューズ", "key": "shoes"},
    {"id": 3, "name": "バッグ", "key": "bag"},
    {"id": 4, "name": "ウェア", "key": "ware"},
    {"id": 5, "name": "グローブ", "key": "glove"},
    {"id": 6, "name": "テープ", "key": "tape"},
    {"id": 7, "name": "クリーナー", "key": "cleaner"},
    {"id": 8, "name": "その他", "key": "other"},
]

# 取り扱いメーカー（サイトの maker sid）
MAKERS = [
    {"id": 1, "name": "サンブリッジ"},
    {"id": 2, "name": "ABS"},
    {"id": 3, "name": "HI-SP"},
    {"id": 4, "name": "ARK"},
    {"id": 7, "name": "STEEL"},
    {"id": 9, "name": "レジェンドスター"},
]

MAKER_BY_ID = {m["id"]: m["name"] for m in MAKERS}

# サイト表記ゆれ → 表示用ブランド名
BRAND_DISPLAY = {
    "DV8": "DV8",
    "Brunswick": "Brunswick",
    "Dexter": "Dexter",
    "B+": "B+",
    "Mechatecter": "Mechatecter",
    "Radical": "Radical",
    "SUNBRIDGE": "Sunbridge",
    "GENESIS": "Genesis",
    "TURBO": "Turbo",
    "EBONITE": "Ebonite",
    "HAMMER": "Hammer",
    "Track": "Track",
    "NANODESU": "Nanodesu",
    "ABS": "ABS",
    "MOTIV": "Motiv",
    "PRO-AM": "Pro-Am",
    "900GLOBAL": "900 Global",
    "STORM": "Storm",
    "ROTO GRIP": "Roto Grip",
    "ハイ・スポーツ社": "HI-SP",
    "ストライクス": "Strikes",
    "マスター(USA)": "Master",
    "HAMMY'S": "Hammy's",
    "レーン・マスター": "Lane Master",
    "WAVE": "Wave",
    "VISE": "Vise",
    "HELLBENT": "Hellbent",
    "STEEL": "Steel",
    "LEGENDSTAR": "Legend Star",
    "ULTIMATE": "Ultimate",
    "COLUMBIA300": "Columbia 300",
    "COLUMBIA 300": "Columbia 300",
}

PRICE_DIGIT = re.compile(r"price(?:white)?-(\d)\.png")
PAGE_RE = re.compile(r"(\d+)\s*[／/]\s*(\d+)")
MAKER_LOGO_RE = re.compile(r"maker_logo(?:_min)?_(\d+)\.")


def abs_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"{BASE}/{path.lstrip('./')}"


def to_halfwidth(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:
            out.append(chr(o - 0xFEE0))
        elif ch == "\u3000":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def normalize_brand_name(raw: str) -> str:
    s = to_halfwidth(raw or "")
    s = s.replace("･", "・").replace("’", "'").replace("＇", "'")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("株式会社", "").strip()
    key = s.upper() if re.fullmatch(r"[A-Za-z0-9 +\-・']+", s) else s
    # 英数字ブランドは大文字キーで照合
    upper_map = {k.upper(): v for k, v in BRAND_DISPLAY.items()}
    if key.upper() in upper_map:
        return upper_map[key.upper()]
    if s in BRAND_DISPLAY:
        return BRAND_DISPLAY[s]
    # マスター表記
    if "マスター" in s and "USA" in s.upper():
        return "Master"
    if s.upper().replace(" ", "") in {"HAMMY'S", "HAMMYS"}:
        return "Hammy's"
    if s in {"STEEL SPORTS", "STEEL"}:
        return "Steel"
    if s in {"レジェンドスター", "LEGENDSTAR"}:
        return "Legend Star"
    return s


def normalize_maker_name(raw: str) -> str:
    s = to_halfwidth(raw or "").replace("株式会社", "").strip()
    s = re.sub(r"\s+", " ", s)
    if s in {"STEEL SPORTS", "STEEL"}:
        return "STEEL"
    if s.startswith("レジェンドスター"):
        return "レジェンドスター"
    return s or ""


def parse_member_price(price_el) -> int | None:
    if not price_el:
        return None
    digits = []
    for img in price_el.find_all("img"):
        src = img.get("src", "")
        m = PRICE_DIGIT.search(src)
        if m and "pricewhite" not in src and "price-" in Path(src).name:
            digits.append(m.group(1))
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def parse_discount(price_el) -> int | None:
    if not price_el:
        return None
    span = price_el.find("span", class_="price")
    if not span:
        return None
    digits = []
    for img in span.find_all("img"):
        src = img.get("src", "")
        m = PRICE_DIGIT.search(src)
        if m and "pricewhite" in src:
            digits.append(m.group(1))
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def parse_list_price(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"([\d,]+)", text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_page_total(html: str) -> int:
    m = PAGE_RE.search(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    return int(m.group(2)) if m else 1


def parse_item_ids(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    ids = []
    for el in soup.select("div.item"):
        link = el.select_one("a.item_img")
        href = link.get("href", "") if link else ""
        sid_m = re.search(r"sid=([^&\"']+)", href)
        if sid_m:
            ids.append(sid_m.group(1))
    return ids


def parse_items(html: str, category: dict) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for el in soup.select("div.item"):
        link = el.select_one("a.item_img")
        img = el.select_one("a.item_img img")
        maker_img = el.select_one("p.item_bland img, p.item_brand img")
        name_el = el.select_one("p.item_name")
        price_el = el.select_one("p.item_price")
        list_el = el.select_one("p.item_normalprice")

        href = link.get("href", "") if link else ""
        sid_m = re.search(r"sid=([^&\"']+)", href)
        sid = sid_m.group(1) if sid_m else ""

        name = (name_el.get_text(strip=True) if name_el else "") or (
            img.get("alt", "").strip() if img else ""
        )
        maker_src = maker_img.get("src", "") if maker_img else ""
        maker_alt = maker_img.get("alt", "").strip() if maker_img else ""
        maker_id_m = MAKER_LOGO_RE.search(maker_src)
        maker_id = int(maker_id_m.group(1)) if maker_id_m else None
        maker = MAKER_BY_ID.get(maker_id) or normalize_maker_name(maker_alt)

        if not name and not sid:
            continue

        items.append(
            {
                "id": sid,
                "name": name,
                "brand": "",
                "brand_id": None,
                "maker": maker,
                "maker_id": maker_id,
                "category_id": category["id"],
                "category": category["name"],
                "category_key": category["key"],
                "image": abs_url(img.get("src", "")) if img else "",
                "member_price": parse_member_price(price_el),
                "list_price": parse_list_price(
                    list_el.get_text(" ", strip=True) if list_el else ""
                ),
                "discount_percent": parse_discount(price_el),
                "url": abs_url(href) if href else "",
            }
        )
    return items


def discover_brands(session: requests.Session) -> list[dict]:
    brands: list[dict] = []
    for maker in MAKERS:
        r = session.get(f"{BASE}/brand.php?sid={maker['id']}", timeout=30)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("#popup-brandlist a"):
            onclick = a.get("onclick") or ""
            m = re.search(r"brand_def',\s*'(\d+)'", onclick)
            if not m:
                continue
            img = a.find("img")
            raw = (img.get("alt") if img else "") or ""
            brand_id = int(m.group(1))
            brands.append(
                {
                    "brand_id": brand_id,
                    "brand": normalize_brand_name(raw),
                    "brand_raw": raw,
                    "maker_id": maker["id"],
                    "maker": maker["name"],
                }
            )
    return brands


def fetch_paginated(
    session: requests.Session,
    first_cmd: str,
    first_sid: str,
) -> list[str]:
    """最初の一覧 + change_page で全ページの商品IDを返す。"""
    r = session.post(
        f"{BASE}/item.php",
        data={"prc": "list", "cmd": first_cmd, "sid": first_sid, "pno": "1"},
        timeout=30,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    ids = parse_item_ids(r.text)
    total_pages = parse_page_total(r.text)
    for pno in range(2, total_pages + 1):
        time.sleep(0.12)
        r = session.post(
            f"{BASE}/item.php",
            data={"prc": "list", "cmd": "change_page", "sid": "", "pno": str(pno)},
            timeout=30,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        ids.extend(parse_item_ids(r.text))
    return ids


def fetch_brand_map(session: requests.Session, brands: list[dict]) -> dict[str, dict]:
    """商品ID → 実ブランド情報。"""
    mapping: dict[str, dict] = {}
    for i, b in enumerate(brands, 1):
        print(
            f"  [{i}/{len(brands)}] {b['maker']} / {b['brand']} (id={b['brand_id']})...",
            end="",
            flush=True,
        )
        ids = fetch_paginated(session, "brand_def", str(b["brand_id"]))
        for sid in ids:
            mapping[sid] = {
                "brand": b["brand"],
                "brand_id": b["brand_id"],
                "maker": b["maker"],
                "maker_id": b["maker_id"],
            }
        print(f" {len(ids)}件")
        time.sleep(0.12)
    return mapping


def fetch_category(session: requests.Session, category: dict) -> list[dict]:
    print(f"\n[{category['name']}] 取得開始...")
    r = session.post(
        f"{BASE}/item.php",
        data={"prc": "list", "cmd": "genre_def", "sid": str(category["id"]), "pno": "1"},
        timeout=30,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    items = parse_items(r.text, category)
    total_pages = parse_page_total(r.text)
    print(f"  page 1/{total_pages} -> {len(items)}件")

    all_items = list(items)
    for pno in range(2, total_pages + 1):
        time.sleep(0.12)
        r = session.post(
            f"{BASE}/item.php",
            data={"prc": "list", "cmd": "change_page", "sid": "", "pno": str(pno)},
            timeout=30,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        all_items.extend(parse_items(r.text, category))
        if pno % 10 == 0 or pno == total_pages:
            print(f"  page {pno}/{total_pages} -> 累計 {len(all_items)}件")

    seen = set()
    unique = []
    for it in all_items:
        key = it["id"] or f"{it['name']}|{it['image']}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    print(f"  完了: {len(unique)}件")
    return unique


def apply_brand_map(items: list[dict], brand_map: dict[str, dict]) -> None:
    matched = 0
    for it in items:
        info = brand_map.get(it["id"])
        if info:
            it["brand"] = info["brand"]
            it["brand_id"] = info["brand_id"]
            it["maker"] = info["maker"]
            it["maker_id"] = info["maker_id"]
            matched += 1
        else:
            # ブランド不明時は取り扱いメーカーを仮ブランドにしない
            it["brand"] = it.get("brand") or "その他"
            it["maker"] = normalize_maker_name(it.get("maker") or "")
    print(f"ブランド紐付け: {matched}/{len(items)}件")


def main() -> None:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; Round1GoodsViewer/1.0)",
            "Referer": f"{BASE}/",
        }
    )
    session.get(f"{BASE}/", timeout=30)

    print("ブランド一覧を取得...")
    brands = discover_brands(session)
    print(f"  {len(brands)} ブランド")

    print("\nブランド別商品IDを取得...")
    brand_map = fetch_brand_map(session, brands)

    all_items: list[dict] = []
    counts: dict[str, int] = {}
    for cat in CATEGORIES:
        cat_items = fetch_category(session, cat)
        counts[cat["name"]] = len(cat_items)
        all_items.extend(cat_items)

    apply_brand_map(all_items, brand_map)

    brand_counts: dict[str, int] = {}
    maker_counts: dict[str, int] = {}
    for it in all_items:
        brand_counts[it["brand"]] = brand_counts.get(it["brand"], 0) + 1
        maker_counts[it["maker"]] = maker_counts.get(it["maker"], 0) + 1

    payload = {
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": BASE,
        "categories": CATEGORIES,
        "makers": MAKERS,
        "brands": brands,
        "counts": counts,
        "brand_counts": dict(sorted(brand_counts.items(), key=lambda x: (-x[1], x[0]))),
        "maker_counts": dict(sorted(maker_counts.items(), key=lambda x: (-x[1], x[0]))),
        "total": len(all_items),
        "items": all_items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存: {OUT}")
    print(f"合計: {len(all_items)}件")
    print("ブランド内訳:")
    for name, n in payload["brand_counts"].items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()
