#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""beijing-house-hunter 一键安装器（跨平台）
用法:
  python install.py                # 自动检测已安装的 Agent 并安装
  python install.py --dir PATH    # 安装到指定 skills 目录
  python install.py --list        # 仅显示检测结果
支持: ZCode(~/.zcode) / Claude Code(~/.claude) / Codex(~/.codex)
"""
import argparse, os, shutil, sys

SKILL_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skills', 'beijing-house-hunter')
AGENTS = [
    ('ZCode',      os.path.expanduser('~/.zcode/skills')),
    ('Claude Code', os.path.expanduser('~/.claude/skills')),
    ('Codex',      os.path.expanduser('~/.codex/skills')),
]

def detect():
    return [(name, d) for name, d in AGENTS if os.path.isdir(os.path.dirname(d))]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', help='安装到指定 skills 目录')
    ap.add_argument('--list', action='store_true', help='仅显示检测结果')
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(SKILL_SRC, 'SKILL.md')):
        sys.exit('错误: 未找到 skills/beijing-house-hunter/SKILL.md — 请在本仓库根目录运行')

    if args.list:
        for name, d in AGENTS:
            print(f"{'[√]' if os.path.isdir(os.path.dirname(d)) else '[ ]'} {name:12s} {d}")
        sys.exit(0)

    targets = [(args.dir,)] if args.dir else detect()
    if not targets:
        sys.exit('未检测到已安装的 Agent（ZCode/Claude Code/Codex）。请用 --dir 指定 skills 目录，\n'
                 '例如: python install.py --dir ~/.claude/skills')

    for t in targets:
        dest_root = t[0]
        dest = os.path.join(os.path.expanduser(dest_root), 'beijing-house-hunter')
        if os.path.exists(dest):
            print(f"跳过 {dest} （已存在；如需更新请先删除该目录）")
            continue
        shutil.copytree(SKILL_SRC, dest)
        print(f"✓ 已安装到 {dest}")

    print("\n完成。对 Agent 说：『用 beijing-house-hunter 帮我找房：预算XX万、XX区、两居』即可触发。")

if __name__ == '__main__':
    main()
