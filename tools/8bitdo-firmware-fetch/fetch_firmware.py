"""
8BitDo 펌웨어 다운로더 v4 — 빠른 + 항상 출력

전략: type 1~50 만, 빠른 timeout, 결과 즉시 저장.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# 매우 첫 단계: 디렉토리/파일 즉시 생성 (artifact 업로드 보장)
OUT_DIR = Path("firmware_dl")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = OUT_DIR / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "_marker.txt").write_text("Python script started\n", encoding="utf-8")

print("=" * 60, flush=True)
print("8BitDo Firmware Fetcher v4", flush=True)
print("=" * 60, flush=True)

try:
    import requests
except ImportError:
    print("[!] requests not installed; pip install requests", flush=True)
    sys.exit(1)


BASES = [
    "http://dl.8bitdo.com:8080",
    "http://dl.8bitdo.cn:8080",
]
ENDPOINT_TOOL = "/firmware/loadNewToolUpdateVersion"  # 실제 앱 API
ENDPOINT_LIST = "/firmware/select"  # 옛 API (디버그용)
ENDPOINT_NEW = "/firmware/loadNewVersion"  # 또 다른 API

TYPE_CANDIDATES = list(range(1, 51))  # 1~50만
VERSION_CANDIDATES = [0]  # 빠르게 1번만


def safe_post(url: str, headers: dict, timeout: float = 5.0) -> dict | None:
    try:
        r = requests.post(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return {"_http": r.status_code, "_body_preview": r.text[:200] if r.text else ""}
        try:
            return r.json()
        except Exception:
            return {"_http": 200, "_body_preview": r.text[:200] if r.text else ""}
    except Exception as e:
        return {"_error": str(e)}


def main() -> int:
    # IP 확인
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        print(f"내 외부 IP: {ip}", flush=True)
    except Exception:
        print("외부 IP 확인 불가", flush=True)

    summary = {"endpoints": {}}

    # 1. 우선 옛 API (select) 어떤지 확인
    for base in BASES:
        print(f"\n=== [{base}] /firmware/select 테스트 ===", flush=True)
        resp = safe_post(f"{base}{ENDPOINT_LIST}", headers={"Beta": "1"}, timeout=8)
        print(f"  → {str(resp)[:200]}", flush=True)
        summary["endpoints"][f"{base}/select"] = resp

    # 2. /firmware/loadNewVersion 테스트
    for base in BASES:
        print(f"\n=== [{base}] /firmware/loadNewVersion 테스트 ===", flush=True)
        resp = safe_post(f"{base}{ENDPOINT_NEW}", headers={"Beta": "1"}, timeout=8)
        print(f"  → {str(resp)[:200]}", flush=True)
        summary["endpoints"][f"{base}/loadNewVersion"] = resp

    # 3. /firmware/loadNewToolUpdateVersion brute force
    print("\n=== /firmware/loadNewToolUpdateVersion 브루트 포스 ===", flush=True)
    type_results = {}
    for base in BASES:
        print(f"\n  base: {base}", flush=True)
        for type_id in TYPE_CANDIDATES:
            for ver in VERSION_CANDIDATES:
                resp = safe_post(
                    f"{base}{ENDPOINT_TOOL}",
                    headers={"type": str(type_id), "version": str(ver)},
                    timeout=4,
                )
                # 의미있는 응답 (msgState/error 외 데이터 있는 거)만 기록
                if isinstance(resp, dict):
                    extras = [k for k in resp if k not in ("msgState", "error", "_http", "_body_preview", "_error")]
                    if any(resp.get(k) not in (None, "", [], {}) for k in extras) and "list" not in extras:
                        type_results[(base, type_id, ver)] = resp
                        print(f"    [+] type={type_id} ver={ver}: {str(resp)[:200]}", flush=True)
                    elif resp.get("list") and len(resp.get("list", [])) > 0:
                        type_results[(base, type_id, ver)] = resp
                        print(f"    [+] type={type_id} ver={ver} (list non-empty): {str(resp)[:200]}", flush=True)
            if type_id % 10 == 0:
                print(f"    진행 type={type_id}, 발견={len(type_results)}", flush=True)
        # base 별 결과 저장
        base_safe = base.replace("://", "_").replace(":", "_").replace("/", "_")
        (DEBUG_DIR / f"{base_safe}_types.json").write_text(
            json.dumps({f"{k[1]}_v{k[2]}": v for k, v in type_results.items() if k[0] == base}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary["type_results_count"] = len(type_results)
    summary["type_results"] = {f"{k[0]}|{k[1]}_v{k[2]}": v for k, v in type_results.items()}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[*] 총 {len(type_results)}개 응답 발견", flush=True)

    if not type_results:
        print("[X] 모든 응답 빈값. API 변경 또는 인증 필요.", flush=True)
        return 1

    # 다운로드 URL 추출
    download_count = 0
    for (base, type_id, ver), data in type_results.items():
        def find_urls(obj, found):
            if isinstance(obj, dict):
                for v in obj.values():
                    find_urls(v, found)
            elif isinstance(obj, list):
                for v in obj:
                    find_urls(v, found)
            elif isinstance(obj, str) and ("/firmwareFile" in obj or obj.endswith(".dat") or obj.endswith(".bin")):
                found.append(obj)

        urls = []
        find_urls(data, urls)
        for u in urls:
            full = u if u.startswith("http") else (base + (u if u.startswith("/") else "/" + u))
            print(f"\n  type={type_id} 다운로드: {full}", flush=True)
            try:
                r = requests.get(full, stream=True, timeout=30)
                if r.status_code != 200:
                    print(f"    HTTP {r.status_code}", flush=True)
                    continue
                fname = os.path.basename(u) or f"type{type_id}.dat"
                outp = OUT_DIR / fname
                total = 0
                with open(outp, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                        total += len(chunk)
                if total < 100:
                    outp.unlink()
                    print(f"    너무 작음 ({total}B)", flush=True)
                    continue
                print(f"    ✓ {total:,} bytes → {outp.name}", flush=True)
                download_count += 1
                meta = outp.with_suffix(outp.suffix + ".json")
                meta.write_text(
                    json.dumps({"type": type_id, "base": base, "url": full, "response": data}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                print(f"    실패: {e}", flush=True)

    print(f"\n[완료] {download_count}개 파일 저장", flush=True)
    return 0 if download_count else 2


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        traceback.print_exc()
        (OUT_DIR / "_error.txt").write_text(f"Exception: {e}\n{traceback.format_exc()}", encoding="utf-8")
        rc = 99
    sys.exit(rc)
