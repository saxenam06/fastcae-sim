// Screenshot the built UI (web/dist/index.html) in headless Edge once the page is ready, with
// WebGL by SwiftShader. No server and no port: Edge is driven over its DevTools pipe.
//
//   node tools/shot.mjs <out.png> [route] [--size 1600x1000] [--wait "<js>"] [--timeout 90000] [--settle 1500]
//
// The route is the hash without its "#/", e.g. `designs/outcome_b_6mm_drive/designs/results`: Git
// Bash rewrites an argument starting "/" (or "#/") into a Windows path.
//
// Edge's own `--screenshot` with `--virtual-time-budget` captures before a lazily loaded view (a
// design, a run, FE's results) has arrived, so it shows the "…" placeholder. Here the page is
// polled until `--wait` holds, by default until no loading placeholder (a `.vol-empty` ending in
// "…") is left, then given `--settle` ms to draw. The page's console errors and exceptions are
// printed. `--size` sets the viewport itself, so a 390 px phone width needs no iframe. `--eval
// "<js>"` prints an expression's value before the capture (a layout's boxes, say). `--act "<js>"`
// runs once the page is ready (a click on a tab, say), and the page is then waited on again.
// `--page <url>` captures another page than the build, e.g. the engineer's running dev server
// (`http://localhost:5190/`); nothing here starts one.

import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { StringDecoder } from "node:string_decoder";
import { fileURLToPath, pathToFileURL } from "node:url";

const EDGE = process.env.EDGE ?? "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const HERE = dirname(fileURLToPath(import.meta.url));
const PAGE = pathToFileURL(resolve(HERE, "../dist/index.html")).href;
const READY = `document.readyState === "complete" && ![...document.querySelectorAll(".vol-empty")].some((e) => e.textContent.trim().endsWith("…"))`;

function options(argv) {
  const o = { out: "", route: "", size: "1600x1000", wait: READY, timeout: 90000, settle: 1500, eval: "", act: "", page: PAGE };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--size") o.size = argv[++i];
    else if (a === "--wait") o.wait = argv[++i];
    else if (a === "--eval") o.eval = argv[++i];
    else if (a === "--act") o.act = argv[++i];
    else if (a === "--page") o.page = argv[++i];
    else if (a === "--timeout") o.timeout = Number(argv[++i]);
    else if (a === "--settle") o.settle = Number(argv[++i]);
    else rest.push(a);
  }
  [o.out, o.route = ""] = rest;
  if (!o.out) {
    console.error("usage: node tools/shot.mjs <out.png> [route] [--size WxH] [--wait js] [--timeout ms] [--settle ms]");
    process.exit(2);
  }
  const [w, h] = o.size.split("x").map(Number);
  return { ...o, w, h };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const o = options(process.argv.slice(2));
  const profile = join(tmpdir(), "zenryx-shot-profile");
  const edge = spawn(
    EDGE,
    [
      "--headless=new",
      "--remote-debugging-pipe",
      "--use-angle=swiftshader",
      "--enable-unsafe-swiftshader",
      "--allow-file-access-from-files",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      `--user-data-dir=${profile}`,
      `--window-size=${Math.max(o.w, 800)},${o.h}`,
      "about:blank",
    ],
    { stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"] },
  );
  const toEdge = edge.stdio[3];
  const fromEdge = edge.stdio[4];
  const decoder = new StringDecoder("utf8");
  const pending = new Map();
  const events = [];
  let buffer = "";
  let id = 0;
  fromEdge.on("data", (chunk) => {
    buffer += decoder.write(chunk);
    let end;
    while ((end = buffer.indexOf("\0")) >= 0) {
      const msg = JSON.parse(buffer.slice(0, end));
      buffer = buffer.slice(end + 1);
      const waiter = msg.id ? pending.get(msg.id) : undefined;
      if (waiter) {
        pending.delete(msg.id);
        if (msg.error) waiter.reject(new Error(`${waiter.method}: ${JSON.stringify(msg.error)}`));
        else waiter.resolve(msg.result);
      } else events.push(msg);
    }
  });
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve_, reject) => {
      const msg = { id: ++id, method, params, ...(sessionId ? { sessionId } : {}) };
      pending.set(msg.id, { resolve: resolve_, reject, method });
      toEdge.write(`${JSON.stringify(msg)}\0`);
    });

  let page;
  for (let i = 0; i < 100 && !page; i++) {
    page = (await send("Target.getTargets")).targetInfos.find((t) => t.type === "page");
    if (!page) await sleep(100);
  }
  if (!page) throw new Error("Edge opened no page");
  const { sessionId } = await send("Target.attachToTarget", { targetId: page.targetId, flatten: true });
  await send("Runtime.enable", {}, sessionId);
  await send("Page.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", { width: o.w, height: o.h, deviceScaleFactor: 1, mobile: o.w < 600 }, sessionId);
  const route = o.route.replace(/^#?\/?/, "");
  await send("Page.navigate", { url: route ? `${o.page}#/${route}` : o.page }, sessionId);

  const t0 = Date.now();
  let ready = false;
  const waitReady = async () => {
    ready = false;
    while (!ready && Date.now() - t0 < o.timeout) {
      await sleep(250);
      const r = await send("Runtime.evaluate", { expression: `Boolean(${o.wait})`, returnByValue: true }, sessionId).catch(() => null);
      ready = r?.result?.value === true;
    }
  };
  await waitReady();
  if (o.act) {
    await sleep(o.settle);
    await send("Runtime.evaluate", { expression: o.act, returnByValue: true }, sessionId);
    await sleep(500);
    await waitReady();
  }
  await sleep(o.settle);
  if (o.eval) {
    const r = await send("Runtime.evaluate", { expression: o.eval, returnByValue: true }, sessionId);
    console.log(JSON.stringify(r.result?.value ?? r.exceptionDetails?.text ?? null, null, 1));
  }
  const { data } = await send("Page.captureScreenshot", { format: "png" }, sessionId);
  mkdirSync(dirname(resolve(o.out)), { recursive: true });
  writeFileSync(o.out, Buffer.from(data, "base64"));

  for (const e of events) {
    if (e.sessionId !== sessionId) continue;
    if (e.method === "Runtime.exceptionThrown") console.error("exception:", e.params.exceptionDetails.exception?.description ?? e.params.exceptionDetails.text);
    if (e.method === "Runtime.consoleAPICalled" && (e.params.type === "error" || e.params.type === "warning")) {
      console.error(`console ${e.params.type}:`, e.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
    }
  }
  console.log(`${o.out}  ${ready ? "ready" : "NOT READY"} after ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  await send("Browser.close").catch(() => {});
  setTimeout(() => edge.kill(), 2000).unref();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
