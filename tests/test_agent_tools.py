from market_analyst.services.agent import format_retrieval_results


def test_format_retrieval_results_includes_scores_and_snippet() -> None:
    text = format_retrieval_results(
        [
            {
                "ticker": "SAMPLE",
                "company_name": "Sample Bank",
                "metadata": {"heading_path": "Sample Bank > Annual Report > Page 2"},
                "rrf_score": 0.032,
                "full_text_rank": 0.12,
                "vector_distance": 0.42,
                "content": "Debt reduced while operating cash flow improved.",
            }
        ]
    )

    assert "Ticker: SAMPLE" in text
    assert "RRF Score: 0.032" in text
    assert "Debt reduced" in text


def test_format_retrieval_results_handles_empty_results() -> None:
    assert "No matching report chunks" in format_retrieval_results([])
