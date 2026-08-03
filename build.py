#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 网站构建脚本：把 writing/ 里的 Markdown 文章生成 essays/ 下的 HTML 页面和文章列表。
# 平时不需要手动运行——Netlify 每次收到后台的发布会自动执行（npm run build → python3 build.py）。

import os, re, json, html as htmlmod, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'writing')
OUT = os.path.join(ROOT, 'essays')

CSS = '''
:root{
  --paper:#fcfaec;--ink:#211212;--ink-2:#584a3c;--accent:#a96c1d;
  --line-soft:rgba(33,18,18,.10);
  --serif-display:'Libre Caslon Display','Noto Serif SC','Songti SC','STSong','SimSun',Georgia,'Times New Roman',serif;
  --serif:'Libre Caslon Text','Noto Serif SC','Songti SC','STSong','SimSun',Georgia,'Times New Roman',serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:1.0625rem;line-height:1.9;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
.wrap{max-width:46rem;margin:0 auto;padding:3rem 1.5rem 4rem}
.page-top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line-soft);padding-bottom:1.2rem;margin-bottom:2.5rem}
.brand{color:var(--ink);text-decoration:none;font-weight:600;letter-spacing:.08em}
.back{font-size:.9rem;text-decoration:none;letter-spacing:.08em}
.essay-date{font-size:.78rem;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);margin:0 0 1rem}
h1{margin:0 0 2rem;font-family:var(--serif-display);font-size:clamp(1.7rem,4vw,2.4rem);line-height:1.35;font-weight:600}
.essay-body h2{font-family:var(--serif-display);font-size:1.4rem;margin:2.2rem 0 1rem}
.essay-body h3{font-family:var(--serif-display);font-size:1.15rem;margin:1.8rem 0 .9rem}
.essay-body p{margin:0 0 1.5rem}
.essay-body img{max-width:100%;height:auto;margin:.5rem 0 1.5rem}
.essay-body blockquote{margin:0 0 1.5rem;padding:.2rem 0 .2rem 1.2rem;border-left:2px solid var(--accent);color:var(--ink-2)}
.essay-body ul,.essay-body ol{margin:0 0 1.5rem;padding-left:1.4rem}
.essay-body li{margin:.35rem 0}
.essay-body code{font-family:Menlo,Consolas,monospace;font-size:.88em;background:rgba(169,108,29,.08);padding:.1em .35em;border-radius:2px}
.essay-body pre{background:var(--paper);border:1px solid var(--line-soft);padding:1rem;overflow-x:auto;margin:0 0 1.5rem}
.essay-body pre code{background:none;padding:0}
.essay-body hr{border:none;border-top:1px solid var(--line-soft);margin:2.5rem 0}
.essay-end{margin-top:3rem;border-top:1px solid var(--line-soft);padding-top:1.5rem;font-size:.9rem;color:var(--ink-2)}
'''

PAGE_TMPL = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 李青林</title>
<style>
{style}
</style>
</head>
<body>
<div class="wrap">
  <div class="page-top">
    <a class="brand" href="../index.html">李青林 · 在案卷之外写作</a>
    <a class="back" href="../index.html#writing">← 返回</a>
  </div>
  <p class="essay-date">{date}</p>
  <h1>{title}</h1>
  <div class="essay-body">
{body}
  </div>
  <p class="essay-end">李青林 · 在案卷之外写作</p>
</div>
</body>
</html>'''


def inline(s):
    tokens = []
    def _save(m):
        tokens.append(m.group(0))
        return '\x00%d\x00' % (len(tokens) - 1)
    s = re.sub(r'<[^>]+>', _save, s)
    s = re.sub(r'`([^`]+)`', lambda m: '<code>' + m.group(1) + '</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', lambda m: '<strong>' + m.group(1) + '</strong>', s)
    s = re.sub(r'\*([^*]+)\*', lambda m: '<em>' + m.group(1) + '</em>', s)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', r'<img src="\2" alt="\1">', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', s)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m.group(1))], s)


def render(body):
    lines = body.replace('\r\n', '\n').split('\n')
    out = []
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        stripped = ln.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith('```'):
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                code.append(lines[i])
                i += 1
            i += 1
            out.append('<pre><code>' + htmlmod.escape('\n'.join(code)) + '</code></pre>')
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            lv = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lv, inline(m.group(2)), lv))
            i += 1
            continue
        if re.match(r'^\s*-{3,}\s*$', ln):
            out.append('<hr>')
            i += 1
            continue
        if stripped.startswith('>'):
            q = []
            while i < n and lines[i].strip().startswith('>'):
                q.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            out.append('<blockquote>' + inline(' '.join(x.strip() for x in q)) + '</blockquote>')
            continue
        if re.match(r'^\s*[-*]\s+', ln):
            items = []
            while i < n and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(inline(re.sub(r'^\s*[-*]\s+', '', lines[i]).strip()))
                i += 1
            out.append('<ul>' + ''.join('<li>%s</li>' % x for x in items) + '</ul>')
            continue
        if re.match(r'^\s*\d+[.)]\s+', ln):
            items = []
            while i < n and re.match(r'^\s*\d+[.)]\s+', lines[i]):
                items.append(inline(re.sub(r'^\s*\d+[.)]\s+', '', lines[i]).strip()))
                i += 1
            out.append('<ol>' + ''.join('<li>%s</li>' % x for x in items) + '</ol>')
            continue
        para = [ln]
        i += 1
        while i < n and lines[i].strip() and not re.match(r'^(#{1,6})\s|^\s*[-*]\s|^\s*\d+[.)]\s|^\s*-{3,}\s*$|^\s*>\s|^```', lines[i]):
            para.append(lines[i])
            i += 1
        out.append('<p>' + inline(' '.join(x.strip() for x in para)) + '</p>')
    return '\n'.join(out)


def parse_md(path):
    raw = open(path, encoding='utf-8').read()
    meta, body = {}, raw
    if raw.startswith('---'):
        end = raw.find('\n---', 3)
        if end != -1:
            for line in raw[3:end].split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip().strip('"\'')
            body = raw[end + 4:].lstrip('\n')
    return meta, body


def main():
    os.makedirs(OUT, exist_ok=True)
    items, valid = [], set()
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith('.md'):
            continue
        meta, body = parse_md(os.path.join(SRC, fn))
        title = meta.get('title') or fn[:-3]
        slug = meta.get('slug') or fn[:-3]
        date = meta.get('date', '')[:10]
        excerpt = meta.get('excerpt', '')
        date_cn = date
        try:
            dt = datetime.date(*[int(x) for x in date.split('-')])
            date_cn = '%d年%d月%d日' % (dt.year, dt.month, dt.day)
        except Exception:
            pass
        page = (PAGE_TMPL
                .replace('{style}', CSS)
                .replace('{title}', htmlmod.escape(title))
                .replace('{date}', date_cn)
                .replace('{body}', render(body)))
        outname = slug + '.html'
        if not re.match(r'^[A-Za-z0-9\-_]+$', slug):
            outname = fn[:-3] + '.html'
        with open(os.path.join(OUT, outname), 'w', encoding='utf-8') as f:
            f.write(page)
        valid.add(outname)
        items.append({'date': date[:7], 'title': title, 'excerpt': excerpt, 'url': 'essays/' + outname})
    for fn in os.listdir(OUT):
        if fn != 'list.json' and fn not in valid:
            os.remove(os.path.join(OUT, fn))
    items.sort(key=lambda x: x['date'], reverse=True)
    with open(os.path.join(OUT, 'list.json'), 'w', encoding='utf-8') as f:
        json.dump({'essays': items}, f, ensure_ascii=False, indent=2)
    print('built %d essays' % len(items))


if __name__ == '__main__':
    main()
