# -*- coding: utf-8 -*-
"""仪表盘：环境检测总览 + 系统安装程序。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.detection import detect_all, list_installed_programs
from app.ui_theme import (
    BG_CARD, GREEN, ORANGE, TEXT_MAIN, TEXT_MUTE, TEXT_SUB, ACCENT,
    BackgroundRunner, Card, Pill, get_font, make_treeview,
)


class DashboardPage(ttk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, padding=20)
        self.app = app
        self._programs: list = []
        self._runner = BackgroundRunner(self)
        self._build_header()
        self._build_stat_cards()
        self._build_tables()
        self.refresh()

    # ------------------------------------------------------------------ 布局
    def _build_header(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="环境总览", style="Title.TLabel").pack(side="left")
        self.status_label = ttk.Label(header, text="准备就绪", style="Sub.TLabel")
        self.status_label.pack(side="left", padx=14)
        self.refresh_btn = ttk.Button(header, text="重新检测", style="Accent.TButton",
                                      command=self.refresh)
        self.refresh_btn.pack(side="right")

    def _build_stat_cards(self) -> None:
        wrap = ttk.Frame(self)
        wrap.pack(fill="x", pady=(16, 16))
        self.stat_vars = {}
        items = (
            ("total", "检测工具总数", TEXT_SUB),
            ("found", "已安装", GREEN),
            ("managed", "本程序托管", ACCENT),
            ("programs", "系统安装程序", ORANGE),
        )
        for i, (key, label, color) in enumerate(items):
            card = ttk.Frame(wrap, style="Card.TFrame", padding=18)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            wrap.grid_columnconfigure(i, weight=1)
            num = ttk.Label(card, text="-", style="Stat.TLabel", foreground=color)
            num.pack(anchor="w")
            ttk.Label(card, text=label, style="CardSub.TLabel").pack(anchor="w", pady=(4, 0))
            self.stat_vars[key] = num

    def _build_tables(self) -> None:
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_rowconfigure(0, weight=1)

        env_card = Card(body, "开发环境检测结果")
        env_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cols = (
            ("display", "工具", 130),
            ("status", "状态", 70),
            ("version", "版本", 110),
            ("managed", "托管", 70),
        )
        self.env_tree, box = make_treeview(env_card.body, cols, height=14)
        box.pack(fill="both", expand=True)
        self.env_tree.tag_configure("ok", foreground=GREEN)
        self.env_tree.tag_configure("missing", foreground=TEXT_MUTE)
        self.env_tree.tag_configure("managed", foreground=ACCENT)
        self.env_tree.bind("<Motion>", self._on_tree_hover)

        prog_card = Card(body, "系统已安装程序（注册表）")
        prog_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        search = ttk.Entry(prog_card.body)
        search.pack(fill="x", pady=(0, 8))
        search.insert(0, "输入名称关键字过滤...")
        search.bind("<FocusIn>", lambda _e: self._clear_hint(search))
        search.bind("<KeyRelease>", lambda _e: self._fill_programs(search.get()))
        self._search = search
        pcols = (
            ("name", "名称", 200),
            ("version", "版本", 90),
            ("publisher", "发布者", 130),
        )
        self.prog_tree, pbox = make_treeview(prog_card.body, pcols, height=13)
        pbox.pack(fill="both", expand=True)

    def _clear_hint(self, entry: ttk.Entry) -> None:
        if entry.get() == "输入名称关键字过滤...":
            entry.delete(0, "end")

    def _on_tree_hover(self, event) -> None:
        row_id = self.env_tree.identify_row(event.y)
        if row_id:
            self.env_tree.configure(cursor="hand2")
        else:
            self.env_tree.configure(cursor="")

    # ------------------------------------------------------------------ 数据
    def refresh(self) -> None:
        if self._runner.running:
            return
        self.refresh_btn.configure(state="disabled")
        self.status_label.configure(text="正在检测本机环境...")

        def task(runner: BackgroundRunner):
            results = detect_all()
            programs = list_installed_programs()
            return results, programs

        self._runner.start(task, on_done=self._on_done, on_error=self._on_error)

    def _on_done(self, payload) -> None:
        results, programs = payload
        self._programs = programs
        self.refresh_btn.configure(state="normal")
        self.status_label.configure(text="检测完成")

        found = sum(1 for r in results if r.found)
        managed = sum(1 for r in results if r.managed)
        self.stat_vars["total"].configure(text=str(len(results)))
        self.stat_vars["found"].configure(text=str(found))
        self.stat_vars["managed"].configure(text=str(managed))
        self.stat_vars["programs"].configure(text=str(len(programs)))

        self.env_tree.delete(*self.env_tree.get_children())
        for r in results:
            tag = "ok" if r.found else "missing"
            self.env_tree.insert(
                "", "end", iid=r.spec_id,
                values=(r.display,
                        "已安装" if r.found else "未安装",
                        r.version or "-",
                        "是" if r.managed else ""),
                tags=(tag, "managed" if r.managed else ""),
            )
        self._fill_programs(self._search.get())

    def _fill_programs(self, keyword: str) -> None:
        self.prog_tree.delete(*self.prog_tree.get_children())
        kw = keyword.strip().lower()
        if kw == "输入名称关键字过滤...":
            kw = ""
        for p in self._programs:
            if kw and kw not in p.name.lower():
                continue
            self.prog_tree.insert("", "end", values=(p.name, p.version, p.publisher))

    def _on_error(self, exc: Exception) -> None:
        self.refresh_btn.configure(state="normal")
        self.status_label.configure(text=f"检测出错：{exc}")
