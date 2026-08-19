import pytest
import numpy as np
from rag_benchmark import RAGBenchMark
from unittest.mock import patch
from unittest.mock import MagicMock
from unittest.mock import AsyncMock

# Mock output for testing
@pytest.fixture
def rag_tester():
    rag_tester = RAGBenchMark('dummy', 1, 'easy', 10, AsyncMock(), "rag_benchmark.pdf")
    return rag_tester

# Verify text extraction on given PDF identified section starts and total sections correctly
def test_chunk_creator(rag_tester):
    test_chunks = rag_tester.chunk_creator("rag_benchmark.pdf")

    assert len(test_chunks) == 4
    
    for i in test_chunks:
        assert i.startswith("Section")

# Verify building an index didn't lead to loss of data
def test_build_index(rag_tester):
    outputs = rag_tester.build_index("rag_benchmark.pdf")

    assert outputs[0].ntotal == 4
    assert len(outputs[1]) == 4

mock_index = MagicMock()
# Verify the injected prompt was appended properly
@patch("rag_benchmark.ollama.embed")
def test_prompt_injector(mock_embed, rag_tester):
    mock_chunks = ["Fake prompt for testing"] * 4

    mock_embed.return_value = {"embeddings": [[0.0]*768]}
    mock_index.search.return_value = (np.array([[0]]), np.array([[0]]))

    result = rag_tester.prompt_injector(mock_index, mock_chunks)
    assert "Fake prompt for testing" in result
    assert "Task: Extract server outage incident reports from the IT log below." in result