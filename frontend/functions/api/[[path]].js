/**
 * Cloudflare Pages Function：将 /api/* 反向代理到后端 FastAPI
 *
 * Pages 环境变量（Settings → Environment variables）：
 *   BACKEND_URL          后端地址，如 https://api.example.com
 *   INTERNAL_API_SECRET  与后端 .env 中 INTERNAL_API_SECRET 一致
 */

const ALLOWED_METHODS = "GET, POST, PUT, DELETE, OPTIONS";

function corsHeaders(origin, env) {
  const allowed = (env.CORS_ORIGINS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const headers = {
    "Access-Control-Allow-Methods": ALLOWED_METHODS,
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "600",
  };
  if (allowed.length === 0 || allowed.includes(origin)) {
    headers["Access-Control-Allow-Origin"] = origin || allowed[0] || "*";
    if (origin && origin !== "*") {
      headers["Access-Control-Allow-Credentials"] = "true";
    }
  }
  return headers;
}

export async function onRequest(context) {
  const { request, env, params } = context;

  if (request.method === "OPTIONS") {
    const origin = request.headers.get("Origin") || "";
    return new Response(null, {
      status: 204,
      headers: corsHeaders(origin, env),
    });
  }

  const backend = (env.BACKEND_URL || "").replace(/\/$/, "");
  if (!backend) {
    return Response.json(
      { error: "BACKEND_URL 未配置" },
      { status: 503 }
    );
  }

  const subPath = params.path ? `/${params.path}` : "";
  const url = new URL(`/api${subPath}${new URL(request.url).search}`, backend);

  const headers = new Headers(request.headers);
  headers.delete("host");
  if (env.INTERNAL_API_SECRET) {
    headers.set("X-Internal-Secret", env.INTERNAL_API_SECRET);
  }
  const clientToken = request.headers.get("X-Client-Token");
  if (clientToken) {
    headers.set("X-Client-Token", clientToken);
  }

  const init = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }

  let response;
  try {
    response = await fetch(url.toString(), init);
  } catch {
    return Response.json({ error: "后端服务不可用" }, { status: 502 });
  }

  const outHeaders = new Headers(response.headers);
  const origin = request.headers.get("Origin") || "";
  for (const [k, v] of Object.entries(corsHeaders(origin, env))) {
    outHeaders.set(k, v);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outHeaders,
  });
}
