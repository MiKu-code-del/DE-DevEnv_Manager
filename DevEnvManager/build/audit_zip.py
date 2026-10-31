# -*- coding: utf-8 -*-
"""审计源码 zip：文件清单、硬编码个人信息、全部网络地址。"""
import re
import zipfile

ZF = r"E:\项目exe\DevEnvManager_源码.zip"
zf = zipfile.ZipFile(ZF)
print("zip 内文件:")
for n in zf.namelist():
    print("  ", n)

bad = []
urls = set()
for n in zf.namelist():
    if n.endswith(".py"):
        text = zf.read(n).decode("utf-8")
        for kw in ("admin", "项目exe", "C:\\Users", "sandbox", "Doubao"):
            if kw in text:
                bad.append((n, kw))
        for m in re.findall(r"https?://[^\s\"')]+", text):
            urls.add(m)

print("硬编码个人信息命中:", bad or "无")
print("代码中全部网络地址:")
for u in sorted(urls):
    print("  ", u)
