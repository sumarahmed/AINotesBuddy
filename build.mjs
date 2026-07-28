import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const output = resolve("dist");
await rm(output, { recursive: true, force: true });
await mkdir(resolve(output, "src"), { recursive: true });
await cp(resolve("index.html"), resolve(output, "index.html"));
await cp(resolve("src", "app.js"), resolve(output, "src", "app.js"));
await cp(resolve("src", "data.js"), resolve(output, "src", "data.js"));
await cp(resolve("src", "styles.css"), resolve(output, "src", "styles.css"));
console.log("Built dependency-free site in dist/");
