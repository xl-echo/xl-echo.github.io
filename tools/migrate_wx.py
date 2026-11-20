# -*- coding: utf-8 -*-
"""抓取"植物之象"公众号文章正文与原图，用于迁移到草本生长观察网站。

用法:
  python tools/migrate_wx.py            # 抓取正文+下载图片，生成 migration_report.json
  python tools/migrate_wx.py --apply    # 根据报告改写 index.html（正文块 + ARTICLES 数组）
"""
import json
import os
import re
import sys
from html import unescape
from html.parser import HTMLParser
from urllib import request as urlreq
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE, 'images')
REPORT = os.path.join(BASE, 'tools', 'migration_report.json')
INDEX_HTML = os.path.join(BASE, 'index.html')

# (slug, 链接, 发布日期)
ARTICLES = [
    ('fangfeng', 'https://mp.weixin.qq.com/s/NDe6y-4tUvPUG55hwtWKpw', '2026-10-21'),
    ('longyan',  'https://mp.weixin.qq.com/s/NPMmtqs1H9JpsZcJDfQQHA', '2026-10-19'),
    ('cheqian',  'https://mp.weixin.qq.com/s/1EpcqbqTq1Ph3Dfd0_T9_A', '2026-10-15'),
    ('buguzhi',  'https://mp.weixin.qq.com/s/kwgvsLDQtdixyoa2WE6M7Q', '2026-10-12'),
    ('biqi',     'https://mp.weixin.qq.com/s/HVxYo5HN25NUK-lVtw9-uA', '2026-10-11'),
    ('gouqi',    'https://mp.weixin.qq.com/s/sQFJ-RzwsgMW4A_p1P4Z6g', '2026-10-10'),
    ('banli',    'https://mp.weixin.qq.com/s/IbV_QjB_kM69DuWC_VwTbw', '2026-10-09'),
    ('bajiaoxin','https://mp.weixin.qq.com/s/MWSUC8WEcUhHUiUHUxgbAg', '2026-10-05'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

HEAD_MAP = {'h1': 'h2', 'h2': 'h2', 'h3': 'h3', 'h4': 'h3', 'h5': 'h3', 'h6': 'h3'}
BLOCK_TAGS = {'p', 'section', 'div', 'blockquote', 'li', 'ul', 'ol', 'table', 'tr'}


def fetch(url, timeout=30):
    req = urlreq.Request(url, headers=HEADERS)
    with urlreq.urlopen(req, timeout=timeout) as r:
        return r.read()


class WxParser(HTMLParser):
    """遍历 js_content，按顺序产出 (类型, 内容) 块。类型: p/h2/h3/quote/li/img"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_js = False
        self.js_depth = 0
        self.buffer = []
        self.blocks = []
        self.quote_depth = 0
        self.heading = None

    def buf_text(self):
        return ''.join(self.buffer).strip()

    def flush(self, forced_type=None):
        text = ''.join(self.buffer)
        self.buffer = []
        text = text.strip()
        if not text:
            return
        # \x01..\x02 包裹的片段转为 **加粗**
        parts = text.split('\x01')
        out = parts[0]
        for seg in parts[1:]:
            if '\x02' in seg:
                b, rest = seg.split('\x02', 1)
                out += '**' + b.strip() + '**' + rest
            else:
                out += '**' + seg.strip() + '**'
        out = re.sub(r'\*\*\s*\*\*', '', out)
        out = re.sub(r'[ \t]+', ' ', out)
        if forced_type:
            self.blocks.append((forced_type, out))
        elif self.heading:
            self.blocks.append((HEAD_MAP.get(self.heading, 'h2'), out))
        elif self.quote_depth > 0:
            self.blocks.append(('quote', out))
        else:
            self.blocks.append(('p', out))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.in_js:
            if tag == 'div' and a.get('id') == 'js_content':
                self.in_js = True
                self.js_depth = 1
            return
        if tag == 'div':
            self.js_depth += 1
            if self.buf_text():
                self.flush()
            return
        if tag == 'img':
            src = (a.get('data-src') or a.get('src') or '').strip()
            if 'mmbiz.qpic.cn' in src:
                if self.buf_text():
                    self.flush()
                self.blocks.append(('img', src))
            return
        if tag in BLOCK_TAGS:
            if tag == 'blockquote':
                self.quote_depth += 1
            if self.buf_text():
                self.flush()
            return
        if tag in HEAD_MAP:
            if self.buf_text():
                self.flush()
            self.heading = tag
            return
        if tag in ('strong', 'b'):
            self.buffer.append('\x01')
            return
        if tag == 'br':
            self.buffer.append('\n')

    def handle_startendtag(self, tag, attrs):
        if tag == 'img':
            self.handle_starttag('img', attrs)
        elif tag == 'br':
            self.buffer.append('\n')

    def handle_endtag(self, tag):
        if not self.in_js:
            return
        if tag == 'div':
            self.js_depth -= 1
            if self.js_depth <= 0:
                self.flush()
                self.in_js = False
            elif self.buf_text():
                self.flush()
            return
        if tag == 'blockquote':
            self.flush()
            self.quote_depth = max(0, self.quote_depth - 1)
            return
        if tag in HEAD_MAP:
            self.flush()
            self.heading = None
            return
        if tag in ('strong', 'b'):
            self.buffer.append('\x02')
            return
        if tag in BLOCK_TAGS:
            self.flush()

    def handle_data(self, data):
        if self.in_js:
            self.buffer.append(data)


def img_ext(url):
    q = parse_qs(urlparse(url).query)
    fmt = (q.get('wx_fmt') or ['jpeg'])[0].lower()
    return {'jpeg': '.jpg', 'jpg': '.jpg', 'png': '.png', 'gif': '.gif', 'webp': '.webp'}.get(fmt, '.jpg')


def meta_of(html, prop):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), html)
    return unescape(m.group(1)).strip() if m else ''


def collect():
    os.makedirs(IMG_DIR, exist_ok=True)
    report = {}
    for slug, url, date in ARTICLES:
        print('抓取 %s (%s) ...' % (slug, url))
        sys.stdout.flush()
        try:
            html = fetch(url).decode('utf-8', 'replace')
        except Exception as e:
            print('  下载失败: %r' % e)
            report[slug] = {'error': str(e), 'url': url, 'date': date}
            continue
        title = meta_of(html, 'og:title') or ''
        digest = meta_of(html, 'og:description') or ''
        digest = digest.replace('温馨提示：本文仅从传统本草象理文化角度分享植物知识，仅供学习参考，不具备诊疗指导作用。草药切勿自行采摘、服用，身体不适请咨询专业医师。', '').replace('💡', '').strip()
        if 'js_content' not in html:
            print('  未找到正文（可能被反爬拦截）')
            report[slug] = {'error': 'no js_content', 'url': url, 'date': date}
            continue
        p = WxParser()
        p.feed(html)
        # 图片按顺序去重，跳过 svg
        seen = []
        for t, c in p.blocks:
            if t == 'img' and c not in seen and 'wx_fmt=svg' not in c:
                seen.append(c)
        # 下载图片
        images = []
        for i, iu in enumerate(seen, 1):
            ext = img_ext(iu)
            fname = '%s-%d%s' % (slug, i, ext)
            fpath = os.path.join(IMG_DIR, fname)
            if not os.path.exists(fpath) or os.path.getsize(fpath) < 500:
                try:
                    data = fetch(iu, timeout=40)
                    with open(fpath, 'wb') as f:
                        f.write(data)
                except Exception as e:
                    print('  图片下载失败 %s: %r' % (iu[:80], e))
                    images.append({'url': iu, 'file': None, 'error': str(e)})
                    continue
            images.append({'url': iu, 'file': 'images/' + fname, 'bytes': os.path.getsize(fpath)})
        # img 块内容替换为本地路径
        file_by_url = {im['url']: im['file'] for im in images if im.get('file')}
        blocks = []
        for t, c in p.blocks:
            if t == 'img':
                local = file_by_url.get(c)
                if local:
                    blocks.append(('img', '![](./%s)' % local))
            else:
                blocks.append((t, c))
        report[slug] = {
            'url': url, 'date': date, 'title': title, 'digest': digest,
            'blocks': blocks, 'images': images,
        }
        print('  标题: %s | 块数: %d | 图片: %d' % (title, len(blocks), len(images)))
        sys.stdout.flush()
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('报告已写入 %s' % REPORT)


def js_str(s):
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').strip()


def to_markdown(blocks):
    lines = []
    i = 0
    n = len(blocks)
    # 首块温馨提示转为引用
    if n and blocks[0][0] == 'p' and ('温馨提示' in blocks[0][1]):
        blocks = [('quote', blocks[0][1].replace('💡', '').strip())] + list(blocks[1:])
        n = len(blocks)
    while i < n:
        t, c = blocks[i]
        if t == 'img':
            lines.append('')
            lines.append(c)
            lines.append('')
            i += 1
            continue
        if t == 'li':
            group = []
            while i < n and blocks[i][0] == 'li':
                group.append(blocks[i][1])
                i += 1
            lines.append('')
            lines.extend('- ' + x for x in group)
            lines.append('')
            continue
        if t == 'quote':
            for ln in c.split('\n'):
                lines.append('> ' + ln)
            lines.append('')
            i += 1
            continue
        if t in ('h2', 'h3'):
            lines.append('')
            lines.append('#' * (2 if t == 'h2' else 3) + ' ' + c)
            lines.append('')
            i += 1
            continue
        for ln in c.split('\n'):
            lines.append(ln)
        lines.append('')
        i += 1
    return '\n'.join(lines).strip()


HUZHANG_ENTRY = """  {
    slug: 'huzhang',
    title: '虎杖：根黄茎斑花白，火气透出体表后化为寒',
    summary: '地下根茎切面黄，地上茎秆绿兼红斑，顶梢花淡绿近白——三种颜色排在同一条路上，是火从郁结到透尽的全过程。',
    date: '2026-11-03',
    hero: 'images/huzhang-hero.png'
  }"""


def apply():
    with open(REPORT, 'r', encoding='utf-8') as f:
        report = json.load(f)
    with open(INDEX_HTML, 'r', encoding='utf-8', newline='') as f:
        html = f.read()

    entries = [HUZHANG_ENTRY]
    for slug, url, date in ARTICLES:
        info = report.get(slug)
        if not info or info.get('error'):
            print('跳过 %s（无报告或抓取失败）' % slug)
            continue
        title = info['title'] or slug
        summary = info['digest']
        if not summary:
            for t, c in info['blocks']:
                if t == 'p' and '温馨提示' not in c:
                    summary = re.sub(r'\*\*', '', c)[:80] + '……'
                    break
        hero = ''
        for im in info['images']:
            if im.get('file'):
                hero = im['file']
                break
        entries.append("  {\n    slug: '%s',\n    title: '%s',\n    summary: '%s',\n    date: '%s',\n    hero: '%s'\n  }" % (
            slug, js_str(title), js_str(summary), date, hero))
        # 替换正文块
        md = to_markdown(info['blocks'])
        block = '<script type="text/markdown" data-slug="%s">\n# %s\n\n%s\n</script>' % (slug, title, md)
        pat = re.compile(r'<script type="text/markdown" data-slug="%s">.*?</script>' % re.escape(slug), re.S)
        if not pat.search(html):
            print('警告: 未找到 %s 的正文块' % slug)
        html = pat.sub(lambda m: block, html, count=1)
        print('%s 完成: 《%s》 hero=%s' % (slug, title, hero or '无'))

    new_array = 'const ARTICLES = [\n' + ',\n'.join(entries) + '\n];'
    html, cnt = re.subn(r'const ARTICLES = \[.*?\n\];', lambda m: new_array, html, count=1, flags=re.S)
    if cnt != 1:
        print('警告: ARTICLES 数组替换数 = %d' % cnt)
    with open(INDEX_HTML, 'w', encoding='utf-8', newline='') as f:
        f.write(html)
    print('index.html 已更新')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--apply' in sys.argv:
        apply()
    else:
        collect()
