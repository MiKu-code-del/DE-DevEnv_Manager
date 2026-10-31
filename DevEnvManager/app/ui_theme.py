# -*- coding: utf-8 -*-
"""深色主题、字体与通用 UI 组件。"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# ------------------------------------------------------------------ 配色
BG_APP = "#1b1d23"        # 主背景
BG_SIDEBAR = "#14161b"    # 侧边栏
BG_CARD = "#23262e"       # 卡片
BG_CARD_2 = "#2a2e38"     # 卡片内次级容器
BG_INPUT = "#1f2229"      # 输入框
BORDER = "#31353f"
BORDER_SOFT = "#2a2e38"

TEXT_MAIN = "#e7e9ee"
TEXT_SUB = "#9aa1ad"
TEXT_MUTE = "#6b7280"

ACCENT = "#4f8cff"
ACCENT_HOVER = "#6ba0ff"
ACCENT_SOFT = "#23406e"

GREEN = "#3fb950"
GREEN_SOFT = "#1d3a26"
ORANGE = "#d29922"
ORANGE_SOFT = "#3d3114"
RED = "#f85149"
RED_SOFT = "#4a2322"
PURPLE = "#a371f7"

FONT_FAMILY = "Microsoft YaHei UI"
MONO_FAMILY = "Cascadia Code"


def get_font(size: int = 9, weight: str = "normal", mono: bool = False) -> tkfont.Font:
    return tkfont.Font(family=MONO_FAMILY if mono else FONT_FAMILY,
                       size=size, weight=weight)


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG_APP)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG_APP, foreground=TEXT_MAIN,
                    font=get_font(9), borderwidth=0)
    style.configure("TFrame", background=BG_APP)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Card2.TFrame", background=BG_CARD_2)
    style.configure("TLabel", background=BG_APP, foreground=TEXT_MAIN)
    style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_MAIN)
    style.configure("Sub.TLabel", background=BG_APP, foreground=TEXT_SUB)
    style.configure("CardSub.TLabel", background=BG_CARD, foreground=TEXT_SUB)
    style.configure("Title.TLabel", background=BG_APP, foreground=TEXT_MAIN,
                    font=get_font(15, "bold"))
    style.configure("CardTitle.TLabel", background=BG_CARD, foreground=TEXT_MAIN,
                    font=get_font(11, "bold"))
    style.configure("H1.TLabel", background=BG_CARD, foreground=TEXT_MAIN,
                    font=get_font(13, "bold"))
    style.configure("Stat.TLabel", background=BG_CARD, foreground=TEXT_MAIN,
                    font=get_font(20, "bold"))

    # 普通按钮
    style.configure("TButton", background=BG_CARD_2, foreground=TEXT_MAIN,
                    padding=(14, 7), borderwidth=0, focusthickness=0)
    style.map("TButton",
              background=[("active", BORDER), ("pressed", BORDER)],
              foreground=[("active", TEXT_MAIN)])

    # 主色按钮
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    padding=(16, 8), font=get_font(9, "bold"))
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)])

    # 危险按钮
    style.configure("Danger.TButton", background=RED_SOFT, foreground=RED,
                    padding=(14, 7))
    style.map("Danger.TButton",
              background=[("active", RED), ("pressed", RED)],
              foreground=[("active", "#ffffff")])

    # 输入框
    style.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT_MAIN,
                    insertcolor=TEXT_MAIN, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, padding=6)

    # 进度条
    style.configure("Horizontal.TProgressbar", troughcolor=BG_INPUT,
                    background=ACCENT, borderwidth=0, thickness=8)

    # 表格
    style.configure("Treeview", background=BG_INPUT, fieldbackground=BG_INPUT,
                    foreground=TEXT_MAIN, rowheight=30, borderwidth=0,
                    font=get_font(9))
    style.configure("Treeview.Heading", background=BG_CARD_2, foreground=TEXT_SUB,
                    font=get_font(9, "bold"), padding=(8, 8), borderwidth=0)
    style.map("Treeview",
              background=[("selected", ACCENT_SOFT)],
              foreground=[("selected", TEXT_MAIN)])
    style.map("Treeview.Heading", background=[("active", BORDER)])

    # 滚动条
    style.configure("Vertical.TScrollbar", background=BG_CARD_2,
                    troughcolor=BG_APP, borderwidth=0, arrowsize=0)
    style.configure("Horizontal.TScrollbar", background=BG_CARD_2,
                    troughcolor=BG_APP, borderwidth=0, arrowsize=0)

    # 单选/复选
    style.configure("TRadiobutton", background=BG_CARD, foreground=TEXT_MAIN)
    style.map("TRadiobutton", background=[("active", BG_CARD)])
    style.configure("TCheckbutton", background=BG_CARD, foreground=TEXT_MAIN)
    style.map("TCheckbutton", background=[("active", BG_CARD)])


# ------------------------------------------------------------------ 组件
class Card(ttk.Frame):
    """带标题栏的卡片容器。"""

    def __init__(self, master, title: str = "", subtitle: str = "", **kw) -> None:
        super().__init__(master, style="Card.TFrame", **kw)
        if title:
            header = ttk.Frame(self, style="Card.TFrame")
            header.pack(fill="x", padx=16, pady=(14, 6))
            ttk.Label(header, text=title, style="CardTitle.TLabel").pack(side="left")
            if subtitle:
                ttk.Label(header, text=subtitle, style="CardSub.TLabel").pack(
                    side="left", padx=8)
        self.body = ttk.Frame(self, style="Card.TFrame")
        self.body.pack(fill="both", expand=True, padx=16, pady=(4, 16))


class Pill(tk.Label):
    """状态胶囊。"""

    def __init__(self, master, text: str, color: str, soft: str, **kw) -> None:
        super().__init__(master, text=text, fg=color, bg=soft,
                         font=get_font(8, "bold"), padx=10, pady=3, bd=0, **kw)


class HoverButton(tk.Label):
    """可变色的扁平按钮（用于侧边栏与工具切换）。"""

    def __init__(self, master, text: str, command=None, active_bg=BORDER,
                 inactive_bg=BG_SIDEBAR, fg=TEXT_SUB, active_fg=TEXT_MAIN,
                 padx=18, **kw) -> None:
        super().__init__(master, text=text, bg=inactive_bg, fg=fg,
                         font=get_font(10), padx=padx, pady=10, anchor="w",
                         cursor="hand2", **kw)
        self._command = command
        self._active_bg = active_bg
        self._inactive_bg = inactive_bg
        self._fg = fg
        self._active_fg = active_fg
        self._selected = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.configure(bg=self._active_bg if selected else self._inactive_bg,
                       fg=self._active_fg if selected else self._fg)

    def _on_enter(self, _event) -> None:
        if not self._selected:
            self.configure(bg=self._active_bg, fg=self._active_fg)

    def _on_leave(self, _event) -> None:
        if not self._selected:
            self.configure(bg=self._inactive_bg, fg=self._fg)

    def _on_click(self, _event) -> None:
        if self._command:
            self._command()


def make_treeview(master, columns: tuple[tuple[str, str, int], ...],
                   height: int = 12) -> tuple[ttk.Treeview, ttk.Frame]:
    """创建带滚动条的 Treeview。

    columns 元素为 (column_key, 标题, 宽度)。
    """
    container = ttk.Frame(master)
    container.configure(style=master.winfo_class() and "TFrame")
    keys = [c[0] for c in columns]
    tree = ttk.Treeview(container, columns=keys, show="headings", height=height)
    for key, heading, width in columns:
        tree.heading(key, text=heading)
        tree.column(key, width=width, anchor="w")
    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return tree, container


# ------------------------------------------------------------------ 后台任务
class BackgroundRunner:
    """在线程中执行任务，通过事件队列把进度/完成事件送回 UI 线程。"""

    def __init__(self, root: tk.Misc) -> None:
        self._root = root
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self.cancel_event = threading.Event()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, task, on_event=None, on_done=None, on_error=None) -> None:
        if self.running:
            raise RuntimeError("已有任务在运行")
        self.cancel_event.clear()
        self._on_event = on_event
        self._on_done = on_done
        self._on_error = on_error

        def worker() -> None:
            try:
                result = task(self)
                self._queue.put(("done", result))
            except Exception as exc:  # noqa: BLE001 - 需把所有异常送回 UI
                self._queue.put(("error", exc))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        self._poll()

    def emit(self, event: str, payload=None) -> None:
        self._queue.put((event, payload))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "done":
                    if self._on_done:
                        self._on_done(payload)
                elif kind == "error":
                    if self._on_error:
                        self._on_error(payload)
                elif self._on_event:
                    self._on_event(kind, payload)
        except queue.Empty:
            pass
        if self.running:
            self._root.after(120, self._poll)
