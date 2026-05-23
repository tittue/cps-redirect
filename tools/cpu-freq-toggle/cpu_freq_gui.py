"""
CPU 클럭 조절 GUI

윈도우 전원 옵션의 PROCTHROTTLEMIN/MAX를 동시에 같은 값으로 설정해서
CPU를 슬라이더 % 값에 **강제 고정**시킨다. (단순 캡이 아니라 확실한 쓰로틀링)

키보드/마우스 후킹 없음 → 게임 안티치트 안전.

실행: python cpu_freq_gui.py
관리자 권한이 없으면 자동으로 권한 상승 프롬프트가 뜸.
"""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox


# -------- 윈도우 전원 옵션 GUID (정식 식별자) --------

SUB_PROCESSOR = "54533251-82be-4824-96c1-47b60b740d00"
PROCTHROTTLEMIN = "893dee8e-2bef-41e0-89c6-b55d0929964c"  # 최소 프로세서 상태
PROCTHROTTLEMAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"  # 최대 프로세서 상태

CREATE_NO_WINDOW = 0x08000000


# -------- 권한 --------

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        return False


def elevate() -> None:
    params = " ".join(f'"{a}"' for a in [sys.argv[0], *sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )


# -------- powercfg 호출 (인코딩 안전) --------

def run_powercfg(*args: str) -> str:
    """여러 인코딩을 순서대로 시도해서 깨지지 않는 결과를 반환."""
    raw = subprocess.run(
        ["powercfg", *args],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    ).stdout
    for enc in ("cp949", "utf-8", "mbcs", "latin-1"):
        try:
            text = raw.decode(enc)
            # 0x 헥사 값이 보이면 디코딩 성공으로 간주
            if "0x" in text or args[0].startswith("/set") or args[0].startswith("-"):
                return text
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def expose_attributes() -> None:
    """숨겨진 '최소/최대 프로세서 상태' 옵션을 노출 (윈도우 기본값에서 숨김)."""
    # -ATTRIB_HIDE 는 hide 플래그를 제거하는 동작이라 안전하게 여러 번 호출해도 OK
    for guid in (PROCTHROTTLEMIN, PROCTHROTTLEMAX):
        run_powercfg("-attributes", SUB_PROCESSOR, guid, "-ATTRIB_HIDE")


def query_value(setting_guid: str) -> tuple[int | None, int | None]:
    """특정 GUID 설정의 AC/DC 값을 0~100 정수로 반환."""
    out = run_powercfg(
        "/query", "SCHEME_CURRENT", SUB_PROCESSOR, setting_guid
    )
    # 라인 단위로 파싱: "AC" 가 포함된 라인의 0x값 → AC, "DC" 라인 → DC
    ac, dc = None, None
    for line in out.splitlines():
        m = re.search(r"0x([0-9a-fA-F]+)", line)
        if not m:
            continue
        val = int(m.group(1), 16)
        upper = line.upper()
        if "AC" in upper and ac is None:
            ac = val
        elif "DC" in upper and dc is None:
            dc = val
    return ac, dc


def set_throttle(percent: int) -> None:
    """MIN = MAX = percent 으로 설정 → CPU를 정확히 그 %에 강제 고정."""
    percent = max(5, min(100, percent))
    for cmd in ("/setacvalueindex", "/setdcvalueindex"):
        run_powercfg(cmd, "SCHEME_CURRENT", SUB_PROCESSOR, PROCTHROTTLEMIN, str(percent))
        run_powercfg(cmd, "SCHEME_CURRENT", SUB_PROCESSOR, PROCTHROTTLEMAX, str(percent))
    run_powercfg("/setactive", "SCHEME_CURRENT")


def label_for(percent: int) -> str:
    if percent <= 50:
        return "🐢 살치 모드"
    if percent <= 80:
        return "🚶 보통"
    return "🚀 고성능"


# -------- GUI --------

class CpuFreqApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("CPU 클럭 조절 (MIN+MAX 강제 고정)")
        root.geometry("460x420")
        root.resizable(False, False)

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        # 1) 현재 상태
        ttk.Label(
            root, text="현재 CPU 강제 고정 %", font=("맑은 고딕", 10)
        ).pack(pady=(15, 0))

        self.current_var = tk.StringVar(value="조회 중...")
        ttk.Label(
            root,
            textvariable=self.current_var,
            font=("맑은 고딕", 22, "bold"),
            foreground="#0066cc",
        ).pack(pady=(0, 5))

        self.detail_var = tk.StringVar(value="")
        ttk.Label(
            root,
            textvariable=self.detail_var,
            font=("맑은 고딕", 9),
            foreground="#888888",
        ).pack(pady=(0, 10))

        # 2) 슬라이더
        slider_frame = ttk.Frame(root)
        slider_frame.pack(fill="x", padx=30)

        self.slider_var = tk.IntVar(value=100)
        self.slider_label = tk.StringVar(value="100% — 🚀 고성능")

        ttk.Label(
            slider_frame,
            textvariable=self.slider_label,
            font=("맑은 고딕", 13, "bold"),
        ).pack()

        self.slider = ttk.Scale(
            slider_frame,
            from_=5,
            to=100,
            orient="horizontal",
            variable=self.slider_var,
            command=self._on_slider,
        )
        self.slider.pack(fill="x", pady=5)

        # 3) 적용 버튼
        apply_btn = ttk.Button(
            root, text="✓ 적용 (MIN+MAX 동시 고정)",
            command=self._on_apply, width=30,
        )
        apply_btn.pack(pady=10)

        # 4) 프리셋
        preset_frame = ttk.LabelFrame(root, text="빠른 설정", padding=10)
        preset_frame.pack(fill="x", padx=20, pady=5)

        presets = [
            ("🐢 살치 (50%)", 50),
            ("🚶 보통 (80%)", 80),
            ("🚀 고성능 (100%)", 100),
        ]
        for i, (text, val) in enumerate(presets):
            btn = ttk.Button(
                preset_frame, text=text,
                command=lambda v=val: self._on_preset(v),
            )
            btn.grid(row=0, column=i, padx=4, sticky="ew")
            preset_frame.columnconfigure(i, weight=1)

        # 5) 상태바
        self.status_var = tk.StringVar(value="MIN과 MAX를 같은 값으로 설정 → CPU 강제 고정")
        ttk.Label(
            root, textvariable=self.status_var,
            font=("맑은 고딕", 9), foreground="#666666",
        ).pack(pady=(10, 0))

        # 초기 attribute 노출 + 상태 로드
        expose_attributes()
        self._refresh()
        root.after(5000, self._auto_refresh)

    def _on_slider(self, _value: str = "") -> None:
        v = self.slider_var.get()
        self.slider_label.set(f"{v}% — {label_for(v)}")

    def _on_apply(self) -> None:
        percent = self.slider_var.get()
        try:
            set_throttle(percent)
            self._refresh()
            self.status_var.set(
                f"✓ {percent}% 고정 적용 (MIN={percent}%, MAX={percent}%)"
            )
        except Exception as e:
            messagebox.showerror("적용 실패", str(e))

    def _on_preset(self, percent: int) -> None:
        self.slider_var.set(percent)
        self._on_slider()
        self._on_apply()

    def _refresh(self) -> None:
        ac_max, dc_max = query_value(PROCTHROTTLEMAX)
        ac_min, dc_min = query_value(PROCTHROTTLEMIN)

        if ac_max is None:
            self.current_var.set("조회 실패")
            self.detail_var.set(
                "powercfg 출력을 읽지 못함. 관리자 권한으로 다시 실행 필요."
            )
            return

        # 메인 표시: MAX 기준 (실제 적용된 상한)
        self.current_var.set(f"{ac_max}%   ({label_for(ac_max)})")

        # 상세: MIN/MAX, AC/DC
        ac_min_s = "?" if ac_min is None else f"{ac_min}%"
        dc_min_s = "?" if dc_min is None else f"{dc_min}%"
        dc_max_s = "?" if dc_max is None else f"{dc_max}%"

        if ac_min == ac_max and dc_min == dc_max:
            self.detail_var.set(
                f"강제 고정됨 (AC: {ac_max}% / DC: {dc_max_s})"
            )
        else:
            self.detail_var.set(
                f"AC: MIN {ac_min_s} ~ MAX {ac_max}%   |   DC: MIN {dc_min_s} ~ MAX {dc_max_s}"
            )

        # 슬라이더 동기화
        self.slider_var.set(ac_max)
        self._on_slider()

    def _auto_refresh(self) -> None:
        self._refresh()
        self.root.after(5000, self._auto_refresh)


def main() -> int:
    if not is_admin():
        root = tk.Tk()
        root.withdraw()
        if messagebox.askyesno(
            "관리자 권한 필요",
            "CPU 클럭 변경에는 관리자 권한이 필요합니다.\n"
            "관리자 권한으로 다시 실행할까요?",
        ):
            elevate()
        return 0

    root = tk.Tk()
    CpuFreqApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
