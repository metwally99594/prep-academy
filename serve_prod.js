const http = require("http");
const fs = require("fs");
const path = require("path");

const BUILD_DIR = "C:\\Users\\Metwaky\\prep-academy\\frontend\\build";
const PORT = 3001;

const MIME_TYPES = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const server = http.createServer((req, res) => {
  let urlPath = req.url.split("?")[0];
  if (urlPath === "/") urlPath = "/index.html";

  const filePath = path.join(BUILD_DIR, urlPath);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback - serve index.html for any non-file route
      fs.readFile(path.join(BUILD_DIR, "index.html"), (err2, indexData) => {
        if (err2) {
          res.writeHead(500);
          res.end("Server Error");
          return;
        }
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(indexData);
      });
      return;
    }
    const ext = path.extname(filePath);
    const contentType = MIME_TYPES[ext] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": contentType });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`Serving production build on http://localhost:${PORT}`);
});
