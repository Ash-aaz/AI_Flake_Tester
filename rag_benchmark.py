import os
import csv
import faiss
import ollama
import argparse
import psutil
import asyncio
import re
import numpy as np
from ollama import AsyncClient
from pypdf import PdfReader
from calculations import validate_json, model_efficiency, calculate_percentiles
from config import DIFFICULTY_CONFIG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGBenchMark:
    def __init__(self, model, run, difficulty, concurrency, client, pdf):
        self.agent = model
        self.total_count = run
        self.prompt_difficulty = difficulty
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = client
        self.file_path = pdf

    def chunk_creator(self, file_path):
        reader = PdfReader(file_path)
        extracted_text = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        chunks = re.split('(?i)(?=Section)', extracted_text)

        del chunks[0]
        return chunks

    def build_index(self, file_path):
        chunks = self.chunk_creator(file_path)
        embedded_chunks = []

        for i in chunks:
            embed = ollama.embed('nomic-embed-text:v1.5', i)
            embedded_chunks.append(embed['embeddings'][0])

        embedded_array = np.array(embedded_chunks, dtype=np.float32)
        index = faiss.IndexFlatL2(len(embedded_chunks[0]))

        index.add(embedded_array)
        return [index, chunks]
    
    def prompt_injector(self, index, chunks):
        prompt = DIFFICULTY_CONFIG[self.prompt_difficulty]['prompt']
        embedded_prompt = ollama.embed('nomic-embed-text:v1.5', prompt)['embeddings'][0]
        embedded_array = np.array([embedded_prompt], dtype=np.float32)

        matching_chunk = index.search(embedded_array, k=1)[1][0][0]
        injected_prompt = prompt + chunks[matching_chunk]

        return injected_prompt
    
    async def generate(self, message):
        async with self.semaphore:
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
        built_index = self.build_index(self.file_path)
        index = built_index[0]
        chunks = built_index[1]

        injected_prompt = self.prompt_injector(index, chunks)

        tasks = [asyncio.create_task(self.generate(injected_prompt)) for _ in range(self.total_count)]
        results = await asyncio.gather(*tasks, return_exceptions= True)
        memory_usage = (psutil.Process(os.getpid()).memory_info().rss) / (1024 * 1024)

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

        adapter = DIFFICULTY_CONFIG[self.prompt_difficulty]['schema']

        flake_counter += validate_json(json_outputs, adapter)
        avg_tps = model_efficiency(duration_outputs, count_outputs)
        percentiles = calculate_percentiles(duration_outputs)

        if avg_tps == 0:
            return None
        else:
            column_name = ["Model Name", "Total Runs", "Flake Score", "Avg. T/s", "Test Difficulty",
                           "P95 Latency", "P99 Latency", "Memory Usage (MB)"]
            model = self.agent + " (RAG)"
            
            if percentiles[0] == None:
                model_data = [model, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          "N/A", "N/A", memory_usage]
            
            else:
                model_data = [model, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          percentiles[0], percentiles[1], memory_usage]

            self.add_data(column_name, model_data)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            prog = 'AI Flake Tester w/ RAG',
            description = 'Tests JSON output schema formatting of AI models with RAG prompt injection',
            epilog = 'Check how RAG affects json outputs')

    parser.add_argument('--model', default='qwen3:1.7b', help='Enter a valid model available on Ollama')
    parser.add_argument('--run', type=int, default=100, help='Enter an integer greater than 0')
    parser.add_argument('--difficulty', default='med', choices=['easy', 'med', 'hard', 'ultra'], help='easy, med, hard, or ultra')
    parser.add_argument('--concurrency', type=int, default=10, help='Enter how many responses should be awaited at a given time.')
    parser.add_argument('--pdf', default='rag_benchmark.pdf', help="Add the pdf path for RAG")

    args = parser.parse_args()

    tester = RAGBenchMark(args.model, args.run, args.difficulty, args.concurrency, AsyncClient(), args.pdf)
    asyncio.run(tester.main())
