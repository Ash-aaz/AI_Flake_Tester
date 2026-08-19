import statistics
import logging
from pydantic import ValidationError
from config import ValidationOutput

logger = logging.getLogger(__name__)

# Models can output JSON not following schema. Function validates all outputs
def validate_json(json_outputs: list, schema_adapter):
        errors = ValidationOutput(flake_counter=0, error_distribution={}, failed_outputs=[])

        for output in json_outputs:
            try:
                schema_adapter.validate_json(output, strict=True)

            # Collect error types to document where models might be failing
            except ValidationError as err:
                errors.flake_counter += 1
                error_list = err.errors()
                for e in error_list:
                    errors.error_distribution[e['type']] = errors.error_distribution.get(e['type'], 0) + 1
                    errors.failed_outputs.append(output)

        # Log info
        logger.info("Flake Counter = %s", errors.flake_counter)
        logger.info("Errors Observed: %s", dict(errors.error_distribution))

        return errors

# Provided comparitive data as to how RAG can affect a model's speed
def model_efficiency(duration_values: list, count_values: list):
    i = 0
    total_tps = 0
    current_count = len(duration_values)

    while i < len(duration_values):
        if (duration_values[i] <= 0):
            i += 1
            current_count -= 1
            continue
        tps = (count_values[i]) / (duration_values[i] * (10**-9))
        total_tps += tps
        i += 1
    
    if current_count == 0:
        logger.info("All prompts failed to generate a valid output.")
        return 0
    else:
        avg_tps = total_tps / current_count
        logger.info("Model's average token generation speed is: %s", avg_tps)
        return avg_tps

# Accounts for outliers unlike averages. Requires 100+ runs        
def calculate_percentiles(duration_values: list):
    if (len(duration_values) < 100):
        return (None, None)
    else:
        converted_values = [d * 10**-9 for d in duration_values]
        percentiles = statistics.quantiles(converted_values, n=100, method='exclusive')
        return percentiles[94], percentiles[98]