from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config.settings import get_settings
from src.infra.external.ollama_client import OllamaClient


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


@dataclass(slots=True)
class OfficialBenchmarkConfig:
    hf_token: str = ""
    gaia_dataset: str = "gaia-benchmark/GAIA"
    gaia_config: str = "2023_level1"
    gaia_split: str = "test"
    bfcl_project_root: str = "data/evaluation/bfcl_official"
    bfcl_model: str = ""
    bfcl_test_category: str = "simple_python"


class OfficialBenchmarkService:
    """Optional official BFCL/GAIA integration.

    This layer deliberately keeps official benchmarks optional:
    - BFCL is driven by the official `bfcl-eval` package/CLI when installed.
    - GAIA is loaded from the gated HuggingFace dataset when the user has access.
    """

    def __init__(self, config: OfficialBenchmarkConfig | None = None) -> None:
        self.config = config or OfficialBenchmarkConfig(
            hf_token=os.getenv("HF_TOKEN", ""),
            gaia_dataset=os.getenv("GAIA_DATASET", "gaia-benchmark/GAIA"),
            gaia_config=os.getenv("GAIA_CONFIG", "2023_level1"),
            gaia_split=os.getenv("GAIA_SPLIT", "test"),
            bfcl_project_root=os.getenv("BFCL_PROJECT_ROOT", "data/evaluation/bfcl_official"),
            bfcl_model=os.getenv("BFCL_MODEL", ""),
            bfcl_test_category=os.getenv("BFCL_TEST_CATEGORY", "simple_python"),
        )

    def status(self) -> dict[str, Any]:
        return {
            "bfcl": self.bfcl_status(),
            "gaia": self.gaia_status(),
            "notes": [
                "BFCL official evaluation requires the bfcl-eval package and a supported model handler or OpenAI-compatible endpoint.",
                "GAIA is a gated HuggingFace dataset; access requires approval and HF_TOKEN.",
            ],
        }

    def bfcl_status(self) -> dict[str, Any]:
        bfcl_cli = self._find_bfcl_cli()
        package_available = self._package_available("bfcl_eval")
        project_root = Path(self.config.bfcl_project_root)
        supported_models = self._bfcl_supported_models()
        return {
            "official": True,
            "available": bool(bfcl_cli and package_available),
            "package_available": package_available,
            "cli_path": bfcl_cli or "",
            "project_root": str(project_root),
            "configured_model": self.config.bfcl_model,
            "configured_model_supported": (
                self.config.bfcl_model in supported_models if self.config.bfcl_model else False
            ),
            "ollama_model_note": (
                "BFCL_MODEL must be a model key from `bfcl models`; local Ollama tags such as "
                "`qwen3.5:4b` are not accepted unless a BFCL custom handler is added."
            ),
            "nearby_supported_qwen_models": [
                model
                for model in supported_models
                if model in {"qwen3-4b", "qwen3-4b-FC", "Qwen/Qwen3-4B", "Qwen/Qwen3-4B-FC"}
            ],
            "configured_test_category": self.config.bfcl_test_category,
            "install_command": "pip install bfcl-eval",
            "generate_command": (
                f"BFCL_PROJECT_ROOT={project_root} bfcl generate "
                f"--model {self.config.bfcl_model or '<MODEL_NAME>'} "
                f"--test-category {self.config.bfcl_test_category}"
            ),
            "evaluate_command": (
                f"BFCL_PROJECT_ROOT={project_root} bfcl evaluate "
                f"--model {self.config.bfcl_model or '<MODEL_NAME>'} "
                f"--test-category {self.config.bfcl_test_category}"
            ),
        }

    def gaia_status(self) -> dict[str, Any]:
        return {
            "official": True,
            "available": self._package_available("datasets") and bool(self.config.hf_token),
            "datasets_package_available": self._package_available("datasets"),
            "has_hf_token": bool(self.config.hf_token),
            "dataset": self.config.gaia_dataset,
            "config": self.config.gaia_config,
            "split": self.config.gaia_split,
            "install_command": "pip install datasets huggingface-hub",
            "access_url": "https://huggingface.co/datasets/gaia-benchmark/GAIA",
        }

    def load_gaia_sample(self, limit: int = 5, level: int | None = None) -> dict[str, Any]:
        loaded = self._load_gaia_dataset(self.config.gaia_config, self.config.gaia_split)
        if not loaded["available"]:
            return {**loaded, "items": []}

        data_dir = loaded["data_dir"]
        dataset = loaded["dataset_obj"]
        items = []
        for row in dataset:
            row_level = _read_level(row)
            if level is not None and row_level != level:
                continue
            items.append(_normalize_gaia_row(row, data_dir=data_dir))
            if len(items) >= limit:
                break
        return {
            "available": True,
            "dataset": self.config.gaia_dataset,
            "config": self.config.gaia_config,
            "split": self.config.gaia_split,
            "data_dir": data_dir,
            "limit": limit,
            "level": level,
            "items": items,
        }

    def run_gaia_evaluation(
        self,
        limit: int = 3,
        level: int | None = 1,
        config: str = "2023_level1",
        split: str = "validation",
        answer_fn: Callable[[dict[str, Any]], str] | None = None,
        save: bool = True,
    ) -> dict[str, Any]:
        """Run a GAIA answer-and-score loop.

        GAIA test answers are private, so local scoring is only meaningful on
        validation splits. For test splits this method still generates answers
        but marks scoring as unavailable.
        """

        started = time.perf_counter()
        loaded = self._load_gaia_dataset(config, split)
        if not loaded["available"]:
            return {**loaded, "ok": False, "details": []}
        data_dir = loaded["data_dir"]
        rows = []
        for row in loaded["dataset_obj"]:
            row_level = _read_level(row)
            if level is not None and row_level != level:
                continue
            rows.append(_normalize_gaia_row(row, data_dir=data_dir))
            if len(rows) >= limit:
                break

        answer_fn = answer_fn or self._answer_gaia_with_ollama
        details = []
        correct_count = 0
        scorable_count = 0
        for row in rows:
            item_started = time.perf_counter()
            try:
                raw_answer = answer_fn(row)
                predicted = extract_gaia_final_answer(raw_answer)
                error = ""
            except Exception as exc:  # noqa: BLE001
                raw_answer = ""
                predicted = ""
                error = str(exc)
            expected = row["final_answer"]
            scorable = split != "test" and expected not in {"", "?"}
            correct = scorable and gaia_answers_match(predicted, expected)
            scorable_count += int(scorable)
            correct_count += int(correct)
            details.append(
                {
                    "task_id": row["task_id"],
                    "level": row["level"],
                    "question": row["question"],
                    "raw_file_path": row["raw_file_path"],
                    "file_path": row["file_path"],
                    "expected_answer": expected if scorable else "",
                    "raw_model_output": raw_answer,
                    "predicted_answer": predicted,
                    "normalized_expected": normalize_gaia_answer(expected) if scorable else "",
                    "normalized_predicted": normalize_gaia_answer(predicted),
                    "scorable": scorable,
                    "correct": correct,
                    "error": error,
                    "latency_ms": round((time.perf_counter() - item_started) * 1000, 2),
                }
            )

        result = {
            "ok": True,
            "benchmark": "GAIA",
            "dataset": self.config.gaia_dataset,
            "config": config,
            "split": split,
            "level": level,
            "limit": limit,
            "case_count": len(details),
            "scorable_count": scorable_count,
            "metrics": {
                "exact_match": _safe_ratio(correct_count, scorable_count),
                "correct": correct_count,
                "scorable": scorable_count,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
            "scoring_note": (
                "Local exact-match scoring is available for validation splits. "
                "GAIA test split answers are private and require leaderboard submission."
            ),
            "details": details,
        }
        if save:
            result.update(self._save_gaia_result(result))
        return result

    def _load_gaia_dataset(self, config: str, split: str) -> dict[str, Any]:
        try:
            from datasets import load_dataset
            from huggingface_hub import snapshot_download
        except ImportError:
            return {
                "available": False,
                "error": "datasets or huggingface-hub package is not installed. Run: pip install datasets huggingface-hub",
                "items": [],
            }
        if not self.config.hf_token:
            return {
                "available": False,
                "error": "HF_TOKEN is not configured. GAIA is gated and requires HuggingFace access approval.",
                "items": [],
            }
        try:
            data_dir = snapshot_download(
                repo_id=self.config.gaia_dataset,
                repo_type="dataset",
                token=self.config.hf_token,
            )
            dataset = load_dataset(
                data_dir,
                config,
                split=split,
                token=self.config.hf_token,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "error": str(exc),
                "dataset_obj": None,
            }
        return {
            "available": True,
            "dataset": self.config.gaia_dataset,
            "config": config,
            "split": split,
            "data_dir": data_dir,
            "dataset_obj": dataset,
        }

    def _answer_gaia_with_ollama(self, row: dict[str, Any]) -> str:
        model_settings = get_settings().model
        gaia_timeout = float(os.getenv("GAIA_MODEL_TIMEOUT_SECONDS", str(max(model_settings.timeout_seconds, 180))))
        client = OllamaClient(replace(model_settings, timeout_seconds=gaia_timeout))
        prompt = build_gaia_prompt(row)
        return client.generate(
            prompt,
            system=(
                "You are a GAIA benchmark answer engine. "
                "Do not show reasoning, calculations, caveats, citations, or explanations. "
                "Use the provided attachment excerpt when present. "
                "The final answer must use exactly the unit and granularity requested by the question; "
                "do not expand or convert it to another unit in the final line. "
                "Output exactly one line: FINAL ANSWER: <answer>."
            ),
            think=False,
            num_predict=256,
        )

    def _save_gaia_result(self, result: dict[str, Any]) -> dict[str, str]:
        output_dir = Path("data/evaluation/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"gaia_{result['config']}_{result['split']}_{timestamp}.json"
        report_path = output_dir / f"gaia_{result['config']}_{result['split']}_{timestamp}.md"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(_render_gaia_markdown(result), encoding="utf-8")
        return {"result_json": str(json_path), "result_report": str(report_path)}

    def run_bfcl_cli(self, mode: str = "status") -> dict[str, Any]:
        if mode not in {"generate", "evaluate", "status"}:
            raise ValueError("mode must be one of: status, generate, evaluate")
        status = self.bfcl_status()
        if mode == "status":
            return status
        if not status["available"]:
            return {"ok": False, "error": "bfcl-eval CLI is not available", "status": status}
        if not self.config.bfcl_model:
            return {"ok": False, "error": "BFCL_MODEL is not configured", "status": status}
        Path(self.config.bfcl_project_root).mkdir(parents=True, exist_ok=True)
        command = [
            status["cli_path"],
            mode,
            "--model",
            self.config.bfcl_model,
            "--test-category",
            self.config.bfcl_test_category,
        ]
        env = {**os.environ, "BFCL_PROJECT_ROOT": self.config.bfcl_project_root}
        completed = subprocess.run(command, env=env, check=False, capture_output=True, text=True, timeout=3600)
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "command": " ".join(command),
            "project_root": self.config.bfcl_project_root,
        }

    def _package_available(self, name: str) -> bool:
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    def _find_bfcl_cli(self) -> str:
        bfcl_cli = shutil.which("bfcl")
        if bfcl_cli:
            return bfcl_cli
        for candidate in (Path(sys.executable).parent / "bfcl", Path(sys.executable).resolve().parent / "bfcl"):
            if candidate.exists():
                return str(candidate)
        return ""

    def _bfcl_supported_models(self) -> list[str]:
        try:
            from bfcl_eval.constants.supported_models import SUPPORTED_MODELS

            return list(SUPPORTED_MODELS)
        except Exception:  # noqa: BLE001
            return []


def _read_level(row: dict[str, Any]) -> int | None:
    raw = row.get("Level") or row.get("level")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _normalize_gaia_row(row: dict[str, Any], data_dir: str = "") -> dict[str, Any]:
    raw_file_path = str(row.get("file_path") or row.get("file_name") or row.get("file") or "")
    file_path = str(Path(data_dir) / raw_file_path) if data_dir and raw_file_path else ""
    return {
        "task_id": str(row.get("task_id") or row.get("id") or ""),
        "level": _read_level(row),
        "question": str(row.get("Question") or row.get("question") or ""),
        "final_answer": str(row.get("Final answer") or row.get("final_answer") or ""),
        "file_path": file_path,
        "raw_file_path": raw_file_path,
    }


def build_gaia_prompt(row: dict[str, Any]) -> str:
    attachment = _read_attachment_preview(row.get("file_path", ""))
    parts = [
        f"Task ID: {row.get('task_id', '')}",
        f"Question:\n{row.get('question', '')}",
    ]
    if attachment:
        parts.append(f"Attachment excerpt:\n{attachment}")
    parts.append("Output exactly one line and nothing else: FINAL ANSWER: <answer>")
    parts.append(
        "Important: preserve the requested answer unit. For example, if the question asks for the number of "
        "thousand hours, answer the number of thousands, not the equivalent number of hours."
    )
    return "\n\n".join(parts)


def extract_gaia_final_answer(output: str) -> str:
    matches = re.findall(r"FINAL ANSWER\s*:\s*(.+)", output, flags=re.IGNORECASE)
    if matches:
        return matches[-1].strip()
    return output.strip().splitlines()[-1].strip() if output.strip() else ""


def normalize_gaia_answer(answer: str) -> str:
    text = str(answer).strip().lower()
    text = re.sub(r"^final answer\s*:\s*", "", text)
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" \t\n\r.。!！?？")
    try:
        value = float(text)
        if value.is_integer():
            return str(int(value))
        return f"{value:.10g}"
    except ValueError:
        return text


def gaia_answers_match(predicted: str, expected: str) -> bool:
    return normalize_gaia_answer(predicted) == normalize_gaia_answer(expected)


def _read_attachment_preview(file_path: str, max_chars: int = 6000) -> str:
    if not file_path:
        return ""
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() not in {".txt", ".csv", ".json", ".xml"}:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if denominator == 0 else round(float(numerator) / float(denominator), 4)


def _render_gaia_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# GAIA Evaluation Report",
        "",
        f"- Config: `{result['config']}`",
        f"- Split: `{result['split']}`",
        f"- Level: `{result['level']}`",
        f"- Cases: {result['case_count']}",
        f"- Exact match: {result['metrics']['exact_match']}",
        f"- Correct/scorable: {result['metrics']['correct']}/{result['metrics']['scorable']}",
        f"- Elapsed: {result['metrics']['elapsed_ms']} ms",
        "",
        "| Task | Expected | Predicted | Correct |",
        "| --- | --- | --- | --- |",
    ]
    for detail in result["details"]:
        expected = str(detail.get("expected_answer", "")).replace("|", "\\|")
        predicted = str(detail.get("predicted_answer", "")).replace("|", "\\|")
        lines.append(f"| `{detail['task_id']}` | {expected} | {predicted} | {detail['correct']} |")
    return "\n".join(lines).strip() + "\n"
