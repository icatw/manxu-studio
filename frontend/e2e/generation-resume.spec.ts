import { expect, test } from "@playwright/test";
import { createPanelViaApi, createProjectViaApi, envelope } from "./helpers/api";
import { deleteProjectByTitle, loginWithEmail } from "./helpers/auth";

const stamp = Date.now();
const email = `e2e-resume-${stamp}@manxu.dev`;
const projectTitle = `E2E Resume ${stamp}`;
const panelId = crypto.randomUUID();
const taskId = crypto.randomUUID();
const assetId = crypto.randomUUID();
const tinyPng =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

test.describe.configure({ mode: "serial" });

test("reload studio resumes polling an active panel_image task", async ({ page }) => {
  await loginWithEmail(page, email);
  const { projectId, episodeId } = await createProjectViaApi(page, {
    title: projectTitle,
    synopsis: "自动化：刷新后续跑进行中的分镜出图任务。",
  });
  await createPanelViaApi(page, episodeId, panelId);

  let taskPolls = 0;
  await page.route(`**/api/v1/episodes/${episodeId}/generation-tasks**`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const now = new Date().toISOString();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        envelope([
          {
            id: taskId,
            project_id: projectId,
            episode_id: episodeId,
            panel_id: panelId,
            task_type: "panel_image",
            status: "running",
            progress: 35,
            result: null,
            error: null,
            retry_of_task_id: null,
            created_at: now,
            updated_at: now,
          },
        ]),
      ),
    });
  });

  await page.route(`**/api/v1/generation-tasks/${taskId}`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    taskPolls += 1;
    const now = new Date().toISOString();
    const done = taskPolls >= 2;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        envelope({
          id: taskId,
          project_id: projectId,
          episode_id: episodeId,
          panel_id: panelId,
          task_type: "panel_image",
          status: done ? "succeeded" : "running",
          progress: done ? 100 : 55,
          result: done ? { panel_id: panelId, asset_id: assetId } : null,
          error: null,
          retry_of_task_id: null,
          created_at: now,
          updated_at: now,
        }),
      ),
    });
  });

  await page.route(`**/api/v1/panels/${panelId}/image-versions**`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const now = new Date().toISOString();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        envelope([
          {
            id: crypto.randomUUID(),
            panel_id: panelId,
            asset_id: assetId,
            image_url: tinyPng,
            is_current: true,
            created_at: now,
          },
        ]),
      ),
    });
  });

  const listTasks = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().includes(`/episodes/${episodeId}/generation-tasks`) &&
      response.ok(),
  );
  await page.goto(`/projects/${projectId}/studio`);
  await listTasks;
  await expect(page.getByText("正在生成画面…")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("img", { name: /第 1 格/ })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByLabel("Notifications alt+T").getByText("第 1 格已完成")).toBeVisible({
    timeout: 15_000,
  });
  expect(taskPolls).toBeGreaterThanOrEqual(2);

  await deleteProjectByTitle(page, projectTitle);
});
