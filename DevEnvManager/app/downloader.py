# -*- coding: utf-8 -*-
"""HTTP 下载与压缩包解压（仅使用标准库）。

- :func:`http_get_json`：拉取 JSON 接口；
- :func:`download_file`：带进度回调、可取消的流式下载，自动处理重定向；
- :func:`extract_zip`：安全解压 zip（防止路径穿越）。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

_USER_AGENT = "DevEnvManager/1.0 (Windows; Environment Manager)"


class DownloadError(Exception):
    pass


@dataclass
class DownloadProgress:
    got: int
    total: int

    @property
    def percent(self) -> float:
        return 0.0 if self.total <= 0 else min(100.0, self.got * 100.0 / self.total)


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Accept": "*/*",
    })


def http_get_json(url: str, timeout: int = 30) -> object:
    try:
        with urllib.request.urlopen(_build_request(url), timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read()
        return json.loads(raw.decode(charset))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise DownloadError(f"请求失败：{url}（{exc}）") from exc


def download_file(
    url: str,
    dest: Path,
    progress_cb=None,
    cancel_event: threading.Event | None = None,
) -> Path:
    """流式下载到 ``dest``，返回最终路径。

    ``progress_cb`` 形如 ``cb(DownloadProgress)``，在下载线程中被调用。
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(_build_request(url), timeout=60) as resp:
            total = 0
            try:
                total = int(resp.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                total = 0
            got = 0
            with open(tmp, "wb") as fh:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise DownloadError("已取消下载")
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
                    if progress_cb is not None:
                        progress_cb(DownloadProgress(got, total))
        tmp.replace(dest)
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"下载失败：{url}（{exc.reason}）") from exc
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        if isinstance(exc, DownloadError):
            raise
        raise DownloadError(f"写入文件失败：{dest}（{exc}）") from exc
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """解压 zip 到目标目录并做路径穿越校验，返回解压目录。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_abs = os.path.abspath(dest_dir)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                target = os.path.abspath(os.path.join(dest_dir, member))
                if not target.startswith(dest_abs + os.sep) and target != dest_abs:
                    raise DownloadError(f"压缩包包含非法路径：{member}")
            zf.extractall(dest_dir)
    except zipfile.BadZipFile as exc:
        raise DownloadError(f"压缩包损坏：{zip_path}") from exc
    return dest_dir


def resolve_single_top_dir(extracted: Path) -> Path:
    """若解压目录内只有一个顶层文件夹，返回该文件夹，否则返回解压目录本身。"""
    entries = [p for p in extracted.iterdir() if p.is_dir()]
    if len(entries) == 1:
        return entries[0]
    return extracted


def remove_path_silent(path: Path) -> None:
    """删除目录或文件，忽略不存在。"""
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def new_temp_dir(prefix: str = "devenv-") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))
