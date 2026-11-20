# -*- coding: utf-8 -*-
"""从公众号文章链接一键入库：抓正文 + 下原图 + 写元数据 + 重生成站点。

用法：
  python tools/add_from_url.py <链接1> [<链接2> ...]              # 只入库并重新生成
  python tools/add_from_url.py --deploy <链接...>                 # 入库 + 生成 + 部署 Cloudflare
  python tools/add_from_url.py --dry-run <链接>                   # 仅预览解析结果，不写文件

自动处理：
  - 从 og:title 取标题，从页面变量取发布日期
  - slug 由标题拼音自动生成（已存在则跳过，避免重复入库）
  - 正文按公众号原格式转 Markdown（小标题/加粗/引用/图片位置）
  - 原文图片下载到 images/<slug>-N.jpg 并替换正文引用
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate_wx import fetch, WxParser, img_ext, meta_of, to_markdown  # noqa: E402
from pypinyin import lazy_pinyin  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(BASE, 'tools', 'articles.json')
MD_DIR = os.path.join(BASE, 'tools', 'markdown')
IMG_DIR = os.path.join(BASE, 'images')
SITE = os.environ.get('SITE_BASE', 'https://caoben-guancha.pages.dev').rstrip('/')


def make_slug(title, existing):
    words = lazy_pinyin(re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', title))
    slug = '-'.join(words)[:32].strip('-')
    while slug in existing:
        slug += '-x'
    return slug


def find_date(html):
    for pat in (r'var create_time\s*=\s*"([^"]+)"',
                r'var ct\s*=\s*"(\d{10})"',
                r'"publish_time"\s*:\s*"([^"]+)"'):
        m = re.search(pat, html)
        if m:
            v = m.group(1)
            if v.isdigit() and len(v) == 10:
                return datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d')
            m2 = re.match(r'(\d{4})-(\d{2})-(\d{2})', v)
            if m2:
                return '%s-%s-%s' % m2.groups()
    return datetime.now().strftime('%Y-%m-%d')


def parse_article(url, slug):
    html = fetch(url).decode('utf-8', 'replace')
    if 'js_content' not in html:
        raise RuntimeError('未取到正文（可能被反爬拦截）')
    title = meta_of(html, 'og:title') or '无标题'
    date = find_date(html)
    p = WxParser()
    p.feed(html)

    seen = []
    for t, c in p.blocks:
        if t == 'img' and c not in seen and 'wx_fmt=svg' not in c:
            seen.append(c)

    os.makedirs(IMG_DIR, exist_ok=True)
    mapping = {}
    for i, iu in enumerate(seen, 1):
        fname = '%s-%d%s' % (slug, i, img_ext(iu))
        fpath = os.path.join(IMG_DIR, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 500:
            try:
                data = fetch(iu, timeout=40)
                with open(fpath, 'wb') as f:
                    f.write(data)
            except Exception as e:
                print('  图片下载失败:', str(e)[:60])
                continue
        mapping[iu] = 'images/' + fname

    blocks = []
    for t, c in p.blocks:
        if t == 'img':
            local = mapping.get(c)
            if local:
                blocks.append(('img', '![](%s)' % local))
        else:
            blocks.append((t, c))

    md = '# %s\n\n%s' % (title, to_markdown(blocks))
    hero = next((mapping[u] for u in seen if u in mapping), '')
    summary = ''
    for t, c in blocks:
        if t == 'p' and '温馨提示' not in c:
            plain = re.sub(r'\*\*', '', c)
            summary = plain[:80] + ('……' if len(plain) > 80 else '')
            break
    return {'slug': slug, 'title': title, 'summary': summary, 'date': date, 'hero': hero,
            'markdown': md, 'images': len(mapping)}


def main():
    args = [a for a in sys.argv[1:]]
    deploy = '--deploy' in args
    dry = '--dry-run' in args
    urls = [a for a in args if a.startswith('http')]
    # --slug 名称（单篇）/ --slugs a,b,c（多篇，按顺序对应）
    slug_single = None
    slug_list = None
    if '--slug' in args:
        slug_single = args[args.index('--slug') + 1]
    if '--slugs' in args:
        slug_list = [x.strip() for x in args[args.index('--slugs') + 1].split(',')]
    if not urls:
        print(__doc__)
        return

    arts = json.load(open(ARTICLES, encoding='utf-8'))
    existing = {a['slug'] for a in arts}
    added = 0

    for idx, url in enumerate(urls):
        print('抓取 %s' % url)
        try:
            probe = fetch(url).decode('utf-8', 'replace')
            title = meta_of(probe, 'og:title') or '无标题'
        except Exception as e:
            print('  失败:', str(e)[:80])
            continue
        if title in {a['title'] for a in arts}:
            print('  已存在，跳过：%s' % title[:30])
            continue
        if slug_single:
            slug = slug_single
        elif slug_list and idx < len(slug_list):
            slug = slug_list[idx]
        else:
            slug = make_slug(title, existing)
        try:
            art = parse_article(url, slug)
        except Exception as e:
            print('  失败:', str(e)[:80])
            continue
        print('  标题: %s' % art['title'])
        print('  日期: %s | 图片: %d 张 | slug: %s' % (art['date'], art['images'], art['slug']))
        if dry:
            print('  预览正文前 200 字:', re.sub(r'\s+', ' ', art['markdown'])[:200])
            continue
        os.makedirs(MD_DIR, exist_ok=True)
        open(os.path.join(MD_DIR, slug + '.md'), 'w', encoding='utf-8').write(art['markdown'])
        arts.append({k: art[k] for k in ('slug', 'title', 'summary', 'date', 'hero')})
        existing.add(slug)
        added += 1

    if dry or not added:
        return

    # 按日期倒序，最新在前
    arts.sort(key=lambda a: a['date'], reverse=True)
    json.dump(arts, open(ARTICLES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n已入库 %d 篇，当前共 %d 篇' % (added, len(arts)))

    print('\n== 重新生成站点 ==')
    env = dict(os.environ, SITE_BASE=SITE, CLOUD_PROXY='1')
    subprocess.run([sys.executable, 'tools/build_static_site.py'], cwd=BASE, env=env, check=True)
    subprocess.run([sys.executable, 'tools/build_dist.py'], cwd=BASE, env=env, check=True)

    if deploy:
        token = os.environ.get('CLOUDFLARE_API_TOKEN')
        if not token:
            print('\n缺少 CLOUDFLARE_API_TOKEN，跳过部署')
        else:
            print('\n== 部署 Cloudflare Pages ==')
            subprocess.run(['./.cf/node_modules/.bin/wrangler', 'pages', 'deploy', 'dist',
                            '--project-name=caoben-guancha', '--branch=main', '--commit-dirty=true'],
                           cwd=BASE, env=dict(os.environ, CLOUDFLARE_API_TOKEN=token), check=True)
            print('\n== 推送 GitHub ==')
            subprocess.run(['git', 'add', '-A'], cwd=BASE, check=True)
            subprocess.run(['git', '-c', 'user.name=xl-echo', '-c', 'user.email=tangshilin@ztoec.com',
                            'commit', '-m', '新增文章 %d 篇' % added], cwd=BASE, check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE, check=True)
            print('\n== 重新推送 IndexNow ==')
            subprocess.run([sys.executable, 'tools/indexnow.py'], cwd=BASE, check=False)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
