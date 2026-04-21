import playwrightChromium from "../assets/renderer/node_modules/playwright-chromium/index.mjs";

const { chromium } = playwrightChromium;

const baseUrl = process.env.DEMO_BASE_URL || "http://127.0.0.1:8765";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("#prompt").fill(
    "Build a judges-first demo deck for a local AI slide generator."
  );
  await page.locator('input[name="tone"][value="professional"]').setChecked(true, { force: true });
  await page
    .locator('input[name="slide_count"][value="8"]')
    .setChecked(true, { force: true });
  await page.getByRole("button", { name: "Generate presentation" }).click();

  await page.waitForFunction(() => {
    const frame = document.querySelector("#viewer-frame");
    return frame && !frame.classList.contains("hidden") && frame.getAttribute("src");
  });

  const viewerSrc = await page.locator("#viewer-frame").getAttribute("src");
  const statusText = await page.locator("#status").textContent();
  const pageText = await page.textContent("body");

  console.log(JSON.stringify({
    ok: true,
    baseUrl,
    viewerSrc,
    statusText,
    hasHeading: pageText.includes("Prompt to interactive Slidev deck"),
  }));
} finally {
  await browser.close();
}
