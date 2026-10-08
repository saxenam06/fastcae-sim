/**
 * Where you are, kept in the address bar: `#/<view>/<id>/<page>/<focus>`.
 *
 * Any view can be linked, reloaded or opened from a saved screenshot's address. `-` stands for an
 * empty part; the focus (an entry's path, a step, a task type) is URI-encoded.
 */

import { useCallback, useEffect, useState } from "react";
import type { View } from "./product";
import { VIEWS } from "./product";

export interface Route {
  view: View;
  /** The record in view: a contract's id, a campaign's, a design's. */
  id: string | null;
  /** The page of the view; null means its first. */
  page: string | null;
  /** What the card shows: an entry's path, a step, a kind. */
  focus: string | null;
}

export type Go = (next: Partial<Route>) => void;

const EMPTY = "-";

export function parse(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/");
  const view = VIEWS.some((v) => v.id === parts[0]) ? (parts[0] as View) : "flow";
  const part = (i: number) => (parts[i] && parts[i] !== EMPTY ? decodeURIComponent(parts[i]) : null);
  return { view, id: part(1), page: part(2), focus: part(3) };
}

export function format(route: Route): string {
  const part = (s: string | null) => (s ? encodeURIComponent(s) : EMPTY);
  const tail = [route.id, route.page, route.focus];
  while (tail.length && !tail[tail.length - 1]) tail.pop();
  return `#/${[route.view, ...tail.map(part)].join("/")}`;
}

/**
 * The route and a way to move it. Moving to another view starts that view afresh unless the
 * caller says otherwise; within a view, what is not named is kept.
 */
export function useRoute(): [Route, Go] {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash));
  useEffect(() => {
    const read = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);
  const go = useCallback<Go>(
    (next) => {
      const base: Route =
        next.view && next.view !== route.view ? { view: next.view, id: null, page: null, focus: null } : route;
      const merged = { ...base, ...next };
      const hash = format(merged);
      if (hash !== window.location.hash) window.location.hash = hash;
      else setRoute(merged);
    },
    [route],
  );
  return [route, go];
}
