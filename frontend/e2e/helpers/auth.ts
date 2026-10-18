import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";
import { waitForLoginCode } from "./mailpit";

export async function loginWithEmail(page: Page, email: string): Promise<void> {
  const requestedAt = new Date().toISOString();
  await page.goto("/login");
  await page.getByPlaceholder("邮箱地址").fill(email);
  await page.getByRole("button", { name: "获取验证码" }).click();
  await page.getByRole("status").filter({ hasText: "验证码已发送" }).waitFor();
  const code = await waitForLoginCode(email, requestedAt);
  await page.getByPlaceholder("6 位验证码").fill(code);
  await page.getByRole("button", { name: "登录或注册" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30_000 });
  await page.getByRole("heading", { name: "我的作品" }).waitFor();
}

async function waitForProjectListReady(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "我的作品" }).waitFor();
  await expect(page.getByText("正在加载作品…")).toHaveCount(0);
  // Count chip like "1 部作品" appears once list query settles.
  await expect(page.getByText(/\d+\s*部作品/)).toBeVisible();
}

export async function deleteProjectByTitle(page: Page, title: string): Promise<void> {
  await page.goto("/projects");
  await waitForProjectListReady(page);

  const openButton = page.getByRole("button", { name: `打开「${title}」` });
  if ((await openButton.count()) === 0) return;

  const article = page.locator("article").filter({ has: openButton }).first();
  await article.getByRole("button", { name: `删除${title}` }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toBeVisible();

  const deleted = page.waitForResponse(
    (response) =>
      response.request().method() === "DELETE" &&
      /\/api\/v1\/projects\/[0-9a-f-]+$/.test(response.url()),
  );
  await dialog.getByRole("button", { name: "删除作品" }).click();
  const result = await deleted;
  expect(result.ok(), `delete status ${result.status()}`).toBeTruthy();
  await expect(openButton).toHaveCount(0, { timeout: 15_000 });
}
