/**
 * POST /api/feed/upload
 * Sube media para posts. Auth required.
 * FormData con campo "file" (imagen, video o documento).
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { processUpload, processPfp } from "../../../lib/media";

function json(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export const POST: APIRoute = async ({ request }) => {
  // Verificar auth
  if (!(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return json({ ok: false, error: "sesión expirada — recarga la página" }, 401);
  }

  // Parsear FormData
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "error al procesar el archivo" }, 400);
  }

  const purpose = form.get("purpose") as string | null;

  // PFP upload
  if (purpose === "pfp") {
    const file = form.get("file") as File | null;
    if (!file || file.size === 0) {
      return json({ ok: false, error: "archivo requerido" }, 400);
    }
    try {
      const pfpUrl = await processPfp(file);
      return json({ ok: true, pfpUrl });
    } catch (e: any) {
      return json({ ok: false, error: e.message || "error al procesar imagen" }, 400);
    }
  }

  // Feed media upload
  const file = form.get("file") as File | null;
  if (!file || file.size === 0) {
    return json({ ok: false, error: "archivo requerido" }, 400);
  }

  try {
    const media = await processUpload(file);
    return json({ ok: true, media });
  } catch (e: any) {
    return json({ ok: false, error: e.message || "error al procesar archivo" }, 400);
  }
};
