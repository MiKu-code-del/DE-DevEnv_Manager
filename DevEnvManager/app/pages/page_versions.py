# -*- coding: utf-8 -*-
"""版本管理：在线安装、本地导入、激活切换与卸载。"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import env_manager
from app.elevate import is_permission_error, relaunch_as_admin
from app.detection import current_version, list_managed_versions
from app.tool_specs import INSTALLABLE_SPECS, RemoteVersion
from app.ui_theme import (
    ACCENT, BG_INPUT, GREEN, RED, TEXT_MAIN, TEXT_MUTE, TEXT_SUB,
    BackgroundRunner, Card, get_font, make_treeview,
)

TOOL_TABS = (("node", "Node.js"), ("go", "Go"), ("jdk", "Temurin JDK"))


class VersionsPage(ttk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.tool_id = "node"
        self._remote: list[RemoteVersion] = []
        self._runner = BackgroundRunner(self)
        self._remote_loaded: set[str] = set()
        self._build()
        self.reload_installed()
        self.fetch_remote()

    # ------------------------------------------------------------------ 布局
    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="版本管理", style="Title.TLabel").pack(side="left")

        tabs = ttk.Frame(header)
        tabs.pack(side="right")
        self.tab_buttons = {}
        for tid, label in TOOL_TABS:
            btn = ttk.Button(tabs, text=label,
                             command=lambda t=tid: self.switch_tool(t))
            btn.pack(side="left", padx=6)
            self.tab_buttons[tid] = btn

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(14, 10))
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_rowconfigure(0, weight=1)

        # 左：已安装
        left = Card(body, "已安装版本", "存放在管理根目录")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cols = (("version", "版本", 200), ("status", "状态", 120))
        self.inst_tree, ibox = make_treeview(left.body, cols, height=12)
        ibox.pack(fill="both", expand=True)
        self.inst_tree.tag_configure("current", foreground=GREEN)

        btns = ttk.Frame(left.body, style="Card.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="激活选中", style="Accent.TButton",
                   command=self.activate_selected).pack(side="left")
        ttk.Button(btns, text="卸载选中", style="Danger.TButton",
                   command=self.uninstall_selected).pack(side="left", padx=8)
        ttk.Button(btns, text="导入本地 zip",
                   command=self.import_zip).pack(side="left")

        # 右：远程
        right = Card(body, "远程版本", "双击行可直接安装")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        rcols = (("version", "版本", 180), ("label", "说明", 150))
        self.remote_tree, rbox = make_treeview(right.body, rcols, height=12)
        rbox.pack(fill="both", expand=True)
        rbtns = ttk.Frame(right.body, style="Card.TFrame")
        rbtns.pack(fill="x", pady=(10, 0))
        ttk.Button(rbtns, text="安装选中", style="Accent.TButton",
                   command=self.install_selected).pack(side="left")
        self.refresh_remote_btn = ttk.Button(rbtns, text="刷新远程列表",
                                              command=self.fetch_remote)
        self.refresh_remote_btn.pack(side="left", padx=8)

        # 底部：进度与日志
        log_card = Card(self, "任务进度与日志")
        log_card.pack(fill="x")
        prog_row = ttk.Frame(log_card.body, style="Card.TFrame")
        prog_row.pack(fill="x")
        self.progress = ttk.Progressbar(prog_row, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.pct_label = ttk.Label(prog_row, text="0%", style="CardSub.TLabel",
                                   width=6)
        self.pct_label.pack(side="left", padx=(10, 0))
        self.cancel_btn = ttk.Button(prog_row, text="取消", style="Danger.TButton",
                                     command=self.cancel_task, state="disabled")
        self.cancel_btn.pack(side="left", padx=(10, 0))

        self.log_text = tk.Text(log_card.body, height=6, bg=BG_INPUT,
                                fg=TEXT_SUB, bd=0, wrap="word",
                                font=get_font(9, mono=True), padx=10, pady=8)
        self.log_text.pack(fill="x", pady=(10, 0))
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------ 工具切换
    def switch_tool(self, tool_id: str) -> None:
        if self._runner.running:
            messagebox.showinfo("提示", "请等待当前任务结束后再切换")
            return
        self.tool_id = tool_id
        for tid, btn in self.tab_buttons.items():
            btn.configure(style="Accent.TButton" if tid == tool_id else "TButton")
        self.reload_installed()
        if tool_id in self._remote_loaded:
            self._fill_remote()
        else:
            self.fetch_remote()

    # ------------------------------------------------------------------ 数据加载
    def reload_installed(self) -> None:
        self.inst_tree.delete(*self.inst_tree.get_children())
        cur = current_version(self.tool_id)
        versions = list_managed_versions(self.tool_id)
        if not versions:
            self.inst_tree.insert("", "end", values=("（暂无已安装版本）", ""))
        for v in versions:
            status = "使用中" if v == cur else ""
            self.inst_tree.insert("", "end", iid=v, values=(v, status),
                                  tags=("current" if v == cur else ""))
        self._update_tab_style()

    def _update_tab_style(self) -> None:
        for tid, btn in self.tab_buttons.items():
            btn.configure(style="Accent.TButton" if tid == self.tool_id else "TButton")

    def fetch_remote(self) -> None:
        if self._runner.running:
            return
        self.refresh_remote_btn.configure(state="disabled")
        self.remote_tree.delete(*self.remote_tree.get_children())
        self.remote_tree.insert("", "end", values=("正在获取版本列表...", ""))
        tid = self.tool_id

        def task(runner: BackgroundRunner):
            return env_manager.fetch_remote_versions(tid)

        def done(payload) -> None:
            self._remote = payload
            self._remote_loaded.add(self.tool_id)
            self.refresh_remote_btn.configure(state="normal")
            self._fill_remote()

        self._runner.start(task, on_done=done, on_error=self._on_remote_error)

    def _on_remote_error(self, exc: Exception) -> None:
        self.refresh_remote_btn.configure(state="normal")
        self.remote_tree.delete(*self.remote_tree.get_children())
        self.remote_tree.insert("", "end", values=(f"获取失败：{exc}", ""))
        self.log(f"获取远程版本失败：{exc}")

    def _fill_remote(self) -> None:
        self.remote_tree.delete(*self.remote_tree.get_children())
        if not self._remote:
            self.remote_tree.insert("", "end", values=("（无可用版本）", ""))
        for rv in self._remote:
            self.remote_tree.insert("", "end", iid=rv.version,
                                    values=(rv.version, rv.label))
        self.remote_tree.bind("<Double-1>", lambda _e: self.install_selected())

    # ------------------------------------------------------------------ 安装
    def install_selected(self) -> None:
        if self._runner.running:
            return
        sel = self.remote_tree.focus()
        rv = next((x for x in self._remote if x.version == sel), None)
        if rv is None:
            return
        if not messagebox.askyesno(
                "确认安装",
                f"确定下载并安装 {INSTALLABLE_SPECS[self.tool_id].display} {rv.version}？\n"
                "安装后将自动激活，新开的终端窗口生效。"):
            return
        self._run_install(
            lambda runner: env_manager.install_version(
                self.tool_id, rv,
                progress_cb=lambda p: runner.emit("progress", p),
                log_cb=lambda m: runner.emit("log", m),
                cancel_event=runner.cancel_event,
            ))

    def import_zip(self) -> None:
        if self._runner.running:
            return
        path = filedialog.askopenfilename(
            title="选择本地压缩包",
            filetypes=[("Zip 压缩包", "*.zip"), ("所有文件", "*.*")])
        if not path:
            return
        self._run_install(
            lambda runner: env_manager.import_local_zip(
                self.tool_id, Path(path),
                log_cb=lambda m: runner.emit("log", m),
            ))

    def _run_install(self, task_factory) -> None:
        self.progress.configure(value=0)
        self.pct_label.configure(text="0%")
        self.cancel_btn.configure(state="normal")

        def on_event(kind, payload) -> None:
            if kind == "progress":
                pct = payload.percent
                self.progress.configure(value=pct)
                self.pct_label.configure(text=f"{pct:.0f}%")
            elif kind == "log":
                self.log(str(payload))

        def done(_payload) -> None:
            self.progress.configure(value=100)
            self.pct_label.configure(text="100%")
            self.cancel_btn.configure(state="disabled")
            self.reload_installed()
            self.log("任务完成。")

        def error(exc: Exception) -> None:
            self.cancel_btn.configure(state="disabled")
            self.log(f"任务失败：{exc}")
            self._handle_possible_permission(exc)

        self._runner.start(task_factory, on_event=on_event,
                           on_done=done, on_error=error)

        self._runner.start(task_factory, on_event=on_event,
                           on_done=done, on_error=error)

    def _handle_possible_permission(self, exc: Exception) -> None:
        if is_permission_error(exc) and messagebox.askyesno(
                "需要管理员权限",
                "当前进程没有写入环境变量的权限。\n"
                "是否以管理员身份重新启动程序？"):
            if relaunch_as_admin():
                self.app.destroy()
                return
        messagebox.showerror("任务失败", str(exc))

    # ------------------------------------------------------------------ 激活/卸载
    def activate_selected(self) -> None:
        if self._runner.running:
            return
        sel = self.inst_tree.focus()
        if not sel or sel not in list_managed_versions(self.tool_id):
            return

        def task(runner: BackgroundRunner):
            env_manager.activate(
                self.tool_id, sel,
                log_cb=lambda m: runner.emit("log", m))
            return None

        self._runner.start(
            task,
            on_event=lambda kind, payload:
                self.log(str(payload)) if kind == "log" else None,
            on_done=lambda _p: (self.log("激活完成。"), self.reload_installed()),
            on_error=lambda exc: messagebox.showerror("激活失败", str(exc)),
        )

    def uninstall_selected(self) -> None:
        if self._runner.running:
            return
        sel = self.inst_tree.focus()
        if not sel or sel not in list_managed_versions(self.tool_id):
            return
        if not messagebox.askyesno(
                "确认卸载",
                f"确定删除 {INSTALLABLE_SPECS[self.tool_id].display} {sel}？\n"
                "该版本的文件将被永久移除。"):
            return
        try:
            env_manager.uninstall_version(self.tool_id, sel)
        except env_manager.EnvError as exc:
            messagebox.showwarning("无法卸载", str(exc))
            return
        self.log(f"已卸载 {sel}")
        self.reload_installed()

    def cancel_task(self) -> None:
        self._runner.cancel_event.set()
        self.log("正在取消...")

    # ------------------------------------------------------------------ 日志
    def log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
