"""
CPU Frequency Toggle (Python 버전)

윈도우 전원 옵션의 "최대 프로세서 상태(%)"를 powercfg로 변경.
오토핫키 같은 키보드 후킹을 사용하지 않으므로 게임 안티치트 위험 없음.

사용법:
    python cpu_freq.py 50        # 살치 모드 (50%)
    python cpu_freq.py 80        # 보통 (80%)
    python cpu_freq.py 100       # 고성능 (100%)
    python cpu_freq.py --status  # 현재 상태 조회

관리자 권한이 없으면 자동으로 권한 상승 프롬프트가 뜸.
"""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        return False


def elevate(args: list[str]) -> None:
    """현재 스크립트를 관리자 권한으로 다시 실행."""
    params = " ".join(f'"{a}"' for a in [sys.argv[0], *args])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )


def run_powercfg(*args: str) -> str:
    result = subprocess.run(
        ["powercfg", *args],
        capture_output=True,
        text=True,
        encoding="cp949",  # 한글 윈도우 기본 인코딩
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return result.stdout


def get_current() -> tuple[int | None, int | None]:
    """현재 활성 프로필의 AC/DC PROCTHROTTLEMAX 값을 반환."""
    out = run_powercfg(
        "/query", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX"
    )
    ac_match = re.search(
        r"(?:현재 AC 전원 설정 인덱스|Current AC Power Setting Index):?\s*0x([0-9a-fA-F]+)",
        out,
    )
    dc_match = re.search(
        r"(?:현재 DC 전원 설정 인덱스|Current DC Power Setting Index):?\s*0x([0-9a-fA-F]+)",
        out,
    )
    ac = int(ac_match.group(1), 16) if ac_match else None
    dc = int(dc_match.group(1), 16) if dc_match else None
    return ac, dc


def set_max(percent: int) -> None:
    run_powercfg(
        "/setacvalueindex",
        "SCHEME_CURRENT",
        "SUB_PROCESSOR",
        "PROCTHROTTLEMAX",
        str(percent),
    )
    run_powercfg(
        "/setdcvalueindex",
        "SCHEME_CURRENT",
        "SUB_PROCESSOR",
        "PROCTHROTTLEMAX",
        str(percent),
    )
    run_powercfg("/setactive", "SCHEME_CURRENT")


def label(percent: int) -> str:
    if percent <= 50:
        return "살치 모드"
    if percent <= 80:
        return "보통"
    return "고성능"


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if args[0] in ("--status", "-s"):
        ac, dc = get_current()
        print(f"AC(충전기): {ac}%  /  DC(배터리): {dc}%")
        return 0

    try:
        percent = int(args[0])
    except ValueError:
        print(f"잘못된 인자: {args[0]} (1~100 사이 정수)")
        return 1

    if not 1 <= percent <= 100:
        print(f"퍼센트는 1~100 사이여야 함: {percent}")
        return 1

    if not is_admin():
        print("관리자 권한으로 다시 실행합니다...")
        elevate([str(percent)])
        return 0

    set_max(percent)
    ac, dc = get_current()
    print(f"[OK] CPU 최대 {percent}% 적용. ({label(percent)})")
    print(f"AC: {ac}%  /  DC: {dc}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
