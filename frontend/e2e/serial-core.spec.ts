import { expect, test } from "@playwright/test";
import { deleteProjectByTitle, loginWithEmail } from "./helpers/auth";

const stamp = Date.now();
const email = `e2e-core-${stamp}@manxu.dev`;
const projectTitle = `E2E 核心 ${stamp}`;
const worldText = "雾港常年被海雾笼罩，灯塔是唯一可靠的地标。";
const styleText = "冷色调、电影感、细雨质感。";
const threadText = "灯塔看守人留下的未拆信件。";

test.describe.configure({ mode: "serial" });

test("email login → create project → bible/threads → studio → reader → delete", async ({ page }) => {
  await loginWithEmail(page, email);

  await page.getByPlaceholder("例如：雾港来信").fill(projectTitle);
  await page.getByPlaceholder("描述主角、冲突与转折").fill("自动化测试：港口迷雾中的信件与失踪的灯塔看守人。");
  await page.getByRole("button", { name: "创建并进入工作区" }).click();

  await expect(page).toHaveURL(new RegExp(`/projects/[0-9a-f-]{36}$`));
  await expect(page.locator("h1", { hasText: projectTitle })).toBeVisible();

  await page.getByRole("tab", { name: "设定集" }).click();
  await page.getByRole("heading", { name: "世界观" }).locator("..").getByRole("textbox").fill(worldText);
  await page.getByRole("heading", { name: "画风规则" }).locator("..").getByRole("textbox").fill(styleText);
  const bibleSave = page.waitForResponse(
    (response) =>
      response.request().method() === "PATCH" &&
      /\/api\/v1\/projects\/[0-9a-f-]+$/.test(response.url()) &&
      response.ok(),
  );
  await page.getByRole("button", { name: "保存设定集" }).click();
  await bibleSave;
  await page.reload();
  await page.getByRole("tab", { name: "设定集" }).click();
  await expect(page.getByRole("heading", { name: "世界观" }).locator("..").getByRole("textbox")).toHaveValue(worldText);
  await expect(page.getByRole("heading", { name: "画风规则" }).locator("..").getByRole("textbox")).toHaveValue(styleText);

  await page.getByRole("tab", { name: "伏笔" }).click();
  await page.getByPlaceholder("写下一条伏笔").fill(threadText);
  const threadCreate = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes("/plot-threads") && response.ok(),
  );
  await page.getByRole("button", { name: "添加" }).click();
  await threadCreate;
  await expect(page.getByText(threadText)).toBeVisible();

  await page.getByRole("tab", { name: "章节" }).click();
  await expect(page.locator("p", { hasText: "第 1 话" })).toBeVisible();
  await page.getByRole("button", { name: "续写下一话" }).click();
  await expect(page).toHaveURL(/\/studio/);
  await page.goBack();
  await expect(page.locator("p", { hasText: "第 2 话" })).toBeVisible();

  await page.getByRole("button", { name: "阅读" }).first().click();
  await expect(page).toHaveURL(/\/read\//);
  await page.goBack();

  await page.getByRole("button", { name: "工作室" }).first().click();
  await expect(page).toHaveURL(/\/studio/);

  await deleteProjectByTitle(page, projectTitle);
});
