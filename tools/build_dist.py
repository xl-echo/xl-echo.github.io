# -*- coding: utf-8 -*-
"""打包可独立部署的整站到 dist/（只含公开静态资源）。"""
import os
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(BASE, 'dist')

FILES = ['index.html', 'robots.txt', 'sitemap.xml', 'llms.txt', 'llms-full.txt', 'feed.xml', 'feed.json']
DIRS = ['article', 'md', 'images', 'js']


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    for f in FILES:
        src = os.path.join(BASE, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DIST, f))
            print('  +', f)
    for d in DIRS:
        src = os.path.join(BASE, d)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(DIST, d))
            n = sum(len(fs) for _, _, fs in os.walk(src))
            print('  + %s/ (%d 个文件)' % (d, n))
    # ---- Cloudflare Pages 专用配置 ----
    headers = '''/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin

/*.md
  Content-Type: text/markdown; charset=utf-8
  Cache-Control: public, max-age=3600

/llms.txt
  Content-Type: text/plain; charset=utf-8
  Cache-Control: public, max-age=3600

/llms-full.txt
  Content-Type: text/plain; charset=utf-8
  Cache-Control: public, max-age=3600

/robots.txt
  Content-Type: text/plain; charset=utf-8

/sitemap.xml
  Content-Type: application/xml; charset=utf-8

/*.html
  Cache-Control: no-cache

/images/*
  Cache-Control: public, max-age=2592000, immutable

/js/*
  Cache-Control: public, max-age=604800
'''
    open(os.path.join(DIST, '_headers'), 'w', encoding='utf-8', newline='').write(headers)
    print('  + _headers (Cloudflare 缓存与 MIME 策略)')

    notfound = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>页面不存在 · 草本生长观察</title>
<meta name="robots" content="noindex">
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#faf7f2;color:#2c2a26;font-family:'Noto Serif SC','Songti SC',serif;font-weight:300;line-height:1.9}
.box{max-width:420px;padding:2rem;text-align:center}
h1{font-size:1.4rem;font-weight:600;letter-spacing:.1em;margin:0 0 1rem}
p{color:#6b6660;font-size:.92rem;margin:0 0 1.6rem}
a{display:inline-block;padding:.55rem 1.5rem;background:#9c3a3a;color:#fff;
text-decoration:none;border-radius:.35rem;font-size:.88rem;letter-spacing:.1em}
</style>
</head>
<body>
<div class="box">
  <h1>这一页没有找到</h1>
  <p>可能是链接失效，或这篇文章已被移动。</p>
  <a href="/">回到文章索引</a>
</div>
</body>
</html>
'''
    open(os.path.join(DIST, '404.html'), 'w', encoding='utf-8', newline='').write(notfound)
    print('  + 404.html (自定义错误页)')

    # IndexNow 密钥文件（引擎校验站点归属）
    for f in os.listdir(BASE):
        if f.endswith('.txt') and len(f) == 36 and f.count('.') == 1:
            shutil.copy2(os.path.join(BASE, f), os.path.join(DIST, f))
            print('  + %s (IndexNow 密钥)' % f)
            break

    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DIST) for f in fs)
    print('dist/ 完成，共 %.1f MB' % (total / 1024 / 1024))


if __name__ == '__main__':
    main()
