#!/usr/bin/env python3
"""每日同步：检查知识库公司卡片更新，有变化则生成HTML并推送"""

import os, sys, json, subprocess, glob
from datetime import datetime

# ===== 路径配置 =====
KB_CARDS = r"E:\知识库\01_公司研究\公司卡片"
OUT_DIR = r"C:\Users\herea\Desktop\html文档"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERT_SCRIPT = os.path.join(OUT_DIR, "..", "batch_convert.py")

# ===== 上次记录的修改时间（存个文件） =====
STATE_FILE = os.path.join(OUT_DIR, ".sync_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_mtimes():
    """获取知识库所有公司卡片文件的修改时间"""
    mtimes = {}
    for d in os.listdir(KB_CARDS):
        dpath = os.path.join(KB_CARDS, d)
        if not os.path.isdir(dpath):
            continue
        for f in os.listdir(dpath):
            if f.endswith('.md') and f != 'INDEX.md':
                fpath = os.path.join(dpath, f)
                mtime = os.path.getmtime(fpath)
                mtimes[fpath] = mtime
    return mtimes

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 开始检查公司卡片变化...")
    
    current_mtimes = get_mtimes()
    prev_state = load_state()
    
    # 找出有变化的文件
    changed_files = []
    for fpath, mtime in current_mtimes.items():
        prev_mtime = prev_state.get(fpath)
        if prev_mtime is None or prev_mtime != mtime:
            changed_files.append(fpath)
    
    if not changed_files:
        print("无变化，跳过。")
        # 更新状态文件（以防文件被删）
        save_state(current_mtimes)
        return
    
    # 找出涉及的公司
    changed_companies = set()
    for fpath in changed_files:
        rel = os.path.relpath(os.path.dirname(fpath), KB_CARDS)
        changed_companies.add(rel)
    
    print(f"检测到 {len(changed_files)} 个文件变更，涉及 {len(changed_companies)} 家公司:")
    for c in sorted(changed_companies):
        print(f"  - {c}")
    
    # 重新生成所有页面（保持一致性，避免遗漏跨公司引用）
    print("正在重新生成HTML页面...")
    code = subprocess.call([sys.executable, CONVERT_SCRIPT], cwd=SCRIPT_DIR)
    if code != 0:
        print(f"ERROR: HTML生成失败 (exit code {code})")
        sys.exit(1)
    
    # 检查 git 是否有变更
    os.chdir(OUT_DIR)
    rc, stdout, stderr = run_cmd("git status --porcelain")
    if not stdout:
        print("git 无变更，跳过推送。")
        save_state(current_mtimes)
        return
    
    changed_count = len(stdout.split('\n'))
    print(f"检测到 {changed_count} 个文件变更，准备提交推送...")
    
    # 构建提交信息
    companies_str = "、".join(sorted(c.split("_")[0] for c in changed_companies))
    msg = f"auto-sync: {companies_str} 卡片更新 ({datetime.now().strftime('%m-%d %H:%M')})"
    
    rc, stdout, stderr = run_cmd("git add -A")
    rc, stdout, stderr = run_cmd(f'git commit -m "{msg}"')
    if rc != 0:
        print(f"提交失败: {stderr}")
        sys.exit(1)
    
    rc, stdout, stderr = run_cmd("git push")
    if rc != 0:
        # 尝试 SSL 绕过
        rc, stdout, stderr = run_cmd("GIT_SSL_NO_VERIFY=1 git push")
        if rc != 0:
            print(f"推送失败: {stderr}")
            sys.exit(1)
    
    # 保存状态
    save_state(current_mtimes)
    
    print(f"✅ 同步完成！已更新并推送 {changed_count} 个文件")


if __name__ == '__main__':
    main()
