const puppeteer = require("puppeteer");

const FRONTEND_URL = "http://localhost:3000";
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

  // Set token in localStorage before navigating
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle0" });
  await page.evaluate((token) => {
    localStorage.setItem("token", token);
  }, FAKE_TOKEN);

  // Navigate to community page
  await page.goto(`${FRONTEND_URL}/community`, { waitUntil: "networkidle0" });

  // Wait for React to settle
  await new Promise(r => setTimeout(r, 3000));

  // Take screenshot
  await page.screenshot({
    path: "C:\\Users\\Metwaky\\prep-academy\\community_page_debug.png",
    fullPage: true,
  });

  // Get viewport size
  const viewport = page.viewport();
  console.log(`Viewport: ${viewport.width}x${viewport.height}`);

  // Get the full CommunityHeader HTML and its computed styles
  const headerDebug = await page.evaluate(() => {
    const results = {};

    // Find the flex container with justify-between (CommunityHeader root)
    const headerRoot = Array.from(document.querySelectorAll("div")).find(
      (d) => d.className.includes("justify-between") && d.className.includes("mb-4")
    );

    if (headerRoot) {
      results.headerHTML = headerRoot.outerHTML.substring(0, 3000);
      results.headerComputedStyles = {
        display: window.getComputedStyle(headerRoot).display,
        position: window.getComputedStyle(headerRoot).position,
        overflow: window.getComputedStyle(headerRoot).overflow,
        visibility: window.getComputedStyle(headerRoot).visibility,
        opacity: window.getComputedStyle(headerRoot).opacity,
      };

      // Find buttons inside header
      const buttons = headerRoot.querySelectorAll("button");
      results.headerButtonCount = buttons.length;
      results.headerButtons = Array.from(buttons).map((b) => {
        const cs = window.getComputedStyle(b);
        return {
          text: b.textContent.trim().substring(0, 50),
          display: cs.display,
          visibility: cs.visibility,
          opacity: cs.opacity,
          position: cs.position,
          zIndex: cs.zIndex,
          pointerEvents: cs.pointerEvents,
          overflow: cs.overflow,
          clip: cs.clip,
          rect: {
            top: b.getBoundingClientRect().top,
            left: b.getBoundingClientRect().left,
            w: b.getBoundingClientRect().width,
            h: b.getBoundingClientRect().height,
          },
          computedStyles: {
            color: cs.color,
            backgroundColor: cs.backgroundColor,
            border: cs.border,
          },
        };
      });

      // Check all children of header
      results.headerChildren = Array.from(headerRoot.children).map((child) => ({
        tag: child.tagName,
        classes: child.className.substring(0, 200),
        childCount: child.children.length,
        display: window.getComputedStyle(child).display,
      }));
    } else {
      results.headerRoot = "NOT FOUND";
    }

    // Check the layout parent
    const mainContent = document.querySelector("main") || document.querySelector('[class*="app-container"]');
    if (mainContent) {
      results.mainContentCSS = {
        display: window.getComputedStyle(mainContent).display,
        position: window.getComputedStyle(mainContent).position,
      };
    }

    // Check for any error boundary or error UI
    results.errorElements = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"]'))
      .map((e) => ({
        text: e.textContent.substring(0, 200),
        classes: e.className.substring(0, 200),
        visible: e.offsetParent !== null,
      }));

    // Check if there are any hidden parent elements that could clip the button
    const allParentsOfButton = [];
    let el = headerRoot;
    let depth = 0;
    while (el && depth < 10) {
      const cs = window.getComputedStyle(el);
      allParentsOfButton.push({
        tag: el.tagName,
        classes: el.className.substring(0, 150),
        display: cs.display,
        overflow: cs.overflow,
        overflowX: cs.overflowX,
        overflowY: cs.overflowY,
        position: cs.position,
        clip: cs.clip,
        clipPath: cs.clipPath,
        opacity: cs.opacity,
      });
      el = el.parentElement;
      depth++;
    }
    results.buttonAncestors = allParentsOfButton;

    return results;
  });

  console.log("\n========== HEADER DEBUG ==========");
  console.log(JSON.stringify(headerDebug, null, 2));

  console.log("\n========== CONSOLE LOGS ==========");
  runtimeLogs.forEach((l) => console.log(l));

  await browser.close();
}

run().catch((err) => {
  console.error("ERROR:", err);
  process.exit(1);
});
