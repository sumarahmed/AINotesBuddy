import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const root = resolve(process.argv[2] || ".");
const port = Number(process.env.PORT || 4173);
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

createServer((request, response) => {
  const requested = decodeURIComponent((request.url || "/").split("?")[0]);
  const safePath = normalize(requested).replace(/^(\.\.[/\\])+/, "");
  let filePath = join(root, safePath === "/" ? "index.html" : safePath);
  if (!filePath.startsWith(root) || !existsSync(filePath)) {
    filePath = join(root, "index.html");
  }
  if (existsSync(filePath) && statSync(filePath).isDirectory()) {
    filePath = join(filePath, "index.html");
  }
  response.writeHead(200, {
    "Content-Type": types[extname(filePath)] || "application/octet-stream",
    "Cache-Control": "no-cache",
  });
  createReadStream(filePath).pipe(response);
}).listen(port, "127.0.0.1", () => {
  console.log(`NotesBuddy running at http://127.0.0.1:${port}`);
});
