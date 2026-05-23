"""
8BitDo 펌웨어 다운로더 — 강화 버전

- 다중 엔드포인트 시도 (.com / .cn / beta)
- POST + GET 둘 다 시도
- Beta 헤더 있는 거 / 없는 거
- 응답 전체를 raw로 저장 (디버그용)
- 모든 펌웨어 다운로드 (Micro 못 찾으면)

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


BASES = [
    "http://dl.8bitdo.com:8080",
    "http://dl.8bitdo.cn:8080",
    "http://beta.8bitdo.com:8080",
    "https://dl.8bitdo.com",
    "https://dl.8bitdo.cn",
]

# 다양한 헤더 조합으로 시도
HEADER_VARIANTS = [
    {"Beta": "1"},
    {"Beta": "0"},
    {},  # 빈 헤더
    {"User-Agent": "Mozilla/5.0 (Linux; Android 12)", "Beta": "1"},
]


def try_fetch_list(out_dir: Path) -> list[dict]:
    """모든 (base, headers) 조합 시도. 첫 성공 응답 반환."""
    debug_dir = out_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    for base_idx, base in enumerate(BASES):
        for hdr_idx, headers in enumerate(HEADER_VARIANTS):
            tag = f"b{base_idx}h{hdr_idx}"
            print(f"\n[*] 시도 {tag}: {base}/firmware/select")
            print(f"    헤더: {headers}")

            for method in ("POST", "GET"):
                try:
                    if method == "POST":
                        r = requests.post(
                            f"{base}/firmware/select",
                            headers=headers,
                            timeout=20,
                        )
                    else:
                        r = requests.get(
                            f"{base}/firmware/select",
                            headers=headers,
                            timeout=20,
                        )
                    print(f"    {method}: HTTP {r.status_code} | len={len(r.content)} | ct={r.headers.get('Content-Type','')}")

                    # raw 저장
                    (debug_dir / f"{tag}_{method}.bin").write_bytes(r.content)

                    if r.status_code != 200:
                        continue
                    if not r.content:
                        continue

                    # JSON 시도
                    try:
                        data = r.json()
                    except json.JSONDecodeError:
                        # 텍스트 미리보기
                        prev = r.text[:300] if r.text else "(empty)"
                        print(f"    JSON 파싱 실패. 미리보기: {prev}")
                        continue

                    items = data.get("list", []) if isinstance(data, dict) else []
                    print(f"    ✓ 응답 OK: {len(items)}개 펌웨어")
                    if items:
                        return items
                    else:
                        print(f"    list 비어있음. 응답: {str(data)[:300]}")

                except requests.RequestException as e:
                    print(f"    {method} 실패: {e}")

    return []


def download_firmwares(items: list[dict], out_dir: Path) -> list[Path]:
    """모든 펌웨어를 받자 (Micro 못 찾으면 일단 다 받음)."""
    # 제품별로 그룹화 후 최신 버전만
    by_product = {}
    for it in items:
        num = it.get("type")
        if num is None:
            continue
        by_product.setdefault(num, []).append(it)

    saved = []
    for num, fws in by_product.items():
        latest = max(fws, key=lambda f: f.get("version", 0))
        name = latest.get("fileName", f"unknown_{num}")
        path = latest.get("filePathName") or latest.get("filePath") or ""

        # URL 패턴: dl.8bitdo.com:8080/firmwareFile/upload/<path>
        if not path:
            print(f"  [!] #{num} {name}: filePath 없음")
            continue

        # 여러 base 시도
        downloaded = False
        for base in BASES:
            if not path.startswith("/"):
                full = f"{base}/{path}"
            else:
                full = f"{base}{path}"
            try:
                print(f"  ⬇ #{num} {name} v{latest.get('version')}: {full}")
                r = requests.get(full, stream=True, timeout=60)
                if r.status_code != 200:
                    print(f"    HTTP {r.status_code}")
                    continue
                fname = os.path.basename(path) or f"{name}_v{latest.get('version')}.dat"
                outp = out_dir / fname
                with open(outp, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                meta = outp.with_suffix(outp.suffix + ".json")
                meta.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"    ✓ {outp.stat().st_size:,} bytes → {outp.name}")
                saved.append(outp)
                downloaded = True
                break
            except requests.RequestException as e:
                print(f"    실패: {e}")

        if not downloaded:
            print(f"    [X] #{num} 다운로드 실패 (모든 base)")

    return saved


def main() -> int:
    out_dir = Path("firmware_dl")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 환경 정보
    print("=" * 60)
    print("8BitDo Firmware Fetcher (강화 버전)")
    print("=" * 60)
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        print(f"내 외부 IP: {ip}")
    except Exception:
        print("외부 IP 확인 불가")
    print(f"출력 폴더: {out_dir.resolve()}")
    print()

    items = try_fetch_list(out_dir)

    if not items:
        print("\n[X] 모든 엔드포인트 실패.")
        print(f"디버그 응답들이 {out_dir / 'debug'} 에 저장됨.")
        print("\n원인 가능성:")
        print("  - 8BitDo 서버가 미국/유럽 IP 차단 (한국 IP만 허용)")
        print("  - API 변경됨")
        print("  - 인증/세션 필요해짐")
        return 1

    print(f"\n[+] {len(items)}개 펌웨어 항목 수신")

    # 우선 Micro 시도
    micros = [it for it in items if "micro" in (it.get("fileName", "")).lower()]
    target = micros if micros else items

    if micros:
        print(f"[+] Micro 들어간 펌웨어 {len(micros)}개 발견:")
        for m in micros:
            print(f"    - {m.get('fileName')} v{m.get('version')}")
    else:
        print("[!] Micro 발견 못함. 모든 펌웨어 다운로드 시도.")
        # 전체 제품 출력
        seen_products = set()
        for it in items:
            num = it.get("type")
            if num not in seen_products:
                seen_products.add(num)
                print(f"    #{num}: {it.get('fileName')}")

    print(f"\n[*] 다운로드 시작 ({len(target)} 항목)")
    saved = download_firmwares(target, out_dir)

    print(f"\n[완료] {len(saved)}개 파일 저장됨")
    for p in saved:
        print(f"  {p}")

    return 0 if saved else 2


if __name__ == "__main__":
    sys.exit(main())
