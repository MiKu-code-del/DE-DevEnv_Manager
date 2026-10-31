# -*- coding: utf-8 -*-
"""环境安装、版本切换与用户 PATH 管理。

目录布局（管理根目录下）::

    tools/
      node/
        versions/22.23.2/...      # 各版本实体目录
        current -> junction       # 指向当前激活版本
      go/
        versions/1.22.0/bin/...
        current -> junction
    downloads/                    # 安装包缓存

切换版本只重建 junction，不反复改写 PATH；PATH 中只保留固定的
``current/<path_rel>`` 条目，首次激活时写入用户级注册表 HKCU\\Environment。
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import threading
from pathlib import Path

from .config import get_config
from .downloader import (
    DownloadError,
    download_file,
    extract_zip,
    http_get_json,
    new_temp_dir,
    remove_path_silent,
    resolve_single_top_dir,
)
from .tool_specs import (
    INSTALLABLE_SPECS,
    RemoteVersion,
    parse_jdk_assets,
)

_CREATE_NO_WINDOW = 0x08000000
_HWND_BROADCAST = 0xFFFF
_WM_SETTINGCHANGE = 0x1A
_SMTO_ABORTIFHUNG = 0x0002


class EnvError(Exception):
    pass


# ====================================================================== 远程版本
def fetch_remote_versions(tool_id: str) -> list[RemoteVersion]:
    spec = INSTALLABLE_SPECS[tool_id]
    cfg = get_config()
    url = spec.versions_url(cfg.arch, cfg.preferred_mirror)
    data = http_get_json(url)
    versions = spec.parse_versions(data, cfg.arch, cfg.preferred_mirror)
    return versions


def _resolve_jdk(remote: RemoteVersion) -> RemoteVersion:
    """JDK 大版本占位条目 -> 真实资产条目。"""
    if remote.kind != "jdk-feature":
        return remote
    data = http_get_json(remote.download_url)
    asset = parse_jdk_assets(data)
    if asset is None:
        raise EnvError(f"未找到 {remote.version} 适用于当前架构的 JDK 包")
    return asset


def normalize_version_name(tool_id: str, name: str) -> str:
    if tool_id == "node":
        return name[1:] if name.startswith("v") else name
    if tool_id == "go":
        return name[2:] if name.startswith("go") else name
    return name  # jdk 保留 release_name，如 jdk-21.0.5+11


# ====================================================================== 用户 PATH
def read_user_path() -> list[str]:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise EnvError(f"读取用户 PATH 失败：{exc}") from exc
    return [item.strip() for item in str(value).split(";") if item.strip()]


def _write_user_path(entries: list[str]) -> None:
    import winreg
    value = ";".join(entries)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, value)
    except OSError as exc:
        raise EnvError(f"写入用户 PATH 失败：{exc}") from exc
    # 同步到当前进程，保证后续子进程立即生效
    os.environ["PATH"] = value + ";" + os.environ.get("PATH", "")
    _broadcast_environment_change()


def _broadcast_environment_change() -> None:
    """通知 Explorer 及其他应用环境变量已变更。"""
    result = ctypes.c_ulong()
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            _HWND_BROADCAST, _WM_SETTINGCHANGE, 0, "Environment",
            _SMTO_ABORTIFHUNG, 5000, ctypes.byref(result),
        )
    except (ctypes.ArgumentError, AttributeError):
        # 广播失败不影响注册表已写入的事实
        pass


def _norm(entry: str) -> str:
    return os.path.normcase(os.path.normpath(entry))


def ensure_user_path_entries(new_entries: list[str]) -> list[str]:
    """把条目追加到用户 PATH（去重），返回本次实际新增的条目。"""
    current = read_user_path()
    existing = {_norm(x) for x in current}
    added: list[str] = []
    for entry in new_entries:
        norm_entry = os.path.normpath(entry)
        if _norm(norm_entry) not in existing:
            current.append(norm_entry)
            existing.add(_norm(norm_entry))
            added.append(norm_entry)
            get_config().add_managed_entry(norm_entry)
    if added:
        _write_user_path(current)
    return added


def replace_user_path(entries: list[str]) -> None:
    """整体替换用户 PATH（PATH 管理页使用，调用方负责界面侧确认）。"""
    normalized = [os.path.normpath(e) for e in entries if e.strip()]
    _write_user_path(normalized)
    # 校准托管记录：仍保留在 PATH 中的托管条目继续保留
    existing = {_norm(e) for e in normalized}
    cfg = get_config()
    cfg.managed_path_entries = [
        e for e in cfg.managed_path_entries if _norm(e) in existing
    ]
    cfg.save()


def remove_user_path_entries(entries: list[str]) -> list[str]:
    current = read_user_path()
    remove = {_norm(x) for x in entries}
    kept = [x for x in current if _norm(x) not in remove]
    removed = [x for x in current if _norm(x) in remove]
    if len(kept) != len(current):
        _write_user_path(kept)
    for entry in removed:
        get_config().remove_managed_entry(entry)
    return removed


# ====================================================================== junction
def _create_junction(link: Path, target: Path) -> None:
    if link.exists() or link.is_symlink():
        os.rmdir(link)  # junction 用 rmdir 只移除链接本身
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, creationflags=_CREATE_NO_WINDOW,
    )
    if proc.returncode != 0 or not link.exists():
        raise EnvError(f"创建 junction 失败：{proc.stderr.strip() or proc.stdout.strip()}")


def _path_entries_for(tool_id: str) -> list[str]:
    spec = INSTALLABLE_SPECS[tool_id]
    link = get_config().current_link(tool_id)
    rels = [spec.path_rel, *spec.extra_path_rels]
    entries = []
    for rel in rels:
        p = link if rel in (".", "") else link / rel
        entries.append(str(p))
    return entries


# ====================================================================== 安装
def install_version(
    tool_id: str,
    remote: RemoteVersion,
    progress_cb=None,
    log_cb=None,
    cancel_event: threading.Event | None = None,
    activate_after: bool = True,
) -> str:
    """下载并安装一个远程版本，返回安装后的版本名。"""
    cfg = get_config()
    cfg.ensure_dirs()
    spec = INSTALLABLE_SPECS[tool_id]

    remote = _resolve_jdk(remote)
    version_name = normalize_version_name(tool_id, remote.version)
    target_dir = cfg.version_dir(tool_id, version_name)
    if target_dir.exists():
        raise EnvError(f"{spec.display} {version_name} 已安装，无需重复安装")

    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    archive = cfg.download_dir / (remote.filename or f"{tool_id}-{version_name}.zip")
    log(f"开始下载 {spec.display} {version_name}")
    download_file(remote.download_url, archive, progress_cb, cancel_event)
    log("下载完成，正在解压...")

    tmp_dir = new_temp_dir()
    try:
        extract_zip(archive, tmp_dir)
        root = resolve_single_top_dir(tmp_dir) if spec.strip_top_level else tmp_dir
        if spec.exe_rel and not (root / spec.exe_rel).exists():
            raise EnvError(f"安装包结构异常，未找到 {spec.exe_rel}")
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        # 同盘 rename 最快，跨盘回退到 shutil.move
        try:
            shutil.move(str(root), str(target_dir))
        except shutil.Error as exc:
            raise EnvError(f"移动安装目录失败：{exc}") from exc
        remove_path_silent(tmp_dir)
    except Exception:
        remove_path_silent(tmp_dir)
        raise

    log(f"已安装到 {target_dir}")
    if activate_after:
        activate(tool_id, version_name, log_cb)
    return version_name


def import_local_zip(
    tool_id: str,
    zip_path: Path,
    version_name: str | None = None,
    log_cb=None,
    activate_after: bool = True,
) -> str:
    """导入本地 zip 包并纳入版本管理。"""
    cfg = get_config()
    cfg.ensure_dirs()
    spec = INSTALLABLE_SPECS[tool_id]
    name = version_name or normalize_version_name(
        tool_id, zip_path.name[:-4] if zip_path.name.lower().endswith(".zip")
        else zip_path.name
    )
    target_dir = cfg.version_dir(tool_id, name)
    if target_dir.exists():
        raise EnvError(f"{spec.display} {name} 已存在")

    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    tmp_dir = new_temp_dir()
    try:
        log(f"正在解压 {zip_path.name}")
        extract_zip(zip_path, tmp_dir)
        root = resolve_single_top_dir(tmp_dir) if spec.strip_top_level else tmp_dir
        if spec.exe_rel and not (root / spec.exe_rel).exists():
            raise EnvError(f"压缩包结构不符，未找到 {spec.exe_rel}")
        shutil.move(str(root), str(target_dir))
        remove_path_silent(tmp_dir)
    except Exception:
        remove_path_silent(tmp_dir)
        raise

    log(f"已导入 {name}")
    if activate_after:
        activate(tool_id, name, log_cb)
    return name


# ====================================================================== 激活 / 卸载
def activate(tool_id: str, version_name: str, log_cb=None) -> None:
    cfg = get_config()
    target_dir = cfg.version_dir(tool_id, version_name)
    if not target_dir.exists():
        raise EnvError(f"版本目录不存在：{target_dir}")

    spec = INSTALLABLE_SPECS[tool_id]
    if spec.exe_rel and not (target_dir / spec.exe_rel).exists():
        raise EnvError(f"版本目录损坏，缺少 {spec.exe_rel}")

    link = cfg.current_link(tool_id)
    link.parent.mkdir(parents=True, exist_ok=True)
    _create_junction(link, target_dir)

    entries = _path_entries_for(tool_id)
    added = ensure_user_path_entries(entries)
    if log_cb:
        if added:
            log_cb(f"已激活 {spec.display} {version_name}，PATH 已更新（新终端生效）")
        else:
            log_cb(f"已切换到 {spec.display} {version_name}（新终端生效）")


def deactivate(tool_id: str) -> None:
    cfg = get_config()
    entries = _path_entries_for(tool_id)
    remove_user_path_entries(entries)
    link = cfg.current_link(tool_id)
    if link.exists() or link.is_symlink():
        os.rmdir(link)


def uninstall_version(tool_id: str, version_name: str) -> None:
    cfg = get_config()
    from .detection import current_version
    if current_version(tool_id) == version_name:
        raise EnvError("该版本正在使用中，请先切换到其他版本或停用后再卸载")
    target_dir = cfg.version_dir(tool_id, version_name)
    if not target_dir.exists():
        raise EnvError("版本不存在")
    shutil.rmtree(target_dir)
