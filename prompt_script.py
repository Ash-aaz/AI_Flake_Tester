import os
import asyncio
import csv
import argparse
from ollama import AsyncClient
from pydantic import ValidationError, TypeAdapter
from typing_extensions import TypedDict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User(TypedDict):
    name: str
    age: int

class Profile(TypedDict):
    name: str
    is_manager: bool

class Employee(TypedDict):
    emp_id: str
    profile: Profile
    skills: list[str]

class Incidents(TypedDict):
    server: str
    downtime_minutes: int
    critical: bool

class Logs(TypedDict):
    log_id: str
    incidents: list[Incidents]

class FlakeTester:
    DIFFICULTY_CONFIG = {
        'easy': {
            'prompt': """You are a strict data extraction API. 
               Task: Extract the names and ages of the people mentioned in the text below. 
               Schema: Return a JSON list of dictionaries. Each dictionary must have two keys: "name" (a string) and "age" (an integer). 
               Input Text: Yesterday, I had lunch with Sarah, who just turned 29. We met up with her boss, David. David is 42 and has been working there for 5 years. Later, we saw a 19-year-old intern named Alex carrying a bunch of coffees. 
               Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting like ```json. Do not include any conversational text.""",
            
            'schema': TypeAdapter(list[User])
        },
        'med': {
            'prompt': """You are a strict data extraction API.
                Task: Extract employee profiles from the messy text below.
                Schema: Return a JSON list of dictionaries. Each dictionary must have three root keys:
                    "emp_id" (a string)
                    "profile" (a nested dictionary containing "name" as a string, and "is_manager" as a boolean)
                    "skills" (a list of strings. If none are mentioned, return an empty list).
                Input Text: I need to update the roster. EMP-402 is John Doe, he is leading the Engineering team right now and codes in Python and C++. 
                Then there is EMP-919, Alice. I think she works in HR? Not a manager though. She knows conflict resolution and Excel. 
                Oh, and EMP-112 is Dave. No idea what his skills are, but he definitely isn't a manager.
                Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting like ```json. Do not include any conversational text.""",

            'schema': TypeAdapter(list[Employee])
        },
        'hard': {
            'prompt': """You are a strict data extraction API.
                Task: Extract server outage incident reports from the IT log below.
                Schema: Return a single JSON object (dictionary). It must contain exactly two keys:
                    "log_id" (a string)
                    "incidents" (a list of dictionaries). Each dictionary in this list must have: "server" (string), "downtime_minutes" (integer), and "critical" (boolean).
                Input Text: Log ID: REP-9981. Yesterday at 0400 hours, Alpha-Node went down for exactly an hour and a half. 
                It took down the Payment Gateway. Total critical failure. Then, Beta-Node stuttered. It was only offline for 15 minutes, taking down the Notification pipeline. 
                Not critical, just annoying. Also, reminder to order more coffee for the breakroom, we are completely out.
                Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting like ```json. Do not include any conversational text.""",
                
            'schema': TypeAdapter(Logs)
        }
    }

    def __init__(self, agent, total_count, prompt_difficulty, client):
        self.agent = agent
        self.total_count = total_count
        self.prompt_difficulty = prompt_difficulty
        self.client = client

    def validate_json(self, json_outputs: list):
        flake_counter = 0

        schema_adapter = self.DIFFICULTY_CONFIG[self.prompt_difficulty]['schema']

        for output in json_outputs:
            try:
                schema_adapter.validate_json(output, strict=True)
            except ValidationError:
                flake_counter += 1
    
        logger.info("Flake Counter = %s", flake_counter)

        return flake_counter

    def model_efficiency(self, duration_values: list, count_values: list):
        i = 0
        total_tps = 0
        current_count = self.total_count

        while i < self.total_count:
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

    async def generate(self):
        message = self.DIFFICULTY_CONFIG[self.prompt_difficulty]['prompt']
        response = await self.client.generate(model=self.agent, prompt=message)

        return (response.response, response.eval_duration, response.eval_count)
    
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

        flake_counter = 0
        valid_results = []

        for values in results:
            if isinstance(values, Exception):
                flake_counter += 1
            else:
                valid_results.append(values)

        if not valid_results:
            logger.info("No valid results found")
            return 0
        else:
            json_outputs, duration_outputs, count_outputs = zip(*valid_results)

        logger.info("Data Generated: %s", len(valid_results))

        flake_counter += self.validate_json(json_outputs)
        avg_tps = self.model_efficiency(duration_outputs, count_outputs)

        if avg_tps == 0:
            return None
        else:
            column_name = ["Model Name", "Flake Score", "Avg. T/s", "Test Difficulty"]
            model_data = [self.agent, flake_counter, avg_tps, self.prompt_difficulty]

            self.add_data(column_name, model_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            prog = 'AI Flake Tester',
            description = 'Tests JSON output schema formatting of AI models',
            epilog = 'Check how good a model really is!')

    parser.add_argument('--model', default='qwen3:1.7b', help='Enter a valid model available on Ollama')
    parser.add_argument('--run', type=int, default=100, help='Enter an integer greater than 0')
    parser.add_argument('--difficulty', default='med', choices=['easy', 'med', 'hard'], help='easy, med, or hard')

    args = parser.parse_args()

    tester = FlakeTester(args.model, args.run, args.difficulty, AsyncClient())
    asyncio.run(tester.main())