import os
import asyncio
import csv
import argparse
import psutil
import datetime as dt
from calculations import validate_json, model_efficiency, calculate_percentiles
from ollama import AsyncClient
from pydantic import TypeAdapter
from typing_extensions import TypedDict, Literal, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Incidents(TypedDict):
    server: str
    downtime_minutes: int
    critical: bool

class Logs(TypedDict):
    log_id: str
    incidents: list[Incidents]

class TeamMember(TypedDict):
    member_id: str
    role: str
    is_lead: bool

class Milestone(TypedDict):
    title: str
    completed: bool
    blockers: list[str]

class Memo(TypedDict):
    project_id: str
    status: Literal["active", "on_hold", "completed"]
    budget_remaining: float
    team: list[TeamMember]
    milestones: list[Milestone]

class AffectedSystems(TypedDict):
    system_name: str
    compromised: bool
    recovery_status: Literal["operational", "degraded", "offline", "unknown"]

class Responders(TypedDict):
    responder_id: str
    role: Literal["incident_lead", "forensics", "communications", "containment",
            "management"]
    is_lead: bool

class Breach(TypedDict):
    incident_id: str
    severity: Literal["low", "medium", "high", "critical"]
    attack_type: Literal["phishing", "ransomware", "ddos", "sql_injection", 
                    "unauthorised_access", "malware"]
    contained: bool
    affected_systems: list[AffectedSystems]
    responders: list[Responders]    
    estimated_data_loss_gb: Optional[float]
    first_detected: Optional[dt.datetime]

class Patient(TypedDict):
    age: int
    sex: Literal["male", "female", "unknown"]
    pre_existing_conditions: list[str]

class Interventions(TypedDict):
    intervention_type: Literal["medication", "procedure", "monitoring", "none"]
    description: str
    effective: Optional[bool]

class Reported(TypedDict):
    role: Literal["physician", "nurse", "pharmacist", "patient", "other"]
    institution_type: Literal["hospital", "clinic", "home", "other"]

class Events(TypedDict):
    event_type: str
    onset_day: int
    duration_hours: Optional[int]
    causality: Literal["definite", "probable", "possible", "unlikely", "unrelated"]
    interventions: list[Interventions]
    
class Report(TypedDict):
    report_id: str
    severity: Literal["mild", "moderate", "severe", "critical"]
    outcome: Literal["resolved", "ongoing", "fatal", "unknown"]
    patient: Patient
    events: list[Events]
    reported_by: Reported

class FlakeTester:
    DIFFICULTY_CONFIG = {
        'easy': {
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
        },
        'med': {
            'prompt': """You are a strict data extraction API.
                Task: Extract a project status report from the internal memo below.
                Schema: Return a single JSON object. It must contain exactly these keys:
                    "project_id" (a string)
                    "status" (a string — infer from context, must be exactly one of: "active", "on_hold", "completed")
                    "budget_remaining" (a float — convert natural language amounts to a numeric value, e.g. "forty thousand" becomes 40000.0)
                    "team" (a list of dictionaries, each containing "member_id" as a string, "role" as a string, and "is_lead" as a boolean)
                    "milestones" (a list of dictionaries, each containing "title" as a string, "completed" as a boolean, and "blockers" as a list of strings — use an empty list if none are mentioned, never null)
                Input Text: Project NOVA-7 is still live as of this week. Budget-wise, we've got roughly forty thousand left to work with. 
                The team lead is ENG-101, Marcus, who's heading up backend. ENG-204, Priya, is handling frontend and ENG-309, Leo, is on QA — neither of them are leads. 
                First milestone, "API Integration", is done. Second one, "UI Overhaul", is still blocked by the design sign-off and pending assets from the client. Third milestone "Load Testing" hasn't been touched yet, no blockers identified.
                Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting like ```json. Do not include any conversational text.""",
                                
            'schema': TypeAdapter(Memo)
        },
        'hard': {
            'prompt': """You are a strict data extraction API.
                Task: Extract a structured security incident report from the analyst note below.
                Schema: Return a single JSON object. It must contain exactly these keys:
                    "incident_id" (a string)
                    "severity" (a string — infer from context, must be exactly one of: 
                        "low", "medium", "high", "critical")
                    "attack_type" (a string — infer from context, must be exactly one of: 
                        "phishing", "ransomware", "ddos", "sql_injection", 
                        "unauthorised_access", "malware")
                    "contained" (a boolean — true only if fully contained, false if ongoing 
                        or partially contained)
                    "affected_systems" (a list of dictionaries, each containing:
                        "system_name" as a string,
                        "compromised" as a boolean,
                        "recovery_status" as a string that must be exactly one of: 
                            "operational", "degraded", "offline", "unknown")
                    "responders" (a list of dictionaries, each containing:
                        "responder_id" as a string,
                        "role" as a string that must be exactly one of: 
                            "incident_lead", "forensics", "communications", "containment",
                            "management"),
                        "is_lead" as a boolean)
                    "estimated_data_loss_gb" (a float or null — explicitly null if unknown, 
                        never absent)
                    "first_detected" (a string or null — ISO 8601 date format if a date can 
                        be inferred, explicitly null if only vague timing is mentioned)
                Input Text: Incident ticket INC-4471. Late Tuesday evening, our intrusion 
                detection flagged unusual privilege escalation across three systems. Someone 
                got hold of valid credentials and moved laterally through the network — 
                classic credential abuse. This is serious but we have not lost control 
                entirely. The DB-Primary server is completely offline, we pulled it. The 
                Web-App cluster is limping along in a degraded state. The Backup-Node was 
                accessed but seems to be holding operationally. We have no reliable way to 
                estimate how much data walked out the door. Containment is still in progress, 
                not fully locked down yet. Response team: SEC-01, Jamie, is running point on 
                this whole thing. SEC-02, Priya, is digging through the logs. SEC-03, Leo, is 
                handling external comms. SEC-04, Morgan, is working on actually stopping the 
                spread. No fixed date on detection, just late Tuesday.
                Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting 
                like ```json. Do not include any conversational text.""",
                
            'schema': TypeAdapter(Breach)
        },
        'ultra': {
            'prompt': """You are a strict data extraction API.
                Task: Extract a structured clinical adverse event report from the physician's note below.
                Schema: Return a single JSON object. It must contain exactly these keys:
                    "report_id" (a string)
                    "severity" (a string — infer from clinical language, must be exactly one of: "mild", "moderate", "severe", "critical")
                    "outcome" (a string — must be exactly one of: "resolved", "ongoing", "fatal", "unknown")
                    "patient" (a dictionary containing "age" as an integer, "sex" as a string that must be exactly one of: "male", "female", "unknown", and "pre_existing_conditions" as a list of strings — empty list if none)
                    "events" (a list of dictionaries, each containing:
                        "event_type" as a string,
                        "onset_day" as an integer — convert ordinal language e.g. "third day of admission" becomes 3,
                        "duration_hours" as an integer or null — must be explicitly null if unknown, never absent,
                        "causality" as a string that must be exactly one of: "definite", "probable", "possible", "unlikely", "unrelated",
                        "interventions" as a list of dictionaries each containing "intervention_type" as a string that must be exactly one of: "medication", "procedure", "monitoring", "none", "description" as a string, and "effective" as a boolean or null — explicitly null if outcome is unknown)
                    "reported_by" (a dictionary containing "role" as a string that must be exactly one of: "physician", "nurse", "pharmacist", "patient", "other", and "institution_type" as a string that must be exactly one of: "hospital", "clinic", "home", "other")
                Input Text: ADR Report REP-2291. Patient is a 67-year-old male, known hypertensive, type 2 diabetic. 
                On the third day of admission, patient developed significant tachycardia and reported crushing chest discomfort — this is not looking mild by any measure. Still being monitored as of this note, no resolution yet. 
                Started on IV metoprolol around day three, unclear if it's helping at this stage. Also placed on continuous cardiac monitoring same day, too early to call effectiveness.
                A secondary reaction, mild skin rash, appeared on day five. Probably related to the antibiotic course. Resolved within 24 hours with topical treatment, which worked. 
                This note filed by the attending physician, institution is a hospital. Causality on the cardiac event — I'd say probable. The rash, possible.
                Strict Constraint: Output ONLY valid JSON. Do not include markdown formatting like ```json. Do not include any conversational text.""",
                                
            'schema': TypeAdapter(Report)
        }
    }

    def __init__(self, agent, total_count, prompt_difficulty, concurrency, client):
        self.agent = agent
        self.total_count = total_count
        self.prompt_difficulty = prompt_difficulty
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = client

    async def generate(self):
        message = self.DIFFICULTY_CONFIG[self.prompt_difficulty]['prompt']

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
        tasks = [asyncio.create_task(self.generate()) for _ in range(self.total_count)]
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

        adapter = self.DIFFICULTY_CONFIG[self.prompt_difficulty]['schema']

        flake_counter += validate_json(json_outputs, adapter)
        avg_tps = model_efficiency(duration_outputs, count_outputs)
        percentiles = calculate_percentiles(duration_outputs)

        if avg_tps == 0:
            return None
        else:
            column_name = ["Model Name", "Total Runs", "Flake Score", "Avg. T/s", "Test Difficulty",
                           "P95 Latency", "P99 Latency", "Memory Usage (MB)"]
            
            if percentiles[0] == None:
                model_data = [self.agent, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          "N/A", "N/A", memory_usage]
            
            else:
                model_data = [self.agent, self.total_count, flake_counter, avg_tps, self.prompt_difficulty,
                          percentiles[0], percentiles[1], memory_usage]

            self.add_data(column_name, model_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            prog = 'AI Flake Tester',
            description = 'Tests JSON output schema formatting of AI models',
            epilog = 'Check how good a model really is!')

    parser.add_argument('--model', default='qwen3:1.7b', help='Enter a valid model available on Ollama')
    parser.add_argument('--run', type=int, default=100, help='Enter an integer greater than 0')
    parser.add_argument('--difficulty', default='med', choices=['easy', 'med', 'hard', 'ultra'], help='easy, med, hard, or ultra')
    parser.add_argument('--concurrency', type=int, default=10, help='Enter how many responses should be awaited at a given time.')

    args = parser.parse_args()

    tester = FlakeTester(args.model, args.run, args.difficulty, args.concurrency, AsyncClient())
    asyncio.run(tester.main())