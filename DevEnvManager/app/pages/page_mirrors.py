# -*- coding: utf-8 -*-
"""镜像加速页。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import mirrors
from app.elevate import is_permission_error, relaunch_as_admin
from app.ui_theme import (
    GREEN, ORANGE, TEXT_MUTE,
    BackgroundRunner, Card, get_font,
)


class MirrorsPage(ttk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, padding=20)
        self.app = app
        self._runner = BackgroundRunner(self)
        self._build()
        self.refresh_status()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="镜像加速", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="刷新当前状态",
                   command=self.refresh_status).pack(side="right")

        hint = ttk.Label(
            self,
            text="将包管理器切换到国内镜像可显著提升依赖下载速度；所有修改仅作用于当前 Windows 用户。",
            style="Sub.TLabel")
        hint.pack(anchor="w", pady=(12, 14))

        # Node 生态
        node_card = Card(self, "Node 生态（npm / pnpm / yarn）",
                         "将对本机已安装的包管理器统一生效")
        node_card.pack(fill="x", pady=(0, 14))
        self.node_current = ttk.Label(node_card.body, text="读取中...",
                                      style="CardSub.TLabel", foreground=GREEN)
        self.node_current.pack(anchor="w")
        row = ttk.Frame(node_card.body, style="Card.TFrame")
        row.pack(fill="x", pady=(10, 0))
        self.node_buttons = {}
        for opt in mirrors.NPM_MIRRORS:
            btn = ttk.Button(row, text=opt.label,
                             command=lambda o=opt: self.apply_node(o))
            btn.pack(side="left", padx=(0, 8))
            self.node_buttons[opt.id] = btn

        # pip
        pip_card = Card(self, "Python pip", "写入 %APPDATA%\\pip\\pip.ini")
        pip_card.pack(fill="x", pady=(0, 14))
        self.pip_current = ttk.Label(pip_card.body, text="读取中...",
                                     style="CardSub.TLabel", foreground=GREEN)
        self.pip_current.pack(anchor="w")
        prow = ttk.Frame(pip_card.body, style="Card.TFrame")
        prow.pack(fill="x", pady=(10, 0))
        self.pip_buttons = {}
        for opt in mirrors.PIP_MIRRORS:
            btn = ttk.Button(prow, text=opt.label,
                             command=lambda o=opt: self.apply_pip(o))
            btn.pack(side="left", padx=(0, 8))
            self.pip_buttons[opt.id] = btn

        # Go
        go_card = Card(self, "Go 模块代理（GOPROXY）",
                       "写入用户环境变量，新终端生效")
        go_card.pack(fill="x")
        self.go_current = ttk.Label(go_card.body, text="读取中...",
                                    style="CardSub.TLabel", foreground=GREEN)
        self.go_current.pack(anchor="w")
        grow = ttk.Frame(go_card.body, style="Card.TFrame")
        grow.pack(fill="x", pady=(10, 0))
        self.go_buttons = {}
        for opt in mirrors.GO_MIRRORS:
            btn = ttk.Button(grow, text=opt.label,
                             command=lambda o=opt: self.apply_go(o))
            btn.pack(side="left", padx=(0, 8))
            self.go_buttons[opt.id] = btn

        self.result_label = ttk.Label(self, text="", style="Sub.TLabel",
                                      foreground=ORANGE)
        self.result_label.pack(anchor="w", pady=(14, 0))

    # ------------------------------------------------------------------ 状态读取
    def on_show(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        npm_reg = mirrors.get_npm_registry("npm")
        self.node_current.configure(
            text=f"当前 npm registry：{npm_reg or '未配置（使用默认源）'}")
        pip_reg = mirrors.get_pip_index_url()
        self.pip_current.configure(
            text=f"当前 pip index-url：{pip_reg or '未配置（使用默认源）'}")
        go_proxy = mirrors.get_goproxy()
        self.go_current.configure(
            text=f"当前 GOPROXY：{go_proxy or '未配置（使用默认源）'}")
        self._highlight_buttons(npm_reg, pip_reg, go_proxy)

    def _highlight_buttons(self, npm_reg, pip_reg, go_proxy) -> None:
        for opt in mirrors.NPM_MIRRORS:
            self.node_buttons[opt.id].configure(
                style="Accent.TButton" if npm_reg and opt.url == npm_reg else "TButton")
        for opt in mirrors.PIP_MIRRORS:
            self.pip_buttons[opt.id].configure(
                style="Accent.TButton" if pip_reg and opt.url == pip_reg else "TButton")
        for opt in mirrors.GO_MIRRORS:
            self.go_buttons[opt.id].configure(
                style="Accent.TButton" if go_proxy and opt.url == go_proxy else "TButton")

    # ------------------------------------------------------------------ 应用设置
    def _set_buttons_state(self, state: str) -> None:
        for group in (self.node_buttons, self.pip_buttons, self.go_buttons):
            for btn in group.values():
                btn.configure(state=state)

    def _run(self, task, success_msg: str) -> None:
        if self._runner.running:
            return
        self._set_buttons_state("disabled")

        def done(_payload) -> None:
            self._set_buttons_state("normal")
            self.result_label.configure(text=success_msg, foreground=GREEN)
            self.refresh_status()

        def error(exc: Exception) -> None:
            self._set_buttons_state("normal")
            self.result_label.configure(text=f"操作失败：{exc}", foreground=ORANGE)
            if is_permission_error(exc) and messagebox.askyesno(
                    "需要管理员权限",
                    "当前进程没有写入环境变量的权限。\n"
                    "是否以管理员身份重新启动程序？"):
                if relaunch_as_admin():
                    self.app.destroy()

        self._runner.start(task, on_done=done, on_error=error)

    def apply_node(self, opt) -> None:
        def task(runner: BackgroundRunner):
            return mirrors.apply_node_mirror(opt.url)
        self._run(task, f"已将 Node 包管理器切换到 {opt.label}")

    def apply_pip(self, opt) -> None:
        def task(runner: BackgroundRunner):
            mirrors.set_pip_index_url(opt.url)
            return None
        self._run(task, f"已将 pip 源切换到 {opt.label}")

    def apply_go(self, opt) -> None:
        def task(runner: BackgroundRunner):
            mirrors.set_goproxy(opt.url)
            return None
        self._run(task, f"已将 GOPROXY 切换到 {opt.label}")
