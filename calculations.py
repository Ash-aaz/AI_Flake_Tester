import statistics
import logging
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_json(json_outputs: list, schema_adapter):
        flake_counter = 0

        for output in json_outputs:
            try:
                schema_adapter.validate_json(output, strict=True)
            except ValidationError:
                flake_counter += 1
    
        logger.info("Flake Counter = %s", flake_counter)

        return flake_counter

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
        
def calculate_percentiles(duration_values: list):
    if (len(duration_values) < 100):
        return (None, None)
    else:
        converted_values = [d * 10**-9 for d in duration_values]
        percentiles = statistics.quantiles(converted_values, n=100, method='exclusive')
        return percentiles[94], percentiles[98]