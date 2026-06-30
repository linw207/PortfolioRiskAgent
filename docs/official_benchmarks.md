# Official BFCL and GAIA Benchmarks

## Why This Is Optional

Day13 already has a deterministic local evaluation set so the project can run without external credentials. Official BFCL and GAIA are now added as optional integrations:

- BFCL official evaluation depends on the `bfcl-eval` package and a supported model handler or OpenAI-compatible endpoint.
- GAIA official data is a gated HuggingFace dataset and requires approved access plus `HF_TOKEN`.

## BFCL

Official source:

- Leaderboard: `https://gorilla.cs.berkeley.edu/leaderboard.html`
- Package: `bfcl-eval`

Install:

```bash
.venv/bin/pip install bfcl-eval
.venv/bin/pip install soundfile
```

Configure:

```bash
export BFCL_PROJECT_ROOT=data/evaluation/bfcl_official
export BFCL_MODEL=<MODEL_NAME_SUPPORTED_BY_BFCL>
export BFCL_TEST_CATEGORY=simple_python
```

`BFCL_MODEL` must use a model key returned by the official CLI:

```bash
.venv/bin/bfcl models
```

The project's Ollama tag `qwen3.5:4b` is valid for the PortfolioRiskAgent runtime, but it is not a BFCL official model key. Nearby BFCL Qwen keys include `qwen3-4b`, `qwen3-4b-FC`, `Qwen/Qwen3-4B`, and `Qwen/Qwen3-4B-FC`. Running the local Ollama tag through BFCL requires a custom BFCL model handler.

Check status:

```bash
.venv/bin/python -B scripts/official_benchmark_status.py
```

Run official CLI through this project:

```bash
.venv/bin/python -B scripts/official_benchmark_status.py --bfcl-mode generate
.venv/bin/python -B scripts/official_benchmark_status.py --bfcl-mode evaluate
```

API:

```bash
curl http://127.0.0.1:8000/evaluations/official/status
curl -X POST http://127.0.0.1:8000/evaluations/official/bfcl/status
```

## GAIA

Official source:

- Dataset: `https://huggingface.co/datasets/gaia-benchmark/GAIA`

Install:

```bash
.venv/bin/pip install datasets huggingface-hub
```

Configure:

```bash
export HF_TOKEN=<YOUR_HUGGINGFACE_TOKEN>
export GAIA_DATASET=gaia-benchmark/GAIA
export GAIA_CONFIG=2023_level1
export GAIA_SPLIT=test
```

The loader follows the official HuggingFace dataset path pattern:

```python
from datasets import load_dataset
from huggingface_hub import snapshot_download

data_dir = snapshot_download(repo_id="gaia-benchmark/GAIA", repo_type="dataset")
dataset = load_dataset(data_dir, "2023_level1", split="test")
```

Load a small sample:

```bash
.venv/bin/python -B scripts/official_benchmark_status.py --gaia-sample --limit 5 --level 1
```

Troubleshooting:

- If `dataset_info` succeeds but `snapshot_download` or `hf_hub_download` returns 403 for files such as `2023/test/metadata.level1.parquet`, the token can see dataset metadata but does not yet have gated file download permission. Re-check the GAIA dataset access request and terms acceptance on HuggingFace.
- If metadata access fails, check `HF_TOKEN` first.

API:

```bash
curl "http://127.0.0.1:8000/evaluations/official/gaia/sample?limit=5&level=1"
curl -X POST "http://127.0.0.1:8000/evaluations/official/gaia/run?config=2023_level1&split=validation&level=1&limit=3"
```

Run GAIA answer-and-score locally:

```bash
.venv/bin/python -B scripts/official_benchmark_status.py \
  --gaia-eval \
  --gaia-config 2023_level1 \
  --gaia-split validation \
  --level 1 \
  --limit 3
```

Scoring boundary:

- `validation` splits include `Final answer`, so this project can run local normalized exact-match scoring after extracting the model's `FINAL ANSWER: ...` line.
- `test` splits intentionally contain private answers (`?`), so the project can generate answers/submissions but cannot compute a local official score.
- The current answer agent uses the configured Ollama chat model. `qwen3-embedding:4b` is not a text generation model; the Ollama server must expose a chat model such as `qwen3:4b` or another configured `OLLAMA_MODEL`.

## Current Boundary

This project can detect official benchmark readiness, load GAIA samples after authorization, and run GAIA validation answer-and-score loops with normalized exact match. Full BFCL scoring still needs a BFCL-supported model handler or API key. Real GAIA model scoring also requires the configured Ollama server to expose a text generation model; the embedding model alone is insufficient.
