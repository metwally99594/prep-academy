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

    // Track API calls for verification
    const apiCalls = [];

    await page.setRequestInterception(true);
    page.on("request", (req) => {
      const u = req.url();
      if (u.includes("/api/auth/me")) {
        apiCalls.push("GET /auth/me");
        req.respond({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_USER) });
      } else if (u.includes("/api/community/feed")) {
        apiCalls.push("GET /community/feed");
        req.respond({ status: 200, contentType: "application/json", body: JSON.stringify({ posts: [], next_cursor: null }) });
      } else if (u.includes("/api/community/posts")) {
        apiCalls.push("POST /community/posts");
        req.respond({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "new-post-123", status: "published" }) });
      } else if (u.includes("/api/admin/activity/heartbeat")) {
        req.respond({ status: 200, contentType: "application/json", body: "{}" });
      } else if (u.match(/\/community\/[^/]+$/)) {
        // Navigate to post after creation - just render community page
        apiCalls.push("GET /community/:postId");
        req.respond({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><html><body>redirected</body></html>" });
      } else {
        req.continue();
      }
    });

    const logs = [];
    page.on("console", m => logs.push(`[${m.type()}] ${m.text()}`));

    // Step 1: Navigate to community page
    await page.goto(`http://localhost:${PORT}`, { waitUntil: "networkidle0" });
    await page.evaluate(t => localStorage.setItem("token", t), FAKE_TOKEN);
    await page.goto(`http://localhost:${PORT}/community`, { waitUntil: "networkidle0" });
    await new Promise(r => setTimeout(r, 3000));

    // Step 2: Check initial state - button should be visible
    const initialCheck = await page.evaluate(() => {
      const h = Array.from(document.querySelectorAll("div")).find(d => d.className.includes("justify-between") && d.className.includes("mb-4"));
      if (!h) return { found: false };
      const btn = h.querySelector("button");
      if (!btn) return { found: true, hasButton: false };
      const cs = window.getComputedStyle(btn);
      return {
        found: true,
        hasButton: true,
        text: btn.textContent.trim(),
        display: cs.display,
        visibility: cs.visibility,
        opacity: cs.opacity,
        rect: { w: btn.getBoundingClientRect().width, h: btn.getBoundingClientRect().height },
      };
    });

    console.log("=== Step 2: Initial button state ===");
    console.log(JSON.stringify(initialCheck, null, 2));

    if (!initialCheck.found || !initialCheck.hasButton) {
      throw new Error("Button not found in DOM!");
    }

    // Step 3: Click the create-post button
    const headerRoot = await page.evaluate(() => {
      const h = Array.from(document.querySelectorAll("div")).find(d => d.className.includes("justify-between") && d.className.includes("mb-4"));
      return h ? true : false;
    });
    await page.evaluate(() => {
      const h = Array.from(document.querySelectorAll("div")).find(d => d.className.includes("justify-between") && d.className.includes("mb-4"));
      const btn = h.querySelector("button");
      btn.click();
    });
    await new Promise(r => setTimeout(r, 1000));

    // Step 4: Check if modal opened
    const modalCheck = await page.evaluate(() => {
      const modal = document.querySelector('[aria-label="Neuen Beitrag erstellen"]');
      if (!modal) {
        // Check for modal by text
        const allDivs = Array.from(document.querySelectorAll("div"));
        const modalDiv = allDivs.find(d => d.textContent.includes("Neuer Beitrag") && !d.className.includes("hidden"));
        return {
          foundByAria: false,
          foundByText: !!modalDiv,
          modalHTML: modalDiv ? modalDiv.outerHTML.substring(0, 500) : null,
        };
      }
      const cs = window.getComputedStyle(modal);
      return {
        foundByAria: true,
        display: cs.display,
        visibility: cs.visibility,
        rect: modal.getBoundingClientRect(),
      };
    });

    console.log("=== Step 4: Modal after click ===");
    console.log(JSON.stringify(modalCheck, null, 2));

    // Step 5: Fill in the form and submit
    const submitResult = await page.evaluate(() => {
      // Find inputs and textarea
      const inputs = document.querySelectorAll('input[placeholder*="Titel"]');
      const textareas = document.querySelectorAll('textarea[placeholder*="Beitrag"]');
      const submitBtns = Array.from(document.querySelectorAll("button")).filter(b => b.textContent.includes("Veröffentlichen"));

      // Check if we can interact
      const titleInput = inputs[0];
      const contentTextarea = textareas[0];
      const submitBtn = submitBtns[0];

      if (!titleInput || !contentTextarea || !submitBtn) {
        return {
          titleFound: !!titleInput,
          contentFound: !!contentTextarea,
          submitFound: !!submitBtn,
        };
      }

      // Fill in the form
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      nativeInputValueSetter.call(titleInput, "Test Beitrag Titel für E2E Test");
      titleInput.dispatchEvent(new Event("input", { bubbles: true }));

      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
      nativeTextareaValueSetter.call(contentTextarea, "Dies ist ein Testbeitrag für den End-to-End Test der Community Funktion.");
      contentTextarea.dispatchEvent(new Event("input", { bubbles: true }));

      // Check if submit is enabled
      const isDisabled = submitBtn.disabled;
      return {
        titleFound: true,
        contentFound: true,
        submitFound: true,
        isDisabled,
        titleValue: titleInput.value,
        contentValue: contentTextarea.value,
      };
    });

    console.log("=== Step 5: Form fill check ===");
    console.log(JSON.stringify(submitResult, null, 2));

    // Click submit
    if (!submitResult.isDisabled) {
      await page.evaluate(() => {
        const submitBtns = Array.from(document.querySelectorAll("button")).filter(b => b.textContent.includes("Veröffentlichen"));
        if (submitBtns[0]) submitBtns[0].click();
      });
      await new Promise(r => setTimeout(r, 2000));
    }

    // Step 6: Final check - did the API call happen?
    console.log("\n=== Step 6: API calls made ===");
    apiCalls.forEach(c => console.log(`  ${c}`));

    console.log("\n=== CONSOLE LOGS ===");
    logs.forEach(l => console.log(l));

    console.log("\n=== E2E TEST RESULT ===");
    console.log(`Button found: ${initialCheck.found && initialCheck.hasButton}`);
    console.log(`Modal opened: ${modalCheck.foundByAria || modalCheck.foundByText}`);
    console.log(`API /community/posts called: ${apiCalls.includes("POST /community/posts")}`);

    await page.screenshot({ path: "C:\\Users\\Metwaky\\prep-academy\\e2e_result.png", fullPage: true });

    await browser.close();
  } catch (err) {
    console.error("E2E ERROR:", err);
  }

  server.close();
});
