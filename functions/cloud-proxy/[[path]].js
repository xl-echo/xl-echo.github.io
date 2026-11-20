// Cloudflare Pages Function：云数据库同源代理
// 作用：浏览器请求本站 /cloud-proxy/.cloud/... → 服务端带正确 Origin 转发到云环境
// 原因：云环境只接受应用保留域名的 Origin，跨域请求会被浏览器 CORS 拦截
const UPSTREAM = 'https://tcm-essays.app.workbuddy.host';
const ALLOWED_ORIGIN = 'https://tcm-essays.app.workbuddy.host';

function corsHeaders(request) {
  const origin = request.headers.get('Origin') || '*';
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': request.headers.get('Access-Control-Request-Headers') || 'apikey,authorization,content-type,prefer,accept-profile,content-profile,x-client-info',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

export async function onRequest(context) {
  const { request } = context;

  // 预检请求直接放行（浏览器跨域调用本站代理时）
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(request) });
  }
  const url = new URL(request.url);

  // /cloud-proxy/.cloud/database/rest/xxx → /.cloud/database/rest/xxx
  const path = url.pathname.replace(/^\/cloud-proxy/, '');
  const target = UPSTREAM + path + url.search;

  const headers = new Headers(request.headers);
  headers.set('Origin', ALLOWED_ORIGIN);
  headers.set('Referer', ALLOWED_ORIGIN + '/');
  headers.delete('host');
  headers.delete('cf-connecting-ip');
  headers.delete('cf-ipcountry');
  headers.delete('cf-ray');
  headers.delete('cf-visitor');
  headers.delete('x-forwarded-proto');

  const init = { method: request.method, headers, redirect: 'manual' };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body;
  }

  let resp;
  try {
    resp = await fetch(target, init);
  } catch (e) {
    return new Response(JSON.stringify({ error: 'upstream_unreachable', detail: String(e) }), {
      status: 502,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }

  const out = new Headers(resp.headers);
  out.delete('content-encoding');
  out.delete('content-length');
  out.delete('transfer-encoding');
  out.delete('access-control-allow-origin');
  const extra = corsHeaders(request);
  for (const k in extra) out.set(k, extra[k]);
  return new Response(resp.body, { status: resp.status, headers: out });
}
