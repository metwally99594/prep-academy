const http = require("http");
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

const BUILD_DIR = "C:\\Users\\Metwaky\\prep-academy\\frontend\\build";
const PORT = 3099;

// Start static server
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".woff2": "font/woff2",
};

function serve(req, res) {
  let p = req.url.split("?")[0];
  if (p === "/") p = "/index.html";
  const fp = path.join(BUILD_DIR, p);
  fs.readFile(fp, (err, data) => {
    if (err) {
      fs.readFile(path.join(BUILD_DIR, "index.html"), (e2, d2) => {
        if (e2) { res.writeHead(500); res.end("Error"); return; }
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(d2);
      });
      return;
    }
    res.writeHead(200, { "Content-Type": MIME[path.extname(fp)] || "application/octet-stream" });
    res.end(data);
  });
}

const server = http.createServer(serve);
server.listen(PORT, async () => {
  console.log(`Server on :${PORT}`);

  try {
    const browser = await puppeteer.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);

    const FAKE_TOKEN = "test.fake.jwt";
    const MOCK_USER = { id: "u1", email: "a@b.com", name: "Test User", is_admin: true, is_verified: true, created_at: "2025-01-01" };

    await page.setRequestInterception(true);
    page.on("request", (req) => {
      const u = req.url();
      if (u.includes("/api/auth/me")) {
        req.respond({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_USER) });
      } else if (u.includes("/api/community/feed")) {
        req.respond({ status: 200, contentType: "application/json", body: JSON.stringify({ posts: [], next_cursor: null }) });
      } else if (u.includes("/api/admin/activity/heartbeat")) {
        req.respond({ status: 200, contentType: "application/json", body: "{}" });
      } else {
        req.continue();
      }
    });

    const logs = [];
    page.on("console", m => logs.push(`[${m.type()}] ${m.text()}`));

    await page.goto(`http://localhost:${PORT}`, { waitUntil: "networkidle0" });
    await page.evaluate(t => localStorage.setItem("token", t), FAKE_TOKEN);
    await page.goto(`http://localhost:${PORT}/community`, { waitUntil: "networkidle0" });
    await new Promise(r => setTimeout(r, 4000));

    const debug = await page.evaluate(() => {
      const r = {};
      const h = Array.from(document.querySelectorAll("div")).find(d => d.className.includes("justify-between") && d.className.includes("mb-4"));
      if (h) {
        r.headerHTML = h.outerHTML.substring(0, 4000);
        const btns = h.querySelectorAll("button");
        r.buttons = Array.from(btns).map(b => {
          const cs = window.getComputedStyle(b);
          return {
            text: b.textContent.substring(0, 80),
            display: cs.display,
            visibility: cs.visibility,
            opacity: cs.opacity,
            rect: b.getBoundingClientRect(),
          };
        });
      } else {
        r.header = "NOT FOUND";
        r.allFlexBetween = Array.from(document.querySelectorAll("div"))
          .filter(d => d.className.includes("flex") && d.className.includes("between"))
          .map(d => ({ classes: d.className.substring(0, 200), html: d.innerHTML.substring(0, 500) }));
      }
      r.bodyText = document.body?.innerText?.substring(0, 500);
      return r;
    });

    console.log("===== PRODUCTION BUILD =====");
    console.log(JSON.stringify(debug, null, 2));
    console.log("\n===== CONSOLE =====");
    logs.forEach(l => console.log(l));

    await page.screenshot({ path: "C:\\Users\\Metwaky\\prep-academy\\prod_community.png", fullPage: true });
    console.log("\nScreenshot saved");

    await browser.close();
  } catch (err) {
    console.error("TEST ERROR:", err);
  }

  server.close();
});
