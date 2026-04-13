import pytest
import pandas as pd

@pytest.fixture
def dummy_dataframe():
    dummy_data = {
    'Model Name': ['qwen3:1.7b', 'gemma4:e4b', 'qwen3.5:9b'],
    'Total Runs': [100, 30, 30],
    'Flake Score': [83, 25, 16],
    'Avg. T/s': [250.56277081148403, 101.83097200727164, 84.03277551284302],
    'Test Difficulty': ['ultra', 'ultra', 'ultra'],
    'P95 Latency': [8.56503722995, 'N/A', 'N/A'],
    'P99 Latency': [13.355484342130001, 'N/A', 'N/A'],
    'Memory Usage (MB)': [54.75, 54.2109375, 55.77734375]
    }

    df = pd.DataFrame(dummy_data)
    return df

def test_label_creation(dummy_dataframe):
    dummy_dataframe['Models'] = dummy_dataframe['Model Name'] + ' (' + dummy_dataframe['Test Difficulty'] + ', runs=' + dummy_dataframe['Total Runs'].astype(str) + ')'
    assert dummy_dataframe['Models'].tolist() == ["qwen3:1.7b (ultra, runs=100)", "gemma4:e4b (ultra, runs=30)", "qwen3.5:9b (ultra, runs=30)"]

def test_filtering(dummy_dataframe):
    filtered_df = dummy_dataframe.copy()

    filtered_df['P95 Latency'] = pd.to_numeric(filtered_df['P95 Latency'], errors='coerce')
    filtered_df['P99 Latency'] = pd.to_numeric(filtered_df['P99 Latency'], errors='coerce')
    filtered_df = filtered_df.dropna(subset=['P95 Latency', 'P99 Latency'])

    assert len(filtered_df) == 1