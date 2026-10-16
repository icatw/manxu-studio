import type { APIRequestContext, Page } from "@playwright/test";

type Envelope<T> = { code: string; message: string; data: T; request_id: string };

async function csrfHeader(page: Page): Promise<Record<string, string>> {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === "manxu_csrf")?.value;
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

async function readData<T>(response: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> {
  if (!response.ok()) {
    throw new Error(`API ${response.status()}: ${await response.text()}`);
  }
  const body = (await response.json()) as Envelope<T>;
  return body.data;
}

export async function createProjectViaApi(
  page: Page,
  input: { title: string; synopsis: string },
): Promise<{ projectId: string; episodeId: string }> {
  const headers = await csrfHeader(page);
  const project = await readData<{ id: string }>(
    await page.request.post("/api/v1/projects", {
      headers,
      data: {
        title: input.title,
        synopsis: input.synopsis,
        genre: "玄幻",
        art_style: "日系漫画",
        aspect_ratio: "landscape",
      },
    }),
  );
  let episodes = await readData<Array<{ id: string }>>(
    await page.request.get(`/api/v1/projects/${project.id}/episodes`),
  );
  if (!episodes[0]?.id) {
    const created = await readData<{ id: string }>(
      await page.request.post(`/api/v1/projects/${project.id}/episodes`, {
        headers,
        data: { title: input.title, synopsis: input.synopsis, panel_count: 1 },
      }),
    );
    episodes = [created];
  }
  return { projectId: project.id, episodeId: episodes[0].id };
}

export async function setEpisodeSummaryViaApi(
  page: Page,
  episodeId: string,
  summary: string,
): Promise<void> {
  const headers = await csrfHeader(page);
  await readData(
    await page.request.patch(`/api/v1/episodes/${episodeId}`, {
      headers,
      data: { summary },
    }),
  );
}

export async function createPanelViaApi(
  page: Page,
  episodeId: string,
  panelId: string,
): Promise<void> {
  const headers = await csrfHeader(page);
  await readData(
    await page.request.post(`/api/v1/episodes/${episodeId}/panels`, {
      headers,
      data: {
        id: panelId,
        scene_description: "雾港灯塔",
        shot: "中景",
        composition: "居中",
        character_actions: "看守人望向海面",
        emotion: "凝重",
        dialogue: "",
        story_purpose: "建立氛围",
        image_prompt: "foggy harbor lighthouse at dusk, cinematic",
        character_ids: [],
      },
    }),
  );
}

export function envelope<T>(data: T) {
  return {
    code: "OK",
    message: "请求成功",
    data,
    request_id: crypto.randomUUID(),
  };
}
