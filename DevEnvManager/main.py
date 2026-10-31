# -*- coding: utf-8 -*-
"""DevEnv Manager（开发环境管家）主入口。

一个用于集中管理 Windows 开发基础环境的桌面程序：
环境检测、多版本安装切换、用户 PATH 治理、镜像加速。
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from app.config import APP_NAME, APP_NAME_CN, APP_VERSION, get_config
from app.ui_theme import (
    ACCENT, BG_SIDEBAR, TEXT_MAIN, TEXT_MUTE, apply_theme, get_font,
)


class MainWindow(tk.Tk):
    NAV_ITEMS = (
        ("dashboard", "环境总览"),
        ("versions", "版本管理"),
        ("path", "PATH 环境变量"),
        ("mirrors", "镜像加速"),
        ("settings", "设置"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME_CN} {APP_VERSION}")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self._center_window()
        apply_theme(self)

        self._pages: dict[str, ttk.Frame] = {}
        self._nav_buttons: dict[str, tk.Widget] = {}
        self._build_sidebar()
        self._content = ttk.Frame(self)
        self._content.pack(side="right", fill="both", expand=True)
        self.show_page("dashboard")

    def _center_window(self) -> None:
        self.update_idletasks()
        w, h = 1180, 760
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=BG_SIDEBAR)
        brand.pack(fill="x", pady=(22, 18), padx=18)
        dot = tk.Label(brand, text="●", fg=ACCENT, bg=BG_SIDEBAR,
                       font=get_font(16))
        dot.pack(side="left")
        tk.Label(brand, text=APP_NAME_CN, fg=TEXT_MAIN, bg=BG_SIDEBAR,
                 font=get_font(12, "bold")).pack(side="left", padx=8)

        for key, label in self.NAV_ITEMS:
            btn = self._nav_button(sidebar, label,
                                    command=lambda k=key: self.show_page(k))
            btn.pack(fill="x")
            self._nav_buttons[key] = btn

        tk.Label(sidebar, text=f"v{APP_VERSION}", fg=TEXT_MUTE, bg=BG_SIDEBAR,
                 font=get_font(8)).pack(side="bottom", pady=16)

    def _nav_button(self, parent, text, command) -> tk.Widget:
        from app.ui_theme import HoverButton
        return HoverButton(parent, "  " + text, command=command)

    def show_page(self, key: str) -> None:
        for nav_key, btn in self._nav_buttons.items():
            btn.set_selected(nav_key == key)

        if key not in self._pages:
            self._pages[key] = self._create_page(key)
        page = self._pages[key]
        for child in self._content.winfo_children():
            child.pack_forget()
        page.pack(fill="both", expand=True)
        if hasattr(page, "on_show"):
            page.on_show()

    def _create_page(self, key: str) -> ttk.Frame:
        # 延迟导入，避免启动时加载全部页面
        if key == "dashboard":
            from app.pages.page_dashboard import DashboardPage
            return DashboardPage(self._content, self)
        if key == "versions":
            from app.pages.page_versions import VersionsPage
            return VersionsPage(self._content, self)
        if key == "path":
            from app.pages.page_path import PathPage
            return PathPage(self._content, self)
        if key == "mirrors":
            from app.pages.page_mirrors import MirrorsPage
            return MirrorsPage(self._content, self)
        if key == "settings":
            from app.pages.page_settings import SettingsPage
            return SettingsPage(self._content, self)
        raise KeyError(key)


def main() -> int:
    get_config().ensure_dirs()
    app = MainWindow()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
