// src/pages/api/sigilum/forge.ts — Proxy para Sigilum Forge
// Llama a Gemma 4 API desde el servidor. Evita CORS del navegador.
// Modo "verify": si description es "ping", solo valida que la key exista.
// Modo "forge": envía el prompt completo y extrae el GLSL.

export const prerender = false;

const BASE = 'https://generativelanguage.googleapis.com/v1beta/models';

const SP = 'ONLY respond with GLSL shader code in a ```glsl code block. Nothing else. No Role:, No Constraint:, No text before or after the code. No markdown except the code block. Example valid response:\n```glsl\n#version 300 es\nprecision highp float;\nvoid main() {}\n```\nDo NOT include any explanatory text, role descriptions, or constraints. ONLY the code block.\n\nIf you include any text outside the code block, the request fails.\n\nGenerate a true 3D ray marching shader with SDFs. Requirements:\n- Use opSmoothUnion, domain warping, Fresnel rim lighting\n- 6 layers: core, shell, orbiting small SDFs, volumetric glow, 3D residue, post-processing (ACES tone mapping, gamma correction, vignette)\n- Orbit camera. Signed Distance Fields only — no flat 2D.\n\nDescription: ';

interface ForgeBody {
  apiKey: string;
  description: string;
}

export async function POST({ request }: { request: Request }) {
  try {
    const body: ForgeBody = await request.json();
    const { apiKey, description } = body;

    if (!apiKey) {
      return json({ error: 'apiKey requerida' }, 400);
    }

    if (description === 'ping') {
      return await verifyKey(apiKey);
    }

    return await forgeSpell(apiKey, description);
  } catch (e: any) {
    return json({ error: e?.message || 'Error interno' }, 500);
  }
}

async function verifyKey(apiKey: string): Promise<Response> {
  const url = `${BASE}?key=${encodeURIComponent(apiKey)}`;
  const resp = await fetch(url);
  if (resp.ok) {
    return json({ ok: true }, 200);
  }
  const err = await resp.json().catch(() => ({}));
  const msg = err?.error?.message || `HTTP ${resp.status}`;
  return json({ error: msg }, resp.status);
}

async function forgeSpell(apiKey: string, description: string): Promise<Response> {
  const url = `${BASE}/gemma-4-31b-it:generateContent?key=${encodeURIComponent(apiKey)}`;

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: SP + description }] }],
      generationConfig: { maxOutputTokens: 8192, temperature: 0.85, topP: 0.95, topK: 64 },
    }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    const msg = err?.error?.message || `HTTP ${resp.status}`;
    return json({ error: msg }, resp.status);
  }

  const data = await resp.json();
  const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? '';
  const glsl = extractGLSL(raw);

  if (!glsl) {
    return json({ error: 'No se pudo extraer GLSL de la respuesta', raw: raw.slice(0, 600) }, 422);
  }

  return json({ glsl }, 200);
}

function extractGLSL(text: string): string | null {
  let m = text.match(/```glsl\s*([\s\S]*?)```/i);
  if (m) return m[1].trim();

  m = text.match(/```\s*([\s\S]*?)```/);
  if (m && m[1].trim().startsWith('#version')) return m[1].trim();

  // Fallback: skip past constraint/role preambles and look for #version
  const cleaned = text.replace(/^\s*\*\s*Role:.*$/gm, '').replace(/^\s*\*\s*Constraint:.*$/gm, '').replace(/^\s*\*\s*Technical Requirements:.*$/gm, '');
  const idx = cleaned.indexOf('#version');
  if (idx >= 0) {
    const after = cleaned.slice(idx);
    const end = after.indexOf('```');
    const chunk = end > 0 ? after.slice(0, end) : after;
    const lines = chunk.split('\n');
    const out: string[] = [];
    for (const ln of lines) {
      const s = ln.trim();
      if (!s || s.startsWith('#') || s.startsWith('precision') || s.startsWith('uniform') ||
          s.startsWith('float') || s.startsWith('vec') || s.startsWith('mat') ||
          s.startsWith('void') || s.startsWith('in ') || s.startsWith('out ') ||
          s.startsWith('const') || s.startsWith('//') || s.startsWith('{') ||
          s.startsWith('}') || s.endsWith(';') || s.match(/^[a-zA-Z]/)) {
        out.push(ln);
      } else break;
    }
    if (out.length > 3) return out.join('\n').trim();
  }

  // Second fallback: original scan from first #version
  const idx2 = text.indexOf('#version');
  if (idx2 < 0) return null;
  const after2 = text.slice(idx2);
  const end2 = after2.indexOf('```');
  const chunk2 = end2 > 0 ? after2.slice(0, end2) : after2;
  const lines2 = chunk2.split('\n');
  const out2: string[] = [];
  for (const ln of lines2) {
    const s = ln.trim();
    if (!s || s.startsWith('#') || s.startsWith('precision') || s.startsWith('uniform') ||
        s.startsWith('float') || s.startsWith('vec') || s.startsWith('mat') ||
        s.startsWith('void') || s.startsWith('in ') || s.startsWith('out ') ||
        s.startsWith('const') || s.startsWith('//') || s.startsWith('{') ||
        s.startsWith('}') || s.endsWith(';') || s.match(/^[a-zA-Z]/)) {
      out2.push(ln);
    } else break;
  }
  return out2.length > 3 ? out2.join('\n').trim() : null;
}

function json(data: any, status: number): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function OPTIONS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}