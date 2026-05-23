"""
8BitDo 펌웨어 다운로더 v5 — 컨트롤러 펌웨어 API + 올바른 URL

이전 v4는 /firmware/loadNewToolUpdateVersion 호출했는데 그건 PC/모바일 앱
업데이트용. 컨트롤러 펌웨어는 /firmware/loadNewVersion 사용.

필요한 헤더 (HttpsUtils.smali line 910-948):
- type: 컨트롤러 모델 ID
- version: 현재 버전
- beta: 베타 식별자
- isLoadBeta: "1"

URL 구성도 수정 — fileURL 이 "/var/lib/tomcat9/webapps//firmwareFile/upload/..."
같은 서버 절대경로로 반환되므로 그 prefix 제거.
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from pathlib import Path

OUT_DIR = Path("firmware_dl")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = OUT_DIR / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "_marker.txt").write_text("Python script v5 started\n", encoding="utf-8")

print("=" * 60, flush=True)
print("8BitDo Firmware Fetcher v5 (controller firmware)", flush=True)
print("=" * 60, flush=True)

try:
    import requests
except ImportError:
    print("[!] pip install requests", flush=True)
    sys.exit(1)


BASES = [
    "http://dl.8bitdo.com:8080",
    "http://dl.8bitdo.cn:8080",
]
ENDPOINT = "/firmware/loadNewVersion"

TYPE_RANGE = list(range(1, 200))


def safe_post(url: str, headers: dict, timeout: float = 5.0) -> dict | None:
    try:
        r = requests.post(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return {"_http": r.status_code, "_body": r.text[:300]}
        try:
            return r.json()
        except Exception:
            return {"_http": 200, "_body": r.text[:300]}
    except Exception as e:
        return {"_error": str(e)}


def fix_url(server_path: str, base: str) -> str:
    """
    8BitDo 서버가 반환하는 fileURL 예시:
        /var/lib/tomcat9/webapps//firmwareFile/upload//abc.zip
    실제 다운로드 URL:
        http://dl.8bitdo.com:8080/firmwareFile/upload/abc.zip
    """
    if server_path.startswith("http"):
        return server_path
    # tomcat webapps 절대 경로 제거
    s = re.sub(r"^.*?/webapps/+", "/", server_path)
    # 연속된 / 정리
    s = re.sub(r"/+", "/", s)
    if not s.startswith("/"):
        s = "/" + s
    return base + s


def extract_files(data: dict) -> list[dict]:
    """응답의 list 안에 있는 파일 정보 모두 추출."""
    if not isinstance(data, dict):
        return []
    items = data.get("list", [])
    if not isinstance(items, list):
        return []
    return items


def main() -> int:
    # IP 확인
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        print(f"외부 IP: {ip}", flush=True)
    except Exception:
        pass

    all_findings = {}

    for base in BASES:
        print(f"\n=== {base}{ENDPOINT} brute force ===", flush=True)
        for type_id in TYPE_RANGE:
            for ver in [0]:
                resp = safe_post(
                    f"{base}{ENDPOINT}",
                    headers={
                        "type": str(type_id),
                        "version": str(ver),
                        "beta": "0",
                        "isLoadBeta": "1",
                    },
                    timeout=4,
                )
                if isinstance(resp, dict):
                    items = extract_files(resp)
                    if items:
                        # 의미 있는 응답
                        key = f"{base}_type{type_id}_v{ver}"
                        all_findings[key] = {"base": base, "type": type_id, "ver": ver, "response": resp, "files": items}
                        # 파일명 보여주기
                        names = [it.get("fileName", "?") for it in items]
                        print(f"  [+] type={type_id}: {names}", flush=True)
            if type_id % 25 == 0:
                print(f"  진행 type={type_id}, 발견={len(all_findings)}", flush=True)

        # 결과 저장
        base_safe = base.replace("://", "_").replace(":", "_").replace("/", "_")
        (DEBUG_DIR / f"{base_safe}_results.json").write_text(
            json.dumps(
                {k: v for k, v in all_findings.items() if v["base"] == base},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

    print(f"\n[*] 총 {len(all_findings)}개 type에서 펌웨어 발견", flush=True)

    if not all_findings:
        print("[X] 컨트롤러 펌웨어 못 찾음. 추가 헤더 필요할 수도.", flush=True)
        return 1

    # 다운로드
    print("\n=== 다운로드 ===", flush=True)
    saved = []
    seen = set()
    for key, info in all_findings.items():
        base = info["base"]
        type_id = info["type"]
        for item in info["files"]:
            server_path = item.get("fileURL") or item.get("filePath") or ""
            if not server_path:
                continue
            url = fix_url(server_path, base)
            if url in seen:
                continue
            seen.add(url)
            fname = item.get("fileName") or os.path.basename(server_path)
            ext = ".zip" if server_path.endswith(".zip") else ".dat"
            outname = f"type{type_id}_{fname}{ext}"
            outname = re.sub(r"[^\w.\-]", "_", outname)
            outp = OUT_DIR / outname

            print(f"\n  type={type_id} {fname}", flush=True)
            print(f"    URL: {url}", flush=True)
            try:
                r = requests.get(url, stream=True, timeout=60)
                print(f"    HTTP {r.status_code}, size={r.headers.get('Content-Length','?')}", flush=True)
                if r.status_code != 200:
                    continue
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
                saved.append(outp)
                # 메타
                outp.with_suffix(outp.suffix + ".json").write_text(
                    json.dumps({"type": type_id, "item": item, "url": url}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                print(f"    실패: {e}", flush=True)

    print(f"\n[완료] {len(saved)}개 펌웨어 파일 저장", flush=True)
    return 0 if saved else 2


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        traceback.print_exc()
        (OUT_DIR / "_error.txt").write_text(f"{e}\n{traceback.format_exc()}", encoding="utf-8")
        rc = 99
    sys.exit(rc)
