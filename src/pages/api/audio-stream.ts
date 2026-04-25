import type { APIRoute } from "astro";
import { spawn } from "child_process";

// Cache de URLs directas para no llamar a yt-dlp en cada request
// TTL 4 horas (las URLs de YouTube expiran, pero duran varias horas)
const urlCache = new Map<string, { url: string; ts: number }>();
const CACHE_TTL = 4 * 60 * 60 * 1000;

async function getDirectAudioUrl(ytUrl: string): Promise<string> {
  const cached = urlCache.get(ytUrl);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.url;
  }

  return new Promise((resolve, reject) => {
    // -f bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio
    // -g = solo imprimir la URL, sin descargar
    // --no-playlist = solo el video, no la playlist completa
    const proc = spawn("yt-dlp", [
      "-f", "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio",
      "-g",
      "--no-playlist",
      "--no-warnings",
      ytUrl,
    ]);

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d: Buffer) => (stdout += d.toString()));
    proc.stderr.on("data", (d: Buffer) => (stderr += d.toString()));

    proc.on("close", (code: number) => {
      if (code !== 0) {
        reject(new Error(`yt-dlp failed (${code}): ${stderr.trim()}`));
        return;
      }
      const url = stdout.trim().split("\n")[0];
      if (!url || !url.startsWith("http")) {
        reject(new Error("yt-dlp returned no valid URL"));
        return;
      }
      urlCache.set(ytUrl, { url, ts: Date.now() });
      resolve(url);
    });
  });
}

export const GET: APIRoute = async ({ url, request }) => {
  const ytUrl = url.searchParams.get("url");

  // Endpoint de resolución: solo devuelve la URL directa (el cliente hace el proxy)
  // Esto evita que el servidor descargue el stream completo
  if (url.searchParams.get("resolve") === "1") {
    if (!ytUrl) {
      return new Response(JSON.stringify({ error: "Missing url param" }), {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    // Sanitizar: solo permitir URLs de YouTube
    const allowed = /^https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/)/;
    if (!allowed.test(ytUrl)) {
      return new Response(JSON.stringify({ error: "Solo se permiten URLs de YouTube" }), {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    try {
      const directUrl = await getDirectAudioUrl(ytUrl);
      return new Response(JSON.stringify({ url: directUrl }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
        },
      });
    } catch (err: any) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }
  }

  // Endpoint de proxy: stream del audio al browser
  // Así el browser recibe audio del mismo origen → createMediaElementSource funciona
  if (!ytUrl) {
    return new Response(JSON.stringify({ error: "Missing url param" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const allowed = /^https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/)/;
  if (!allowed.test(ytUrl)) {
    return new Response("Forbidden", { status: 403 });
  }

  try {
    const directUrl = await getDirectAudioUrl(ytUrl);

    // Leer range header si existe (para seeking)
    const rangeHeader = request.headers.get("range");

    const upstreamHeaders: Record<string, string> = {
      "User-Agent": "Mozilla/5.0 (compatible; audio-proxy/1.0)",
    };
    if (rangeHeader) upstreamHeaders["Range"] = rangeHeader;

    const upstream = await fetch(directUrl, { headers: upstreamHeaders });

    const headers: Record<string, string> = {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    };

    const ct = upstream.headers.get("content-type");
    if (ct) headers["Content-Type"] = ct;
    const cl = upstream.headers.get("content-length");
    if (cl) headers["Content-Length"] = cl;
    const cr = upstream.headers.get("content-range");
    if (cr) headers["Content-Range"] = cr;
    headers["Accept-Ranges"] = "bytes";

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
