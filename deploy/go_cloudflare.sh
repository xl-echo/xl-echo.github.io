#!/usr/bin/env bash
# 用 Cloudflare API Token 一键部署到 Pages
# 用法： CLOUDFLARE_API_TOKEN=xxx bash deploy/go_cloudflare.sh 项目名 [自定义域名]
#   projectname 建议英文短名，如 caoben-guancha
set -euo pipefail

PROJECT="${1:?用法: CLOUDFLARE_API_TOKEN=xxx bash deploy/go_cloudflare.sh 项目名 [域名]}"
CUSTOM_DOMAIN="${2:-}"
: "${CLOUDFLARE_API_TOKEN:?缺少 CLOUDFLARE_API_TOKEN 环境变量}"

WRANGLER="./.cf/node_modules/.bin/wrangler"
[ -x "$WRANGLER" ] || { echo "缺少 wrangler，请先运行：npm install --no-save wrangler@latest --prefix ./.cf"; exit 1; }

echo "==> 1/5 校验令牌"
if ! $WRANGLER whoami >/tmp/whoami.txt 2>&1; then
  echo "令牌无效或无权限："; cat /tmp/whoami.txt; exit 1
fi
grep -E "Account|Email|accounts" /tmp/whoami.txt | head -5 || cat /tmp/whoami.txt

echo "==> 2/5 创建/确认 Pages 项目：$PROJECT"
$WRANGLER pages project create "$PROJECT" --production-branch=main 2>&1 | grep -vE "^$" | tail -3 || echo "(项目已存在，继续)"

echo "==> 3/5 按最终域名重新生成站点"
if [ -n "$CUSTOM_DOMAIN" ]; then
  SITE_BASE="https://$CUSTOM_DOMAIN" python tools/build_static_site.py | tail -2
else
  SITE_BASE="https://$PROJECT.pages.dev" python tools/build_static_site.py | tail -2
fi
python tools/build_dist.py | tail -3

echo "==> 4/5 上传部署"
DEPLOY_LOG=$(mktemp)
$WRANGLER pages deploy dist --project-name="$PROJECT" --branch=main --commit-dirty=true 2>&1 | tee "$DEPLOY_LOG" | tail -6

URL=$(grep -oE 'https://[a-z0-9-]+\.pages\.dev' "$DEPLOY_LOG" | head -1 || true)
echo
if [ -n "$URL" ]; then
  echo "部署地址：$URL"
  echo "==> 5/5 自动验收"
  bash deploy/verify.sh "$URL" || true
else
  echo "未从输出中解析到地址，请手动打开 Cloudflare 控制台确认。"
fi
rm -f "$DEPLOY_LOG" /tmp/whoami.txt
