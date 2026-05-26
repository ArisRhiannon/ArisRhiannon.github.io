import type { APIRoute } from "astro";
import { readJson } from "../../lib/data";
import { jsonResponse } from "../../lib/response";

export const GET: APIRoute = () => {
  try {
    const data = readJson("nav.json");
    return jsonResponse(data, 200);
  } catch {
    return jsonResponse({}, 200);
  }
};
