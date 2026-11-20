# 提交收录：只剩最后两步

站点已经上线并通过爬虫验证，现在只差"告诉搜索引擎来抓"。

**地址**
- 网站：https://xl-echo.github.io
- 站点地图：https://xl-echo.github.io/sitemap.xml

---

## 动作一：把验证码发我（10 秒）

三个平台都可以选「HTML 标签验证」，页面会给你一行类似这样的代码：

```html
<meta name="baidu-site-verification" content="codeva-XXXXXXXXXX" />
```

你只需要把 `content="..."` 里面的那串字符复制给我，例如：

> 百度：codeva-AbCdEf1234
> Google：AbCdEf1234567890

我收到后执行一条命令，验证标签会自动加到全站每一页，然后推送 GitHub，你回平台点「完成验证」即可。

**为什么必须你点这一步**：验证标签的获取需要登录你的站长账号，我进不去。

---

## 动作二：提交站点地图（各 30 秒）

验证通过后，在平台里找到「站点地图 / Sitemap」入口，填入：

```
sitemap.xml
```

（多数平台已自动读取，只需确认提交。）

| 平台 | 入口 |
|---|---|
| 百度搜索资源平台 | https://ziyuan.baidu.com → 资源提交 → 普通收录 → sitemap |
| Google Search Console | https://search.google.com/search-console → 站点地图 |
| Bing Webmaster | https://www.bing.com/webmasters → Sitemap |

---

## 提交后会发生什么

| 平台 | 首次收录预期 |
|---|---|
| Google | 3 天 ~ 2 周开始出现 |
| Bing | 1 ~ 4 周 |
| 百度 | 2 周 ~ 2 个月（`github.io` 域名权重低，会慢一些） |

前两周只收录首页是正常现象，文章页会随权重积累逐步放出。

---

## 想更快？两个可选动作

**1. 绑自有域名（效果最明显）**

`github.io` 在国内百度权重低、访问偶尔超时（实测约 10% 请求 30 秒超时）。
绑定自有域名后：访问稳定、百度权重提升、品牌归属清晰。

做法：买个域名（约 30–60 元/年）→ GitHub 仓库 Settings → Pages → Custom domain 填入 →
域名商处加一条 CNAME 指向 `xl-echo.github.io` → 我重跑生成命令切换 canonical 并推送。

**2. 公众号引流（权重提升最快）**

百度对"被大量真实用户访问和引用"的站点给权重。你的公众号是现成流量入口：
每篇文章末尾加一句"完整图文见 xl-echo.github.io"，比任何技术手段都有效。

---

## 日常维护（无需人工）

新增文章后执行：

```bash
python tools/build_static_site.py && git add -A && git commit -m "新增：xxx" && git push
```

GitHub Pages 会在 1 分钟内自动重新部署，sitemap、llms.txt、md 镜像同步更新。
