# 开发环境管家（DevEnv Manager）

一个用于集中管理 Windows 开发基础环境的单文件 exe 程序，无需安装、双击即用，全部功能基于 Python 标准库实现。

## 功能一览

### 1. 环境总览
- 自动检测 **25 种**常见开发工具的安装状态、版本与路径：
  - 运行时/语言：Node.js、Python、Java（JRE/JDK）、Go、Rust、Ruby、PHP、Deno、Bun、.NET、Perl
  - 包管理器：npm、pnpm、yarn、pip、cargo
  - 构建工具：Maven、Gradle、CMake、GCC/MinGW
  - 容器/云原生：Docker、kubectl
  - 其他：Git、VS Code CLI
- 并发检测，数秒出结果；同时读取注册表，列出系统全部已安装程序（支持关键字过滤）。

### 2. 版本管理
- 支持 **Node.js、Go、Temurin JDK** 三类运行时的在线安装：
  - 自动拉取完整版本列表（含 LTS / 稳定版 / 历史版本标记）
  - 带进度条下载、自动解压、多版本并存
  - 一键切换版本，支持本地 zip 导入、版本卸载
- 版本切换通过目录 junction（`current`）实现，不反复改写 PATH。

### 3. PATH 环境变量
- 用户 PATH 可视化编辑：新增、删除、上移、下移、打开目录
- 系统 PATH 只读展示；自动标红失效目录、标记本程序托管条目
- 修改需点击“保存更改”才会写入注册表，避免误操作

### 4. 镜像加速
- npm / pnpm / yarn registry 一键切换（npmmirror、华为云、腾讯云、官方）
- pip 源切换（清华、阿里、华为、腾讯、官方），写入 `%APPDATA%\pip\pip.ini`
- Go 模块代理 GOPROXY 设置（goproxy.cn、阿里云、goproxy.io、官方）

### 5. 设置
- 自定义环境管理根目录、CPU 架构（x64 / arm64）、Node 下载源偏好
- 下载缓存查看与清理

## 数据与安全

- 引导配置：`%LOCALAPPDATA%\DevEnvManager\config.json`
- 工具版本与安装包默认存放：`%USERPROFILE%\.dev-env-manager\`（可在设置中更改）
- 仅修改**当前用户（HKCU）**的环境变量与 PATH，不触碰系统级注册表
- 所有文件均位于管理根目录，删除程序后直接删除该目录即可，无残留
- 若当前进程没有环境变量写入权限，程序会提示并支持“以管理员身份重启”

## 使用方式

双击 `DevEnvManager.exe` 即可运行（单文件约 12 MB，首次启动需几秒解压）。建议在新打开的终端窗口中验证环境切换结果。

## 源码结构

```
DevEnvManager/
├── main.py                  # 主窗口入口
├── app/
│   ├── config.py            # 配置与路径
│   ├── tool_specs.py        # 工具规格、版本源与下载模板
│   ├── detection.py         # 环境检测引擎
│   ├── downloader.py        # HTTP 下载与 zip 解压
│   ├── env_manager.py       # 安装、junction、PATH 注册表
│   ├── mirrors.py           # 镜像源管理
│   ├── elevate.py           # 管理员提权
│   ├── process_util.py      # 子进程与编码处理
│   ├── ui_theme.py          # 深色主题与通用组件
│   └── pages/               # 五个 GUI 页面
└── build/                   # 图标、打包脚本与产物
```

技术栈：Python 3.11 + tkinter/ttk + urllib + winreg，PyInstaller `--onefile --windowed` 打包。
