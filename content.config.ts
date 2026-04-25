import { defineCollection, z } from 'astro:content';

export const collections = {
  garden: defineCollection({
    type: 'content',
    schema: z.object({
      title: z.string(),
      stage: z.enum(['seed', 'sprout', 'evergreen']),
      tags: z.array(z.string()).default([]),
      created: z.string(),
      updated: z.string(),
      related: z.array(z.string()).default([]),
    }),
  }),
  blog: defineCollection({
    type: 'content',
    schema: z.object({
      title: z.string(),
      date: z.string(),
      tags: z.array(z.string()).default([]),
      draft: z.boolean().default(false),
    }),
  }),
};
