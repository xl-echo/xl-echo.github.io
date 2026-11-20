#!/usr/bin/env bash
# Cloudflare Pages 构建脚本
# 用法： bash deploy/cloudflare.sh https://你的项目名.pages.dev
# 例：   bash deploy/cloudflare.sh https://caoben-guancha.pages.dev
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "用法：bash deploy/cloudflare.sh https://你的项目名.pages.dev"
  echo "（项目名就是你在 Cloudflare 创建 Pages 项目时填的名字）"
  exit 1
fi

SITE="$1"
echo "==> 站点域名：$SITE"

echo "==> 1/3 按新域名重新生成（canonical / sitemap / llms.txt / md 镜像）"
SITE_BASE="$SITE" python tools/build_static_site.py | tail -3

echo "==> 2/3 构建上传目录 dist/"
python tools/build_dist.py

echo "==> 3/3 打包上传用的 zip"
python - <<'PY'
import shutil, os
shutil.make_archive('tcm-essays-site', 'zip', '.', 'dist')
print('tcm-essays-site.zip %.2f MB' % (os.path.getsize('tcm-essays-site.zip') / 1024 / 1024))
PY

echo
echo "完成。接下来："
echo "  1) 打开 https://dash.cloudflare.com → Workers & Pages → 你的项目"
echo "  2) Create new deployment → 拖入 dist 目录（或上传 tcm-essays-site.zip 解压后的内容）"
echo "  3) 部署完成后执行验收：bash deploy/verify.sh $SITE"
