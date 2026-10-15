#!/usr/bin/env node
/**
 * Headless product walkthrough with Playwright video → demo/out/product.webm
 * Requires local stack on :5173 and Mailpit on :8025.
 */
import { chromium } from "playwright";
import { mkdirSync, readdirSync, copyFileSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "out");
const VIDEO_DIR = join(OUT, "pw-video");
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

async function waitForLoginCode(email, afterIso) {
  const normalized = email.trim().toLowerCase();
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const response = await fetch(
      `${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${normalized}`)}`,
    );
    if (!response.ok) throw new Error(`Mailpit HTTP ${response.status}`);
    const payload = await response.json();
    const candidates = (payload.messages ?? [])
      .filter((m) => !afterIso || m.Created >= afterIso)
      .sort((a, b) => b.Created.localeCompare(a.Created));
    for (const summary of candidates) {
      const detail = await (await fetch(`${MAILPIT}/api/v1/message/${summary.ID}`)).json();
      const body = `${detail.Text}\n${detail.HTML}`;
      const match = body.match(/验证码是\s*(\d{6})/);
      if (match?.[1]) return match[1];
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`no login code for ${email}`);
}

async function pause(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  if (existsSync(VIDEO_DIR)) rmSync(VIDEO_DIR, { recursive: true, force: true });
  mkdirSync(VIDEO_DIR, { recursive: true });

  const email = `demo-${Date.now()}@manxu.dev`;
  const title = `演示作品 ${Date.now()}`;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: "zh-CN",
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  try {
    const requestedAt = new Date().toISOString();
    await page.goto(`${BASE}/login`);
    await pause(1200);
    await page.getByPlaceholder("邮箱地址").fill(email);
    await page.getByRole("button", { name: "获取验证码" }).click();
    await page.getByRole("status").filter({ hasText: "验证码已发送" }).waitFor();
    const code = await waitForLoginCode(email, requestedAt);
    await page.getByPlaceholder("6 位验证码").fill(code);
    await page.getByRole("button", { name: "登录或注册" }).click();
    await page.getByRole("heading", { name: "我的作品" }).waitFor({ timeout: 30_000 });
    await pause(2000);

    await page.getByRole("link", { name: /新建|创建/ }).first().click().catch(async () => {
      await page.goto(`${BASE}/projects/new`);
    });
    await pause(1500);

    // Prefer simple create if planner is heavy
    const titleBox = page.getByPlaceholder("例如：雾港来信");
    if (await titleBox.count()) {
      await titleBox.fill(title);
      await page.getByPlaceholder("描述主角、冲突与转折").fill(
        "灯塔看守人失踪后，港口被海雾困住；一封未拆的信成为唯一线索。",
      );
      const createBtn = page.getByRole("button", { name: /创建并进入工作区|创建作品/ });
      if (await createBtn.count()) {
        await createBtn.first().click();
      }
    } else {
      await page.goto(`${BASE}/projects`);
    }

    await pause(2500);
    // Overview or studio
    if (page.url().includes("/projects/")) {
      await pause(2000);
      const studio = page.getByRole("button", { name: "工作室" }).first();
      if (await studio.count()) {
        await studio.click();
        await pause(3000);
      }
      const tabs = ["设定集", "伏笔", "章节"];
      for (const name of tabs) {
        const tab = page.getByRole("tab", { name });
        if (await tab.count()) {
          await tab.click();
          await pause(1200);
        }
      }
    }

    await page.goto(`${BASE}/projects`);
    await page.getByRole("heading", { name: "我的作品" }).waitFor();
    await pause(2500);
  } finally {
    await context.close();
    await browser.close();
  }

  const videos = readdirSync(VIDEO_DIR).filter((f) => f.endsWith(".webm"));
  if (!videos.length) throw new Error("no playwright video written");
  const dest = join(OUT, "product.webm");
  copyFileSync(join(VIDEO_DIR, videos[0]), dest);
  console.log(`wrote ${dest}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
