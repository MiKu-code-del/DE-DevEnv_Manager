# -*- coding: utf-8 -*-
"""开发环境检测引擎。

检测策略：
1. ``shutil.which`` 在 PATH 中定位可执行文件；
2. 启动该命令的版本参数（Windows 下 .cmd/.bat 批处理走 ``shell=True``，
   并隐藏控制台窗口），用正则解析版本号；
3. 根据可执行文件路径是否位于本程序管理根目录，判断是否由本程序托管。

另外提供注册表“已安装程序”扫描，用于仪表盘展示系统级安装记录。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import get_config
from .process_util import run_cmd
from .tool_specs import TOOL_SPECS, ToolSpec


@dataclass
class DetectionResult:
    spec_id: str
    display: str
    category: str
    found: bool
    version: str = ""
    path: str = ""
    managed: bool = False
    note: str = ""


def _extract_version(text: str, pattern: str) -> str:
    if not text:
        return ""
    m = re.search(pattern, text)
    if not m:
        return ""
    if m.groups():
        return m.group(1).strip()
    return m.group(0).strip()


def detect_tool(spec: ToolSpec) -> DetectionResult:
    result = DetectionResult(spec.id, spec.display, spec.category, found=False,
                             note=spec.note)
    executable = None
    for cmd in spec.commands:
        executable = shutil.which(cmd)
        if executable:
            break
    if not executable:
        return result

    result.path = executable
    cfg = get_config()
    try:
        common = os.path.commonpath([os.path.normcase(executable),
                                     os.path.normcase(str(cfg.root_dir))])
        result.managed = os.path.normcase(common) == os.path.normcase(str(cfg.root_dir))
    except ValueError:
        result.managed = False

    # 批处理（npm.cmd 等）在 Windows 必须经 cmd.exe 解析
    use_shell = executable.lower().endswith((".cmd", ".bat"))
    args = [spec.commands[0], *spec.version_args]
    try:
        stdout, stderr, _code = run_cmd(args, shell=use_shell, timeout=15)
        raw = stdout + stderr if spec.use_stderr else (stdout or stderr)
        version = _extract_version(raw, spec.version_pattern)
        if version:
            result.version = version
            result.found = True
        else:
            # 命令存在但版本解析失败，保留路径信息
            result.version = "未知版本"
            result.found = True
    except (subprocess.TimeoutExpired, OSError) as exc:
        result.version = "检测失败"
        result.note = f"{spec.note}（{type(exc).__name__}）".strip()
        result.found = True
    return result


def detect_all() -> list[DetectionResult]:
    """并发检测全部工具，避免逐个启动进程造成长时间等待。"""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(detect_tool, TOOL_SPECS))
    # 保持规格表中的原始顺序
    order = {spec.id: i for i, spec in enumerate(TOOL_SPECS)}
    return sorted(results, key=lambda r: order[r.spec_id])


# ------------------------------------------------------------------ 托管版本扫描
def list_managed_versions(tool_id: str) -> list[str]:
    vdir = get_config().versions_dir(tool_id)
    if not vdir.exists():
        return []
    return sorted([p.name for p in vdir.iterdir() if p.is_dir()], reverse=True)


def current_version(tool_id: str) -> str | None:
    """读取 current junction 指向的版本名。"""
    link = get_config().current_link(tool_id)
    if not link.exists() and not link.is_symlink():
        return None
    try:
        target = os.readlink(str(link))
    except OSError:
        return None
    return Path(target).name


def is_current_active(tool_id: str) -> bool:
    """current 链路存在且其可执行文件能在 PATH 中被找到时视为生效。"""
    link = get_config().current_link(tool_id)
    return link.exists()


# ------------------------------------------------------------------ 注册表程序扫描
@dataclass
class InstalledProgram:
    name: str
    version: str
    publisher: str
    location: str


def _iter_uninstall_keys():
    import winreg
    roots = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for root, sub in roots:
        try:
            with winreg.OpenKey(root, sub) as parent:
                count = winreg.QueryInfoKey(parent)[0]
                for i in range(count):
                    try:
                        child_name = winreg.EnumKey(parent, i)
                        with winreg.OpenKey(parent, child_name) as child:
                            yield child
                    except OSError:
                        continue
        except OSError:
            continue


def _read_value(key, name: str) -> str:
    import winreg
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip()
    except OSError:
        return ""


def list_installed_programs() -> list[InstalledProgram]:
    programs: list[InstalledProgram] = []
    seen: set[str] = set()
    for key in _iter_uninstall_keys():
        display = _read_value(key, "DisplayName")
        if not display or _read_value(key, "ParentKeyName"):
            continue  # 跳过系统补丁
        if display in seen:
            continue
        seen.add(display)
        programs.append(InstalledProgram(
            name=display,
            version=_read_value(key, "DisplayVersion"),
            publisher=_read_value(key, "Publisher"),
            location=_read_value(key, "InstallLocation"),
        ))
    programs.sort(key=lambda p: p.name.lower())
    return programs
