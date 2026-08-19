# AI Flake Tester — Observations

An architecture that tests a local AI model's capability of adhering to strict structured outputs - in this case, following a strict JSON schema. The measurement is split into two modes: the base mode gives the model a universal system prompt depending on the difficulty tier, while the RAG mode injects additional context from a reference PDF. An earlier version of this benchmark produced a confident architectural finding (GDN incompatibility with RAG) that turned out to be entirely a measurement artifact. After fixing five pipeline defects, the general observation is that RAG improves schema adherence in specific, attributable cases rather than uniformly.

# Setup

## Models Tested
- **gemma4:e4b** - Mixture of Experts, standard transformer attention
- **qwen3:1.7b** - 1.7B dense, standard transformer attention
- **qwen3.5:2b** - 2B dense, GDN (Gated DeltaNet) hybrid attention
- **qwen3.5:9b** - 9.7B dense, GDN hybrid attention
- **ibm/granite4.1:3b** - 3.4B dense, standard transformer attention

## Difficulty Tiers
- **easy:** Flat schema with explicit values. Server outage log extraction - three servers, downtime in minutes, boolean criticality. No inference required beyond unit conversion.
- **med:** Single nesting level with mild ambiguity. Project status memo - enum inference for status, natural language budget conversion to float, nested team members with lead designation, blockers as empty list not null.
- **hard:** Two nesting levels with enum inference and nullable fields. Security incident report - six-value attack type enum inferred from informal language, four-value recovery status, responder role enums, `Optional[float]` for data loss, `Optional[datetime]` for detection timestamp.
- **ultra:** Three nesting levels with multiple clinical enums and asymmetric nullable fields. Adverse event report - severity and causality inferred from hedged clinical language, two events with different nullable field values, intervention effectiveness as `Optional[bool]` varying between null and true across entries.

## Measurement Metric
The primary metric is the *flake score* - measured using Pydantic V2's strict mode with a binary pass or fail per output generated. Each invalid schema increments the score by one; a perfect score is zero.

## Observed Error Types
- **json_invalid:** Output is not parseable JSON at all - includes markdown wrapping, reasoning text mixed into output, truncated responses, and empty response bodies.
- **missing:** Output is valid JSON but one or more required fields are absent. A single output can produce multiple missing errors if several fields are dropped.
- **literal_error:** Output contains a field value that does not match the allowed enum - e.g. `"description"` where the schema requires one of `"medication"`, `"procedure"`, `"monitoring"`, or `"none"`.
- **datetime_parsing:** A datetime field contains a string that cannot be parsed as a valid ISO 8601 datetime - e.g. the model outputs `"late Tuesday"` instead of null.

## RAG Pipeline
PDF → section chunks (`Section` serves as the separator word) → nomic-embed-text v1.5 embeds the extracted chunks → FAISS IndexFlatL2 creates the indexed vectors → nearest chunk to the system prompt is retrieved and injected into the prompt as additional context.

## Hardware & Configuration
- **GPU:** RTX 5080 Mobile Laptop GPU (16GB VRAM)
- **Ollama Version:** 0.30.6
- **num_ctx:** 20000
- **Sampling:** left at model defaults (unpinned)
- **Runs:** 100 per model-difficulty configuration

# False Hypothesis
In an earlier version of the project the Qwen3.5 family consistently showed degraded performance when RAG was introduced. This led to a hypothesis that GDN based architecture could perform worse at strict schema adherence with RAG compared to standard attention transformers. However, later data revealed that the score surfaced from three primary issues:
1. Due to the Qwen3.5 family having thinking capabilities the model would eat up its context window and since the earlier version discarded `response.thinking` and only considered `response.response` all of the model's work would be thrown away. This resulted in `json_invalid` errors since to the script the model never responded.
2. Ollama by default restricts the context windows for the model to `4096` tokens. The Qwen3.5 would often spend its entire context budget thinking about the problem rather than outputting a valid response.
3. Additionally an earlier version of the PDF contained contradictions to the system prompt. When provided with contradictory information the model's token consumption problem would be aggravated trying to resolve it leading to extremely long run times and high flake scores.

Once the PDF was fixed and the context window was extended to `20000` the catastrophic performance degradation disappeared and the results were either neutral or slightly positive.

# Results

| Model | Tier | Base | RAG | Base Error (type × count) | RAG Error (type × count) | Effect |
|---|---|---|---|---|---|---|
| gemma4:e4b | easy | 0 | 0 | — | — | neutral |
| gemma4:e4b | med | 6 | 3 | json_invalid × 6 | json_invalid × 3 | neutral |
| gemma4:e4b | hard | 27 | 28 | json_invalid × 27 | json_invalid × 28 | neutral |
| gemma4:e4b | ultra | 63 | 0 | literal_error × 61 | — | ✓ improved |
| granite4.1:3b | easy | 0 | 0 | — | — | neutral |
| granite4.1:3b | med | 19 | 0 | missing × 41 | — | ✓ improved |
| granite4.1:3b | hard | 0 | 0 | — | — | neutral |
| granite4.1:3b | ultra | 15 | 0 | missing × 29 | — | ✓ improved |
| qwen3:1.7b | easy | 0 | 0 | — | — | neutral |
| qwen3:1.7b | med | 0 | 0 | — | — | neutral |
| qwen3:1.7b | hard | 9 | 24 | datetime_parsing × 5 | missing × 72 | ✗ degraded |
| qwen3:1.7b | ultra | 92 | 69 | missing × 230 | missing × 193 | ✓ improved |
| qwen3.5:2b | easy | 4 | 3 | json_invalid × 4 | missing × 3 | neutral |
| qwen3.5:2b | med | 23 | 20 | json_invalid × 17 | json_invalid × 17 | neutral |
| qwen3.5:2b | hard | 39 | 21 | json_invalid × 24 | literal_error × 14 | ✓ improved |
| qwen3.5:2b | ultra | 95 | 96 | missing × 178 | missing × 208 | neutral† |
| qwen3.5:9b | easy | 0 | 0 | — | — | neutral† |
| qwen3.5:9b | med | 0 | 0 | — | — | neutral† |
| qwen3.5:9b | hard | 1 | 1 | json_invalid × 1 | json_invalid × 1 | neutral† |
| qwen3.5:9b | ultra | 30 | 23 | missing × 27 | missing × 31 | neutral† |
| granite4.1:3b | med | 10 | 0 | missing × 41 | — | ✓ improved |
| granite4.1:3b | ultra | 32 | 2 | missing × 29 | — | ✓ improved |

† bounded - qwen3.5:2b and qwen3.5:9b eval_counts approach or hit the 20000 num_ctx ceiling; true flake rate may be lower

**Reproducibility note:** Granite baselines shifted across two runs — med moved from 19 to 10, ultra from 15 to 32. RAG results were stable at 0 in both batches. All sampling was left at model defaults (unpinned temperature). The variance suggests baselines are single draws from a wide distribution; the RAG stability suggests the reference PDF removes the ambiguity.

# Findings

## Non-Uniform Effect
RAG's effect on structured output compliance is non-uniform. Of the 20 model-tier pairs tested, four showed clear improvement, one showed clear degradation, and the remainder were neutral.

## Attributable Improvements
Where RAG improved scores, the improvement maps to a specific field and a specific PDF rule:

| Model / Tier | Base | RAG | Failed Field | PDF Rule |
|---|---|---|---|---|
| gemma4:e4b ultra | 63 | 0 | `intervention_type` = "description" | medication covers topical agents |
| granite4.1:3b ultra | 15–32 | 0–2 | `effective` omitted (3 per output) | effectiveness always present, never omitted |
| granite4.1:3b med | 10–19 | 0 | `is_lead`, `blockers` omitted | not-lead recorded explicitly; empty list not null |
| qwen3:1.7b ultra | 92 | 69 | `missing` 230→193 | partial improvement, not fully resolved |

Granite baselines are given as ranges across two batches; RAG results were stable in both.

## Reduced Variance
RAG reduced output variance across repeated runs. Baseline scores shifted by up to 2× between batches (granite med: 19 then 10; granite ultra: 15 then 32) while RAG scores for the same configurations remained at or near zero. The reference PDF removes the ambiguity the model was resolving stochastically.

## Small-Model Degradation
qwen3:1.7b on hard degraded from 9 to 24 with RAG. The dominant error type shifted from `datetime_parsing` (5) to `missing` (72) — the added context caused the model to drop required fields it could otherwise produce, suggesting the injected prompt exceeded what the model could hold alongside a moderately complex schema.

## Reduced Reasoning Cost
Reasoning-enabled models consumed substantially fewer tokens with RAG. qwen3.5:9b on ultra dropped from ~18,700 to ~6,000 eval tokens per request - the reference PDF removed the need to deliberate over enum boundaries. For structured output tasks where the answer is either schema-valid or not, deliberation does not reliably improve the outcome, and the reduced token cost is a practical benefit for deployment.

## Error Taxonomy as a Measurement Contribution
The flake score alone cannot distinguish unparseable output from a single wrong enum value. Adding error type distribution as a metric made the improvement claims mechanistic rather than correlational — without it, gemma4 ultra going from 63 to 0 is an observed number; with it, the cause is identifiable as a single `intervention_type` enum that the PDF resolved.

# Not Supported
- No architectural correlation was found between attention mechanism design and RAG's effect on structured outputs. GDN-based models and standard attention transformers showed comparable patterns once pipeline defects were resolved.
- No singular complexity threshold exists where RAG consistently influences the score in one direction. `gemma4:e4b` improves at ultra but not hard. `granite4.1:3b` improves at med and ultra but not hard. `qwen3:1.7b` degrades at hard but improves at ultra.
- The majority of runs were neutral. A blanket claim that "RAG improves structured output adherence" is not supported by this data.

# Limitations
- Tested on a single hardware configuration (RTX 5080 Mobile, 16GB VRAM)
- Sampling parameters left at model defaults and unpinned across runs. Baseline magnitude shifts of up to 2x were observed; precise flake scores are single draws from a wide distribution
- Tests used a single PDF and one prompt per difficulty tier
- qwen3.5 family rows are bounded by the 20000 `num_ctx` ceiling. True flake rates may be lower
- Flake score measures schema compliance, not extraction accuracy. A model can score zero while emitting factually incorrect field values. For example, `duration_hours: null` was accepted for a stated 24-hour resolution, and `"role": "lead"` was accepted where `"backend"` was correct, because `Optional[int]` and plain `str` admit both

# Reproducing

## Prerequisites
- [Ollama](https://ollama.com/) installed and running via `ollama serve`
- Required models pulled:
    ```
    ollama pull gemma4:e4b
    ollama pull qwen3:1.7b
    ollama pull qwen3.5:2b
    ollama pull qwen3.5:9b
    ollama pull ibm/granite4.1:3b
    ollama pull nomic-embed-text:v1.5
    ```
- Python 3.10+ with dependencies installed:
    `pip install -r requirements.txt`

## Running a base benchmark
`python main.py --model gemma4:e4b --run 100 --difficulty ultra --concurrency 10`

## Running a RAG benchmark
`python rag_benchmark.py --model gemma4:e4b --run 100 --difficulty ultra --concurrency 10 --pdf rag_benchmark.pdf`

## Generating Graphs
`python visualise.py`

## Running the Test Suite
`python -m pytest test_main.py test_calculations.py test_visualise.py test_rag_benchmark.py -v`


## Important notes
- `num_ctx` is set to 20000 in both `main.py` and `rag_benchmark.py`. Reasoning-enabled models (qwen3.5 family, gemma4) consume substantially more context than non-reasoning models. Lowering this value will produce truncation artifacts, particularly `json_invalid` errors with identical `eval_count` values across requests.
- `ollama serve` must be running in a separate terminal before executing any benchmark.
- Results are appended to `models_info.csv`. Delete or rename the file before a fresh run to avoid mixing datasets.
- Logs are written to `logs/base/` and `logs/rag/` with per-model-per-difficulty filenames.