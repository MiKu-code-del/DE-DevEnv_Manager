# -*- coding: utf-8 -*-
"""GUI 冒烟测试：启动窗口、逐页切换后自动关闭。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import MainWindow  # noqa: E402

app = MainWindow()
pages = ["dashboard", "versions", "path", "mirrors", "settings"]
state = {"i": 0}


def step():
    if state["i"] >= len(pages):
        print("SMOKE OK")
        app.destroy()
        return
    key = pages[state["i"]]
    app.show_page(key)
    print("page:", key)
    state["i"] += 1
    app.after(700, step)


app.after(500, step)
app.mainloop()
