# -*- coding: utf-8 -*-
"""IndexNow 主动推送：把 sitemap 里的全部 URL 推给 Bing / Yandex 等引擎。

不需要任何账号或密钥申请——只需站点根目录放一个 {key}.txt 证明站点归属。
用法：python tools/indexnow.py
"""
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINT = 'https://api.indexnow.org/indexnow'


def collect_urls():
    sitemap = os.path.join(BASE, 'sitemap.xml')
    xml = open(sitemap, encoding='utf-8').read()
    return re.findall(r'<loc>(.*?)</loc>', xml)


def main():
    cfg = json.load(open(os.path.join(BASE, 'tools', 'indexnow.json'), encoding='utf-8'))
    key, host = cfg['key'], cfg['host']
    urls = collect_urls()
    payload = {
        'host': host,
        'key': key,
        'keyLocation': 'https://%s/%s.txt' % (host, key),
        'urlList': urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
            body = r.read(200).decode('utf-8', 'replace')
        print('提交 %d 个 URL → HTTP %d %s' % (len(urls), code, body.strip()[:120]))
        if code in (200, 202):
            print('已受理（200/202 表示引擎已接收，将在其抓取周期内处理）')
        else:
            print('未被受理，检查 key 文件是否已发布到站点根目录')
    except urllib.error.HTTPError as e:
        print('提交失败 HTTP %d: %s' % (e.code, e.read(300).decode('utf-8', 'replace')))
    except Exception as e:
        print('提交异常:', e)


if __name__ == '__main__':
    main()
