from __future__ import annotations

import unittest
from pathlib import Path

from src.app.service.evaluation.official import (
    OfficialBenchmarkConfig,
    OfficialBenchmarkService,
    extract_gaia_final_answer,
    gaia_answers_match,
)
from src.factory import create_container


class DayThirteenEvaluationTest(unittest.TestCase):
    def test_evaluation_service_runs_all_required_suites(self) -> None:
        result = create_container().evaluation_service.run_all()
        self.assertIn("summary", result)
        self.assertIn("suites", result)
        for suite_name in ["tool_call", "announcement_risk", "guardrail", "end_to_end", "stability"]:
            self.assertIn(suite_name, result["suites"])
            self.assertGreater(result["suites"][suite_name]["case_count"], 0)

    def test_evaluation_metrics_match_minimum_dataset(self) -> None:
        result = create_container().evaluation_service.run_all()
        summary = result["summary"]
        self.assertEqual(summary["tool_call_accuracy"], 1.0)
        self.assertEqual(summary["risk_identification_f1"], 1.0)
        self.assertEqual(summary["guardrail_interception_rate"], 1.0)
        self.assertEqual(summary["end_to_end_completion_rate"], 1.0)
        self.assertEqual(summary["stability_pass_rate"], 1.0)

    def test_stability_suite_contains_required_failure_modes(self) -> None:
        result = create_container().evaluation_service.evaluate_stability()
        ids = {item["id"] for item in result["details"]}
        self.assertIn("stability_model_unavailable", ids)
        self.assertIn("stability_data_source_unavailable", ids)
        self.assertIn("stability_notification_failure", ids)
        self.assertIn("stability_agent_max_steps", ids)
        self.assertEqual(result["metrics"]["pass_rate"], 1.0)

    def test_static_app_contains_evaluation_panel(self) -> None:
        html = Path("src/static/app.html").read_text(encoding="utf-8")
        js = Path("src/static/app.js").read_text(encoding="utf-8")
        self.assertIn("评估面板", html)
        self.assertIn("/evaluations/run", js)
        self.assertIn("tool_call_accuracy", js)

    def test_official_benchmark_status_is_non_crashing_without_credentials(self) -> None:
        service = OfficialBenchmarkService(OfficialBenchmarkConfig(hf_token=""))
        status = service.status()
        self.assertIn("bfcl", status)
        self.assertIn("gaia", status)
        self.assertFalse(status["gaia"]["has_hf_token"])
        sample = service.load_gaia_sample(limit=1)
        self.assertFalse(sample["available"])
        self.assertTrue("HF_TOKEN" in sample["error"] or "datasets package" in sample["error"])

    def test_gaia_answer_normalization_and_extraction(self) -> None:
        self.assertEqual(extract_gaia_final_answer("Reasoning\nFINAL ANSWER: 1,000."), "1,000.")
        self.assertTrue(gaia_answers_match("1,000.", "1000"))
        self.assertTrue(gaia_answers_match(" FINAL ANSWER: Paris ", "paris"))

    def test_gaia_evaluation_scores_fake_agent_answers(self) -> None:
        service = OfficialBenchmarkService(OfficialBenchmarkConfig(hf_token="fake"))

        class FakeDataset(list):
            pass

        def fake_load(config: str, split: str) -> dict:
            return {
                "available": True,
                "dataset": "gaia-benchmark/GAIA",
                "config": config,
                "split": split,
                "data_dir": "",
                "dataset_obj": FakeDataset(
                    [
                        {
                            "task_id": "gaia_fake_1",
                            "Question": "What is 2+2?",
                            "Level": 1,
                            "Final answer": "4",
                            "file_path": "",
                        },
                        {
                            "task_id": "gaia_fake_2",
                            "Question": "What city?",
                            "Level": 1,
                            "Final answer": "Paris",
                            "file_path": "",
                        },
                    ]
                ),
            }

        service._load_gaia_dataset = fake_load  # type: ignore[method-assign]
        result = service.run_gaia_evaluation(
            limit=2,
            level=1,
            answer_fn=lambda row: f"scratchpad\nFINAL ANSWER: {row['final_answer']}",
            save=False,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["metrics"]["exact_match"], 1.0)


if __name__ == "__main__":
    unittest.main()
