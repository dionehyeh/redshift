import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const API = process.env.API_BASE_URL || "http://localhost:8000";

async function proxy(
  req: NextRequest,
  ctx: { params: { path: string[] } }
) {
  const { getToken } = auth();
  const token = await getToken();
  const path = ctx.params.path || [];
  const targetUrl = `${API}/api/v1/${path.join("/")}${req.nextUrl.search}`;

  try {
    const res = await fetch(targetUrl, {
      method: req.method,
      headers: {
        "Content-Type": req.headers.get("content-type") ?? "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
      cache: "no-store",
    });

    const bodyText = await res.text();
    return new NextResponse(bodyText, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unable to reach backend service";
    return NextResponse.json(
      { error: { code: "PROXY_ERROR", message } },
      { status: 502 }
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as DELETE };
