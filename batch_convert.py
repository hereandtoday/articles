#!/usr/bin/env python3
"""批量将知识库公司卡片转换为静态HTML网站页面"""

import os, re, json
import markdown

KB_ROOT = r"E:\知识库\01_公司研究\公司卡片"
OUT_ROOT = r"C:\Users\herea\Desktop\html文档"

CSS = """:root{--ink:#14181f;--ink-soft:#3c4451;--ink-mute:#6c7686;--rule:#dde2ea;--rule-strong:#b9c1cf;--paper:#fff;--paper-soft:#f6f8fb;--accent:#1f4ea8;--accent-light:#e8edf5;--code-bg:#f1f4f9;--code-ink:#16213a;--table-row-alt:#fafbfd;--positive:#1c6e3d;--negative:#a32a2a;--warning:#c97a1a}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{font-size:16px;-webkit-text-size-adjust:100%}@media(max-width:600px){html{font-size:15px}}
body{font-family:"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Inter",-apple-system,sans-serif;color:var(--ink);background:var(--paper);line-height:1.65}
h1{font-size:20px;font-weight:700;margin:0 0 10px;color:#1a365d;line-height:1.3}
h2{font-size:1.2rem;font-weight:700;color:#1a365d;margin:1.8em 0 .6em;padding-bottom:6px;border-bottom:2px solid var(--rule)}
h3{font-size:1.05rem;font-weight:600;color:var(--ink-soft);margin:1.4em 0 .5em}
p{margin-bottom:1em;text-align:justify;word-break:break-word}
hr{border:none;height:1px;background:var(--rule);margin:1.8em 0}
blockquote{margin:1em 0;padding:12px 16px;background:#f7f3eb;border-left:4px solid #b85a20;color:#4a3a2a;font-size:14px;line-height:1.5;border-radius:0 4px 4px 0}
blockquote p{margin-bottom:0}
strong{color:var(--ink);font-weight:700}
code{font-family:"JetBrains Mono","SF Mono",monospace;background:var(--accent-light);padding:2px 6px;border-radius:3px;font-size:13px;color:var(--accent)}
pre{background:var(--code-bg);border:1px solid var(--rule);border-radius:6px;padding:14px 18px;margin:12px 0;overflow-x:auto;font-size:13px;line-height:1.5;font-family:"JetBrains Mono","SF Mono",monospace;color:var(--code-ink)}
pre code{background:none;padding:0;color:var(--code-ink)}
li{margin-bottom:4px;line-height:1.6;margin-left:20px}
ul,ol{margin:8px 0}
table{width:100%;border-collapse:collapse;margin:1em 0;font-size:13px;line-height:1.5}
table th{background:var(--accent);color:#fff;font-weight:600;padding:8px 12px;border:1px solid var(--accent);text-align:left;font-size:12px;white-space:nowrap}
table td{padding:7px 12px;border:1px solid var(--rule);vertical-align:top}
table tbody tr:nth-child(even) td{background:var(--table-row-alt)}
table tbody tr:hover td{background:var(--accent-light);cursor:pointer}
.pos{color:var(--positive);font-weight:600}
.neg{color:var(--negative);font-weight:600}
.warn{color:var(--warning);font-weight:600}
"""


def strip_frontmatter(text):
    if text.startswith('---'):
        idx = text.find('---', 3)
        if idx != -1:
            return text[idx+3:].lstrip()
    return text


def preprocess_obsidian(text):
    lines = text.split('\n')
    result = []
    in_callout = False
    for line in lines:
        m = re.match(r'^>\s*\[!(\w+)\]\s*(.*)', line)
        if m:
            text_content = m.group(2).strip()
            result.append(f'> **{text_content}**' if text_content else '')
            in_callout = True
            continue
        if in_callout and line.startswith('>'):
            content = line[1:].strip()
            result.append(f'> {content}' if content else '>')
            continue
        in_callout = False
        result.append(line)
    return '\n'.join(result)


def markdown_to_html(md_text, company_name, card_name):
    md_text = strip_frontmatter(md_text)
    lines = md_text.split('\n')
    clean_lines = []
    skip_h1 = True
    for line in lines:
        if skip_h1 and line.startswith('# ') and not line.startswith('## '):
            skip_h1 = False
            continue
        clean_lines.append(line)
    md_text = '\n'.join(clean_lines)
    md_text = preprocess_obsidian(md_text)
    md_text = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', md_text)
    html_body = markdown.markdown(md_text, extensions=['extra', 'tables', 'fenced_code', 'sane_lists'])
    return html_body


def build_html_page(company_name, card_name, body_html):
    title = f"{company_name} · {card_name}"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="body">
<h1>{title}</h1>
{body_html}
</div>
</body>
</html>"""


def get_card_name(file_stem, company_name):
    if file_stem == f"{company_name}总览":
        return "总览"
    name_map = {
        '商业模式': '商业模式', '成长性': '成长性', '盈利能力': '盈利能力',
        '估值': '估值', '风险': '风险', '影响因素': '影响因素',
        '逻辑链路': '逻辑链路', '跟踪清单': '跟踪清单',
        '公司发展历程': '公司发展历程', '变更记录': '变更记录',
    }
    return name_map.get(file_stem, file_stem)


def main():
    companies = []
    dirs = sorted(os.listdir(KB_ROOT))
    total_companies = 0
    total_pages = 0

    for item in dirs:
        company_dir = os.path.join(KB_ROOT, item)
        if not os.path.isdir(company_dir):
            continue
        parts = item.rsplit('_', 1)
        if len(parts) != 2:
            continue
        company_name = parts[0]
        company_code = parts[1]
        company_id = item
        total_companies += 1

        out_dir = os.path.join(OUT_ROOT, company_id)
        os.makedirs(out_dir, exist_ok=True)

        md_files = sorted([f for f in os.listdir(company_dir) if f.endswith('.md') and f != 'INDEX.md'])
        card_names = []

        for md_file in md_files:
            file_stem = md_file[:-3]
            if file_stem == '认知复盘':
                continue
            card_name = get_card_name(file_stem, company_name)
            md_path = os.path.join(company_dir, md_file)
            with open(md_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            body_html = markdown_to_html(md_text, company_name, card_name)
            page_html = build_html_page(company_name, card_name, body_html)
            if file_stem == f"{company_name}总览":
                out_file = f"{company_name}总览.html"
            else:
                out_file = f"{file_stem}.html"
            out_path = os.path.join(out_dir, out_file)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            total_pages += 1
            card_names.append(card_name)

        companies.append({"id": company_id, "name": company_name, "code": company_code, "cards": card_names})

    print(f"✅ {total_companies}家公司, {total_pages}个页面")

    # Merge with existing companies.json to preserve ratings
    json_path = os.path.join(OUT_ROOT, 'data', 'companies.json')
    existing = {}
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            for c in json.load(f):
                existing[c['id']] = c

    new_list = []
    for c in companies:
        cid = c['id']
        if cid in existing:
            ec = existing[cid]
            new_list.append({
                "id": cid, "name": c['name'], "code": ec.get('code', c['code']),
                "rating": ec.get('rating', ''), "category": ec.get('category', ''),
                "certainty": ec.get('certainty', ''), "margin": ec.get('margin', ''),
                "updated": ec.get('updated', '')
            })
        else:
            new_list.append({"id": cid, "name": c['name'], "code": c['code'],
                             "rating": "", "category": "", "certainty": "", "margin": "", "updated": ""})

    existing_order = {c['id']: i for i, c in enumerate(existing.values())} if existing else {}
    new_list.sort(key=lambda c: (0, existing_order.get(c['id'])) if c['id'] in existing_order else (1, c['name']))

    os.makedirs(os.path.join(OUT_ROOT, 'data'), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_list, f, ensure_ascii=False, indent=2)

    print(f"📋 companies.json: {len(new_list)}家公司")


if __name__ == '__main__':
    main()
