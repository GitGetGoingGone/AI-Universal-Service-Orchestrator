import { z } from "zod";

/** Validates PATCH body.multi_agent_config before persisting to platform_config. */
export const multiAgentConfigPatchSchema = z.object({
  enabled: z.boolean(),
  workflow_order: z.array(z.string().min(1).max(128)).max(64),
  agents: z
    .array(
      z
        .object({
          id: z.string().min(1).max(128),
        })
        .passthrough()
    )
    .max(64),
});

export type MultiAgentConfigPatch = z.infer<typeof multiAgentConfigPatchSchema>;

export function parseMultiAgentConfigPatch(raw: unknown): MultiAgentConfigPatch | null {
  const r = multiAgentConfigPatchSchema.safeParse(raw);
  return r.success ? r.data : null;
}
