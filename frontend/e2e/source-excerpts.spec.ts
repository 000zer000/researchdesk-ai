import { test, expect } from "@playwright/test";

test("source excerpts have their own mode and never show an AI-generation label", async ({
  page,
}) => {
  await page.route("**/api/research", async (route) => {
    expect(route.request().postDataJSON().response_mode).toBe("extractive");
    await route.fulfill({
      json: {
        status: "answered",
        origin: "source_extract",
        elapsed_seconds: 0.02,
        answer: {
          abstain: false,
          claims: [
            {
              text: "Synthetic source excerpt for browser testing, not model inference.",
              kind: "source_excerpt",
              origin: "source_extract",
              citations: [],
            },
          ],
          limitations: ["Relevance and completeness require review."],
        },
        evidence: [],
        trace: [],
        calculations: null,
        model_calls: [],
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Documentary response mode").selectOption("extractive");
  await page
    .getByRole("button", { name: "Research question", exact: true })
    .click();
  await expect(
    page.getByText("Verbatim source excerpts", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".claim .origin-label")).toHaveText(
    "Verbatim source excerpt · no AI synthesis",
  );
  await expect(page.locator(".answer-card")).not.toContainText(
    "Generated explanation",
  );
  await page.screenshot({
    path: "test-results/source-excerpts-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByLabel("Documentary response mode")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/source-excerpts-mobile.png",
    fullPage: true,
  });
});
