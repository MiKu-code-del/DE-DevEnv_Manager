# -*- coding: utf-8 -*-
"""工具规格定义。

- ``ToolSpec``：描述如何检测一个已安装的命令行工具（命令名、版本参数、解析正则）。
- ``InstallableSpec``：描述可在线下载、多版本管理的工具（版本源、下载地址、目录规则）。

所有网络请求由 :mod:`app.downloader` 统一执行，本模块只负责 URL 构造与数据解析。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

# 分类
CAT_RUNTIME = "运行时 / 语言"
CAT_PKG = "包管理器"
CAT_BUILD = "构建工具"
CAT_CONTAINER = "容器 / 云原生"
CAT_TOOL = "常用工具链"


@dataclass(frozen=True)
class ToolSpec:
    id: str
    display: str
    category: str
    commands: tuple[str, ...]
    version_args: tuple[str, ...] = ("--version",)
    use_stderr: bool = False
    # 提取版本号的正则（取第一个捕获组；没有捕获组则取整个匹配）
    version_pattern: str = r"(\d+\.\d+(?:\.\d+)?)"
    homepage: str = ""
    note: str = ""


@dataclass
class RemoteVersion:
    """远程可下载版本。"""
    version: str
    label: str          # 附加标记，如 LTS / 稳定版
    download_url: str
    filename: str
    kind: str = "zip"   # zip / installer


@dataclass
class InstallableSpec:
    tool_id: str
    display: str
    # 接收 (原始 JSON, arch, mirror)，返回 RemoteVersion 列表
    parse_versions: Callable[[object, str, str], list[RemoteVersion]]
    versions_url: Callable[[str, str], str]
    path_rel: str = "."                       # 激活时加入 PATH 的相对目录（相对版本根）
    exe_rel: str = ""                         # 用于校验安装结果的可执行文件相对路径
    strip_top_level: bool = True              # 解压时是否剥掉压缩包内唯一顶层目录
    extra_path_rels: tuple[str, ...] = ()     # 额外需要加入 PATH 的相对目录
    homepage: str = ""


# ====================================================================== 检测规格
TOOL_SPECS: list[ToolSpec] = [
    ToolSpec("node", "Node.js", CAT_RUNTIME, ("node",),
             version_pattern=r"v?([\d.]+)", homepage="https://nodejs.org"),
    ToolSpec("npm", "npm", CAT_PKG, ("npm",), ("--version",),
             homepage="https://www.npmjs.com"),
    ToolSpec("pnpm", "pnpm", CAT_PKG, ("pnpm",), ("--version",),
             homepage="https://pnpm.io"),
    ToolSpec("yarn", "Yarn", CAT_PKG, ("yarn",), ("--version",),
             homepage="https://yarnpkg.com"),
    ToolSpec("deno", "Deno", CAT_RUNTIME, ("deno",),
             homepage="https://deno.com"),
    ToolSpec("bun", "Bun", CAT_RUNTIME, ("bun",),
             homepage="https://bun.sh"),
    ToolSpec("python", "Python", CAT_RUNTIME, ("python",),
             homepage="https://www.python.org"),
    ToolSpec("pip", "pip", CAT_PKG, ("pip",),
             version_pattern=r"pip\s+([\d.]+)"),
    ToolSpec("java", "Java (JRE)", CAT_RUNTIME, ("java",), ("-version",),
             use_stderr=True, version_pattern=r'version "([^"]+)"',
             homepage="https://adoptium.net"),
    ToolSpec("javac", "Java 编译器 (JDK)", CAT_RUNTIME, ("javac",), ("-version",),
             use_stderr=True, version_pattern=r'javac\s+([\d._]+)'),
    ToolSpec("go", "Go", CAT_RUNTIME, ("go",),
             version_pattern=r"go\s+version\s+go([\d.]+)",
             homepage="https://go.dev"),
    ToolSpec("rustc", "Rust", CAT_RUNTIME, ("rustc",),
             version_pattern=r"rustc\s+([\d.]+)", homepage="https://www.rust-lang.org"),
    ToolSpec("cargo", "Cargo", CAT_PKG, ("cargo",),
             version_pattern=r"cargo\s+([\d.]+)"),
    ToolSpec("ruby", "Ruby", CAT_RUNTIME, ("ruby",),
             version_pattern=r"ruby\s+([\d.]+)", homepage="https://www.ruby-lang.org"),
    ToolSpec("php", "PHP", CAT_RUNTIME, ("php",),
             version_pattern=r"PHP\s+([\d.]+)", homepage="https://www.php.net"),
    ToolSpec("dotnet", ".NET SDK", CAT_RUNTIME, ("dotnet",),
             homepage="https://dotnet.microsoft.com"),
    ToolSpec("perl", "Perl", CAT_RUNTIME, ("perl",),
             version_pattern=r"(v5\.\d+\.\d+)", homepage="https://www.perl.org"),
    ToolSpec("git", "Git", CAT_TOOL, ("git",),
             version_pattern=r"git\s+version\s+(\d+\.\d+\.\d+)",
             homepage="https://git-scm.com"),
    ToolSpec("mvn", "Maven", CAT_BUILD, ("mvn",),
             version_pattern=r"Apache Maven\s+([\d.]+)",
             homepage="https://maven.apache.org"),
    ToolSpec("gradle", "Gradle", CAT_BUILD, ("gradle",),
             version_pattern=r"Gradle\s+([\d.]+)", homepage="https://gradle.org"),
    ToolSpec("cmake", "CMake", CAT_BUILD, ("cmake",),
             version_pattern=r"cmake\s+version\s+([\d.]+)", homepage="https://cmake.org"),
    ToolSpec("gcc", "GCC / MinGW", CAT_BUILD, ("gcc",),
             version_pattern=r"gcc.*?\(.*?\)\s+([\d.]+)", homepage="https://www.mingw-w64.org"),
    ToolSpec("docker", "Docker", CAT_CONTAINER, ("docker",),
             version_pattern=r"Docker\s+version\s+([\d.]+)",
             homepage="https://www.docker.com"),
    ToolSpec("kubectl", "kubectl", CAT_CONTAINER, ("kubectl",), ("version", "--client"),
             version_pattern=r"v?([\d.]+)", homepage="https://kubernetes.io"),
    ToolSpec("code", "VS Code CLI", CAT_TOOL, ("code",),
             homepage="https://code.visualstudio.com"),
]

TOOL_SPEC_BY_ID: dict[str, ToolSpec] = {s.id: s for s in TOOL_SPECS}


# ====================================================================== 可安装规格
def _node_versions_url(arch: str, mirror: str) -> str:
    if mirror == "official":
        return "https://nodejs.org/dist/index.json"
    return "https://registry.npmmirror.com/-/binary/node/index.json"


def _parse_node_versions(data: object, arch: str, mirror: str) -> list[RemoteVersion]:
    assert isinstance(data, list)
    arch_token = "win-x64" if arch == "x64" else "win-arm64"
    zip_name = f"{arch_token}-zip"
    result: list[RemoteVersion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))      # 形如 v20.10.0
        if not version:
            continue
        # 兼容 files 为字符串数组（现行）与对象数组（旧版）两种格式
        files = set()
        for f in item.get("files", []):
            if isinstance(f, str):
                files.add(f)
            elif isinstance(f, dict) and f.get("name"):
                files.add(str(f.get("name")))
        if zip_name not in files:
            continue
        if mirror == "official":
            base = "https://nodejs.org/dist/"
        else:
            base = "https://registry.npmmirror.com/-/binary/node/"
        filename = f"node-{version}-{arch_token}.zip"
        url = f"{base}{version}/{filename}"
        lts = item.get("lts")
        label = f"LTS（{lts}）" if lts else "Current"
        result.append(RemoteVersion(version, label, url, filename))
    return result


def _go_versions_url(arch: str, mirror: str) -> str:
    # include=all 返回全部历史版本，而非仅最新稳定版
    return "https://golang.google.cn/dl/?mode=json&include=all"


def _parse_go_versions(data: object, arch: str, mirror: str) -> list[RemoteVersion]:
    assert isinstance(data, list)
    go_arch = "amd64" if arch == "x64" else "arm64"
    result: list[RemoteVersion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))       # go1.22.0
        if not version:
            continue
        for f in item.get("files", []):
            if not isinstance(f, dict):
                continue
            if f.get("os") == "windows" and f.get("arch") == go_arch \
                    and f.get("kind") == "archive":
                filename = str(f.get("name"))
                url = f"https://golang.google.cn/dl/{filename}"
                label = "稳定版" if item.get("stable") else "历史版本"
                result.append(RemoteVersion(version, label, url, filename))
                break
    return result


def _jdk_versions_url(arch: str, mirror: str) -> str:
    # 该接口返回大版本列表；具体资产在选中大版本后按 URL 模板再拉取
    return "https://api.adoptium.net/v3/info/available_releases"


def _parse_jdk_versions(data: object, arch: str, mirror: str) -> list[RemoteVersion]:
    """这里把大版本（8/11/17/21...）转成“延迟解析”的占位条目。

    真正的下载链接在用户选中后通过 :func:`build_jdk_asset_url` 拉取资产得到。
    """
    if not isinstance(data, dict):
        return []
    result: list[RemoteVersion] = []
    most_recent_lts = data.get("most_recent_lts")
    for feature in data.get("available_releases", []):
        if not isinstance(feature, int) or feature < 8:
            continue
        label = "LTS" if feature in (8, 11, 17, 21, 25) else "最新特性版"
        if feature == most_recent_lts:
            label += "（推荐）"
        # download_url 占位：资产接口地址，由调用方识别 jdk: 前缀语义
        result.append(RemoteVersion(
            version=f"jdk{feature}",
            label=label,
            download_url=build_jdk_asset_url(feature, arch),
            filename="",
            kind="jdk-feature",
        ))
    return result


def build_jdk_asset_url(feature: int, arch: str) -> str:
    adoptium_arch = "x64" if arch == "x64" else "aarch64"
    return (
        "https://api.adoptium.net/v3/assets/feature_releases/"
        f"{feature}/ga?image_type=jdk&os=windows&architecture={adoptium_arch}"
        "&heap_size=normal&page=0&page_size=1&sort_order=DESC"
    )


def parse_jdk_assets(data: object) -> RemoteVersion | None:
    """解析某个 JDK 大版本的资产接口返回，取最新一个 zip 包。"""
    if not isinstance(data, list) or not data:
        return None
    entry = data[0]
    if not isinstance(entry, dict):
        return None
    release = entry.get("release", {}) or {}
    binary = entry.get("binary", {}) or {}
    package = binary.get("package", {}) or {}
    link = package.get("link")
    name = package.get("name")
    if not link or not name:
        return None
    release_name = str(release.get("release_name") or name)
    return RemoteVersion(version=release_name, label="Temurin JDK",
                         download_url=str(link), filename=str(name))


INSTALLABLE_SPECS: dict[str, InstallableSpec] = {
    "node": InstallableSpec(
        tool_id="node", display="Node.js",
        parse_versions=_parse_node_versions,
        versions_url=_node_versions_url,
        path_rel=".", exe_rel="node.exe",
        homepage="https://nodejs.org",
    ),
    "go": InstallableSpec(
        tool_id="go", display="Go",
        parse_versions=_parse_go_versions,
        versions_url=_go_versions_url,
        path_rel="bin", exe_rel=os.path.join("bin", "go.exe"),
        homepage="https://go.dev",
    ),
    "jdk": InstallableSpec(
        tool_id="jdk", display="Eclipse Temurin JDK",
        parse_versions=_parse_jdk_versions,
        versions_url=_jdk_versions_url,
        path_rel="bin", exe_rel=os.path.join("bin", "java.exe"),
        homepage="https://adoptium.net",
    ),
}


