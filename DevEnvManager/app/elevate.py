# -*- coding: utf-8 -*-
"""管理员权限检测与提权重启。"""
from __future__ import annotations

import ctypes
import sys


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, ctypes.ArgumentError):
        return False


def relaunch_as_admin() -> bool:
    """以 UAC 提权方式重新启动当前程序，返回是否成功发起。"""
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        executable = sys.executable
        params = " ".join(
            [f'"{sys.argv[0]}"',
             *[f'"{a}"' for a in sys.argv[1:]]]
        )
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1)
    return rc > 32


def is_permission_error(exc: Exception) -> bool:
    text = str(exc)
    return isinstance(exc, PermissionError) or "WinError 5" in text or "拒绝访问" in text
