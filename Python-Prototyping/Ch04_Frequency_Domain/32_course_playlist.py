"""32 把一门 B 站网课的目录页对到《信号与系统学习路线》的 8 步上,算每条路线要看多久。

输入是你从 B 站「合集列表」复制下来的 HTML 片段(每集一个 title 和一个 duration),
本脚本只读标题和时长,**不看视频内容** —— 所以「哪一集讲什么」都是从标题推的。
文档 Documents/数学基础/信号与系统学习路线.md 第六节里出现的集数与总时长全部来自这里。

课程:2022 浙江大学《信号与系统》,胡浩基老师,60 集。

用法:
    .venv/bin/python Ch04_Frequency_Domain/32_course_playlist.py [目录页.txt]
    不给路径时读 ~/Desktop/ 下文件名含「胡浩基」的 .txt
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# 路线第 N 步 → 必看(精看)集号。集号 = 目录页里的顺序(从 1 数起)
CORE = {
    "1 离散信号": [2, 3, 4],
    "2 系统": [6],
    "3 卷积": [7, 8, 12],
    "4 DFT": [17, 32, 33, 35],
    "5 性质与坑": [36, 37],
    "7 采样与混叠": [38, 39, 42, 43],
    "8 进二维": [29],
}
# 选看:很长,或者我没法从标题确认它讲什么
OPTIONAL = {
    "2 系统(典型系统,2 小时)": [5],
    "5 DFT 性质(只挑频移/卷积/共轭对称/帕塞瓦尔)": [34],
    "6 频率响应(待确认哪集真在讲)": [23, 27, 28],
}
SUPPLEMENT = {
    "连续傅里叶(级数 + 性质)": [15, 22],
    "拉普拉斯变换": list(range(45, 54)),
    "Z 变换": list(range(54, 61)),
}


def find_file() -> Path:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        return Path(sys.argv[1])
    hits = sorted((Path.home() / "Desktop").glob("*胡浩基*.txt"))
    if not hits:
        sys.exit("找不到目录页文件,请把路径作为第一个参数给出")
    return hits[0]


def parse(text: str) -> list[tuple[str, int]]:
    items = re.findall(r'title="([^"]+)" class="title">.*?duration">\s*([\d:]+)', text, flags=re.S)
    out = []
    for title, dur in items:
        p = [int(x) for x in dur.split(":")]
        sec = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
        out.append((title, sec))
    return out


def hm(sec: int) -> str:
    return f"{sec // 3600} 小时 {sec % 3600 // 60:02d} 分"


def total(eps: list[tuple[str, int]], ids: list[int]) -> int:
    return sum(eps[i - 1][1] for i in ids)


def main() -> None:
    path = find_file()
    eps = parse(path.read_text(encoding="utf-8"))
    print(f"{path.name}:{len(eps)} 集,总计 {hm(sum(s for _, s in eps))}")
    print("\n[必看,按路线步骤]")
    core_ids: list[int] = []
    for step, ids in CORE.items():
        print(f"  第 {step:10s} 集 {ids}:{hm(total(eps, ids))}")
        core_ids += ids
    print(f"  必看合计 {len(core_ids)} 集:{hm(total(eps, core_ids))}")
    print("\n[选看]")
    for name, ids in OPTIONAL.items():
        print(f"  {name:36s} 集 {ids}:{hm(total(eps, ids))}")
    opt_ids = [i for ids in OPTIONAL.values() for i in ids]
    only34 = total(eps, core_ids + [34])
    print(f"  必看 + 第 34 集:{hm(only34)};必看 + 34 + 23/27/28:{hm(total(eps, core_ids + [34, 23, 27, 28]))}")
    print("\n[补全线]")
    for name, ids in SUPPLEMENT.items():
        span = f"{ids[0]}~{ids[-1]}" if ids == list(range(ids[0], ids[-1] + 1)) else "、".join(map(str, ids))
        print(f"  {name:12s} 集 {span}:{hm(total(eps, ids))}")
    print("\n[几集最长的]")
    for i in sorted(range(1, len(eps) + 1), key=lambda k: -eps[k - 1][1])[:4]:
        print(f"  第 {i} 集 {hm(eps[i - 1][1])}:{eps[i - 1][0]}")
    print("\n[标题核对,文档里引用到的几集]")
    for i in (5, 6, 7, 8, 17, 29, 32, 34, 36, 37, 42, 44):
        print(f"  {i:2d}  {eps[i - 1][0]}")
    missing = set(core_ids + opt_ids) - set(range(1, len(eps) + 1))
    assert not missing, f"集号越界:{missing}"


if __name__ == "__main__":
    main()
