// Real UI + real local model only. No response routes or synthetic content.
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { mkdir, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";

await mkdir("docs/demo", { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
  recordVideo: { dir: "work/recordings", size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();
const responses = [];
page.on("response", async (r) => {
  if (r.url().endsWith("/api/research")) responses.push(await r.json());
});
try {
  await page.goto("http://127.0.0.1:8000/");
  await page
    .locator(".metric strong")
    .first()
    .filter({ hasText: "391,035" })
    .waitFor();
  await page.waitForTimeout(1300); // Intentional reading pauses in a human-viewable recording.
  await page
    .getByLabel("Research question", { exact: true })
    .fill(
      "Which supply-chain risks does Apple disclose in its 2024 annual report?",
    );
  const modelResponse = page.waitForResponse(
    (r) => r.url().endsWith("/api/research") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Research question", exact: true })
    .click();
  const response = await modelResponse;
  const actual = await response.json();
  if (
    !response.ok() ||
    actual.status !== "answered" ||
    actual.origin !== "live local inference"
  )
    throw new Error(
      `Actual local inference failed: HTTP ${response.status()} ${actual.status || actual.detail}`,
    );
  await page.getByText("Inspect tool trace").waitFor({ timeout: 100000 });
  await page.locator(".claim").first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(2500);
  await page.locator(".citations button").first().click();
  await page.getByRole("link", { name: "Open official filing" }).waitFor();
  await page.mouse.move(0, 0);
  await page.screenshot({
    path: "docs/demo/research-desktop.png",
    fullPage: true,
  });
  await page.waitForTimeout(2500);
  await page
    .getByRole("button", { name: "Financials & Valuation", exact: true })
    .click();
  await page.getByTestId("enterprise-value").waitFor();
  await page.getByTestId("enterprise-value").scrollIntoViewIfNeeded();
  await page.waitForTimeout(1600);
  await page.getByLabel("Discount rate", { exact: true }).fill("12");
  await page.waitForTimeout(900);
  await page.mouse.move(0, 0);
  const valuationScroll = await page.evaluate(() => window.scrollY);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "docs/demo/valuation-desktop.png",
    fullPage: true,
  });
  await page.evaluate((y) => window.scrollTo(0, y), valuationScroll);
  await page.waitForTimeout(1700);
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export this scenario to PDF" })
    .click();
  await (await downloadPromise).saveAs("work/demo-scenario.pdf");
  await page.waitForTimeout(1200);
  await page
    .getByRole("button", { name: "Sources & Evaluation", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Official source register" })
    .waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1700);
  await page.screenshot({
    path: "docs/demo/sources-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await page
    .getByRole("heading", { name: "From filings to findings." })
    .waitFor();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(400);
  await page.screenshot({
    path: "docs/demo/research-mobile.png",
    fullPage: true,
  });
  const video = page.video();
  await context.close();
  await video.saveAs("work/ResearchDesk-real-demo.webm");
  await browser.close();
  await writeFile(
    "docs/demo/recording.json",
    JSON.stringify(
      {
        recorded_at: new Date().toISOString(),
        code_commit: execFileSync("git", ["rev-parse", "HEAD"], {
          encoding: "utf8",
        }).trim(),
        actual_model_calls: responses.map((r) => ({
          status: r.status,
          origin: r.origin,
          answer: r.answer,
          model: r.model,
          elapsed_seconds: r.elapsed_seconds,
        })),
        note: "Actual Chromium recording; no mocked network routes; loading and inference are visible; PDF uses a 12% discount-rate scenario. No hosted interactive service.",
      },
      null,
      2,
    ) + "\n",
  );
  console.log("Recorded real local-model browser session.");
} finally {
  await browser.close();
}
