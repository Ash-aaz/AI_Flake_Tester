import pytest
import csv
from main import FlakeTester
from unittest.mock import patch
from unittest.mock import MagicMock
from unittest.mock import AsyncMock

# Mock output for testing
@pytest.fixture
def easy_tester():
    easy_tester = FlakeTester('dummy', 1, 'easy', 10, AsyncMock())
    return easy_tester

mock = MagicMock()
mock.response = '[{"name": "Sarah", "age": 29}]'
mock.eval_duration = 2000000000
mock.eval_count = 100
mock.thinking = "Sample model thought process"

# Verify generate returns the correct tuple
@pytest.mark.asyncio
async def test_generate(easy_tester):
    easy_tester.client.generate.return_value = mock
    result = await easy_tester.generate()
    assert result == ('[{"name": "Sarah", "age": 29}]', 2000000000, 100, "Sample model thought process")

# Verify that data is written correctly to CSV when an output is flagged as incorrect
@pytest.mark.asyncio
@patch("main.FlakeTester.generate", new_callable=AsyncMock)
async def test_main(mock_generate, tmp_path, monkeypatch, easy_tester):
    monkeypatch.chdir(tmp_path)

    mock_generate.return_value = ('[{"name": "Sarah", "age": 29}]', 2000000000, 100, "Sample model thought process")

    await easy_tester.main()
    test_file = tmp_path / "models_info.csv"

    with open(test_file, "r") as file:
        reader = csv.reader(file)
        rows = list(reader)

        assert rows[0] == ['Model Name', 'Total Runs', 'Flake Score', 'Avg. T/s', 'Test Difficulty',
                           "P95 Latency", "P99 Latency", "Memory Usage (MB)", "Max Error Type", "Error Count"]
        assert rows[1][:7] == ['dummy', '1', '1', '50.0', 'easy', "N/A", "N/A"]
        assert float(rows[1][7]) > 0
        assert rows[1][8] != "N/A"
        assert float(rows[1][9]) > 0
