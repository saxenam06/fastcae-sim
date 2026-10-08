/**
 * JSON: the contract as its file holds it, with the hashes that identify it.
 *
 * The other pages are readings of this file; this one is the file itself, so that whatever a page
 * shows can be checked against what is written. The head stays put and the sheet below scrolls on
 * its own, so the hashes and the copy button remain in view however far down one reads.
 */

import { useEffect, useState } from "react";
import { Hash } from "../panel/bits";
import type { PageProps } from "./parts";

type Copied = "idle" | "copied" | "failed";

export function Json({ c }: PageProps) {
  const [copied, setCopied] = useState<Copied>("idle");

  useEffect(() => {
    if (copied === "idle") return;
    const timer = window.setTimeout(() => setCopied("idle"), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(c.json);
      setCopied("copied");
    } catch {
      // No clipboard in this context (a file:// page, a denied permission): say so, change nothing.
      setCopied("failed");
    }
  };

  return (
    <div className="stage-scroll ct-page ct-json">
      <div className="ct-json-head">
        <dl className="kv ct-json-kv">
          <dt>hash</dt>
          <dd>{c.hash ? <Hash value={c.hash} /> : <span className="dim">-</span>}</dd>
          <dt>frozen hash</dt>
          <dd>
            {c.frozen_hash ? (
              <Hash value={c.frozen_hash} />
            ) : (
              <span className="dim">{c.loaded ? "not frozen" : "-"}</span>
            )}
          </dd>
          <dt>file</dt>
          <dd className="ct-json-file">{c.file}</dd>
        </dl>
        <div className="ct-json-copy">
          <button onClick={copy} title="Copy the file's text">
            Copy
          </button>
          <span className="dim" aria-live="polite">
            {copied === "copied" ? "copied" : copied === "failed" ? "the clipboard is not available here" : ""}
          </span>
        </div>
      </div>
      <pre className="ct-json-pre mono">{c.json}</pre>
    </div>
  );
}
