# 部署到自己的服务器（Nginx）

整站是纯静态文件，不需要 Node、Java、数据库容器，任何装了 Nginx 的服务器都能跑。
云数据库（阅读量/评论/访客记录）仍走 WorkBuddy 托管服务，无需迁移数据。

---

## 一、为什么要迁

当前托管域名 `tcm-essays.app.workbuddy.host` 带**访问保护**：不带 `?sharecode=` 时，
所有路径（含 robots.txt / sitemap.xml）都返回 **403**。实测 Baiduspider、Googlebot、GPTBot
访问均为 403，搜索引擎与 AI 爬虫完全进不来，收录必然为 0。

迁到自有域名后，全站公开可抓取，收录与 AI 检索才真正成立。

---

## 二、准备

- 一台公网服务器（1 核 1G 足够，纯静态几乎不吃资源）
- 一个域名，解析 A 记录到服务器 IP
- 国内服务器需完成 **ICP 备案**（未备案 80/443 会被拦截）
- 服务器已装 Nginx（`nginx -v` 可查）

---

## 三、上传文件

本地执行（把 `dist/` 整个目录传上去）：

```bash
rsync -avz --delete ./dist/ root@你的服务器IP:/var/www/tcm-essays/
```

没有 rsync 就用 scp：

```bash
scp -r ./dist/* root@你的服务器IP:/var/www/tcm-essays/
```

服务器上确保目录存在且属主正确：

```bash
mkdir -p /var/www/tcm-essays
chown -R www-data:www-data /var/www/tcm-essays   # CentOS 用 nginx:nginx
```

---

## 四、配置 Nginx

把 `deploy/nginx.conf` 里的 `server_name` 改成你的域名，然后：

```bash
cp nginx.conf /etc/nginx/conf.d/tcm-essays.conf
nginx -t && systemctl reload nginx
```

配置文件已包含：UTF-8 编码、gzip 压缩、静态资源长缓存、HTML 不缓存（便于更新即时生效）、
`try_files` 兜底、安全响应头。

---

## 五、开启 HTTPS（强烈建议）

```bash
# Ubuntu/Debian
apt install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名

# CentOS
yum install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名
```

证书 90 天自动续期，certbot 会自己加定时任务。

---

## 六、改域名并重新生成（关键一步）

站内的 canonical、sitemap、llms.txt、md 镜像头部都写死了域名，换域名必须重新生成：

```bash
# 本地执行，把域名换成你的
SITE_BASE=https://你的域名 python tools/build_static_site.py
python tools/build_dist.py
rsync -avz --delete ./dist/ root@你的服务器IP:/var/www/tcm-essays/
```

也可以把域名固化到配置里，之后直接跑生成器即可：

```bash
python -c "import sys; sys.path.insert(0,'tools'); from site_config import set_site; set_site('https://你的域名')"
```

---

## 七、上线验收（必做）

在服务器或本地执行：

```bash
# 1. 免参数访问必须 200（这是本次迁移的核心目的）
curl -o /dev/null -w "%{http_code}\n" https://你的域名/
curl -o /dev/null -w "%{http_code}\n" https://你的域名/article/fangfeng.html
curl -o /dev/null -w "%{http_code}\n" https://你的域名/robots.txt
curl -o /dev/null -w "%{http_code}\n" https://你的域名/sitemap.xml

# 2. 模拟爬虫，同样必须 200
curl -o /dev/null -w "%{http_code}\n" -A "Baiduspider/2.0" https://你的域名/article/fangfeng.html
curl -o /dev/null -w "%{http_code}\n" -A "GPTBot/1.0" https://你的域名/llms.txt

# 3. 阅读量/评论仍可用（打开任一文章页，阅读数字应递增）
```

四项全 200，再去提交搜索引擎。

---

## 八、提交收录

| 平台 | 地址 | 操作 |
|---|---|---|
| 百度搜索资源平台 | ziyuan.baidu.com | 添加站点 → HTML 标签验证 → 提交 sitemap |
| Google Search Console | search.google.com/search-console | 添加资源 → 验证 → 提交 sitemap |
| Bing Webmaster | bing.com/webmasters | 添加站点 → 提交 sitemap |
| 神马/头条 | 各自站长平台 | 同上 |

验证用的 HTML 标签加到 `index.html` 的 `<head>` 里即可，我可以帮你加。

---

## 九、日常更新文章

现有文章的正文源在 `tools/markdown/*.md`，元数据在 `tools/articles.json`。

新增一篇：

1. 把正文写成 `tools/markdown/<slug>.md`（首行放 `# 标题`）
2. 在 `tools/articles.json` 追加一条（slug / title / summary / date / hero）
3. 图片放进 `images/`，命名 `<slug>-1.jpg` 递增
4. 重新生成并上传：

```bash
python tools/build_static_site.py && python tools/build_dist.py
rsync -avz --delete ./dist/ root@你的服务器IP:/var/www/tcm-essays/
```

sitemap、llms.txt、md 镜像会自动更新，无需手工维护。
