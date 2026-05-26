import type { APIRoute } from "astro";

export const POST: APIRoute = ({ cookies }) => {
  cookies.delete("aris_admin", { path: "/" });
  return new Response("ok", { status: 200 });
};
