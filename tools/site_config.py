# -*- coding: utf-8 -*-
"""站点域名配置：换域名后重跑生成器即可全部更新（canonical/sitemap/llms/md 头部）。"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, 'tools', 'site.json')
DEFAULT_SITE = 'https://tcm-essays.app.workbuddy.host'


def get_site():
    # 优先级：环境变量 > site.json > 默认托管域名
    env = os.environ.get('SITE_BASE', '').strip().rstrip('/')
    if env:
        return env
    if os.path.exists(CFG):
        try:
            return json.load(open(CFG, encoding='utf-8'))['site'].rstrip('/')
        except Exception:
            pass
    return DEFAULT_SITE


def set_site(url):
    url = url.strip().rstrip('/')
    json.dump({'site': url}, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return url
