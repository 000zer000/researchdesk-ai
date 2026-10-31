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
  await expect(page.locator(".metric strong").first()).toContainText(
    live ? "391,035" : "100",
  );
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
  await expect(page.locator("h1")).toHaveText("From filings to findings.");
  await expect(
    page.getByLabel("Covered company", { exact: true }),
  ).toBeVisible();
  await page.mouse.move(0, 0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `test-results/${live ? "real-model" : "simulated"}-mobile.png`,
    fullPage: true,
  });
  if (live) {
    await page
      .getByLabel("Covered company", { exact: true })
      .selectOption("DELL");
    await expect(page.locator(".metric strong").first()).toContainText(
      "88,425",
    );
  }
  await page
    .getByLabel("Covered company", { exact: true })
    .selectOption("AAPL");
  await page.getByLabel("Analysis date", { exact: true }).fill("2024-10-31");
  await expect(page.locator(".metric strong").first()).toContainText(
    live ? "383,285" : "Unavailable",
  );
  await page.route("**/api/financials?as_of=2024-01-01", (r) =>
    r.fulfill({
      status: 503,
      json: { detail: "Explicit test of a data-service failure" },
    }),
  );
  await page.getByLabel("Analysis date", { exact: true }).fill("2024-01-01");
  await expect(page.getByRole("alert")).toContainText(
    "Data service unavailable",
  );
  await expect(page.locator(".metric strong").first()).toContainText(
    "Unavailable",
  );
});

test("financial guard displays verified data and both conflicting source proofs", async ({
  page,
}) => {
  // Explicit browser test double: regression of display behavior, not inference.
  const observation = {
    metric: "revenue",
    fiscal_year: 2024,
    company: "AAPL",
    raw_value: 110000000,
    unit: "USD",
    currency: "USD",
    start: "2023-10-01",
    end: "2024-09-30",
    scope: "consolidated",
    concept: "synthetic:Revenue",
    reporting_basis: "as_reported",
    restates_accession: null,
    accession: "SYNTHETIC-ORIGINAL",
    filed: "2024-11-01",
    evidence_id: "SYNTHETIC-original-proof",
  };
  await page.route("**/api/research", (route) =>
    route.fulfill({
      json: {
        status: "source_conflict",
        origin: "EXPLICIT CONFLICT DISPLAY TEST DOUBLE",
        answer: {
          abstain: true,
          claims: [],
          limitations: ["Ambiguous source versions; no conclusion chosen."],
        },
        verified_financials: {
          measures: [],
          issues: [],
          conflicts: [
            {
              metric: "revenue",
              reason: "Different values in comparable source versions.",
            },
          ],
          observations: [
            observation,
            {
              ...observation,
              raw_value: 111000000,
              reporting_basis: "restated",
              restates_accession: "SYNTHETIC-ORIGINAL",
              accession: "SYNTHETIC-RESTATED",
              evidence_id: "SYNTHETIC-restated-proof",
            },
          ],
        },
        evidence: [],
        trace: [],
        calculations: null,
        elapsed_seconds: 0.01,
      },
    }),
  );
  await page.goto("/");
  await page
    .getByLabel("Research question", { exact: true })
    .fill("Compare the 2024 revenue sources.");
  await page
    .getByRole("button", { name: "Research question", exact: true })
    .click();
  await expect(page.locator(".result-status")).toContainText("source conflict");
  const panel = page.getByRole("region", { name: "Verified financial data" });
  await expect(panel).toContainText("110,000,000 USD");
  await expect(panel).toContainText("111,000,000 USD");
  await expect(panel).toContainText("restates SYNTHETIC-ORIGINAL");
  await expect(page.locator(".answer-card > .claim")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/simulated-v1.1-conflict-mobile.png",
    fullPage: true,
  });
});

if (live)
  test("real financial proposal retains canonical evidence in the UI", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByLabel("Research question", { exact: true })
      .fill("What was Apple operating income for 2024?");
    await page
      .getByRole("button", { name: "Research question", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Verified financial data" }),
    ).toContainText("123,216 USD million", { timeout: 100000 });
    await expect(
      page.getByRole("region", { name: "Verified financial data" }),
    ).toContainText("2023-10-01/2024-09-28");
    await expect(page.locator(".model-meta")).toContainText(
      "live local inference",
    );
    await page.screenshot({
      path: "test-results/real-v1.1-financial-desktop.png",
      fullPage: true,
    });
  });
