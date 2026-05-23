"""
8BitDo 펌웨어 다운로더 (특히 Micro 타겟)

8BitDo 공식 펌웨어 서버에 직접 붙어서:
- 전체 제품 목록 조회
- "Micro" 들어간 제품 자동 검색
- 최신 펌웨어 .bin 다운로드

기반: https://github.com/fwupd/8bitdo-firmware/blob/master/8bitdo-firmware.py
원작자: Florian 'floe' Echtler / 블로그: ladis.cloud/blog/posts/firmware-update-8bitdo.html

실행: python fetch_firmware.py
필요: pip install requests
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

try:
    import requests
except ImportError:
    print("[!] requests 라이브러리가 필요합니다.")
    print("    pip install requests")
    sys.exit(1)


BASE = "http://dl.8bitdo.com:8080"
HEADERS = {"Beta": "1"}


def fetch_list() -> list[dict]:
    """전체 제품/펌웨어 목록 조회."""
    print(f"[*] 펌웨어 목록 요청: {BASE}/firmware/select")
    r = requests.post(f"{BASE}/firmware/select", headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("list", [])


def group_by_product(items: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for it in items:
        out.setdefault(it["type"], []).append(it)
    return out


def find_micro(products: dict[int, list[dict]]) -> list[tuple[int, list[dict]]]:
    """제품명에 'micro' 들어간 모든 그룹 반환."""
    matches = []
    for num, fws in products.items():
        name = fws[0].get("fileName", "").lower()
        if "micro" in name:
            matches.append((num, fws))
    return matches


def show_all(products: dict[int, list[dict]]) -> None:
    print("\n=== 전체 제품 목록 ===")
    for num in sorted(products):
        name = products[num][0]["fileName"]
        latest = max(products[num], key=lambda f: f.get("version", 0))
        print(f"  #{num:3d}  {name}  (latest v{latest.get('version')})")


def download_latest(num: int, fws: list[dict], outdir: Path) -> Path:
    """해당 제품의 최신 펌웨어 다운로드."""
    outdir.mkdir(parents=True, exist_ok=True)
    latest = max(fws, key=lambda f: f.get("version", 0))
    path = latest.get("filePathName") or latest.get("filePath") or ""
    if not path:
        raise RuntimeError(f"filePathName 없음: {latest}")
    if not path.startswith("/"):
        path = "/" + path
    url = BASE + path
    fname = os.path.basename(url)
    outpath = outdir / fname

    print(f"\n[*] 다운로드: {url}")
    print(f"    → {outpath}")

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(outpath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # 메타데이터 저장
    meta_path = outpath.with_suffix(outpath.suffix + ".json")
    meta_path.write_text(
        json.dumps(latest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"    메타: {meta_path}")
    print(f"    크기: {outpath.stat().st_size:,} bytes")
    return outpath


def main() -> int:
    try:
        items = fetch_list()
    except Exception as e:
        print(f"[!] 펌웨어 목록 조회 실패: {e}")
        print("    8BitDo 서버 접근 불가능. 네트워크 확인.")
        return 1

    print(f"[*] {len(items)}개 펌웨어 항목 수신")
    products = group_by_product(items)
    print(f"[*] {len(products)}개 제품")

    micro_matches = find_micro(products)
    if not micro_matches:
        print("\n[!] 'Micro' 제품을 못 찾았습니다.")
        show_all(products)
        print("\n번호 알려주시면 그 제품 펌웨어 받기 가능합니다.")
        return 2

    outdir = Path("firmware_dl")
    print(f"\n[+] 'Micro' 일치 제품 {len(micro_matches)}개:")
    for num, fws in micro_matches:
        print(f"  - #{num}: {fws[0]['fileName']} ({len(fws)} 버전)")

    # 모두 다운로드
    for num, fws in micro_matches:
        try:
            path = download_latest(num, fws, outdir)
            print(f"[OK] 저장: {path}")
        except Exception as e:
            print(f"[!] #{num} 다운로드 실패: {e}")

    print("\n========================================")
    print(f"완료. {outdir.resolve()} 폴더 확인.")
    print("이 .bin 파일을 GitHub Release에 업로드해 주세요.")
    print("========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
