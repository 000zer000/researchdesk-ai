import { test, expect } from "@playwright/test";
const live = process.env.E2E_MODE === "live";
test("company → research → evidence → scenario → PDF", async ({ page }) => {
  if (!live) {
    const evidence = {
      id: "AAPL-2024-original-test",
      company: "AAPL",
      fiscal_year: 2024,
      filed: "2024-11-01",
      section: "Original synthetic fixture",
      text: "Clearly simulated provider output for deterministic browser testing. This is not model inference.",
      url: "https://example.com/original-fixture",
      start: -1,
      end: -1,
      offset_basis: "synthetic fixture",
    };
    await page.route("**/api/health", (r) =>
      r.fulfill({
        json: { model_configured: true, model: "EXPLICIT TEST DOUBLE" },
      }),
    );
    await page.route("**/api/sources?*", (r) => r.fulfill({ json: [] }));
    await page.route("**/api/evidence/*", (r) => r.fulfill({ json: evidence }));
    await page.route("**/api/research", (r) =>
      r.fulfill({
        json: {
          status: "answered",
          origin: "EXPLICIT E2E TEST DOUBLE",
          answer: {
            abstain: false,
            claims: [
              {
                text: "Simulated response, not real inference.",
                citations: [evidence.id],
              },
            ],
            limitations: [],
          },
          evidence: [evidence],
          trace: [],
          calculations: null,
          elapsed_seconds: 0.01,
        },
      }),
    );
  }
  await page.goto("/");
  await expect(
    page.getByText(live ? "391,035" : "100", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByLabel("Research question", { exact: true })
    .fill(
      "Which supply-chain risks does Apple disclose in its 2024 annual report?",
    );
  await page
    .getByRole("button", { name: "Research question", exact: true })
    .click();
  await expect(page.getByText("Inspect tool trace")).toBeVisible({
    timeout: 100000,
  });
  await page.locator(".citations button").first().click();
  await expect(
    page.getByRole("link", { name: "Open official filing" }),
  ).toBeVisible();
  if (live)
    await expect(page.getByText(/live local inference/).first()).toBeVisible();
  await page
    .getByRole("button", { name: "Financials & Valuation", exact: true })
    .click();
  const ev = page.getByTestId("enterprise-value");
  await expect(ev).toBeVisible();
  const original = await ev.innerText();
  await page.getByLabel("Discount rate", { exact: true }).fill("12");
  await expect(ev).not.toHaveText(original);
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export this scenario to PDF" })
    .click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain(".pdf");
  const path = await download.path();
  expect(path).toBeTruthy();
  await page.screenshot({
    path: `test-results/${live ? "real-model" : "simulated"}-desktop.png`,
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await expect(page.locator("h1")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `test-results/${live ? "real-model" : "simulated"}-mobile.png`,
    fullPage: true,
  });
});
