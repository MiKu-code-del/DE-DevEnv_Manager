# -*- coding: utf-8 -*-
"""在完整令牌下测试注册表写入，结果写入文件。"""
import winreg
from pathlib import Path

out = Path(r"E:\项目exe\DevEnvManager\build\reg_write_result.txt")
try:
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                       winreg.KEY_SET_VALUE)
    winreg.SetValueEx(k, "DevEnvTest", 0, winreg.REG_SZ, "1")
    k.Close()
    k2 = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                        winreg.KEY_SET_VALUE)
    winreg.DeleteValue(k2, "DevEnvTest")
    k2.Close()
    out.write_text("WRITE OK", encoding="utf-8")
except PermissionError as e:
    out.write_text(f"PERMISSION DENIED: {e}", encoding="utf-8")
