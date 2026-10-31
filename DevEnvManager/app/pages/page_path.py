# -*- coding: utf-8 -*-
"""PATH 环境变量治理页。"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import env_manager
from app.config import get_config
from app.elevate import is_permission_error, relaunch_as_admin
from app.ui_theme import (
    ACCENT, GREEN, ORANGE, RED, TEXT_MUTE,
    BackgroundRunner, Card, get_font, make_treeview,
)


class PathPage(ttk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, padding=20)
        self.app = app
        self._entries: list[str] = []
        self._dirty = False
        self._runner = BackgroundRunner(self)
        self._build()
        self.load_user_path()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="PATH 环境变量", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="打开 Windows 环境变量设置",
                   command=self.open_windows_settings).pack(side="right")

        warn = ttk.Frame(self, style="Card.TFrame", padding=12)
        warn.pack(fill="x", pady=(14, 14))
        ttk.Label(warn,
                  text="注意：PATH 控制命令行工具的查找位置，删除必要条目可能导致软件无法启动。"
                       "本页的修改需点击“保存更改”才会写入注册表，建议先确认后再保存。",
                  style="Card.TLabel", foreground=ORANGE, wrap=1000).pack(anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_rowconfigure(0, weight=1)

        # 用户 PATH（可编辑）
        user_card = Card(body, "用户 PATH（可编辑）")
        user_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cols = (("path", "路径", 300), ("managed", "来源", 90))
        self.user_tree, box = make_treeview(user_card.body, cols, height=14)
        box.pack(fill="both", expand=True)
        self.user_tree.tag_configure("managed", foreground=ACCENT)
        self.user_tree.tag_configure("missing", foreground=RED)

        btns = ttk.Frame(user_card.body, style="Card.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="上移", command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(btns, text="下移", command=lambda: self.move(1)).pack(side="left", padx=8)
        ttk.Button(btns, text="新增", command=self.add_entry).pack(side="left")
        ttk.Button(btns, text="删除", style="Danger.TButton",
                   command=self.delete_entry).pack(side="left", padx=8)
        ttk.Button(btns, text="打开目录",
                   command=self.open_selected).pack(side="left")

        save_row = ttk.Frame(user_card.body, style="Card.TFrame")
        save_row.pack(fill="x", pady=(10, 0))
        self.save_btn = ttk.Button(save_row, text="保存更改", style="Accent.TButton",
                                   command=self.save, state="disabled")
        self.save_btn.pack(side="left")
        self.dirty_label = ttk.Label(save_row, text="", style="CardSub.TLabel",
                                     foreground=ORANGE)
        self.dirty_label.pack(side="left", padx=10)

        # 系统 PATH（只读）
        sys_card = Card(body, "系统 PATH（只读，需管理员权限才能修改）")
        sys_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        scols = (("path", "路径", 380),)
        self.sys_tree, sbox = make_treeview(sys_card.body, scols, height=16)
        sbox.pack(fill="both", expand=True)
        self.sys_tree.tag_configure("missing", foreground=RED)

    # ------------------------------------------------------------------ 加载
    def on_show(self) -> None:
        if not self._dirty:
            self.load_user_path()
        self.load_system_path()

    def load_user_path(self) -> None:
        self._entries = env_manager.read_user_path()
        self._dirty = False
        self._fill_user_tree()
        self.save_btn.configure(state="disabled")
        self.dirty_label.configure(text="")

    def _fill_user_tree(self) -> None:
        self.user_tree.delete(*self.user_tree.get_children())
        managed = {os.path.normcase(os.path.normpath(e))
                   for e in get_config().managed_path_entries}
        for i, entry in enumerate(self._entries):
            is_managed = os.path.normcase(os.path.normpath(entry)) in managed
            exists = os.path.exists(entry)
            tags = []
            if is_managed:
                tags.append("managed")
            if not exists:
                tags.append("missing")
            self.user_tree.insert("", "end", iid=str(i),
                                  values=(entry, "本程序" if is_managed else "用户"),
                                  tags=tuple(tags))

    def load_system_path(self) -> None:
        import winreg
        self.sys_tree.delete(*self.sys_tree.get_children())
        try:
            with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                value, _ = winreg.QueryValueEx(key, "Path")
        except OSError as exc:
            self.sys_tree.insert("", "end", values=(f"读取失败：{exc}",))
            return
        for entry in str(value).split(";"):
            entry = entry.strip()
            if not entry:
                continue
            expanded = os.path.expandvars(entry)
            tag = ("missing",) if not os.path.exists(expanded) else ()
            self.sys_tree.insert("", "end", values=(expanded,), tags=tag)

    # ------------------------------------------------------------------ 编辑操作
    def _selected_index(self) -> int | None:
        sel = self.user_tree.focus()
        if not sel:
            return None
        try:
            return int(sel)
        except ValueError:
            return None

    def move(self, delta: int) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        new_idx = idx + delta
        if not (0 <= new_idx < len(self._entries)):
            return
        item = self._entries.pop(idx)
        self._entries.insert(new_idx, item)
        self._mark_dirty()
        self._fill_user_tree()
        self.user_tree.focus(str(new_idx))
        self.user_tree.selection_set(str(new_idx))

    def add_entry(self) -> None:
        folder = filedialog.askdirectory(title="选择要加入 PATH 的目录")
        if not folder:
            return
        norm = os.path.normpath(folder)
        if os.path.normcase(norm) in {os.path.normcase(e) for e in self._entries}:
            messagebox.showinfo("提示", "该目录已在 PATH 中")
            return
        self._entries.append(norm)
        self._mark_dirty()
        self._fill_user_tree()

    def delete_entry(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        if not messagebox.askyesno("确认", f"确定从 PATH 移除该条目？\n{self._entries[idx]}"):
            return
        self._entries.pop(idx)
        self._mark_dirty()
        self._fill_user_tree()

    def open_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        path = self._entries[idx]
        if os.path.exists(path):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            messagebox.showwarning("提示", "目录不存在，可能已被移动或删除")

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.save_btn.configure(state="normal")
        self.dirty_label.configure(text="有未保存的更改")

    def save(self) -> None:
        try:
            env_manager.replace_user_path(self._entries)
        except env_manager.EnvError as exc:
            if is_permission_error(exc) and messagebox.askyesno(
                    "需要管理员权限",
                    "当前进程没有写入环境变量的权限。\n"
                    "是否以管理员身份重新启动程序？"):
                if relaunch_as_admin():
                    self.app.destroy()
                    return
            messagebox.showerror("保存失败", str(exc))
            return
        self._dirty = False
        self.save_btn.configure(state="disabled")
        self.dirty_label.configure(text="已保存并生效")
        self._fill_user_tree()

    def open_windows_settings(self) -> None:
        os.startfile("SystemPropertiesAdvanced.exe")  # type: ignore[attr-defined]
