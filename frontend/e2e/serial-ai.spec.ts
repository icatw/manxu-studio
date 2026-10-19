import { expect, test } from "@playwright/test";
import { deleteProjectByTitle, loginWithEmail } from "./helpers/auth";

const liveAi = process.env.E2E_LIVE_AI === "1";
const email = process.env.E2E_AI_EMAIL ?? "e2e-serial@manxu.dev";
const stamp = Date.now();
const premise = `一座漂浮在永夜海上的图书馆，馆员靠收集失踪旅人的梦境续写史书。编号 ${stamp}`;

test.describe.configure({ mode: "serial" });

test.skip(!liveAi, "Set E2E_LIVE_AI=1 to spend real model tokens");

test("AI plan → create multi-episode project → generate summary → read", async ({ page }) => {
  test.setTimeout(300_000);
  await loginWithEmail(page, email);

  await page.getByRole("link", { name: "AI 策划" }).click();
  await expect(page).toHaveURL(/\/projects\/new/);
  await page.getByLabel("作品创意").fill(premise);
  await page.locator("label", { hasText: "第一季话数" }).locator("select").selectOption("3");

  const planResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes("/projects/plan") &&
      response.status() !== 0,
    { timeout: 180_000 },
  );
  await page.getByRole("button", { name: "生成季策划" }).click();
  const planResult = await planResponse;
  expect(planResult.ok(), `plan status ${planResult.status()}`).toBeTruthy();

  await expect(page.getByText("策划完成")).toBeVisible({ timeout: 30_000 });
  const titleInput = page.getByLabel("作品名");
  await expect(titleInput).toHaveValue(/.+/);
  const plannedTitle = await titleInput.inputValue();
  const disposableTitle = `E2E AI ${stamp} ${plannedTitle}`.slice(0, 60);
  await titleInput.fill(disposableTitle);

  await page.getByRole("button", { name: "确认创建作品" }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/[0-9a-f-]{36}$`), { timeout: 60_000 });
  await expect(page.locator("h1", { hasText: disposableTitle })).toBeVisible();
  await expect(page.locator("p", { hasText: "第 1 话" })).toBeVisible();

  await page.getByRole("tab", { name: "设定集" }).click();
  await expect(page.getByRole("heading", { name: "世界观" }).locator("..").getByRole("textbox")).not.toHaveValue("");

  await page.getByRole("tab", { name: "话次" }).click();
  const summaryResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes("/summary") &&
      response.status() !== 0,
    { timeout: 180_000 },
  );
  await page.getByRole("button", { name: "生成摘要" }).first().click();
  const summaryResult = await summaryResponse;
  expect(summaryResult.ok(), `summary status ${summaryResult.status()}`).toBeTruthy();
  await expect(page.getByText(/摘要：/).first()).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "更多" }).first().click();
  await page.getByRole("menuitem", { name: "阅读" }).click();
  await expect(page).toHaveURL(/\/read\//);

  await deleteProjectByTitle(page, disposableTitle);
});
