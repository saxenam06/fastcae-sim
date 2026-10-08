/**
 * Where the snapshot comes from.
 *
 * Today it is bundled: `zenryx.api.snapshot` writes `snapshot.json` beside this file, and the dev
 * server reloads the page when it is rewritten. When the API exists (PLT-5) this becomes a fetch of
 * `/api/snapshot`, and nothing else in the UI changes.
 */

import type { Snapshot } from "./types";

export async function loadSnapshot(): Promise<Snapshot> {
  const bundled = await import("./snapshot.json");
  return bundled.default as unknown as Snapshot;
}
