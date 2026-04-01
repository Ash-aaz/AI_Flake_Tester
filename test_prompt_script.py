import pytest
import csv
from prompt_script import FlakeTester
from unittest.mock import patch
from unittest.mock import MagicMock
from unittest.mock import AsyncMock

@pytest.fixture
def easy_tester():
    easy_tester = FlakeTester('dummy', 1, 'easy', AsyncMock())
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
    med_tester = FlakeTester('dummy', 1, 'med', MagicMock())
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
    hard_tester = FlakeTester('dummy', 1, 'hard', MagicMock())
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
    efficiency_tester = FlakeTester('dummy', 5, 'easy', MagicMock())
    return efficiency_tester

def test_model_efficiency(efficiency_tester):
    duration_values = [2000000000, 3000000000, 2000000000, 1000000000, 0]
    count_values = [100, 150, 120, 80, 0]

    assert efficiency_tester.model_efficiency(duration_values, count_values) == pytest.approx(60.0)

mock = MagicMock()
mock.response = '[{"name": "Sarah", "age": 29}]'
mock.eval_duration = 2000000000
mock.eval_count = 100
@pytest.mark.asyncio

async def test_generate(easy_tester):

    easy_tester.client.generate.return_value = mock
    result = await easy_tester.generate()
    assert result == ('[{"name": "Sarah", "age": 29}]', 2000000000, 100)

@pytest.mark.asyncio
@patch("prompt_script.FlakeTester.generate", new_callable=AsyncMock)
async def test_main(mock_generate, tmp_path, monkeypatch, easy_tester):
    monkeypatch.chdir(tmp_path)

    mock_generate.return_value = ('[{"name": "Sarah", "age": 29}]', 2000000000, 100)

    await easy_tester.main()
    test_file = tmp_path / "models_info.csv"

    with open(test_file, "r") as file:
        reader = csv.reader(file)
        rows = list(reader)

        assert rows[0] == ['Model Name', 'Flake Score', 'Avg. T/s', 'Test Difficulty']
        assert rows[1] == ['dummy', '0', '50.0', 'easy']
