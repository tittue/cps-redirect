"""
CPU 클럭 조절 GUI

윈도우 전원 옵션의 "최대 프로세서 상태(%)"를 슬라이더로 직관적으로 조절.
키보드 후킹 없음 → 게임 안티치트 안전.

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


# -------- 권한 / powercfg --------

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        return False


def elevate() -> None:
    """현재 스크립트를 관리자 권한으로 다시 실행."""
    params = " ".join(f'"{a}"' for a in [sys.argv[0], *sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )


CREATE_NO_WINDOW = 0x08000000


def run_powercfg(*args: str) -> str:
    result = subprocess.run(
        ["powercfg", *args],
        capture_output=True,
        text=True,
        encoding="cp949",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    return result.stdout


def get_current() -> tuple[int | None, int | None]:
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
        root.title("CPU 클럭 조절")
        root.geometry("420x360")
        root.resizable(False, False)

        # 기본 폰트
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        # 현재 상태 표시
        self.current_var = tk.StringVar(value="조회 중...")
        ttk.Label(
            root,
            text="현재 CPU 최대 사용률",
            font=("맑은 고딕", 10),
        ).pack(pady=(20, 0))

        ttk.Label(
            root,
            textvariable=self.current_var,
            font=("맑은 고딕", 22, "bold"),
            foreground="#0066cc",
        ).pack(pady=(0, 15))

        # 슬라이더
        slider_frame = ttk.Frame(root)
        slider_frame.pack(fill="x", padx=30, pady=5)

        self.slider_var = tk.IntVar(value=100)
        self.slider_label = tk.StringVar(value="100%")

        ttk.Label(
            slider_frame,
            textvariable=self.slider_label,
            font=("맑은 고딕", 14, "bold"),
        ).pack()

        self.slider = ttk.Scale(
            slider_frame,
            from_=10,
            to=100,
            orient="horizontal",
            variable=self.slider_var,
            command=self._on_slider,
        )
        self.slider.pack(fill="x", pady=5)

        # 적용 버튼
        apply_btn = ttk.Button(
            root, text="✓ 적용", command=self._on_apply, width=20
        )
        apply_btn.pack(pady=10)

        # 프리셋 버튼
        preset_frame = ttk.LabelFrame(root, text="빠른 설정", padding=10)
        preset_frame.pack(fill="x", padx=20, pady=10)

        presets = [
            ("🐢 살치 (50%)", 50),
            ("🚶 보통 (80%)", 80),
            ("🚀 고성능 (100%)", 100),
        ]
        for i, (text, val) in enumerate(presets):
            btn = ttk.Button(
                preset_frame,
                text=text,
                command=lambda v=val: self._on_preset(v),
            )
            btn.grid(row=0, column=i, padx=4, sticky="ew")
            preset_frame.columnconfigure(i, weight=1)

        # 상태 메시지
        self.status_var = tk.StringVar(value="")
        ttk.Label(
            root,
            textvariable=self.status_var,
            font=("맑은 고딕", 9),
            foreground="#666666",
        ).pack(pady=(5, 0))

        # 초기 상태 로드
        self._refresh()
        # 5초마다 외부 변경 감지용 자동 새로고침
        root.after(5000, self._auto_refresh)

    def _on_slider(self, _value: str) -> None:
        v = self.slider_var.get()
        self.slider_label.set(f"{v}% — {label_for(v)}")

    def _on_apply(self) -> None:
        percent = self.slider_var.get()
        try:
            set_max(percent)
            self._refresh()
            self.status_var.set(f"✓ {percent}% 적용됨 ({label_for(percent)})")
        except Exception as e:
            messagebox.showerror("적용 실패", str(e))

    def _on_preset(self, percent: int) -> None:
        self.slider_var.set(percent)
        self._on_slider("")
        self._on_apply()

    def _refresh(self) -> None:
        ac, dc = get_current()
        if ac is None:
            self.current_var.set("조회 실패")
            return
        if ac == dc:
            self.current_var.set(f"{ac}%   ({label_for(ac)})")
        else:
            self.current_var.set(
                f"AC {ac}% / DC {dc}%   ({label_for(ac)})"
            )
        self.slider_var.set(ac)
        self._on_slider("")

    def _auto_refresh(self) -> None:
        self._refresh()
        self.root.after(5000, self._auto_refresh)


def main() -> int:
    if not is_admin():
        # 권한 없으면 메시지 보여주고 권한 상승
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
    app = CpuFreqApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
