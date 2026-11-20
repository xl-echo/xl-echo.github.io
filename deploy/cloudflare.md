# 部署到 Cloudflare Pages（免费，¥0）

整站是纯静态文件，Cloudflare Pages 免费版提供 **无限带宽**、自动 HTTPS、全球 CDN，
无需服务器、无需备案、无需信用卡。

云数据库（阅读量/评论/访客记录）继续走 WorkBuddy 托管服务，已验证跨域名可用，不受影响。

---

## 一、注册并创建项目

1. 打开 https://dash.cloudflare.com/sign-up ，用邮箱注册（免费）
2. 登录后左侧菜单 → **Workers & Pages**
3. 点 **Create** → 选 **Pages** 标签 → **Upload assets**（拖拽上传，不用连 Git）
4. 项目名填一个英文短名，例如 `caoben-guancha`
   - 这会决定你的访问地址：`https://caoben-guancha.pages.dev`
   - 名字一旦确定不能改，想好再填
5. 先随便传个空目录或直接点下一步，项目创建后会得到预览地址

> 也可以先创建项目、后传文件；上传入口在同一页面的 **Create new deployment**。

---

## 二、按你的域名重新生成（关键一步）

站内的 canonical、sitemap、llms.txt 都写着域名，必须按最终地址重新生成一次。
把下面的域名换成你实际的项目地址：

```bash
bash deploy/cloudflare.sh https://caoben-guancha.pages.dev
```

脚本会：
1. 按新域名重新生成全部页面与 SEO 文件
2. 构建 `dist/` 上传目录（含 `_headers` 缓存策略、`404.html`）
3. 打包 `tcm-essays-site.zip`

---

## 三、上传

**方式 A：网页拖拽（推荐，最简单）**

1. 回到 Cloudflare 项目页 → **Create new deployment**
2. 把 `dist` 文件夹整个拖进上传区域
3. 等 10~30 秒，部署完成，访问 `https://项目名.pages.dev` 验证

**方式 B：命令行（Wrangler，适合以后频繁更新）**

```bash
npm install -g wrangler          # 只需装一次
wrangler login                   # 浏览器授权
cd dist && wrangler pages deploy . --project-name=caoben-guancha
```

以后每次更新文章，只需重跑 `build_static_site.py` + `build_dist.py`，再执行上面最后一条命令。

---

## 四、验收（必须做）

```bash
bash deploy/verify.sh https://caoben-guancha.pages.dev
```

脚本会检查 11 项：首页、文章页、robots、sitemap、llms.txt、md 镜像，
以及 Baiduspider / Googlebot / GPTBot / ClaudeBot / PerplexityBot 五种真实爬虫 UA。

**全部 ✓ 才算成功**。这一步与之前托管域名最大的区别就是：不会再出现 403。

---

## 五、绑定自己的域名（可选，但仍免费）

`*.pages.dev` 在中国大陆访问偶尔不稳，绑定自有域名后体验更好：

1. Cloudflare 项目 → **Custom domains** → **Set up a custom domain**
2. 输入你的域名（如 `caoben.example.com`），按提示在域名服务商处加一条 CNAME
3. 证书自动签发，无需申请
4. 绑定后重新生成一次（换域名必须重跑）：
   ```bash
   bash deploy/cloudflare.sh https://caoben.example.com
   ```
   然后重新拖拽上传 `dist`。

> 用海外域名无需备案。若要换成国内服务器（访问更快、百度收录更友好），
> 参见 `deploy/README.md` 的 Nginx 方案，届时需要 ICP 备案。

---

## 六、提交收录

部署验收通过后，立即提交（sitemap 地址统一填 `https://你的域名/sitemap.xml`）：

| 平台 | 地址 |
|---|---|
| 百度搜索资源平台 | https://ziyuan.baidu.com |
| Google Search Console | https://search.google.com/search-console |
| Bing Webmaster | https://www.bing.com/webmasters |

**百度验证方式**：选「HTML 标签验证」，把百度给的那行 `<meta name="baidu-site-verification" content="xxx" />`
发我，我加到所有页面的 `<head>` 里再重新部署。

**AI 侧无需提交**：`llms.txt`、`robots.txt`（已放行 20 个 AI 爬虫 UA）、
纯文本镜像都已就位，模型抓取到即可用。

---

## 七、日常更新文章

```bash
# 1. 新文章正文放 tools/markdown/<slug>.md，元数据追加到 tools/articles.json
# 2. 图片放 images/，命名 <slug>-1.jpg 递增
# 3. 重新生成并上传
python tools/build_static_site.py && python tools/build_dist.py
cd dist && wrangler pages deploy . --project-name=caoben-guancha
```

sitemap、llms.txt、md 镜像、上一篇/下一篇导航都会自动更新。

---

## 附：本次已做的 Cloudflare 适配

| 文件 | 作用 |
|---|---|
| `_headers` | 缓存策略（图片 30 天、HTML 不缓存）+ 安全响应头 + `.md` 的正确 MIME 类型 |
| `404.html` | 自定义错误页，风格与站点一致，并带返回索引入口 |
| `_redirects`（未启用） | 如将来改过 URL 结构，可在这里配 301 跳转 |
