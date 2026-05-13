const http = require("http");
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

const BUILD_DIR = "C:\\Users\\Metwaky\\prep-academy\\frontend\\build";
const PORT = 3099;

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

// Test with invalid payloads that mimic production crash
async function runTest(mockSpecialties, mockExamTypes, label) {
  return new Promise(async (resolve) => {
    try {
      const browser = await puppeteer.launch({
        headless: true,
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
      });
      const page = await browser.newPage();
      page.setDefaultTimeout(15000);

      const errors = [];
      page.on("pageerror", err => errors.push(err.message));
      page.on("console", m => {
        if (m.type() === "error" || m.type() === "warning") {
          errors.push(`[${m.type()}] ${m.text()}`);
        }
      });

      await page.setRequestInterception(true);
      page.on("request", (req) => {
        const u = req.url();
        if (u.includes("/api/specialties")) {
          req.respond({ status: 200, contentType: "application/json", body: JSON.stringify(mockSpecialties) });
        } else if (u.includes("/api/exam-types")) {
          req.respond({ status: 200, contentType: "application/json", body: JSON.stringify(mockExamTypes) });
        } else {
          req.continue();
        }
      });

      await page.goto(`http://localhost:${PORT}`, { waitUntil: "networkidle0" });
      await new Promise(r => setTimeout(r, 3000));

      const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 300) || "");
      const errorElements = await page.evaluate(() => {
        return document.querySelector('[role="alert"], [class*="Error"], [class*="error"]')?.textContent?.substring(0, 200) || null;
      });
      const hasCrash = errors.length > 0;

      console.log(`\n[${label}]`);
      console.log(`  Errors: ${errors.length > 0 ? errors.join("; ") : "NONE"}`);
      console.log(`  ErrorBoundary triggered: ${errorElements || "no"}`);
      console.log(`  Body starts with: ${bodyText.substring(0, 80)}`);
      console.log(`  RESULT: ${hasCrash ? "FAIL" : "PASS"}`);

      await browser.close();
      resolve(!hasCrash);
    } catch (e) {
      console.log(`[${label}] CRASHED: ${e.message}`);
      resolve(false);
    }
  });
}

server.listen(PORT, async () => {
  console.log(`Server on :${PORT}`);

  // Test 1: Normal arrays (should always work)
  await runTest(
    [{ id: "kardio", name_de: "Kardiologie", icon: "Heart", question_count: 100 }],
    [{ id: "medat", name: "MedAT", question_count: 50 }],
    "Test 1: Normal arrays"
  );

  // Test 2: null specialties (production crash scenario)
  await runTest(
    null,
    [{ id: "medat", name: "MedAT", question_count: 50 }],
    "Test 2: null specialties"
  );

  // Test 3: object specialties (unexpected shape)
  await runTest(
    { error: "not found" },
    [{ id: "medat", name: "MedAT", question_count: 50 }],
    "Test 3: object specialties"
  );

  // Test 4: both null
  await runTest(
    null,
    null,
    "Test 4: both null"
  );

  // Test 5: undefined (missing data field)
  await runTest(
    undefined,
    [{ id: "medat", name: "MedAT", question_count: 50 }],
    "Test 5: undefined specialties"
  );

  console.log("\n=== ALL TESTS COMPLETE ===");
  server.close();
});
