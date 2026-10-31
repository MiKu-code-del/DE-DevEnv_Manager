# -*- coding: utf-8 -*-
"""设置页。"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.config import (
    APP_NAME, APP_NAME_CN, APP_VERSION, ARCH_ARM64, ARCH_X64, get_config,
)
from app.ui_theme import ORANGE, RED, Card, get_font


class SettingsPage(ttk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, padding=20)
        self.app = app
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="设置", style="Title.TLabel").pack(anchor="w")

        # 管理根目录
        root_card = Card(self, "环境管理根目录",
                         "所有工具版本、junction 与安装包均存放于此")
        root_card.pack(fill="x", pady=(16, 14))
        self.root_label = ttk.Label(root_card.body, text="", style="Card.TLabel",
                                    font=get_font(9, mono=True))
        self.root_label.pack(anchor="w")
        row = ttk.Frame(root_card.body, style="Card.TFrame")
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text="更改目录", style="Accent.TButton",
                   command=self.change_root).pack(side="left")
        ttk.Button(row, text="打开目录",
                   command=lambda: os.startfile(str(get_config().root_dir))  # type: ignore[attr-defined]
                   ).pack(side="left", padx=8)

        # 架构与下载偏好
        pref_card = Card(self, "下载偏好")
        pref_card.pack(fill="x", pady=(0, 14))
        self.arch_var = tk.StringVar(value=get_config().arch)
        ttk.Label(pref_card.body, text="CPU 架构：", style="Card.TLabel").pack(anchor="w")
        arch_row = ttk.Frame(pref_card.body, style="Card.TFrame")
        arch_row.pack(fill="x", pady=(4, 10))
        ttk.Radiobutton(arch_row, text="x64（主流 Intel / AMD）",
                        variable=self.arch_var, value=ARCH_X64,
                        command=self.save_prefs).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(arch_row, text="arm64（骁龙 X / 树莓派等）",
                        variable=self.arch_var, value=ARCH_ARM64,
                        command=self.save_prefs).pack(side="left")

        ttk.Label(pref_card.body, text="Node.js 下载源：",
                  style="Card.TLabel").pack(anchor="w")
        self.mirror_var = tk.StringVar(value=get_config().preferred_mirror)
        mirror_row = ttk.Frame(pref_card.body, style="Card.TFrame")
        mirror_row.pack(fill="x", pady=(4, 0))
        ttk.Radiobutton(mirror_row, text="npmmirror 国内镜像（推荐）",
                        variable=self.mirror_var, value="npmmirror",
                        command=self.save_prefs).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mirror_row, text="Node.js 官方源",
                        variable=self.mirror_var, value="official",
                        command=self.save_prefs).pack(side="left")

        # 下载缓存
        cache_card = Card(self, "下载缓存")
        cache_card.pack(fill="x", pady=(0, 14))
        self.cache_label = ttk.Label(cache_card.body, text="", style="Card.TLabel")
        self.cache_label.pack(anchor="w")
        crow = ttk.Frame(cache_card.body, style="Card.TFrame")
        crow.pack(fill="x", pady=(10, 0))
        ttk.Button(crow, text="打开缓存目录",
                   command=lambda: os.startfile(str(get_config().download_dir))  # type: ignore[attr-defined]
                   ).pack(side="left")
        ttk.Button(crow, text="清空缓存", style="Danger.TButton",
                   command=self.clear_cache).pack(side="left", padx=8)

        # 关于
        about = Card(self, "关于")
        about.pack(fill="x")
        info = (
            f"{APP_NAME_CN}（{APP_NAME}）v{APP_VERSION}\n\n"
            "用于集中管理 Windows 上的开发基础环境：Node.js、Go、JDK 等运行时的"
            "多版本安装与切换，25 种常见开发工具的检测，用户 PATH 治理，以及 "
            "npm/pip/GOPROXY 镜像加速。\n\n"
            "安全说明：程序仅修改当前用户（HKCU）的环境变量与 PATH，不触碰系统级 "
            "注册表；所有版本文件均位于管理根目录，卸载程序后可直接删除该目录，"
            "不会在系统中留下残留。"
        )
        ttk.Label(about.body, text=info, style="Card.TLabel",
                  wraplength=900, justify="left").pack(anchor="w")

        self.refresh_values()

    def on_show(self) -> None:
        self.refresh_values()

    def refresh_values(self) -> None:
        cfg = get_config()
        self.root_label.configure(text=str(cfg.root_dir))
        self.arch_var.set(cfg.arch)
        self.mirror_var.set(cfg.preferred_mirror)
        size, count = self._cache_stats()
        self.cache_label.configure(
            text=f"缓存目录：{cfg.download_dir}\n已缓存安装包 {count} 个，"
                 f"共 {size / 1024 / 1024:.1f} MB")

    def _cache_stats(self) -> tuple[int, int]:
        d = get_config().download_dir
        if not d.exists():
            return 0, 0
        total = 0
        count = 0
        for f in d.iterdir():
            if f.is_file():
                total += f.stat().st_size
                count += 1
        return total, count

    def change_root(self) -> None:
        folder = filedialog.askdirectory(title="选择新的管理根目录")
        if not folder:
            return
        cfg = get_config()
        if os.path.normcase(folder) == os.path.normcase(str(cfg.root_dir)):
            return
        if not messagebox.askyesno(
                "确认更改",
                "更改根目录后，新安装的版本将存放到新目录。\n"
                "已安装的旧版本不会自动迁移，且当前 PATH 中的旧 junction 仍指向旧目录。\n"
                "确定继续？"):
            return
        cfg.root_dir = folder
        cfg.ensure_dirs()
        cfg.save()
        self.refresh_values()

    def save_prefs(self) -> None:
        cfg = get_config()
        cfg.arch = self.arch_var.get()
        cfg.preferred_mirror = self.mirror_var.get()
        cfg.save()

    def clear_cache(self) -> None:
        cfg = get_config()
        if not cfg.download_dir.exists():
            return
        if not messagebox.askyesno("确认", "确定删除缓存目录中的全部安装包？"):
            return
        for f in cfg.download_dir.iterdir():
            try:
                if f.is_file():
                    f.unlink()
            except OSError as exc:
                messagebox.showwarning("清理失败", f"{f.name}: {exc}")
        self.refresh_values()
