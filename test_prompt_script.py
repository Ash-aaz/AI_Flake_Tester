import pytest
from prompt_script import Flake_Tester
from unittest.mock import patch

@pytest.fixture
def easy_tester():
    easy_tester = Flake_Tester('dummy', 1, 'easy')
    return easy_tester

def test_validate_json_easy_ideal(easy_tester):
    ideal_output = ['[{"name": "Sarah", "age": 29}, {"name": "David", "age":42}]']
    assert easy_tester.validate_json(ideal_output) == 0

false_cases_easy = (['[{"name": "Sarah", "age": "twenty-nine"}, {"name": "David", "age":42}]'], ['[{"name": "David"}]'], ['{"name": "Sarah", "age": 29}'], 
                   ['Here is the extracted data you requested: [{"name": "Alex", "age": 19}]'], ['```json\n[{"name": "Sarah", "age": 29}]\n```'])

@pytest.mark.parametrize("incorrect_output", false_cases_easy)
def test_validate_json_easy_false(incorrect_output, easy_tester):
    assert easy_tester.validate_json(incorrect_output) == 1

@pytest.fixture
def med_tester():
    med_tester = Flake_Tester('dummy', 1, 'med')
    return med_tester

def test_validate_json_med_ideal(med_tester):
    ideal_output = ['[{"emp_id": "EMP-402", "profile": {"name": "John Doe", "is_manager": true}, "skills": ["Python", "C++"]}, {"emp_id": "EMP-919", "profile": {"name": "Alice", "is_manager": false}, "skills": ["conflict resolution", "Excel"]}]']
    assert med_tester.validate_json(ideal_output) == 0

false_cases_med = (['[{"emp_id": "EMP-402", "profile": {"name": "John Doe", "is_manager": "true"}, "skills": ["Python", "C++"]}]'], ['[{"emp_id": "EMP-919", "profile": {"name": "Alice"}, "skills": ["Excel"]}]'], 
                   ['[{"emp_id": "EMP-112", "profile": {"name": "Dave", "is_manager": false}, "skills": "None"}]'], ['```json\n[{"emp_id": "EMP-402", "profile": {"name": "John Doe", "is_manager": true}, "skills": ["Python", "C++"]}]\n```'])

@pytest.mark.parametrize("incorrect_output", false_cases_med)
def test_validate_json_med_false(incorrect_output, med_tester):
    assert med_tester.validate_json(incorrect_output) == 1

@pytest.fixture
def hard_tester():
    hard_tester = Flake_Tester('dummy', 1, 'hard')
    return hard_tester

def test_validate_json_hard_ideal(hard_tester):
    ideal_output = ['{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}, {"server": "Beta-Node", "downtime_minutes": 15, "critical": false}]}']
    assert hard_tester.validate_json(ideal_output) == 0

false_cases_hard = (['[{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}]'], ['{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": "90", "critical": true}]}'], 
                    ['{"incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}'], ['Here is the server incident log: {"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}'], 
                    ['```json\n{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}\n```'])

@pytest.mark.parametrize("incorrect_output", false_cases_hard)
def test_validate_json_hard_false(incorrect_output, hard_tester):
    assert hard_tester.validate_json(incorrect_output) == 1

@pytest.fixture
def efficiency_tester():
    efficiency_tester = Flake_Tester('dummy', 5, 'easy')
    return efficiency_tester

def test_model_efficiency(efficiency_tester):
    duration_values = [2000000000, 3000000000, 2000000000, 1000000000, 0]
    count_values = [100, 150, 120, 80, 0]

    assert efficiency_tester.model_efficiency(duration_values, count_values) == pytest.approx(60.0)

@pytest.mark.asyncio
@patch("prompt_script.AsyncClient.generate")
async def test_generate(mock_generate, easy_tester):
    dummy_ollama_payload = {"response": '[{"name": "Sarah", "age": 29}]', "eval_duration": 2000000000, "eval_count": 100}
    mock_generate.return_value = dummy_ollama_payload

    result = await easy_tester.generate()

    assert result == ('[{"name": "Sarah", "age": 29}]', 2000000000, 100)

@pytest.mark.asyncio
@patch("prompt_script.Flake_Tester.generate")
async def test_main(mock_generate, tmp_path, monkeypatch, easy_tester):
    monkeypatch.chdir(tmp_path)

    mock_generate.return_value = ('[{"name": "Sarah", "age": 29}]', 2000000000, 100)

    await easy_tester.main()
    test_file = tmp_path / "models_info.csv"

    assert test_file.exists()