#!/usr/bin/env bash
# 部署脚本使用说明：
#   1. 改下面三行配置
#   2. bash deploy.sh
set -euo pipefail

SERVER="root@你的服务器IP"          # 例：root@1.2.3.4
REMOTE_DIR="/var/www/tcm-essays"
SITE_URL="https://你的域名"          # 例：https://caoben.example.com

echo "==> 1/3 按域名重新生成站点"
SITE_BASE="$SITE_URL" python tools/build_static_site.py
python tools/build_dist.py

echo "==> 2/3 上传到服务器"
rsync -avz --delete ./dist/ "$SERVER:$REMOTE_DIR/"

echo "==> 3/3 线上验收（应全部 200）"
for p in "" "article/fangfeng.html" "robots.txt" "sitemap.xml" "llms.txt"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$SITE_URL/$p")
  echo "  /$p → $code"
done
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -A "Baiduspider/2.0" "$SITE_URL/article/fangfeng.html")
echo "  Baiduspider UA → $code"

echo "完成。若全部 200，即可去百度/Google 提交 sitemap。"
