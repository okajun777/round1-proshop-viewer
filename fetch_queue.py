#!/usr/bin/env python3
"""ラウンドワン各店舗のボウリング混雑・待ち時間を取得して queue.json に保存する。"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.round1.co.jp/yoyaku"
SELECT_URL = f"{BASE}/queue/select_store/?target=1"
WAIT_URL = f"{BASE}/queue/has_no_wait.php"
OUT = Path(__file__).with_name("queue.json")
STORES_OUT = Path(__file__).with_name("stores.json")

SERVICE_DEPARTMENT_ID = "1"  # bowling
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/queue/bowling/",
    "Origin": "https://www.round1.co.jp",
}
JST = timezone(timedelta(hours=9))
MAX_WORKERS = 8


def fetch_store_catalog(session: requests.Session) -> list[dict]:
    """公式の店舗選択ページから地区・都道府県・店舗一覧を取得する。"""
    r = session.get(SELECT_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    stores: list[dict] = []
    for li in soup.select("ul.queue_select_store_accordion > li"):
        region = None
        for cand in li.find_all(["a", "button", "div", "span"], limit=30):
            text = cand.get_text(strip=True)
            if text.endswith("地区"):
                region = text
                break
        if not region:
            continue

        for pref_div in li.select(".name_prefectures"):
            prefecture = pref_div.get_text(strip=True)
            wrap = pref_div.find_next_sibling("div", class_="collapse_wrap")
            if wrap is None and pref_div.parent:
                wrap = pref_div.parent.select_one(".collapse_wrap")
            if wrap is None:
                continue

            for inp in wrap.select("input.store_id"):
                store_id = inp.get("value")
                if not store_id:
                    continue
                label = li.find("label", attrs={"for": inp.get("id")})
                name = label.get_text(strip=True) if label else store_id
                stores.append(
                    {
                        "id": store_id,
                        "name": name,
                        "prefecture": prefecture,
                        "region": region,
                    }
                )
    return stores


def fetch_wait(session: requests.Session, store_id: str) -> dict:
    r = session.post(
        WAIT_URL,
        data={
            "store_id": store_id,
            "service_department_id": SERVICE_DEPARTMENT_ID,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def fetch_one(store: dict) -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        msg = fetch_wait(session, store["id"])
    except Exception as exc:  # noqa: BLE001 - collect per-store errors
        return {
            **store,
            "ok": False,
            "error": str(exc),
            "available": None,
            "wait_time": None,
            "wait_group_num": None,
            "update_date": None,
            "update_time": None,
            "detail": None,
            "queue_url": (
                f"{BASE}/queue/bowling/index.php"
                f"?service_department_id={SERVICE_DEPARTMENT_ID}&store_id={store['id']}"
            ),
        }

    available = bool(msg.get("available")) if msg.get("result") else None
    wait_time = msg.get("wait_time")
    wait_group = msg.get("wait_group_num")
    try:
        wait_group_num = int(wait_group) if wait_group is not None else None
    except (TypeError, ValueError):
        wait_group_num = None

    return {
        **store,
        "ok": bool(msg.get("result")),
        "error": None if msg.get("result") else "api_result_false",
        "available": available,
        "wait_time": wait_time if available else None,
        "wait_group_num": wait_group_num if available else None,
        "update_date": msg.get("update_date"),
        "update_time": msg.get("update_time"),
        "detail": msg.get("detail"),
        "queue_url": (
            f"{BASE}/queue/bowling/index.php"
            f"?service_department_id={SERVICE_DEPARTMENT_ID}&store_id={store['id']}"
        ),
    }


def main() -> None:
    started = time.perf_counter()
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching store catalog...")
    stores = fetch_store_catalog(session)
    if not stores:
        raise SystemExit("No stores found from select_store page")

    STORES_OUT.write_text(
        json.dumps({"updated_at": datetime.now(JST).isoformat(), "stores": stores}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  {len(stores)} stores")

    print("Fetching wait status...")
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_one, store): store["id"] for store in stores}
        for fut in as_completed(futures):
            results.append(fut.result())

    # Stable order: original catalog order
    by_id = {row["id"]: row for row in results}
    ordered = [by_id[s["id"]] for s in stores if s["id"] in by_id]

    waiting = [
        row
        for row in ordered
        if row.get("available") and isinstance(row.get("wait_time"), (int, float)) and row["wait_time"] > 0
    ]
    waiting.sort(key=lambda r: (-(r["wait_time"] or 0), r["name"]))

    now = datetime.now(JST)
    payload = {
        "updated_at": now.isoformat(),
        "updated_at_display": now.strftime("%Y-%m-%d %H:%M"),
        "source": WAIT_URL,
        "service": "bowling",
        "store_count": len(ordered),
        "waiting_count": len(waiting),
        "elapsed_sec": round(time.perf_counter() - started, 2),
        "stores": ordered,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {OUT.name}: {len(ordered)} stores, "
        f"{len(waiting)} waiting, {payload['elapsed_sec']}s"
    )


if __name__ == "__main__":
    main()
