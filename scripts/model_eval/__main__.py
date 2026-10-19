"""CLI: python -m model_eval --config baseline --case A-duo --trials 1"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from model_eval.configs import build_configs
from model_eval.scoring import TrialScore, summarize_scores
from model_eval.trajectory import run_trial

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_OUT = REPO_ROOT / "var" / "model-eval" / "runs"
SCORECARD_TEMPLATE = Path(__file__).resolve().parent / "templates" / "blind_scorecard.csv"


def _load_cases(selected: list[str] | None) -> list[dict]:
    cases = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if selected and payload["id"] not in selected:
            continue
        cases.append(payload)
    if not cases:
        raise SystemExit(f"未找到 fixture（dir={FIXTURES_DIR}, selected={selected}）")
    return cases


def _require_live() -> None:
    if os.environ.get("MODEL_EVAL_LIVE", "").strip() != "1":
        raise SystemExit(
            "拒绝执行：设置 MODEL_EVAL_LIVE=1 才会调用真实模型。"
            "密钥用环境变量注入，勿写入仓库。"
        )


async def _async_main(args: argparse.Namespace) -> int:
    _require_live()
    configs = build_configs()
    selected_configs = args.config or list(configs.keys())
    for config_id in selected_configs:
        if config_id not in configs:
            raise SystemExit(f"未知配置: {config_id}；可选: {', '.join(configs)}")

    cases = _load_cases(args.case)
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(args.out or DEFAULT_OUT) / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "configs": selected_configs,
        "cases": [case["id"] for case in cases],
        "trials": args.trials,
        "skip_images": args.skip_images,
        "with_agnes_refs": args.with_agnes_refs,
        "panel_image_limit": args.panel_image_limit,
        "note": (
            "Arm A = prompt-only images (default). "
            "Arm B = --with-agnes-refs (Agnes only; not directly comparable to baseline)."
        ),
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if SCORECARD_TEMPLATE.exists():
        shutil.copy(SCORECARD_TEMPLATE, out_root / "blind_scorecard.csv")

    trials: list[TrialScore] = []
    for config_id in selected_configs:
        config = configs[config_id]
        for case in cases:
            for trial_index in range(1, args.trials + 1):
                trial_dir = out_root / config_id / case["id"]
                print(
                    f"[model-eval] config={config_id} case={case['id']} "
                    f"trial={trial_index}/{args.trials}",
                    flush=True,
                )
                score = await run_trial(
                    config=config,
                    case=case,
                    trial_index=trial_index,
                    out_dir=trial_dir,
                    skip_images=args.skip_images,
                    with_agnes_refs=args.with_agnes_refs,
                    panel_image_limit=args.panel_image_limit,
                )
                trials.append(score)
                print(
                    f"  -> outcome_pass={score.outcome_pass} "
                    f"first_failure={score.first_failure} "
                    f"latency_ms={score.total_latency_ms}",
                    flush=True,
                )

    summary = summarize_scores(trials)
    (out_root / "summary.json").write_text(
        json.dumps(
            {"manifest": manifest, "summary": summary, "trials": [t.to_dict() for t in trials]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_summary_csv(out_root / "summary.csv", summary)
    print(f"[model-eval] done -> {out_root}", flush=True)
    return 0


def _write_summary_csv(path: Path, summary: dict) -> None:
    rows = summary.get("groups") or []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "key",
                "trials",
                "pass_count",
                "pass_at_1",
                "avg_latency_ms",
                "avg_images",
                "first_failures",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "first_failures": "|".join(row.get("first_failures") or []),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manxu offline model evaluation harness")
    parser.add_argument(
        "--config",
        action="append",
        help="配置 id，可重复；默认全部（baseline,agnes-full,mix-text,mix-image）",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="fixture id，可重复；默认全部（A-duo,B-crowd,C-style）",
    )
    parser.add_argument("--trials", type=int, default=2, help="每配置×case 的重复次数")
    parser.add_argument("--skip-images", action="store_true", help="只跑文本阶段")
    parser.add_argument(
        "--with-agnes-refs",
        action="store_true",
        help="Arm B：Agnes 出图时附带定妆/上一格参考（勿与 baseline 直接横比）",
    )
    parser.add_argument("--panel-image-limit", type=int, default=4)
    parser.add_argument("--out", type=str, default="", help="输出根目录，默认 var/model-eval/runs")
    parser.add_argument("--run-id", type=str, default="")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
