const mailpitBase = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

type MailpitMessageSummary = {
  ID: string;
  To: Array<{ Address: string }>;
  Subject: string;
  Created: string;
};

type MailpitMessage = {
  ID: string;
  Text: string;
  HTML: string;
};

export async function waitForLoginCode(email: string, afterIso?: string): Promise<string> {
  const normalized = email.trim().toLowerCase();
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const response = await fetch(
      `${mailpitBase}/api/v1/search?query=${encodeURIComponent(`to:${normalized}`)}`,
    );
    if (!response.ok) {
      throw new Error(`Mailpit search failed: HTTP ${response.status}`);
    }
    const payload = (await response.json()) as { messages?: MailpitMessageSummary[] };
    const candidates = (payload.messages ?? [])
      .filter((message) => !afterIso || message.Created >= afterIso)
      .sort((a, b) => b.Created.localeCompare(a.Created));

    for (const summary of candidates) {
      const detailResponse = await fetch(`${mailpitBase}/api/v1/message/${summary.ID}`);
      if (!detailResponse.ok) continue;
      const detail = (await detailResponse.json()) as MailpitMessage;
      const body = `${detail.Text}\n${detail.HTML}`;
      const match = body.match(/验证码是\s*(\d{6})/);
      if (match?.[1]) return match[1];
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for login code for ${normalized}`);
}
