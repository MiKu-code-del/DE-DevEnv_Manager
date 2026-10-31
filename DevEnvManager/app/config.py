# -*- coding: utf-8 -*-
"""全局配置与路径常量。

引导配置固定存放在 %LOCALAPPDATA%\\DevEnvManager\\config.json，
其中记录用户可更改的“环境管理根目录”等设置；
所有下载的工具版本、junction、安装包都放在管理根目录下。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "DevEnv Manager"
APP_NAME_CN = "开发环境管家"
APP_VERSION = "1.0.0"

# 架构选项
ARCH_X64 = "x64"
ARCH_ARM64 = "arm64"


def _default_root() -> Path:
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return Path(home) / ".dev-env-manager"


def _bootstrap_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "DevEnvManager"


class Config:
    """应用配置（单例风格，进程内共享）。"""

    def __init__(self) -> None:
        self._bootstrap_file = _bootstrap_dir() / "config.json"
        self.root_dir: Path = _default_root()
        self.arch: str = ARCH_X64
        self.preferred_mirror: str = "npmmirror"
        # 由本程序写入用户 PATH 的条目（绝对路径），便于审计与清理
        self.managed_path_entries: list[str] = []
        self.load()

    # ------------------------------------------------------------------ 持久化
    def load(self) -> None:
        if not self._bootstrap_file.exists():
            return
        try:
            data = json.loads(self._bootstrap_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        root = data.get("root_dir")
        if root:
            self.root_dir = Path(root)
        self.arch = data.get("arch", ARCH_X64)
        self.preferred_mirror = data.get("preferred_mirror", "npmmirror")
        entries = data.get("managed_path_entries", [])
        if isinstance(entries, list):
            self.managed_path_entries = [str(x) for x in entries]

    def save(self) -> None:
        self._bootstrap_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "root_dir": str(self.root_dir),
            "arch": self.arch,
            "preferred_mirror": self.preferred_mirror,
            "managed_path_entries": self.managed_path_entries,
        }
        tmp = self._bootstrap_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._bootstrap_file)

    # ------------------------------------------------------------------ 目录
    def ensure_dirs(self) -> None:
        """创建管理根目录下的标准结构。"""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    @property
    def tools_dir(self) -> Path:
        return self.root_dir / "tools"

    @property
    def download_dir(self) -> Path:
        return self.root_dir / "downloads"

    def tool_dir(self, tool_id: str) -> Path:
        return self.tools_dir / tool_id

    def versions_dir(self, tool_id: str) -> Path:
        return self.tool_dir(tool_id) / "versions"

    def version_dir(self, tool_id: str, version: str) -> Path:
        return self.versions_dir(tool_id) / version

    def current_link(self, tool_id: str) -> Path:
        """当前激活版本的 junction 路径。"""
        return self.tool_dir(tool_id) / "current"

    # ------------------------------------------------------------------ PATH 条目
    def add_managed_entry(self, path: str | Path) -> None:
        norm = os.path.normpath(str(path))
        if norm not in self.managed_path_entries:
            self.managed_path_entries.append(norm)
            self.save()

    def remove_managed_entry(self, path: str | Path) -> None:
        norm = os.path.normpath(str(path))
        if norm in self.managed_path_entries:
            self.managed_path_entries.remove(norm)
            self.save()


# 进程级单例
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
