"""
KeyMacro GUI — 키 + 딜레이 + 랜덤 딜레이 매크로 도구

설계 목표:
- 키보드 후킹 (SetWindowsHookEx) 사용하지 않음 — GetAsyncKeyState 폴링
- 키 입력은 SendInput Win32 API 직접 호출 (ctypes)
- 매크로 스텝마다 랜덤 딜레이로 패턴 분석 회피
- 트리거 키 누르면 매크로 실행, 같은 키 다시 누르면 중지

사용 흐름:
1. 8BitDo Micro 를 K(키보드) 모드로 PC 연결
2. 8BitDo 앱에서 트리거로 쓸 버튼을 "F23" 같은 안 쓰는 키에 매핑
3. 이 프로그램에서 매크로 정의 + Trigger를 "F23"으로
4. 게임 화면에서 F23 한 번 누르면 매크로 시작 / 다시 누르면 중지

⚠ 메이플 안티치트는 시간이 지남에 따라 새 탐지 룰이 추가될 수 있음.
   이 도구는 일반적인 후킹/인젝션 흔적은 남기지 않지만, 100% 안전 보장은 불가능.
   본인 계정/리스크 책임 하에 사용할 것.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import random
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field, asdict
from pathlib import Path
from tkinter import ttk, filedialog, messagebox


# ============================================================
# Windows API (SendInput, GetAsyncKeyState)  — ctypes 직접 호출
# ============================================================

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    ]


class _INPUT_union(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUT_union)]


def _send_key_event(vk: int, key_up: bool) -> None:
    """SendInput으로 키 이벤트 1개 전송. 스캔코드 모드라 가장 흔적이 적음."""
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    flags = KEYEVENTF_SCANCODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(
        type=INPUT_KEYBOARD,
        u=_INPUT_union(
            ki=KEYBDINPUT(
                wVk=0,  # 스캔코드 모드면 0
                wScan=scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=ctypes.cast(0, ctypes.POINTER(wt.ULONG)),
            )
        ),
    )
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def press_key(vk: int, hold_ms: int = 30) -> None:
    """키를 잠깐 눌렀다 뗌."""
    _send_key_event(vk, key_up=False)
    time.sleep(hold_ms / 1000.0)
    _send_key_event(vk, key_up=True)


def is_key_pressed(vk: int) -> bool:
    """GetAsyncKeyState — 후킹 안 함."""
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


# ============================================================
# 가상 키코드 매핑 (사람이 읽기 좋은 이름 ↔ Win32 VK)
# ============================================================

VK_MAP: dict[str, int] = {
    # 알파벳
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
    # 숫자
    **{str(d): 0x30 + d for d in range(10)},
    # 방향키
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    # 기능키
    **{f"F{n}": 0x6F + n for n in range(1, 25) if n <= 12} | {f"F{n}": 0x87 + n - 13 for n in range(13, 25)},
    # 특수
    "SPACE": 0x20, "ENTER": 0x0D, "TAB": 0x09, "ESC": 0x1B,
    "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,
    "LSHIFT": 0xA0, "RSHIFT": 0xA1,
    "LCTRL": 0xA2, "RCTRL": 0xA3,
    "LALT": 0xA4, "RALT": 0xA5,
    "BACKSPACE": 0x08, "DELETE": 0x2E, "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    # 마이너스/기호
    "MINUS": 0xBD, "EQUAL": 0xBB, "COMMA": 0xBC, "DOT": 0xBE, "SLASH": 0xBF,
    "SEMICOLON": 0xBA, "QUOTE": 0xDE, "LBRACKET": 0xDB, "RBRACKET": 0xDD, "BACKSLASH": 0xDC,
    "TILDE": 0xC0,
}

# F13 ~ F24 매핑 보정
for n in range(13, 25):
    VK_MAP[f"F{n}"] = 0x7C + (n - 13)


def vk_from_name(name: str) -> int | None:
    return VK_MAP.get(name.upper())


# ============================================================
# 매크로 모델
# ============================================================

@dataclass
class MacroStep:
    key: str = "X"            # 키 이름
    hold_ms: int = 30         # 눌렀다 떼는 시간
    delay_min_ms: int = 100   # 다음 스텝까지 최소 딜레이
    delay_max_ms: int = 150   # 최대 딜레이 (이 사이 랜덤)

    def delay_ms(self) -> int:
        if self.delay_max_ms <= self.delay_min_ms:
            return self.delay_min_ms
        return random.randint(self.delay_min_ms, self.delay_max_ms)


@dataclass
class MacroProfile:
    name: str = "Untitled"
    trigger_key: str = "F23"     # 매크로 시작/중지 키
    loop: bool = True            # True면 트리거 다시 누를 때까지 반복
    steps: list[MacroStep] = field(default_factory=list)


# ============================================================
# 매크로 실행 엔진
# ============================================================

class MacroEngine:
    def __init__(self, on_status):
        self.profile: MacroProfile = MacroProfile()
        self.running = False
        self._stop_flag = threading.Event()
        self._worker: threading.Thread | None = None
        self._trigger_thread: threading.Thread | None = None
        self._trigger_active = False
        self.on_status = on_status

    def set_profile(self, p: MacroProfile) -> None:
        self.profile = p

    # ---- 트리거 감지 (백그라운드) ----

    def start_trigger_listener(self) -> None:
        if self._trigger_active:
            return
        self._trigger_active = True
        self._trigger_thread = threading.Thread(target=self._trigger_loop, daemon=True)
        self._trigger_thread.start()

    def stop_trigger_listener(self) -> None:
        self._trigger_active = False

    def _trigger_loop(self) -> None:
        last_state = False
        while self._trigger_active:
            vk = vk_from_name(self.profile.trigger_key)
            if vk is None:
                time.sleep(0.2)
                continue
            cur = is_key_pressed(vk)
            # rising edge = press
            if cur and not last_state:
                if self.running:
                    self.stop()
                else:
                    self.start()
                time.sleep(0.3)  # debounce
            last_state = cur
            time.sleep(0.01)

    # ---- 매크로 실행 ----

    def start(self) -> None:
        if self.running or not self.profile.steps:
            return
        self.running = True
        self._stop_flag.clear()
        self.on_status(f"▶ 매크로 실행 중 ({len(self.profile.steps)} 스텝)")
        self._worker = threading.Thread(target=self._run_macro, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        if not self.running:
            return
        self._stop_flag.set()
        self.running = False
        self.on_status("■ 정지됨")

    def _run_macro(self) -> None:
        try:
            while not self._stop_flag.is_set():
                for step in self.profile.steps:
                    if self._stop_flag.is_set():
                        break
                    vk = vk_from_name(step.key)
                    if vk is not None:
                        press_key(vk, hold_ms=step.hold_ms)
                    # 랜덤 딜레이 (interruptible)
                    delay_s = step.delay_ms() / 1000.0
                    end = time.time() + delay_s
                    while time.time() < end:
                        if self._stop_flag.is_set():
                            break
                        time.sleep(0.005)
                if not self.profile.loop:
                    break
        finally:
            self.running = False
            self.on_status("■ 매크로 종료")


# ============================================================
# GUI
# ============================================================

class Theme:
    BG = "#15171f"
    PANEL = "#1f2230"
    PANEL_2 = "#2a2e3f"
    TEXT = "#e8e9f3"
    DIM = "#8b8fa3"
    ACCENT = "#5ed4a3"
    WARN = "#ffc857"
    DANGER = "#ff6b6b"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.engine = MacroEngine(on_status=self._set_status)
        self.steps_vars: list[tuple[tk.StringVar, tk.IntVar, tk.IntVar, tk.IntVar]] = []

        root.title("KeyMacro — 랜덤 딜레이 매크로")
        root.geometry("680x640")
        root.configure(bg=Theme.BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # 헤더
        tk.Label(
            root, text="⌨  KeyMacro",
            bg=Theme.BG, fg=Theme.TEXT,
            font=("맑은 고딕", 18, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 0))
        tk.Label(
            root, text="키 + 딜레이 + 랜덤 딜레이 매크로 — 후킹 없음, SendInput 직접",
            bg=Theme.BG, fg=Theme.DIM,
            font=("맑은 고딕", 9),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        # 트리거 / 모드
        top = tk.Frame(root, bg=Theme.PANEL)
        top.pack(fill="x", padx=16, pady=6)

        tk.Label(top, text="트리거 키", bg=Theme.PANEL, fg=Theme.TEXT,
                 font=("맑은 고딕", 10)).grid(row=0, column=0, padx=12, pady=12, sticky="w")
        self.trigger_var = tk.StringVar(value="F23")
        tk.Entry(top, textvariable=self.trigger_var, width=8,
                 bg=Theme.PANEL_2, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                 relief="flat", font=("Consolas", 11)).grid(row=0, column=1, padx=4)

        self.loop_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            top, text="루프 (트리거 다시 누르면 정지)",
            variable=self.loop_var,
            bg=Theme.PANEL, fg=Theme.TEXT,
            activebackground=Theme.PANEL, selectcolor=Theme.PANEL_2,
            font=("맑은 고딕", 10),
        ).grid(row=0, column=2, padx=20, sticky="w")

        # 매크로 스텝 리스트
        list_frame = tk.LabelFrame(
            root, text=" 매크로 스텝 ",
            bg=Theme.PANEL, fg=Theme.TEXT,
            font=("맑은 고딕", 10, "bold"),
            relief="flat", bd=0, padx=8, pady=8,
        )
        list_frame.pack(fill="both", expand=True, padx=16, pady=6)

        header = tk.Frame(list_frame, bg=Theme.PANEL)
        header.pack(fill="x", pady=(0, 4))
        for txt, w in [("#", 3), ("키", 10), ("Hold(ms)", 10),
                       ("Delay min", 10), ("Delay max", 10), ("", 8)]:
            tk.Label(header, text=txt, bg=Theme.PANEL, fg=Theme.DIM,
                     font=("맑은 고딕", 9), width=w, anchor="w").pack(side="left", padx=4)

        # 스크롤 영역
        canvas = tk.Canvas(list_frame, bg=Theme.PANEL, highlightthickness=0, height=280)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.steps_holder = tk.Frame(canvas, bg=Theme.PANEL)
        self.steps_holder.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.steps_holder, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # 스텝 추가/삭제 버튼
        btn_row = tk.Frame(root, bg=Theme.BG)
        btn_row.pack(fill="x", padx=16, pady=4)

        tk.Button(
            btn_row, text="+ 스텝 추가", bg=Theme.PANEL_2, fg=Theme.TEXT,
            font=("맑은 고딕", 10), relief="flat", cursor="hand2", pady=6, padx=12,
            activebackground=Theme.ACCENT, activeforeground="#000",
            command=self._add_step,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_row, text="프리셋: 강줄기 펄스", bg=Theme.PANEL_2, fg=Theme.WARN,
            font=("맑은 고딕", 10), relief="flat", cursor="hand2", pady=6, padx=12,
            command=self._preset_pulse,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_row, text="저장", bg=Theme.PANEL_2, fg=Theme.TEXT,
            font=("맑은 고딕", 10), relief="flat", cursor="hand2", pady=6, padx=12,
            command=self._save_profile,
        ).pack(side="right", padx=2)
        tk.Button(
            btn_row, text="불러오기", bg=Theme.PANEL_2, fg=Theme.TEXT,
            font=("맑은 고딕", 10), relief="flat", cursor="hand2", pady=6, padx=12,
            command=self._load_profile,
        ).pack(side="right", padx=2)

        # 실행 / 정지 큰 버튼
        run_row = tk.Frame(root, bg=Theme.BG)
        run_row.pack(fill="x", padx=16, pady=(10, 4))

        self.run_btn = tk.Button(
            run_row, text="▶  매크로 시작 / 정지 (트리거 키)",
            bg=Theme.ACCENT, fg="#000",
            font=("맑은 고딕", 12, "bold"),
            relief="flat", cursor="hand2", pady=12,
            command=self._toggle_macro,
        )
        self.run_btn.pack(fill="x")

        # 상태바
        self.status_var = tk.StringVar(value="대기 중 — 트리거 키 입력 대기")
        tk.Label(
            root, textvariable=self.status_var,
            bg=Theme.BG, fg=Theme.DIM,
            font=("맑은 고딕", 9),
        ).pack(side="bottom", pady=8)

        # 경고
        warn = tk.Label(
            root,
            text="⚠ 메이플 사용 시 본인 책임. 후킹/인젝션은 없지만 100% 안전 보장 X",
            bg=Theme.BG, fg=Theme.DANGER,
            font=("맑은 고딕", 8),
        )
        warn.pack(side="bottom")

        # 초기 스텝 한 줄
        self._add_step()
        self.engine.start_trigger_listener()

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- 스텝 UI ----

    def _add_step(self, key="X", hold=30, dmin=100, dmax=200) -> None:
        row = tk.Frame(self.steps_holder, bg=Theme.PANEL)
        row.pack(fill="x", pady=2)

        idx = len(self.steps_vars) + 1
        tk.Label(row, text=str(idx), bg=Theme.PANEL, fg=Theme.DIM,
                 width=3, font=("Consolas", 10)).pack(side="left", padx=4)

        key_var = tk.StringVar(value=key)
        hold_var = tk.IntVar(value=hold)
        dmin_var = tk.IntVar(value=dmin)
        dmax_var = tk.IntVar(value=dmax)

        for var, w in [(key_var, 10), (hold_var, 10),
                       (dmin_var, 10), (dmax_var, 10)]:
            tk.Entry(row, textvariable=var, width=w,
                     bg=Theme.PANEL_2, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                     relief="flat", font=("Consolas", 10)).pack(side="left", padx=4)

        tk.Button(
            row, text="✕", bg=Theme.PANEL, fg=Theme.DANGER,
            font=("맑은 고딕", 9), relief="flat", cursor="hand2",
            command=lambda r=row: self._remove_step(r),
        ).pack(side="left", padx=4)

        self.steps_vars.append((key_var, hold_var, dmin_var, dmax_var))

    def _remove_step(self, row) -> None:
        # 찾아서 vars 에서도 제거
        children = list(self.steps_holder.children.values())
        try:
            idx = children.index(row)
            self.steps_vars.pop(idx)
        except ValueError:
            pass
        row.destroy()

    def _gather_profile(self) -> MacroProfile:
        steps = []
        for key_v, hold_v, dmin_v, dmax_v in self.steps_vars:
            try:
                steps.append(MacroStep(
                    key=key_v.get().strip(),
                    hold_ms=max(1, hold_v.get()),
                    delay_min_ms=max(0, dmin_v.get()),
                    delay_max_ms=max(0, dmax_v.get()),
                ))
            except tk.TclError:
                continue
        return MacroProfile(
            name="current",
            trigger_key=self.trigger_var.get().strip() or "F23",
            loop=self.loop_var.get(),
            steps=steps,
        )

    # ---- 동작 ----

    def _toggle_macro(self) -> None:
        self.engine.set_profile(self._gather_profile())
        if self.engine.running:
            self.engine.stop()
        else:
            self.engine.start()

    def _set_status(self, msg: str) -> None:
        try:
            self.root.after(0, lambda: self.status_var.set(msg))
        except RuntimeError:
            pass

    # ---- 프리셋 ----

    def _preset_pulse(self) -> None:
        # 강줄기 펄스 — 위방향키를 약간씩 끊어서 누름 (블투/프레임 불안정성 완충)
        # 클릭하면 기존 스텝 모두 지우고 이걸로 채움
        for row in list(self.steps_holder.children.values()):
            row.destroy()
        self.steps_vars.clear()
        # 위방향키 짧은 펄스 5개, 사이 랜덤 딜레이
        for _ in range(5):
            self._add_step(key="UP", hold=80, dmin=20, dmax=60)

    # ---- 저장/불러오기 ----

    def _save_profile(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON profile", "*.json")],
            title="매크로 프로필 저장",
        )
        if not path:
            return
        p = self._gather_profile()
        Path(path).write_text(
            json.dumps(asdict(p), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._set_status(f"저장됨: {Path(path).name}")

    def _load_profile(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON profile", "*.json")],
            title="매크로 프로필 불러오기",
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("불러오기 실패", str(e))
            return
        self.trigger_var.set(data.get("trigger_key", "F23"))
        self.loop_var.set(data.get("loop", True))
        for row in list(self.steps_holder.children.values()):
            row.destroy()
        self.steps_vars.clear()
        for s in data.get("steps", []):
            self._add_step(
                key=s.get("key", "X"),
                hold=s.get("hold_ms", 30),
                dmin=s.get("delay_min_ms", 100),
                dmax=s.get("delay_max_ms", 150),
            )
        self._set_status(f"불러옴: {Path(path).name}")

    def _on_close(self) -> None:
        self.engine.stop()
        self.engine.stop_trigger_listener()
        self.root.destroy()


def main() -> int:
    if sys.platform != "win32":
        print("Windows 전용 도구입니다.")
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
