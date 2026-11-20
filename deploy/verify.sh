#!/usr/bin/env bash
# 上线验收：检查公开可访问性与爬虫抓取权限
# 用法：bash deploy/verify.sh https://你的域名
set -uo pipefail
SITE="${1:?用法: bash deploy/verify.sh https://你的域名}"
SITE="${SITE%/}"
PASS=0; FAIL=0

check() { # $1=描述 $2=期望 $3...=curl参数
  local desc="$1" expect="$2"; shift 2
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$@")
  if [ "$code" = "$expect" ]; then
    printf "  ✓ %-42s %s\n" "$desc" "$code"; PASS=$((PASS+1))
  else
    printf "  ✗ %-42s 期望%s实际%s\n" "$desc" "$expect" "$code"; FAIL=$((FAIL+1))
  fi
}

echo "== 基础可访问性 =="
check "首页"                     200 "$SITE/"
check "文章页"                   200 "$SITE/article/fangfeng.html"
check "robots.txt"               200 "$SITE/robots.txt"
check "sitemap.xml"              200 "$SITE/sitemap.xml"
check "llms.txt（AI 索引）"      200 "$SITE/llms.txt"
check "Markdown 镜像"            200 "$SITE/md/fangfeng.md"

echo "== 搜索引擎爬虫 =="
check "Baiduspider"              200 -A "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)" "$SITE/article/fangfeng.html"
check "Googlebot"                200 -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" "$SITE/article/fangfeng.html"

echo "== AI 爬虫 =="
check "GPTBot"                   200 -A "Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)" "$SITE/llms.txt"
check "ClaudeBot"                200 -A "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)" "$SITE/article/fangfeng.html"
check "PerplexityBot"            200 -A "Mozilla/5.0 (compatible; PerplexityBot/1.0)" "$SITE/article/fangfeng.html"

echo
echo "通过 $PASS 项，失败 $FAIL 项"
if [ "$FAIL" -eq 0 ]; then
  echo "全部通过 → 可以去提交 sitemap 了"
else
  echo "存在失败项 → 先排查再提交，否则收录会受影响"
fi
