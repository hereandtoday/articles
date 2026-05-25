#!/usr/bin/env python3
"""每日同步：检查知识库公司卡片更新，有变化则生成HTML并推送"""

import os, sys, json, subprocess
from datetime import datetime

KB_CARDS = r"E:\知识库\01_公司研究\公司卡片"
OUT_DIR = r"C:\Users\herea\Desktop\html文档"
STATE_FILE = os.path.join(OUT_DIR, ".sync_state.json")
CONVERT_SCRIPT = os.path.join(os.path.dirname(OUT_DIR), "batch_convert.py")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def get_mtimes():
    mtimes = {}
    for d in os.listdir(KB_CARDS):
        dpath = os.path.join(KB_CARDS, d)
        if not os.path.isdir(dpath):
            continue
        for f in os.listdir(dpath):
            if f.endswith('.md') and f != 'INDEX.md':
                fpath = os.path.join(dpath, f)
                mtimes[fpath] = os.path.getmtime(fpath)
    return mtimes


def run(cmd, cwd=None):
    """Run shell command, return (code, stdout)"""
    p = subprocess.Popen(
        cmd, shell=True, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = p.communicate()
    # Decode with replacement for Chinese chars
    out_str = out.decode('utf-8', errors='replace').strip()
    err_str = err.decode('utf-8', errors='replace').strip()
    return p.returncode, out_str, err_str


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 开始检查...")

    current_mtimes = get_mtimes()
    prev_state = load_state()

    # 首次运行（无状态）→ 全量生成并记录状态即可
    is_first_run = not prev_state

    # 找变化文件
    changed = []
    for fp, mt in current_mtimes.items():
        if fp not in prev_state or prev_state[fp] != mt:
            changed.append(fp)

    if not changed and not is_first_run:
        print("无变化，跳过。")
        return

    if is_first_run:
        print("首次运行，全量生成...")
    else:
        companies = sorted(set(os.path.basename(os.path.dirname(f)) for f in changed))
        print(f"{len(changed)} 个文件变更，涉及 {len(companies)} 家公司: {', '.join(c.split('_')[0] for c in companies)}")

    # 生成HTML
    rc, out, err = run(f'python "{CONVERT_SCRIPT}"', cwd=os.path.dirname(OUT_DIR))
    if rc != 0:
        print(f"HTML生成失败:\n{err}")
        sys.exit(1)

    # 检查 git 变更
    os.chdir(OUT_DIR)
    rc, out, err = run("git status --porcelain")
    if not out:
        print("git 无变更，跳过推送。")
        save_state(current_mtimes)
        return

    changed_count = len(out.split('\n'))
    print(f"检测到 {changed_count} 个文件变更，提交推送...")

    # 提交信息
    if not is_first_run:
        companies = sorted(set(
            os.path.basename(os.path.dirname(f)).split('_')[0]
            for f in changed
        ))
        msg = f"auto-sync: {','.join(companies)} ({datetime.now().strftime('%m-%d %H:%M')})"
    else:
        msg = f"auto-sync: 全量更新 ({datetime.now().strftime('%m-%d %H:%M')})"

    run("git add -A", cwd=OUT_DIR)
    rc, out, err = run(f'git commit -m "{msg}"', cwd=OUT_DIR)
    if rc != 0 and 'nothing to commit' not in err:
        print(f"提交警告: {err}")

    # 推送（带SSL绕过）
    rc, out, err = run("git push", cwd=OUT_DIR)
    if rc != 0:
        print("SSL推送失败，尝试无SSL验证...")
        rc, out, err = run("env GIT_SSL_NO_VERIFY=1 git push", cwd=OUT_DIR)
        if rc != 0:
            print(f"推送失败:\n{err}")
            sys.exit(1)

    save_state(current_mtimes)
    print(f"✅ 同步完成！推送 {changed_count} 个文件")


if __name__ == '__main__':
    main()
