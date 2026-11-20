# -*- coding: utf-8 -*-
"""把 SPA 站点生成为多页静态站（SEO 友好）。

输入：当前 index.html（含 ARTICLES 数组与 markdown 内容块）
输出：
  index.html            首页（静态文章列表 + 搜索）
  article/<slug>.html   每篇文章独立页面（正文为真 HTML，爬虫可直接读取）
  sitemap.xml           站点地图
  robots.txt            爬虫规则
"""
import html as htmllib
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'index.html')
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from site_config import get_site
SITE = get_site()


def read_source():
    style = re.search(r'<style>([\s\S]*?)</style>', open(SRC, encoding='utf-8').read()).group(1)
    arts = json.load(open(os.path.join(BASE, 'tools', 'articles.json'), encoding='utf-8'))
    mds = {}
    for a in arts:
        fp = os.path.join(BASE, 'tools', 'markdown', a['slug'] + '.md')
        mds[a['slug']] = open(fp, encoding='utf-8').read()
    return style, arts, mds


def md_to_html(md):
    """把文章 markdown 转成 HTML（覆盖本项目用到的语法子集）。"""
    md = md.lstrip('\ufeff').strip()
    lines = md.split('\n')
    # 去掉首个一级标题（页面已单独展示标题）
    if lines and lines[0].startswith('# '):
        lines = lines[1:]
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        # 图片
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', line.strip())
        if m:
            alt = m.group(1) or '配图'
            url = m.group(2)
            if url.startswith('./'):
                url = '../' + url[2:]
            out.append('<img src="%s" alt="%s" loading="lazy">' % (url, htmllib.escape(alt)))
            i += 1
            continue
        # 标题
        if line.startswith('### '):
            out.append('<h3>%s</h3>' % inline(line[4:]))
            i += 1
            continue
        if line.startswith('## '):
            out.append('<h2>%s</h2>' % inline(line[3:]))
            i += 1
            continue
        # 引用（连续行合并）
        if line.startswith('> '):
            buf = []
            while i < n and lines[i].startswith('> '):
                buf.append(lines[i][2:])
                i += 1
            out.append('<blockquote>%s</blockquote>' % inline(' '.join(buf)))
            continue
        # 列表
        if line.startswith('- '):
            items = []
            while i < n and lines[i].startswith('- '):
                items.append('<li>%s</li>' % inline(lines[i][2:]))
                i += 1
            out.append('<ul>%s</ul>' % ''.join(items))
            continue
        # 段落（连续非空行合并）
        buf = []
        while i < n and lines[i].strip() and not re.match(r'^(#{2,3} |>\s|- |!\[)', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append('<p>%s</p>' % inline(' '.join(buf)))
    return '\n'.join(out)


def inline(text):
    t = htmllib.escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return t


COMMON_JS = r"""
<script>
const PUBLIC_CONFIG = {
  endpoint: 'https://tcm-essays.app.workbuddy.host',
  oauthRelayBaseUrl: 'https://www.workbuddy.cn/v2/as/genie-baas/oauth',
  publishableKey: 'wbpk_EIsoihXP3ZYjkKInTKBILH_TLGA16wfGCVb5UbnKijw7UymOM4vXoN5'
};
let cloud = null;
try {
  if (window.WorkBuddyCloud) {
    cloud = WorkBuddyCloud.createWorkBuddyCloud({
      endpoint: PUBLIC_CONFIG.endpoint,
      oauthRelayBaseUrl: PUBLIC_CONFIG.oauthRelayBaseUrl,
      publishableKey: PUBLIC_CONFIG.publishableKey
    });
  }
} catch (e) { console.warn('云服务初始化失败'); }

function $(sel) { return document.querySelector(sel); }
function showToast(msg) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}
function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}
function escapeHtml(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// 访客记录：zxinc 开源IP库(JSONP/区县级) 为主，ipip.net(市级) 为备
function geoZxinc() {
  return new Promise(function (resolve) {
    var cbName = '_zxinc_cb_' + Date.now();
    var script = document.createElement('script');
    var timer = setTimeout(function () { cleanup(); resolve(null); }, 4000);
    function cleanup() {
      clearTimeout(timer);
      try { delete window[cbName]; } catch (e) { window[cbName] = undefined; }
      if (script.parentNode) script.parentNode.removeChild(script);
    }
    window[cbName] = function (res) {
      cleanup();
      try {
        var c = res && res.data && res.data.country;
        if (!c || c.indexOf('–') < 0) { resolve(null); return; }
        var p = c.split('–');
        resolve({ country: p[0] || null, region: p[1] || null, city: p[2] || null, district: p[3] || null });
      } catch (e) { resolve(null); }
    };
    script.src = 'https://ip.zxinc.org/api.php?type=jsonp&callback=' + cbName;
    script.onerror = function () { cleanup(); resolve(null); };
    document.head.appendChild(script);
  });
}

function logVisit(page) {
  if (!cloud) return;
  var base = {
    page: page,
    referrer: document.referrer || null,
    user_agent: navigator.userAgent,
    screen_width: screen.width,
    screen_height: screen.height,
    language: navigator.language
  };
  geoZxinc().then(function (g) {
    if (g) { base.country_name = g.country; base.region = g.region; base.city = g.city; base.district = g.district; }
    return cloud.database.from('visitor_logs').insert(base);
  }).catch(function () {
    return fetch('https://myip.ipip.net/json', { signal: AbortSignal.timeout ? AbortSignal.timeout(4000) : undefined })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.ret === 'ok' && Array.isArray(res.data && res.data.location)) {
          var loc = res.data.location;
          base.country_name = loc[0] || null; base.region = loc[1] || null; base.city = loc[2] || null;
        }
        return cloud.database.from('visitor_logs').insert(base);
      })
      .catch(function () { return cloud.database.from('visitor_logs').insert(base); });
  }).then(function () {}).catch(function () {});
}

// 广告位
const AD_CONFIG = {
  enabled: true,
  tag: '公众号',
  title: '植物之象',
  desc: '每天一味本草，取象比类',
  url: ''
};
function renderAd() {
  const box = $('#ad-float');
  if (!box || !AD_CONFIG.enabled) { if (box) box.style.display = 'none'; return; }
  $('#ad-tag').textContent = AD_CONFIG.tag;
  $('#ad-title').textContent = AD_CONFIG.title;
  $('#ad-desc').textContent = AD_CONFIG.desc;
  const link = $('#ad-link');
  if (AD_CONFIG.url) { link.href = AD_CONFIG.url; } else { link.removeAttribute('href'); link.style.cursor = 'default'; }
  try { if (sessionStorage.getItem('ad_closed') === '1') box.style.display = 'none'; } catch (e) {}
  const closeBtn = $('#ad-close');
  if (closeBtn) closeBtn.addEventListener('click', () => {
    box.style.display = 'none';
    try { sessionStorage.setItem('ad_closed', '1'); } catch (e) {}
  });
}
</script>
"""

HEADER_TPL = """<header class="site-header">
  <div class="site-header-inner">
    <a class="site-title" href="{{HOME}}">
      <span class="seal">草本</span>
      <span>草本生长观察</span>
    </a>
    <div class="header-actions">
      <span class="site-subtitle">取象比类 · 以形察理</span>
      <div class="search-box">
        <svg class="search-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
        <input type="search" id="search-input" placeholder="搜索本草…" autocomplete="off">
      </div>
    </div>
  </div>
</header>"""

AD_TPL = """<div class="ad-float" id="ad-float">
  <button class="ad-close" id="ad-close" type="button" aria-label="关闭">×</button>
  <a id="ad-link" href="#" target="_blank" rel="noopener">
    <span class="ad-tag" id="ad-tag"></span>
    <strong class="ad-title" id="ad-title"></strong>
    <span class="ad-desc" id="ad-desc"></span>
  </a>
</div>
<div class="toast" id="toast"></div>"""

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%239c3a3a'/%3E%3Ctext x='32' y='45' font-size='38' text-anchor='middle' fill='%23ffffff' font-family='Songti SC, SimSun, serif' font-weight='600'%3E%E8%8D%89%3C/text%3E%3C/svg%3E"


def head(title, desc, canonical, keywords, og_image=None, jsonld=None, home='./', alt_md=None, extra_ld=None, js_base='./'):
    og_img = ('<meta property="og:image" content="%s">' % og_image) if og_image else ''
    ld = ('<script type="application/ld+json">%s</script>' % jsonld) if jsonld else ''
    if extra_ld:
        ld += ''.join('<script type="application/ld+json">%s</script>' % x for x in extra_ld)
    alt = ('<link rel="alternate" type="text/markdown" href="%s" title="Markdown 纯文本版">' % alt_md) if alt_md else ''
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESC}}">
<meta name="keywords" content="{{KEYWORDS}}">
<meta name="author" content="植物之象">
<link rel="canonical" href="{{CANONICAL}}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="草本生长观察">
<meta property="og:title" content="{{TITLE}}">
<meta property="og:description" content="{{DESC}}">
<meta property="og:url" content="{{CANONICAL}}">
{{OG_IMAGE}}
{{ALT_MD}}
<link rel="icon" href="{{FAVICON}}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@200;300;400;500;600;700&display=swap" rel="stylesheet">
<script src="{{JS_BASE}}js/workbuddy-cloud-sdk.js"></script>
<style>{{STYLE}}</style>
{{JSONLD}}
</head>""".replace('{{TITLE}}', htmllib.escape(title)).replace('{{DESC}}', htmllib.escape(desc)) \
        .replace('{{KEYWORDS}}', htmllib.escape(keywords)).replace('{{CANONICAL}}', canonical) \
        .replace('{{OG_IMAGE}}', og_img).replace('{{ALT_MD}}', alt).replace('{{FAVICON}}', FAVICON).replace('{{JS_BASE}}', js_base) \
        .replace('{{STYLE}}', '{{__STYLE__}}').replace('{{JSONLD}}', ld)


def build_article(a, md, style, prev_a, next_a):
    body_html = md_to_html(md)
    desc = re.sub(r'\*\*', '', a['summary'])[:120]
    herb = a['title'].split('：')[0].split('——')[0][:8]
    keywords = '%s,中药,本草,法象药理,植物之象,形态气机' % herb
    canonical = '%s/article/%s.html' % (SITE, a['slug'])
    hero_abs = ('%s/%s' % (SITE, a['hero'])) if a['hero'] else None
    jsonld = (
        '{"@context":"https://schema.org","@type":"Article",'
        '"headline":"%s","description":"%s","datePublished":"%s",'
        '"author":{"@type":"Person","name":"植物之象"},'
        '"publisher":{"@type":"Organization","name":"草本生长观察"},'
        '"mainEntityOfPage":"%s"}' % (
            a['title'].replace('"', '\\"'), desc.replace('"', '\\"'), a['date'], canonical)
    )
    related = []
    if prev_a:
        related.append('<a class="rel-item" href="%s.html"><span class="rel-label">上一篇</span>%s</a>' % (prev_a['slug'], prev_a['title']))
    if next_a:
        related.append('<a class="rel-item" href="%s.html"><span class="rel-label">下一篇</span>%s</a>' % (next_a['slug'], next_a['title']))

    breadcrumb = ('{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":['
                  '{"@type":"ListItem","position":1,"name":"文章索引","item":"%s/"},'
                  '{"@type":"ListItem","position":2,"name":"%s","item":"%s"}]}' % (
                      SITE, a['title'].replace('"', '\\"'), canonical))
    page = head(a['title'], desc, canonical, keywords, hero_abs, jsonld,
                home='../index.html', alt_md='../md/%s.md' % a['slug'], extra_ld=[breadcrumb], js_base='../')
    page += """
<body>
""" + HEADER_TPL.replace('{{HOME}}', '../index.html') + """
<main class="main page-article">
  <a class="back-link" href="../index.html">← 返回索引</a>
  {{HERO}}
  <div class="article-header">
    <div class="article-date">{{DATE}}</div>
    <h1 class="article-h1">{{H1}}</h1>
    <div class="article-stats"><span class="view-count">阅读 …</span></div>
  </div>
  <div class="article-body">
{{BODY}}
  </div>
  {{RELATED}}
  <section class="comments-section">
    <h3 class="comments-title">评论 <span class="comments-count" id="comments-count"></span></h3>
    <div class="comment-form">
      <textarea id="comment-content" placeholder="写下你的看法…" maxlength="500"></textarea>
      <button class="comment-submit" id="comment-submit">提交评论</button>
      <div class="comment-error" id="comment-error"></div>
    </div>
    <ul class="comment-list" id="comment-list"><li class="loading">加载中…</li></ul>
  </section>
</main>
<footer class="site-footer">
  草本生长观察 · 形态节律禀赋 → 气机偏性 → 功效
</footer>
""" + AD_TPL + COMMON_JS + """
<script>
const SLUG = '{{SLUG}}';
async function incrementAndShowViews() {
  const el = $('.view-count');
  if (!cloud) { if (el) el.textContent = '阅读量统计暂不可用'; return; }
  try {
    await cloud.database.rpc('increment_view', { slug_param: SLUG });
    const { data, error } = await cloud.database.from('article_views')
      .select('view_count').eq('article_slug', SLUG).maybeSingle();
    if (el && !error) el.textContent = '阅读 ' + (data ? data.view_count : 0);
  } catch (e) { if (el) el.textContent = '阅读 …'; }
}
async function loadComments() {
  const list = $('#comment-list');
  if (!list) return;
  if (!cloud) { list.innerHTML = '<li class="comment-empty">评论功能暂不可用</li>'; return; }
  try {
    const { data, error } = await cloud.database.from('comments')
      .select('id, content, created_at').eq('article_slug', SLUG)
      .order('created_at', { ascending: false }).limit(50);
    if (error) throw error;
    renderComments(data || []);
  } catch (e) { list.innerHTML = '<li class="comment-empty">评论加载失败，请稍后重试</li>'; }
}
function renderComments(comments) {
  const list = $('#comment-list');
  const countEl = $('#comments-count');
  if (countEl) countEl.textContent = '(' + comments.length + ')';
  if (!list) return;
  if (!comments.length) { list.innerHTML = '<li class="comment-empty">尚无评论，期待你的见解</li>'; return; }
  list.innerHTML = comments.map(c =>
    '<li class="comment-item"><div class="comment-head"><span class="comment-nickname">匿名读者</span>' +
    '<span class="comment-time">' + formatTime(c.created_at) + '</span></div>' +
    '<div class="comment-content">' + escapeHtml(c.content) + '</div></li>'
  ).join('');
}
async function submitComment() {
  const contentEl = $('#comment-content');
  const errorEl = $('#comment-error');
  const btn = $('#comment-submit');
  const content = contentEl.value.trim();
  errorEl.textContent = '';
  if (!content) { errorEl.textContent = '请输入评论内容'; return; }
  if (!cloud) { errorEl.textContent = '评论服务暂不可用'; return; }
  btn.disabled = true; btn.textContent = '提交中…';
  try {
    const { error } = await cloud.database.from('comments').insert({ article_slug: SLUG, content: content });
    if (error) throw error;
    contentEl.value = '';
    showToast('评论已发布');
    await loadComments();
  } catch (e) { errorEl.textContent = '提交失败，请稍后重试'; }
  finally { btn.disabled = false; btn.textContent = '提交评论'; }
}
document.addEventListener('DOMContentLoaded', () => {
  renderAd();
  logVisit('/article/' + SLUG);
  incrementAndShowViews();
  loadComments();
  $('#comment-submit').addEventListener('click', submitComment);
  // 顶栏搜索：跳回首页并带关键词
  const si = $('#search-input');
  if (si) si.addEventListener('keydown', e => {
    if (e.key === 'Enter') { location.href = '../index.html?q=' + encodeURIComponent(si.value.trim()); }
  });
});
</script>
</body>
</html>"""
    hero_tpl = ('<img class="article-hero" src="../%s" alt="%s">' % (a['hero'], htmllib.escape(a['title']))) if a['hero'] else ''
    page = page.replace('{{HERO}}', hero_tpl).replace('{{DATE}}', a['date']) \
        .replace('{{H1}}', htmllib.escape(a['title'])).replace('{{BODY}}', body_html) \
        .replace('{{SLUG}}', a['slug'])
    related_html = ('<nav class="related-nav">%s</nav>' % ''.join(related)) if related else ''
    page = page.replace('{{RELATED}}', related_html)
    return page


def build_home(arts, style):
    items = []
    for a in arts:
        items.append("""    <li class="article-item">
      <a class="article-link" href="article/{{SLUG}}.html" data-search="{{HAY}}">
        <h2 class="article-title">{{TITLE}}</h2>
        <p class="article-summary">{{SUMMARY}}</p>
        <div class="article-meta">
          <span>{{DATE}}</span>
          <span class="view-count" data-slug="{{SLUG}}">阅读 …</span>
        </div>
      </a>
    </li>""".replace('{{SLUG}}', a['slug'])
                   .replace('{{TITLE}}', htmllib.escape(a['title']))
                   .replace('{{SUMMARY}}', htmllib.escape(a['summary']))
                   .replace('{{DATE}}', a['date'])
                   .replace('{{HAY}}', htmllib.escape(a['title'] + ' ' + a['summary'])))
    desc = '草本生长观察：以形态、节律、禀赋推演气机偏性与功效的本草笔记，收录虎杖、防风、龙眼、车前、补骨脂、荸荠、枸杞、板栗、芭蕉心等植物观察文章。'
    jsonld = ('{"@context":"https://schema.org","@type":"WebSite","name":"草本生长观察",'
              '"url":"%s/","description":"%s","inLanguage":"zh-CN",'
              '"potentialAction":{"@type":"SearchAction","target":{"@type":"EntryPoint",'
              '"urlTemplate":"%s/index.html?q={search_term_string}"},"query-input":"required name=search_term_string"},'
              '"publisher":{"@type":"Organization","name":"草本生长观察"}}'
              % (SITE, desc, SITE))
    page = head('草本生长观察 · 本草形态与气机笔记', desc, SITE + '/',
                '本草,中药,法象药理,植物之象,虎杖,防风,龙眼,车前,补骨脂,荸荠,枸杞,板栗,芭蕉心',
                None, jsonld, js_base='./')
    page += """
<body>
""" + HEADER_TPL.replace('{{HOME}}', './index.html') + """
<main class="main page-home">
  <div class="search-meta" id="search-meta"></div>
  <div class="page-label">文章索引</div>
  <ul class="article-list" id="article-list">
{{ITEMS}}
  </ul>
  <div class="search-empty" id="search-empty" style="display:none">没有找到相关文章，换个关键词试试</div>
</main>
<footer class="site-footer">
  草本生长观察 · 形态节律禀赋 → 气机偏性 → 功效
</footer>
""" + AD_TPL + COMMON_JS + """
<script>
// 旧版 hash 链接兼容：#/article/xxx → article/xxx.html
(function () {
  var m = location.hash.match(/^#\\/article\\/(.+)$/);
  if (m) location.replace('article/' + m[1] + '.html');
})();

// 搜索过滤（静态列表）
function applySearch() {
  const input = $('#search-input');
  const kw = (input ? input.value : '').trim();
  const items = document.querySelectorAll('.article-item');
  let visible = 0;
  items.forEach(el => {
    const hay = (el.querySelector('.article-link').getAttribute('data-search') || '').toLowerCase();
    const hit = !kw || hay.indexOf(kw.toLowerCase()) >= 0;
    el.style.display = hit ? '' : 'none';
    if (hit) visible++;
  });
  const meta = $('#search-meta');
  if (kw) { meta.textContent = '找到 ' + visible + ' 篇相关文章'; meta.style.display = 'block'; }
  else { meta.style.display = 'none'; }
  $('#search-empty').style.display = (kw && visible === 0) ? 'block' : 'none';
}
// 阅读量批量回填
async function fillViews() {
  if (!cloud) return;
  try {
    const { data, error } = await cloud.database.from('article_views').select('article_slug, view_count');
    if (error || !data) return;
    const map = {};
    data.forEach(r => { map[r.article_slug] = r.view_count; });
    document.querySelectorAll('.view-count').forEach(el => {
      const c = map[el.dataset.slug] || 0;
      el.textContent = '阅读 ' + c;
    });
  } catch (e) {}
}
document.addEventListener('DOMContentLoaded', () => {
  renderAd();
  logVisit('home');
  fillViews();
  const si = $('#search-input');
  const q = new URLSearchParams(location.search).get('q');
  if (q && si) { si.value = q; }
  applySearch();
  if (si) si.addEventListener('input', applySearch);
});
</script>
</body>
</html>"""
    page = page.replace('{{ITEMS}}', '\n'.join(items))
    return page


def main():
    style, arts, mds = read_source()
    os.makedirs(os.path.join(BASE, 'article'), exist_ok=True)
    # 文章页（上一篇/下一篇按日期倒序相邻）
    for idx, a in enumerate(arts):
        prev_a = arts[idx - 1] if idx > 0 else None
        next_a = arts[idx + 1] if idx + 1 < len(arts) else None
        html = build_article(a, mds[a['slug']], style, prev_a, next_a)
        html = html.replace('{{__STYLE__}}', style)
        open(os.path.join(BASE, 'article', a['slug'] + '.html'), 'w', encoding='utf-8', newline='').write(html)
        print('生成 article/%s.html' % a['slug'])
    # 首页
    home = build_home(arts, style).replace('{{__STYLE__}}', style)
    open(SRC, 'w', encoding='utf-8', newline='').write(home)
    print('生成 index.html')
    # sitemap
    urls = ['  <url><loc>%s/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>' % SITE]
    for a in arts:
        urls.append('  <url><loc>%s/article/%s.html</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>'
                    % (SITE, a['slug'], a['date']))
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + '\n'.join(urls) + '\n</urlset>\n')
    open(os.path.join(BASE, 'sitemap.xml'), 'w', encoding='utf-8', newline='').write(sitemap)
    print('生成 sitemap.xml')
    # ---- 面向 AI 的索引与纯文本镜像 ----
    md_dir = os.path.join(BASE, 'md')
    os.makedirs(md_dir, exist_ok=True)
    for a in arts:
        md = mds[a['slug']].strip()
        head_md = ('# %s\n\n> 来源：草本生长观察 · %s\n> 原文：%s/article/%s.html\n> 发布日期：%s\n\n---\n\n'
                   % (a['title'], a['date'], SITE, a['slug'], a['date']))
        open(os.path.join(md_dir, a['slug'] + '.md'), 'w', encoding='utf-8', newline='').write(head_md + md + '\n')
    print('生成 md/ 纯文本镜像 %d 篇' % len(arts))

    llms = ['# 草本生长观察', '',
            '> 以「形态 → 气机 → 功效」的方法论记录本草植物的观察笔记，每篇聚焦一味植物，',
            '> 从根、茎、叶、花、果的形态与生长节律推演其气机偏性。', '',
            '本站为纯文本可读的静态站点，所有正文均可直接抓取，无需执行 JavaScript。',
            '每篇文章同时提供 Markdown 纯文本版（见各条目 md 链接），便于模型直接引用。', '',
            '## 文章']
    for a in arts:
        raw = re.sub(r'\s+', '', re.sub(r'\*\*', '', a['summary']))
        one = raw[:60]
        cut = max(one.rfind('。'), one.rfind('；'), one.rfind('，'), one.rfind('—'))
        if cut >= 20:
            one = one[:cut + 1]
        if len(raw) > len(one):
            one = one.rstrip('，；—') + '……'
        llms.append('- [%s](%s/article/%s.html) — %s（%s）｜纯文本：%s/md/%s.md'
                    % (a['title'], SITE, a['slug'], one, a['date'], SITE, a['slug']))
    llms += ['', '## 说明',
             '- 内容性质：传统文化与植物形态观察笔记，不构成诊疗建议',
             '- 站点地图：%s/sitemap.xml' % SITE,
             '- 全文合集：%s/llms-full.txt' % SITE, '']
    open(os.path.join(BASE, 'llms.txt'), 'w', encoding='utf-8', newline='').write('\n'.join(llms))
    print('生成 llms.txt')

    full = ['# 草本生长观察 — 全文合集', '',
            '> 全部文章纯文本合集，供 AI 检索与引用。原文地址见每篇开头。', '']
    for a in arts:
        full.append('=' * 60)
        full.append('## %s' % a['title'])
        full.append('原文：%s/article/%s.html ｜ 发布日期：%s' % (SITE, a['slug'], a['date']))
        full.append('')
        full.append(mds[a['slug']].strip())
        full.append('')
    open(os.path.join(BASE, 'llms-full.txt'), 'w', encoding='utf-8', newline='').write('\n'.join(full))
    print('生成 llms-full.txt')

    # ---- robots：显式放行主流 AI 爬虫 + 声明站点地图 ----
    ai_bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web',
               'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended',
               'CCBot', 'Bytespider', 'meta-externalagent', 'Amazonbot', 'YouBot',
               'cohere-ai', 'Diffbot', 'Timpibot', 'PanguBot', 'Baiduspider', 'Sogou web spider']
    lines = ['# 草本生长观察 — 允许搜索引擎与 AI 助手抓取并引用本站内容', '',
             'User-agent: *', 'Allow: /', '',
             '# AI 爬虫显式放行（便于大模型检索与答案引用）']
    for b in ai_bots:
        lines += ['User-agent: %s' % b, 'Allow: /', '']
    lines += ['# 站点索引',
              'Sitemap: %s/sitemap.xml' % SITE,
              '# AI 友好索引（llms.txt 约定）：%s/llms.txt' % SITE, '']
    open(os.path.join(BASE, 'robots.txt'), 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('生成 robots.txt（含 AI 爬虫规则）')

    # ---- 防回归自检：所有页面必须引用云 SDK（缺失会导致阅读量/评论全失效）----
    missing = []
    pages = [SRC] + [os.path.join(BASE, 'article', a['slug'] + '.html') for a in arts]
    for fp in pages:
        if 'workbuddy-cloud-sdk.js' not in open(fp, encoding='utf-8').read():
            missing.append(os.path.basename(fp))
    if missing:
        raise SystemExit('构建失败：以下页面缺少云 SDK 引用 -> %s' % ', '.join(missing))
    print('自检通过：全部页面已引用云 SDK')


if __name__ == '__main__':
    main()
