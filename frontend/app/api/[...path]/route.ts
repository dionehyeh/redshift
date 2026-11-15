import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

async function proxy(
  request: NextRequest,
  context: { params: { path: string[] } }
): Promise<Response> {
  const path = context.params.path.map(encodeURIComponent).join("/");
  const target = `${API_BASE.replace(/\/+$/, "")}/api/${path}${request.nextUrl.search}`;
  const session = await auth();
  const token = await session.getToken();
  const headers = new Headers();
  const contentType = request.headers.get("content-type");

  if (contentType) headers.set("content-type", contentType);
  if (token) headers.set("authorization", `Bearer ${token}`);

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch (error) {
    console.error("Backend API proxy request failed", {
      method: request.method,
      path,
      error,
    });
    return NextResponse.json(
      {
        error: {
          code: "BACKEND_UNAVAILABLE",
          message: "The backend API is unavailable",
          details: {},
        },
      },
      { status: 502 }
    );
  }

  const responseHeaders = new Headers();
  for (const name of ["content-type", "retry-after", "www-authenticate"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
