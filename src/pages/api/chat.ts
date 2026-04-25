import type { APIRoute } from "astro";

const PASSWORD = "Bebaziel777";
const LLAMA_URL = "http://host.docker.internal:8080/v1/chat/completions";

export const POST: APIRoute = async ({ request }) => {
  const body = await request.json().catch(() => null);
  if (!body) return new Response("bad request", { status: 400 });

  const { password, messages } = body;
  if (password !== PASSWORD) {
    return new Response("unauthorized", { status: 401 });
  }

  const upstream = await fetch(LLAMA_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gemma-4",
      messages,
      stream: true,
      temperature: 0.7,
      max_tokens: 4096,
    }),
  });

  if (!upstream.ok) {
    return new Response("llama.cpp error", { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
};
