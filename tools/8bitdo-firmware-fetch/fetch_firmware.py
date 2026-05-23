"""
8BitDo 펌웨어 다운로더 v3 — 실제 앱 API 기반

이전 fetcher 는 deprecated된 /firmware/select 호출해서 빈 list 받음.
실제 8BitDo 앱은 /firmware/loadNewToolUpdateVersion 사용 — type, version 헤더 필요.

전략:
1. type 1~199 brute force, 각 type 마다 ver 0/1/100/1000 시도
2. 유의미한 응답 모두 수집
3. 응답 데이터에서 파일 URL 추출 → 다운로드
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("[!] pip install requests")
    sys.exit(1)


BASES = [
    "http://dl.8bitdo.com:8080",
    "http://dl.8bitdo.cn:8080",
    "http://beta.8bitdo.com:8080",
]

# 실제 앱이 사용하는 엔드포인트 (HttpsUtils.smali line 198)
ENDPOINT = "/firmware/loadNewToolUpdateVersion"

# type 후보 — brute force
TYPE_RANGE = range(1, 200)


def try_type(base: str, type_id: int, version: int = 0) -> dict | None:
    """특정 type+version 으로 펌웨어 정보 요청."""
    try:
        r = requests.post(
            f"{base}{ENDPOINT}",
            headers={
                "type": str(type_id),
                "version": str(version),
            },
            timeout=10,
        )
        if r.status_code != 200:
            return None
        try:
            d = r.json()
        except json.JSONDecodeError:
            return None
        if not isinstance(d, dict):
            return None
        # 의미 있는 응답: msgState=1 외에 데이터 키 존재
        extra_keys = [
            k for k in d.keys()
            if k not in ("msgState", "error")
            and d.get(k) not in (None, "", [], {})
        ]
        if extra_keys:
            return d
        return None
    except requests.RequestException:
        return None


def scan_base(base: str) -> dict[int, dict]:
    """한 base 에서 모든 type 시도."""
    print(f"\n=== Base: {base} ===")
    found = {}
    for type_id in TYPE_RANGE:
        if type_id % 25 == 0:
            print(f"  진행: type={type_id} (찾은 거: {len(found)})", flush=True)
        for ver in [0, 1, 100, 1000]:
            resp = try_type(base, type_id, ver)
            if resp:
                found[type_id] = resp
                print(f"  [+] type={type_id} ver={ver}")
                print(f"      {json.dumps(resp, ensure_ascii=False)[:250]}")
                break
    return found


def extract_urls(data: dict) -> list[str]:
    """응답 dict 에서 다운로드 URL 후보 추출."""
    urls = []
    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            if obj.endswith(".dat") or obj.endswith(".bin") or "/firmware" in obj or "upload" in obj.lower():
                urls.append(obj)
    walk(data)
    return urls


def main() -> int:
    out_dir = Path("firmware_dl")
    out_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = out_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("8BitDo Firmware Fetcher v3 (실제 앱 API 사용)")
    print("=" * 60)
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        print(f"내 외부 IP: {ip}")
    except Exception:
        print("외부 IP 확인 불가")
    print(f"엔드포인트: POST {ENDPOINT}")
    print()

    all_found = {}
    for base in BASES:
        try:
            results = scan_base(base)
        except KeyboardInterrupt:
            break
        all_found[base] = results
        debug_file = debug_dir / f"{base.replace('://','_').replace(':','_').replace('/','_')}.json"
        debug_file.write_text(
            json.dumps({str(k): v for k, v in results.items()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    total = sum(len(r) for r in all_found.values())
    print(f"\n총 {total}개 (base, type) 조합에서 응답 받음")

    if total == 0:
        print("[X] 모든 시도 빈 응답.")
        print("   가능성:")
        print("   - 서버가 GitHub IP 차단")
        print("   - type 헤더 외에 추가 인증 필요")
        print("   - API 또 다른 엔드포인트 사용")
        return 1

    # 다운로드 시도
    print("\n=== 다운로드 시도 ===")
    saved = []
    seen_urls = set()
    for base, results in all_found.items():
        for type_id, data in results.items():
            urls = extract_urls(data)
            for u in urls:
                full = u if u.startswith("http") else (base + (u if u.startswith("/") else "/" + u))
                if full in seen_urls:
                    continue
                seen_urls.add(full)
                print(f"\n  type={type_id} URL: {full}")
                try:
                    r = requests.get(full, stream=True, timeout=60)
                    print(f"    HTTP {r.status_code} | len={r.headers.get('Content-Length','?')}")
                    if r.status_code != 200:
                        continue
                    fname = os.path.basename(u) or f"type{type_id}.dat"
                    outp = out_dir / fname
                    total_size = 0
                    with open(outp, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                            total_size += len(chunk)
                    if total_size < 100:
                        outp.unlink()
                        print(f"    너무 작음 ({total_size}B) — skip")
                        continue
                    print(f"    ✓ {total_size:,} bytes → {outp.name}")
                    saved.append(outp)
                    # 메타도 저장
                    meta = outp.with_suffix(outp.suffix + ".json")
                    meta.write_text(
                        json.dumps({"type": type_id, "base": base, "url": full, "response": data}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as e:
                    print(f"    실패: {e}")

    print(f"\n총 {len(saved)}개 파일 저장")
    return 0 if saved else 2


if __name__ == "__main__":
    sys.exit(main())
