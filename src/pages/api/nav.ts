import type { APIRoute } from 'astro';
import { readFileSync } from 'fs';
import { join } from 'path';

export const GET: APIRoute = () => {
  const raw = readFileSync(join(process.cwd(), 'data/nav.json'), 'utf-8');
  return new Response(raw, {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
};