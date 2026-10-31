# -*- coding: utf-8 -*-
"""镜像源 / 代理加速管理。

覆盖：
- Node 生态：npm、pnpm、yarn 的 registry（调用各自 config 命令）；
- Python：pip 全局配置文件 ``%APPDATA%\\pip\\pip.ini``；
- Go：用户环境变量 ``GOPROXY``。
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .process_util import run_cmd


@dataclass(frozen=True)
class MirrorOption:
    id: str
    label: str
    url: str


NPM_MIRRORS: list[MirrorOption] = [
    MirrorOption("npmmirror", "npmmirror 淘宝镜像", "https://registry.npmmirror.com"),
    MirrorOption("huawei", "华为云", "https://repo.huaweicloud.com/repository/npm/"),
    MirrorOption("tencent", "腾讯云", "https://mirrors.cloud.tencent.com/npm/"),
    MirrorOption("official", "官方源", "https://registry.npmjs.org"),
]

PIP_MIRRORS: list[MirrorOption] = [
    MirrorOption("tuna", "清华大学", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    MirrorOption("aliyun", "阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
    MirrorOption("huawei", "华为云", "https://repo.huaweicloud.com/repository/pypi/simple"),
    MirrorOption("tencent", "腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple"),
    MirrorOption("official", "官方源", "https://pypi.org/simple"),
]

GO_MIRRORS: list[MirrorOption] = [
    MirrorOption("goproxycn", "七牛 goproxy.cn（推荐）", "https://goproxy.cn,direct"),
    MirrorOption("aliyun", "阿里云", "https://mirrors.aliyun.com/goproxy/,direct"),
    MirrorOption("goproxyio", "goproxy.io", "https://goproxy.io,direct"),
    MirrorOption("official", "官方源", "https://proxy.golang.org,direct"),
]


class MirrorError(Exception):
    pass


# ------------------------------------------------------------------ 通用命令
def _run(cmd: list[str], use_shell: bool = False) -> str:
    try:
        stdout, stderr, code = run_cmd(cmd, shell=use_shell, timeout=30)
    except OSError as exc:
        raise MirrorError(str(exc)) from exc
    if code != 0:
        raise MirrorError(stderr.strip() or stdout.strip() or "命令执行失败")
    return stdout.strip()


# ------------------------------------------------------------------ Node 生态
def _which(tool: str) -> str | None:
    return shutil.which(tool)


def get_npm_registry(tool: str = "npm") -> str | None:
    if not _which(tool):
        return None
    try:
        out = _run([tool, "config", "get", "registry"], use_shell=True)
        return out or None
    except MirrorError:
        return None


def set_npm_registry(tool: str, url: str) -> None:
    if not _which(tool):
        raise MirrorError(f"未检测到 {tool}，请先安装 Node.js 环境")
    _run([tool, "config", "set", "registry", url], use_shell=True)


def available_node_tools() -> list[str]:
    return [t for t in ("npm", "pnpm", "yarn") if _which(t)]


def apply_node_mirror(url: str, tools: list[str] | None = None) -> list[str]:
    """对存在的 Node 包管理器统一设置 registry，返回成功设置的工具。"""
    targets = tools or available_node_tools()
    done: list[str] = []
    errors: list[str] = []
    for tool in targets:
        try:
            set_npm_registry(tool, url)
            done.append(tool)
        except MirrorError as exc:
            errors.append(f"{tool}: {exc}")
    if errors and not done:
        raise MirrorError("；".join(errors))
    return done


# ------------------------------------------------------------------ pip
def pip_ini_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "pip" / "pip.ini"


def get_pip_index_url() -> str | None:
    ini = pip_ini_path()
    if not ini.exists():
        return None
    try:
        for line in ini.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.lower().startswith("index-url"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    except OSError:
        return None
    return None


def set_pip_index_url(url: str) -> None:
    ini = pip_ini_path()
    ini.parent.mkdir(parents=True, exist_ok=True)
    content = "[global]\nindex-url = {url}\ndisable-pip-version-check = true\n".format(url=url)
    tmp = ini.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(ini)


# ------------------------------------------------------------------ Go 代理
def _read_user_env(name: str) -> str | None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except OSError:
        return None


def get_goproxy() -> str | None:
    return os.environ.get("GOPROXY") or _read_user_env("GOPROXY")


def set_goproxy(value: str) -> None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "GOPROXY", 0, winreg.REG_SZ, value)
    except OSError as exc:
        raise MirrorError(f"写入 GOPROXY 失败：{exc}") from exc
    os.environ["GOPROXY"] = value
    # 复用 env_manager 的广播逻辑
    from .env_manager import _broadcast_environment_change
    _broadcast_environment_change()
