"""
CPU 클럭 조절 GUI

윈도우 전원 옵션의 PROCTHROTTLEMIN / PROCTHROTTLEMAX 를 동시에 같은 값으로 설정해서
CPU를 슬라이더 % 값에 강제 고정시킨다.

키보드/마우스 후킹 없음 → 게임 안티치트 안전.

실행: python cpu_freq_gui.py
관리자 권한이 없으면 자동으로 권한 상승 프롬프트가 뜸.

키 단축키 (창에 포커스 있을 때):
    Space / Enter    토글 (저전력 ↔ 고성능)
    1                저전력 (50%)
    2                보통 (80%)
    3                고성능 (100%)
    Esc              종료
"""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont


# -------- 윈도우 전원 옵션 GUID --------

SUB_PROCESSOR = "54533251-82be-4824-96c1-47b60b740d00"
PROCTHROTTLEMIN = "893dee8e-2bef-41e0-89c6-b55d0929964c"  # 최소 프로세서 상태
PROCTHROTTLEMAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"  # 최대 프로세서 상태

CREATE_NO_WINDOW = 0x08000000

LOW_PERCENT = 50
HIGH_PERCENT = 100


# -------- 색상 팔레트 (다크 + 네온 액센트) --------

class Theme:
    BG       = "#1a1d29"
    PANEL    = "#252938"
    PANEL_2  = "#2d3142"
    TEXT     = "#e8e9f3"
    DIM      = "#8b8fa3"
    ACCENT   = "#4d7cff"
    LOW      = "#5ed4a3"
    MID      = "#ffc857"
    HIGH     = "#ff6b6b"
    OFF      = "#3a3f54"


# -------- 권한 / powercfg --------

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


def run_powercfg(*args: str) -> str:
    raw = subprocess.run(
        ["powercfg", *args],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    ).stdout
    for enc in ("cp949", "utf-8", "mbcs", "latin-1"):
        try:
            text = raw.decode(enc)
            if "0x" in text or args[0].startswith(("/set", "-")):
                return text
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def expose_attributes() -> None:
    for guid in (PROCTHROTTLEMIN, PROCTHROTTLEMAX):
        run_powercfg("-attributes", SUB_PROCESSOR, guid, "-ATTRIB_HIDE")


def query_value(setting_guid: str) -> tuple[int | None, int | None]:
    out = run_powercfg(
        "/query", "SCHEME_CURRENT", SUB_PROCESSOR, setting_guid
    )
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
    percent = max(5, min(100, percent))
    for cmd in ("/setacvalueindex", "/setdcvalueindex"):
        run_powercfg(cmd, "SCHEME_CURRENT", SUB_PROCESSOR, PROCTHROTTLEMIN, str(percent))
        run_powercfg(cmd, "SCHEME_CURRENT", SUB_PROCESSOR, PROCTHROTTLEMAX, str(percent))
    run_powercfg("/setactive", "SCHEME_CURRENT")


def mode_for(percent: int) -> tuple[str, str]:
    """(라벨, 색상) 반환."""
    if percent <= 50:
        return ("저전력", Theme.LOW)
    if percent <= 80:
        return ("보통", Theme.MID)
    return ("고성능", Theme.HIGH)


# -------- 커스텀 토글 위젯 --------

class ToggleSwitch(tk.Canvas):
    """클릭하면 저전력 ↔ 고성능 토글. iOS 느낌 스위치."""

    def __init__(self, parent, on_toggle, width=180, height=70):
        super().__init__(
            parent, width=width, height=height,
            bg=Theme.PANEL, highlightthickness=0, bd=0,
        )
        self.w = width
        self.h = height
        self.is_on = False  # True = 저전력 모드 ON
        self.on_toggle = on_toggle
        self._draw()
        self.bind("<Button-1>", lambda e: self._toggled_by_user())

    def set_state(self, is_on: bool, fire=False):
        if self.is_on != is_on:
            self.is_on = is_on
            self._draw()
            if fire and self.on_toggle:
                self.on_toggle(self.is_on)

    def _toggled_by_user(self):
        self.is_on = not self.is_on
        self._draw()
        if self.on_toggle:
            self.on_toggle(self.is_on)

    def _draw(self):
        self.delete("all")
        pad = 6
        track_color = Theme.LOW if self.is_on else Theme.OFF
        # 트랙 (둥근 사각형 흉내)
        r = self.h // 2 - pad
        self.create_oval(pad, pad, pad + 2 * r, pad + 2 * r, fill=track_color, outline="")
        self.create_oval(self.w - pad - 2 * r, pad, self.w - pad, pad + 2 * r, fill=track_color, outline="")
        self.create_rectangle(pad + r, pad, self.w - pad - r, pad + 2 * r, fill=track_color, outline="")
        # 노브
        knob_r = r - 4
        if self.is_on:
            cx = self.w - pad - r
        else:
            cx = pad + r
        cy = pad + r
        self.create_oval(cx - knob_r, cy - knob_r, cx + knob_r, cy + knob_r, fill="#ffffff", outline="")
        # 텍스트
        label = "저전력 ON" if self.is_on else "고성능 모드"
        text_color = Theme.TEXT if self.is_on else Theme.DIM
        self.create_text(self.w // 2, self.h - 5, text=label, fill=text_color, font=("맑은 고딕", 8))


# -------- 메인 앱 --------

class CpuFreqApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("CPU 클럭 조절")
        root.geometry("480x560")
        root.resizable(False, False)
        root.configure(bg=Theme.BG)

        # ttk 스타일 다크 테마
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TFrame", background=Theme.BG,
        )
        style.configure(
            "Card.TFrame", background=Theme.PANEL,
        )
        style.configure(
            "Dark.Horizontal.TScale",
            background=Theme.PANEL, troughcolor=Theme.PANEL_2,
        )

        # === 헤더 ===
        header = tk.Frame(root, bg=Theme.BG)
        header.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            header, text="⚡  CPU 클럭 컨트롤",
            bg=Theme.BG, fg=Theme.TEXT,
            font=("맑은 고딕", 16, "bold"),
        ).pack(anchor="w")

        tk.Label(
            header,
            text="MIN = MAX 동시 고정으로 CPU 클럭을 정확히 잠금",
            bg=Theme.BG, fg=Theme.DIM,
            font=("맑은 고딕", 9),
        ).pack(anchor="w", pady=(2, 0))

        # === 현재 상태 카드 ===
        status_card = tk.Frame(root, bg=Theme.PANEL)
        status_card.pack(fill="x", padx=20, pady=10)

        # 좌측: LED + 상태 텍스트
        left = tk.Frame(status_card, bg=Theme.PANEL)
        left.pack(side="left", fill="both", expand=True, padx=20, pady=18)

        led_row = tk.Frame(left, bg=Theme.PANEL)
        led_row.pack(anchor="w")
        self.led = tk.Canvas(led_row, width=14, height=14, bg=Theme.PANEL, highlightthickness=0)
        self.led.pack(side="left", padx=(0, 8))
        self.led_id = self.led.create_oval(2, 2, 12, 12, fill=Theme.OFF, outline="")
        self.mode_label = tk.Label(
            led_row, text="--",
            bg=Theme.PANEL, fg=Theme.TEXT,
            font=("맑은 고딕", 11, "bold"),
        )
        self.mode_label.pack(side="left")

        self.percent_label = tk.Label(
            left, text="-- %",
            bg=Theme.PANEL, fg=Theme.TEXT,
            font=("맑은 고딕", 32, "bold"),
        )
        self.percent_label.pack(anchor="w", pady=(8, 0))

        self.detail_label = tk.Label(
            left, text="조회 중...",
            bg=Theme.PANEL, fg=Theme.DIM,
            font=("맑은 고딕", 9),
        )
        self.detail_label.pack(anchor="w", pady=(2, 0))

        # 우측: 토글 스위치
        right = tk.Frame(status_card, bg=Theme.PANEL)
        right.pack(side="right", padx=20, pady=18)

        tk.Label(
            right, text="원클릭 토글",
            bg=Theme.PANEL, fg=Theme.DIM,
            font=("맑은 고딕", 9),
        ).pack(anchor="e", pady=(0, 6))

        self.toggle = ToggleSwitch(right, on_toggle=self._on_toggle)
        self.toggle.pack()

        # === 슬라이더 ===
        slider_frame = tk.Frame(root, bg=Theme.BG)
        slider_frame.pack(fill="x", padx=20, pady=(15, 5))

        row = tk.Frame(slider_frame, bg=Theme.BG)
        row.pack(fill="x")
        tk.Label(
            row, text="수동 조절",
            bg=Theme.BG, fg=Theme.TEXT,
            font=("맑은 고딕", 10, "bold"),
        ).pack(side="left")

        self.slider_value_lbl = tk.Label(
            row, text="100%",
            bg=Theme.BG, fg=Theme.ACCENT,
            font=("맑은 고딕", 11, "bold"),
        )
        self.slider_value_lbl.pack(side="right")

        self.slider_var = tk.IntVar(value=100)
        self.slider = ttk.Scale(
            slider_frame, from_=5, to=100,
            orient="horizontal", variable=self.slider_var,
            command=self._on_slider, style="Dark.Horizontal.TScale",
        )
        self.slider.pack(fill="x", pady=(5, 8))

        apply_btn = tk.Button(
            slider_frame, text="✓  슬라이더 값 적용",
            bg=Theme.ACCENT, fg="#ffffff",
            font=("맑은 고딕", 10, "bold"),
            relief="flat", cursor="hand2", pady=8,
            activebackground="#3a6ae0", activeforeground="#ffffff",
            command=self._on_apply,
        )
        apply_btn.pack(fill="x")

        # === 프리셋 ===
        preset_frame = tk.Frame(root, bg=Theme.BG)
        preset_frame.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(
            preset_frame, text="프리셋",
            bg=Theme.BG, fg=Theme.TEXT,
            font=("맑은 고딕", 10, "bold"),
        ).pack(anchor="w")

        preset_row = tk.Frame(preset_frame, bg=Theme.BG)
        preset_row.pack(fill="x", pady=(6, 0))

        for i, (txt, val, color) in enumerate([
            ("저전력 50%", 50, Theme.LOW),
            ("보통 80%", 80, Theme.MID),
            ("고성능 100%", 100, Theme.HIGH),
        ]):
            b = tk.Button(
                preset_row, text=txt,
                bg=Theme.PANEL_2, fg=color,
                font=("맑은 고딕", 10, "bold"),
                relief="flat", cursor="hand2", pady=10,
                activebackground=color, activeforeground="#ffffff",
                command=lambda v=val: self._on_preset(v),
            )
            b.grid(row=0, column=i, padx=3, sticky="ew")
            preset_row.columnconfigure(i, weight=1)

        # === 상태바 ===
        self.status_var = tk.StringVar(
            value="Space/Enter = 토글  |  1/2/3 = 프리셋  |  Esc = 종료"
        )
        tk.Label(
            root, textvariable=self.status_var,
            bg=Theme.BG, fg=Theme.DIM,
            font=("맑은 고딕", 8),
        ).pack(side="bottom", pady=8)

        # 키 단축키 (창 내부 한정 — 글로벌 후킹 아님, 안티치트 안전)
        root.bind("<space>", lambda e: self._toggle_now())
        root.bind("<Return>", lambda e: self._toggle_now())
        root.bind("1", lambda e: self._on_preset(50))
        root.bind("2", lambda e: self._on_preset(80))
        root.bind("3", lambda e: self._on_preset(100))
        root.bind("<Escape>", lambda e: root.destroy())

        # 초기화
        expose_attributes()
        self._refresh()
        root.after(5000, self._auto_refresh)
        root.focus_force()

    # ---- 이벤트 ----

    def _on_slider(self, _value: str = "") -> None:
        v = self.slider_var.get()
        self.slider_value_lbl.config(text=f"{v}%")

    def _on_apply(self) -> None:
        self._apply_percent(self.slider_var.get(), origin="슬라이더")

    def _on_preset(self, percent: int) -> None:
        self.slider_var.set(percent)
        self._on_slider()
        self._apply_percent(percent, origin="프리셋")

    def _on_toggle(self, is_on: bool) -> None:
        target = LOW_PERCENT if is_on else HIGH_PERCENT
        self._apply_percent(target, origin="토글")

    def _toggle_now(self) -> None:
        """현재가 고성능이면 저전력으로, 아니면 고성능으로."""
        ac, _ = query_value(PROCTHROTTLEMAX)
        if ac is None or ac >= 90:
            self._apply_percent(LOW_PERCENT, origin="단축키")
        else:
            self._apply_percent(HIGH_PERCENT, origin="단축키")

    def _apply_percent(self, percent: int, origin: str = "") -> None:
        try:
            set_throttle(percent)
            self._refresh()
            label, _ = mode_for(percent)
            tag = f"[{origin}] " if origin else ""
            self.status_var.set(f"{tag}{percent}% 고정 적용됨 ({label})")
        except Exception as e:
            messagebox.showerror("적용 실패", str(e))

    # ---- 화면 갱신 ----

    def _refresh(self) -> None:
        ac_max, dc_max = query_value(PROCTHROTTLEMAX)
        ac_min, dc_min = query_value(PROCTHROTTLEMIN)

        if ac_max is None:
            self.percent_label.config(text="?? %")
            self.detail_label.config(
                text="powercfg 출력 파싱 실패 — 관리자 권한 확인 필요"
            )
            self.led.itemconfig(self.led_id, fill=Theme.HIGH)
            self.mode_label.config(text="오류")
            return

        label, color = mode_for(ac_max)

        self.percent_label.config(text=f"{ac_max} %", fg=color)
        self.mode_label.config(text=label, fg=color)
        self.led.itemconfig(self.led_id, fill=color)

        if ac_min == ac_max and dc_min == dc_max:
            self.detail_label.config(
                text=f"강제 고정 중 · MIN = MAX = {ac_max}%",
            )
        else:
            self.detail_label.config(
                text=f"MIN {ac_min or '?'}% ~ MAX {ac_max}%   (DC: {dc_min or '?'}~{dc_max or '?'}%)"
            )

        # 슬라이더 / 토글 동기화
        self.slider_var.set(ac_max)
        self._on_slider()
        self.toggle.set_state(ac_max <= 60)

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
