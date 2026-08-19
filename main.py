import os
import asyncio
import csv
import argparse
import psutil
from config import DIFFICULTY_CONFIG
from calculations import validate_json, model_efficiency, calculate_percentiles
from ollama import AsyncClient
import logging

logger = logging.getLogger(__name__)

class FlakeTester:
    def __init__(self, agent, total_count, prompt_difficulty, concurrency, client):
        self.agent = agent
        self.total_count = total_count
        self.prompt_difficulty = prompt_difficulty
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = client

    # Wait for model's response then return all relevant data as a tuple
    async def generate(self):
        message = DIFFICULTY_CONFIG[self.prompt_difficulty]['prompt']

        async with self.semaphore:
            response = await self.client.generate(model=self.agent, prompt=message, options={"num_ctx": 20000})
            return (response.response, response.eval_duration, response.eval_count, response.thinking)

    # Add collected data to CSV file for easier access
    def add_data(self, column_name, model_data):
        if os.path.isfile('models_info.csv'):
                with open('models_info.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(model_data)
    
        else:
            with open('models_info.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(column_name)
                writer.writerow(model_data)


    async def main(self):
        tasks = [asyncio.create_task(self.generate()) for _ in range(self.total_count)]
        results = await asyncio.gather(*tasks, return_exceptions= True)
        memory_usage = (psutil.Process(os.getpid()).memory_info().rss) / (1024 * 1024)

        flake_counter = 0
        valid_results = []

        for values in results:
            # Increment flake counter if the model failed to generate a response
            if isinstance(values, Exception):
                flake_counter += 1
            else:
                valid_results.append(values)

        if not valid_results:
            logger.info("No valid results found")
            return 0
        else:
            json_outputs, duration_outputs, count_outputs, thinking_response = zip(*valid_results)
            # Log thinking and eval_counts to log file for future reference
            for i in range(len(json_outputs)):
                logger.info("Eval Count: %s", count_outputs[i])
                if thinking_response[i]: 
                    logger.info("Thinking: %s", thinking_response[i][:500])

        logger.info("Data Generated: %s", len(valid_results))

        adapter = DIFFICULTY_CONFIG[self.prompt_difficulty]['schema']

        # Validate outputs and gather quantifiable data
        output_errors = validate_json(json_outputs=json_outputs, schema_adapter=adapter)
        flake_counter += output_errors.flake_counter

        if not output_errors.error_distribution:
            max_error_type = "N/A"
            max_error_count = "N/A"
        else:
            max_error_type = max(output_errors.error_distribution, key=output_errors.error_distribution.get)
            max_error_count = output_errors.error_distribution[max_error_type]

        avg_tps = model_efficiency(duration_outputs, count_outputs)
        percentiles = calculate_percentiles(duration_outputs)

        # Log all failed outputs for future reference
        for fail in output_errors.failed_outputs:
            logger.info(fail)

        if avg_tps == 0:
            return None
        else:
            # Create columns and add row to CSV file
            column_name = ["Model Name", "Total Runs", "Flake Score", "Avg. T/s", "Test Difficulty",
                           "P95 Latency", "P99 Latency", "Memory Usage (MB)", "Max Error Type", "Error Count"]
            
            if percentiles[0] is None:
                model_data = [self.agent, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          "N/A", "N/A", memory_usage, max_error_type, max_error_count]
            
            else:
                model_data = [self.agent, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          percentiles[0], percentiles[1], memory_usage, max_error_type, max_error_count]

            self.add_data(column_name, model_data)

if __name__ == "__main__":
    # CLI arguments
    parser = argparse.ArgumentParser(
            prog = 'AI Flake Tester',
            description = 'Tests JSON output schema formatting of AI models',
            epilog = 'Check how good a model really is!')

    parser.add_argument('--model', default='qwen3:1.7b', help='Enter a valid model available on Ollama')
    parser.add_argument('--run', type=int, default=100, help='Enter an integer greater than 0')
    parser.add_argument('--difficulty', default='med', choices=['easy', 'med', 'hard', 'ultra'], help='easy, med, hard, or ultra')
    parser.add_argument('--concurrency', type=int, default=10, help='Enter how many responses should be awaited at a given time.')

    args = parser.parse_args()

    logs_file = args.model.replace("/", "_").replace(":", "_") + "_" + args.difficulty + "_base.log"
    logging.basicConfig(level=logging.INFO, filename=f'logs/base/{logs_file}', format='%(asctime)s [%(levelname)s] %(message)s')
    logging.getLogger("httpx").setLevel(logging.WARNING)

    tester = FlakeTester(args.model, args.run, args.difficulty, args.concurrency, AsyncClient())
    asyncio.run(tester.main())