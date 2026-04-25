// src/blocks/registry.ts — NUNCA modificar sin autorización
export const BLOCK_REGISTRY = {
  now_preview:  () => import('../features/now/index.astro'),
  radio_banner: () => import('../features/radio/RadioPlayer.astro'),
  // bookshelf_preview: () => import('../features/bookshelf/BookshelfPreview.astro'),
} as const;
export type BlockType = keyof typeof BLOCK_REGISTRY;
