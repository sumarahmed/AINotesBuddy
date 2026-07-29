import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const output = resolve("dist");
await rm(output, { recursive: true, force: true });
await mkdir(resolve(output, "client", "src"), { recursive: true });
await mkdir(resolve(output, "server"), { recursive: true });
await mkdir(resolve(output, ".openai"), { recursive: true });
await cp(resolve("index.html"), resolve(output, "client", "index.html"));
await cp(resolve("src", "app.js"), resolve(output, "client", "src", "app.js"));
await cp(resolve("src", "styles.css"), resolve(output, "client", "src", "styles.css"));
await cp(resolve("site-worker.mjs"), resolve(output, "server", "index.js"));
await cp(
  resolve(".openai", "hosting.json"),
  resolve(output, ".openai", "hosting.json"),
);
console.log("Built dependency-free site in dist/");
