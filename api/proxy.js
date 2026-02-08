/**
 * Vercel Edge Function — API CORS 代理
 *
 * 接收前端发来的 API 请求，转发到目标服务器并返回响应。
 * 用于绕过浏览器 CORS 限制，API Key 仅经过用户自己的 Vercel 服务。
 *
 * 用法: GET/POST /api/proxy?url=<encodeURIComponent(targetUrl)>
 */

export const config = { runtime: 'edge' };

// 不转发的请求头（浏览器专用头）
const SKIP_REQ_HEADERS = new Set([
    'host', 'connection', 'accept-encoding', 'origin', 'referer',
    'sec-fetch-mode', 'sec-fetch-site', 'sec-fetch-dest',
    'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform',
]);

// 不转发的响应头
const SKIP_RESP_HEADERS = new Set([
    'content-encoding', 'transfer-encoding', 'connection',
]);

// CORS 响应头
function corsHeaders() {
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Expose-Headers': '*',
    };
}

export default async function handler(request) {
    // ── CORS 预检 ──
    if (request.method === 'OPTIONS') {
        return new Response(null, { status: 200, headers: corsHeaders() });
    }

    // ── 解析目标 URL ──
    const { searchParams } = new URL(request.url);
    const targetUrl = searchParams.get('url');

    if (!targetUrl) {
        return new Response(
            JSON.stringify({ error: { message: '缺少 url 参数' } }),
            { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders() } }
        );
    }

    // ── 构建转发请求头 ──
    const forwardHeaders = new Headers();
    for (const [key, value] of request.headers.entries()) {
        if (!SKIP_REQ_HEADERS.has(key.toLowerCase())) {
            forwardHeaders.set(key, value);
        }
    }

    // ── 转发请求 ──
    try {
        const fetchOptions = {
            method: request.method,
            headers: forwardHeaders,
        };

        // POST 请求转发请求体
        if (request.method === 'POST') {
            fetchOptions.body = await request.arrayBuffer();
        }

        const resp = await fetch(targetUrl, fetchOptions);

        // ── 构建响应头 ──
        const responseHeaders = new Headers(corsHeaders());
        for (const [key, value] of resp.headers.entries()) {
            if (!SKIP_RESP_HEADERS.has(key.toLowerCase())) {
                responseHeaders.set(key, value);
            }
        }

        // ── 返回响应 ──
        return new Response(await resp.arrayBuffer(), {
            status: resp.status,
            headers: responseHeaders,
        });

    } catch (err) {
        return new Response(
            JSON.stringify({ error: { message: `代理请求失败: ${err.message}` } }),
            {
                status: 502,
                headers: { 'Content-Type': 'application/json', ...corsHeaders() },
            }
        );
    }
}
