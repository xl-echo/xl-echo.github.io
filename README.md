# 草本生长观察

以「形态 → 气机 → 功效」的方法论记录本草植物的观察笔记。纯静态站点，无后端依赖（阅读量/评论走托管云数据库）。

## 目录结构

```
index.html            首页（静态文章列表 + 顶栏搜索）
article/*.html        9 篇文章页（服务端 HTML，爬虫可直接读取）
md/*.md               每篇文章的 Markdown 纯文本镜像（供 AI 抓取）
images/               公众号原文配图
js/                   云 SDK（自托管，避免 CDN 不稳定）
tools/
  build_static_site.py  内容生成器（文章页 + 首页 + sitemap + llms.txt + md 镜像）
  build_dist.py         部署包构建（dist/ + _headers + 404.html）
  site_config.py        站点域名配置（canonical/sitemap 等统一由此生成）
  articles.json         文章元数据
  markdown/             文章正文源（新增文章写这里）
deploy/               部署配置与脚本（Cloudflare Pages / Nginx）
```

## 重新生成站点

```bash
python tools/build_static_site.py   # 生成页面与 SEO/AI 索引文件
python tools/build_dist.py          # 构建可部署目录 dist/
```

换域名时：

```bash
SITE_BASE=https://你的域名 python tools/build_static_site.py && python tools/build_dist.py
```

## 新增一篇文章

1. 正文写入 `tools/markdown/<slug>.md`，首行为 `# 标题`
2. 在 `tools/articles.json` 追加一条（`slug` / `title` / `summary` / `date` / `hero`）
3. 图片放入 `images/`，命名 `<slug>-1.jpg` 递增
4. 重新执行上面的生成命令

`sitemap.xml`、`llms.txt`、Markdown 镜像、上下篇导航都会自动更新。

## 部署

- **Cloudflare Pages（免费）**：见 `deploy/cloudflare.md`
- **自有服务器 Nginx**：见 `deploy/README.md`

## 可发现性

- 传统 SEO：独立文章页、canonical、Open Graph、Article / BreadcrumbList / WebSite 结构化数据、`sitemap.xml`
- AI 检索：`llms.txt` 站点索引、`llms-full.txt` 全文合集、每篇 `md/` 纯文本镜像、`robots.txt` 显式放行 20 个 AI 爬虫 UA

## 说明

站内文章为传统文化与植物形态观察笔记，不构成诊疗建议。
