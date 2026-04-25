import { defineMiddleware } from "astro:middleware";

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Rutas protegidas: todo /admin/* excepto /admin/login
  if (pathname.startsWith("/admin") && pathname !== "/admin/login") {
    const session = context.cookies.get("aris_admin");
    if (!session?.value || !(await verifySession(session.value, import.meta.env.ADMIN_JWT_SECRET))) {
      return context.redirect("/admin/login");
    }
  }

  return next();
});

async function verifySession(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf(".");
    if (dot < 0) return false;
    const payload = token.slice(0, dot);
    const sigB64  = token.slice(dot + 1);

    const key = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" }, false, ["verify"]
    );

    const sigBytes = Uint8Array.from(atob(sigB64), (c) => c.charCodeAt(0));
    const valid = await crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(payload));
    if (!valid) return false;

    // Verificar expiración (8h)
    const { ts } = JSON.parse(atob(payload));
    return Date.now() - ts < 8 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}