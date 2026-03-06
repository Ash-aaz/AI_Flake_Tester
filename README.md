# FlakeTest-AI: Output Reliability Checker

A Local LLM benchmarking tool that validates if the model outputs valid JSON or hallucinates.

## Project Overview

When an AI model is asked to output valid JSON schemas often times it might hallucinate and include artifact within the schema (such as using markdown).
If generating large datasets this poses a massive since the data might end up becoming poisoned by the model's hallucination. If this data
is then used to for training it might result in a vastly inferior output than initially expected.

This script aims to run validate a model's JSON output abilities and give it a score based on total prompts ran, and hallucinated outputs. A model scoring 0
means the model didn't make any mistakes during data generation. Additionally, the script also uses telemetry data to calculate the model's average tokens/sec
output speed.

## Tech Stack

### Python
The project scripts are coded entirely in Python to make use of its vast array of libraries that helped simplify passing the
large number of prompts to the selected model and testing the scripts validation techniques.

### Ollama API
Ollama's API was used to validate that the user has the desired model installed on their device and then ping it for generating the JSON 
output that'll be tested.

### Pydantic
The `pydantic` library, specifically the `.validate.json()` function they offer was specifically used to test the validdity of the JSON
schemas outputted by the models.

### Asyncio
The model's output and generation quality were tested by giving it the same prompt a 100 times. To ensure efficient usage of time the `asyncio` library was used
to send several requests to the API simultaenously.

### Pytest
To ensure that the script was able to differentiate between correct JSON schemas and incorrect ones `pytest` was used to check the script throws out invalid JSON schemas.
The `@pytest.mark.parametrize()` function was used to test a plethora of invalid scenarios such as: markdown generation and missing keys.

## Running the Script

### Prerequisites
* Ensure **Ollama** is installed on your device and running in the background
* The desired must be downloaded in Ollama or pulled from the terminal(e.g. `ollama pull qwen3:1.7b`)

### Installations
* Ensure you have **Python 3.10** or higher installed.
* The script depends on a few key libraries ensure you have the following installed before running the scipt:
`pip install pydantic>=2.0.0 ollama pytest pytest-asyncio`

## Usage (Command Line Interface)

The script is executed via the command line. It utilises the `argparse` library to allow users to easily configure their benchmarking parameters without altering the code. The following flags are available:

* `--model`: Specifies the local LLM to be tested. (Default: `qwen3:1.7b`)
* `--run`: Sets the total number of prompts the model should generate during the test. (Default: `100`)
* `--difficulty`: Determines the complexity of the JSON schema the model is required to output. Available options are `easy`, `med`, and `hard`. (Default: `easy`)

**Example Command:**
`python prompt_script.py --model qwen3:1.7b --run 100 --difficulty hard`

## Evaluation Metrics

* **Flake Score:** This calculates the total number of times the model failed to output a valid JSON schema. By utilising Pydantic V2's Strict Mode, the script mercilessly catches common AI hallucinations. This includes missing keys, improper type coercion (such as outputting a string "90" instead of an integer 90), and "Markdown Traps" where the model wraps the JSON in standard markdown formatting.

* **Average T/s (Tokens per Second):** This calculates the model's generation efficiency. The script extracts the eval_duration (provided in nanoseconds by the Ollama API) and converts it into standard seconds (multiplying by 10^-9) before dividing the total eval_count (tokens) by this duration. The framework also includes a safeguard to drop the iteration count and prevent zero-division errors if the API crashes or returns an empty payload.

* **Data Logging:** Upon completion, the script logs the test results, including the model name, difficulty level, total iterations, average T/s, and final Flake Score. This data is dynamically appended to a models_info.csv file for easy academic review and comparison.

## Testing Methodology

To ensure high software reliability and accuracy in the benchmarking math, the framework is backed by a fully automated, asynchronous test suite using `pytest`.

The validation logic is rigorously tested using `@pytest.mark.parametrize` to feed the system a plethora of targeted "Flake Vectors" (e.g., hallucinated strings, markdown traps, or malformed data) to guarantee the strict validation catches errors as intended. Furthermore, the suite employs `unittest.mock` to intercept network calls and isolate the file-system. This allows for deterministic math and integration testing without actually pinging the Ollama API or overwriting the real CSV data.