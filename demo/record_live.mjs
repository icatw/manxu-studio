#!/usr/bin/env node
/**
 * Headed Chrome recording against the running main app (localhost:5173).
 * Prefers an existing rich project URL when PROJECT_ID is set.
 */
import { createRequire } from "node:module";
import { mkdirSync, readdirSync, copyFileSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUT = join(__dirname, "out");
const VIDEO_DIR = join(OUT, "live-video");
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const cookieName = process.env.COOKIE_NAME ?? "manxu_session";
const cookieValue = process.env.COOKIE_VALUE;
const projectId = process.env.PROJECT_ID ?? "";
const episodeId = process.env.EPISODE_ID ?? "";

if (!cookieValue) {
  console.error("COOKIE_VALUE is required");
  process.exit(1);
}

const require = createRequire(join(ROOT, "frontend/package.json"));
const { chromium } = require("@playwright/test");

async function pause(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function safeClick(page, locator, waitMs = 1500) {
  if ((await locator.count()) === 0) return false;
  await locator.first().click({ timeout: 5000 }).catch(() => {});
  await pause(waitMs);
  return true;
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  if (existsSync(VIDEO_DIR)) rmSync(VIDEO_DIR, { recursive: true, force: true });
  mkdirSync(VIDEO_DIR, { recursive: true });

  console.log(`Opening real Chrome → ${BASE}`);
  const browser = await chromium.launch({
    channel: "chrome",
    headless: false,
    slowMo: 120,
    args: ["--window-size=1440,900", "--window-position=60,40"],
  });

  const context = await browser.newContext({
    locale: "zh-CN",
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });

  await context.addCookies([
    {
      name: cookieName,
      value: cookieValue,
      url: BASE,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  const page = await context.newPage();

  try {
    // 1) Library
    await page.goto(`${BASE}/projects`, { waitUntil: "networkidle" });
    await pause(3500);

    // 2) Open known project overview
    if (projectId) {
      await page.goto(`${BASE}/projects/${projectId}`, { waitUntil: "networkidle" });
    } else {
      const openBtn = page.getByRole("button", { name: /打开/ }).first();
      await safeClick(page, openBtn, 3500);
    }
    await pause(3000);

    // 3) Overview tabs
    for (const name of ["章节", "设定集", "伏笔"]) {
      await safeClick(page, page.getByRole("tab", { name }), 2000);
    }
    await pause(1500);

    // 4) Studio
    if (projectId) {
      const studioUrl = episodeId
        ? `${BASE}/projects/${projectId}/studio?episodeId=${episodeId}`
        : `${BASE}/projects/${projectId}/studio`;
      await page.goto(studioUrl, { waitUntil: "networkidle" });
    } else {
      await safeClick(page, page.getByRole("button", { name: "工作室" }), 2000);
    }
    await pause(4500);

    // Side / mode affordances
    for (const name of ["故事", "角色", "场景", "分镜", "预览", "导出"]) {
      const tab = page.getByRole("tab", { name });
      const btn = page.getByRole("button", { name: new RegExp(name) });
      if (await tab.count()) await safeClick(page, tab, 1800);
      else if (await btn.count()) await safeClick(page, btn, 1800);
    }
    await pause(2500);

    // 5) Reader if possible
    if (projectId && episodeId) {
      await page.goto(`${BASE}/projects/${projectId}/read/${episodeId}`, {
        waitUntil: "networkidle",
      });
      await pause(4000);
    }

    // 6) Back to library
    await page.goto(`${BASE}/projects`, { waitUntil: "networkidle" });
    await pause(3500);
  } finally {
    await context.close();
    await browser.close();
  }

  const videos = readdirSync(VIDEO_DIR).filter((f) => f.endsWith(".webm"));
  if (!videos.length) throw new Error("no video written");
  const dest = join(OUT, "product-live.webm");
  copyFileSync(join(VIDEO_DIR, videos[0]), dest);
  writeFileSync(join(OUT, "product-live.path.txt"), `${dest}\n`);
  console.log(`wrote ${dest}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
