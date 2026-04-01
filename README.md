# FlakeTest-AI: Output Reliability Checker

A local LLM benchmarking tool that validates whether a model outputs valid JSON or hallucinates.

## Project Overview

When an AI model is asked to output valid JSON schemas, it will often hallucinate and include 
artefacts within the output (such as markdown formatting or incorrect types). If generating 
large datasets, this poses a significant risk — poisoned data used for training can result in 
a vastly inferior model output.

This script validates a model's JSON output reliability and assigns it a flake score based on 
total prompts run and hallucinated outputs. A score of 0 means the model made no mistakes. The 
script also uses Ollama telemetry to calculate average tokens/sec generation speed.

## Tech Stack

### Python
Coded entirely in Python. Uses asyncio for concurrent prompt dispatch, Pydantic V2 for strict 
JSON validation, and argparse for the CLI.

### Ollama API
Used to query locally installed models. The `AsyncClient` is shared across all concurrent tasks 
for efficient connection management.

### Pydantic V2
`TypeAdapter.validate_json()` with strict mode is used to validate model outputs against 
predefined schemas. Schemas are defined per difficulty level in `DIFFICULTY_CONFIG`.

### Asyncio
Prompts are dispatched concurrently using `asyncio.gather`. Failed tasks are caught via 
`return_exceptions=True` and counted as flakes rather than crashing the run.

### Pytest
Full async test suite using `pytest` and `pytest-asyncio`. Uses `unittest.mock` with `AsyncMock` 
to isolate network calls and filesystem operations for deterministic testing.

## Prerequisites

### Ollama Setup

**Linux:** Ollama does not run as a GUI. Start the server manually in a terminal before 
running the script and keep it running:
```
ollama serve
```

**Windows/macOS:** The Ollama desktop application handles this automatically.

Pull the desired model before running:
```
ollama pull qwen3:1.7b
```

### Python Dependencies

Python 3.10 or higher required. Install dependencies:
```
pip install -r requirements.txt
```

## Usage
```
python prompt_script.py --model qwen3:1.7b --run 100 --difficulty hard
```

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--model` | Ollama model to test | `qwen3:1.7b` |
| `--run` | Number of prompts to generate | `100` |
| `--difficulty` | Schema complexity: `easy`, `med`, `hard` | `med` |

## Evaluation Metrics

**Flake Score:** Total number of outputs that failed strict Pydantic V2 validation. Catches 
missing keys, type coercion errors (e.g. `"90"` instead of `90`), and markdown wrapping. 
Network failures are also counted as flakes.

**Average T/s:** Model generation speed calculated from Ollama's `eval_count` (tokens) and 
`eval_duration` (nanoseconds). Tasks with zero duration are excluded to prevent division errors.

**CSV Logging:** Results are appended to `models_info.csv` with columns: Model Name, Flake 
Score, Avg. T/s, Test Difficulty.

## Running the Test Suite
```
python -m pytest test_prompt_script.py -v
```

## Project Structure
```
AI_Flake_Tester/
├── prompt_script.py        # Main benchmarking script
├── test_prompt_script.py   # Test suite
├── requirements.txt        
├── models_info.csv         # Generated on first run
└── README.md
```