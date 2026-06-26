"""Integration tests for the orchestrator ETLPipeline class."""

from __future__ import annotations

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from src.etl.pipeline import ETLPipeline, PipelineResult


def test_pipeline_run_success(sample_csv: Path, test_engine) -> None:
    """Verifies that the orchestrator executes extract, validate, clean, transform, load sequentially."""
    
    # We patch the database engine used in the ETLPipeline to run against our test sqlite engine
    with patch("src.etl.pipeline.engine", test_engine):
             
        # Mock settings to point DATA_DIR to temp directory
        settings_mock = MagicMock()
        settings_mock.DATA_DIR = sample_csv.parent
        settings_mock.ENVIRONMENT = "development"
        
        pipeline = ETLPipeline(settings_mock)
        result = pipeline.run(sample_csv.name)
        
        assert isinstance(result, PipelineResult)
        assert result.status == "SUCCESS"
        assert result.rows_extracted == 3
        assert result.rows_cleaned == 3
        assert result.rows_transformed == 3
        assert result.rows_loaded == 3
        assert result.raw_quality_score == 100.0
        assert result.transformed_quality_score == 100.0
        assert len(result.errors) == 0
        assert "extract" in result.stage_timings
        assert "load" in result.stage_timings
