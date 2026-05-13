const puppeteer = require("puppeteer");

const FRONTEND_URL = "http://localhost:3001";
const FAKE_TOKEN = "eyJ0ZXN0Ijp0cnVlfQ.test-token-for-ui-verification";

const MOCK_USER = {
  id: "test-user-id",
  email: "test@example.com",
  name: "Test User",
  is_admin: true,
  is_verified: true,
  created_at: "2025-01-01T00:00:00Z",
};

async function run() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(15000);

  // Mock backend endpoints
  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const url = req.url();
    if (url.includes("/api/auth/me")) {
      req.respond({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_USER),
      });
    } else if (url.includes("/api/community/feed")) {
      req.respond({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          posts: [
            {
              id: "post-1",
              title: "Test Post",
              content: "This is a test post",
              type: "discussion",
              author: { id: "author-1", name: "Author", avatar_url: null },
              created_at: new Date().toISOString(),
              specialty_tags: [],
              topic_tags: [],
              stats: { likes: 0, comments: 0, views: 0 },
            },
          ],
          next_cursor: null,
        }),
      });
    } else if (url.includes("/api/admin/activity/heartbeat")) {
      req.respond({ status: 200, contentType: "application/json", body: "{}" });
    } else {
      req.continue();
    }
  });

  // Collect logs
  const runtimeLogs = [];
  page.on("console", (msg) => {
    runtimeLogs.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Set token before navigating to community
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle0" });
  await page.evaluate((token) => {
    localStorage.setItem("token", token);
  }, FAKE_TOKEN);

  await page.goto(`${FRONTEND_URL}/community`, { waitUntil: "networkidle0" });
  await new Promise(r => setTimeout(r, 4000));

  await page.screenshot({
    path: "C:\\Users\\Metwaky\\prep-academy\\community_prod.png",
    fullPage: true,
  });

  // Detailed debug
  const debug = await page.evaluate(() => {
    const r = {};
    const headerRoot = Array.from(document.querySelectorAll("div")).find(
      (d) => d.className.includes("justify-between") && d.className.includes("mb-4")
    );
    if (headerRoot) {
      r.headerHTML = headerRoot.outerHTML.substring(0, 3000);
      const btns = headerRoot.querySelectorAll("button");
      r.buttons = Array.from(btns).map(b => ({
        text: b.textContent.substring(0, 60),
        display: window.getComputedStyle(b).display,
        rect: { t: b.getBoundingClientRect().top, l: b.getBoundingClientRect().left, w: b.getBoundingClientRect().width, h: b.getBoundingClientRect().height },
      }));
    }
    r.bodyText = document.body?.innerText?.substring(0, 500);
    return r;
  });

  console.log("===== PRODUCTION BUILD DEBUG =====");
  console.log(JSON.stringify(debug, null, 2));
  console.log("\n===== LOGS =====");
  runtimeLogs.forEach(l => console.log(l));

  await browser.close();
}

run().catch(err => { console.error("ERROR:", err); process.exit(1); });
