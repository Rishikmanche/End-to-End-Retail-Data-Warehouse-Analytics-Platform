"""ETL Pipeline orchestrator.

Coordinates extraction, raw validation, cleaning, transformation, transformed validation,
and loading into the PostgreSQL data warehouse. Emits detailed metrics and execution summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime
from pathlib import Path
import uuid

from src.config.config import get_settings, Settings
from src.database.database import engine
from src.etl.extract.extractor import DataExtractor
from src.etl.load.loader import DataLoader
from src.etl.transform.clean import DataCleaner
from src.etl.transform.transformer import DataTransformer
from src.utils.logger import get_logger
from src.validation.validator import DataValidator

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Stores execution metrics and outcomes of the ETL pipeline run."""
    run_id: str
    status: str  # 'SUCCESS', 'FAILED', 'QUALITY_FAILURE'
    start_time: datetime.datetime
    end_time: datetime.datetime
    rows_extracted: int
    rows_cleaned: int
    rows_transformed: int
    rows_loaded: int
    rows_rejected: int
    raw_quality_score: float
    transformed_quality_score: float
    stage_timings: dict[str, float]
    errors: list[str]

    def summary(self) -> str:
        """Returns a string summarizing the pipeline execution."""
        duration = (self.end_time - self.start_time).total_seconds()
        return (
            f"=== ETL PIPELINE RUN SUMMARY ===\n"
            f"Run ID: {self.run_id}\n"
            f"Status: {self.status}\n"
            f"Duration: {duration:.2f} seconds\n"
            f"Rows Extracted: {self.rows_extracted}\n"
            f"Rows Cleaned: {self.rows_cleaned}\n"
            f"Rows Transformed: {self.rows_transformed}\n"
            f"Rows Loaded: {self.rows_loaded}\n"
            f"Rows Rejected: {self.rows_rejected}\n"
            f"Raw Quality Score: {self.raw_quality_score:.2f}%\n"
            f"Transformed Quality Score: {self.transformed_quality_score:.2f}%\n"
            f"Stage Timings: {self.stage_timings}\n"
            f"Errors: {self.errors}\n"
            f"================================"
        )


class ETLPipeline:
    """Orchestrates the entire ETL workflow from CSV extraction to DB load."""

    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or get_settings()
        self.logger = logger
        self.run_id = str(uuid.uuid4())
        
        # Initialize modules
        self.extractor = DataExtractor(self.config.DATA_DIR)
        self.cleaner = DataCleaner()
        self.transformer = DataTransformer()
        self.validator = DataValidator(engine)
        self.loader = DataLoader(engine)

    def run(self, filename: str = "superstore_sales.csv") -> PipelineResult:
        """Runs the end-to-end ETL process.

        Args:
            filename: Name of the raw CSV file to process.

        Returns:
            A PipelineResult object.
        """
        start_time = datetime.datetime.utcnow()
        self.logger.info("Starting ETL pipeline run. Run ID: %s", self.run_id)

        stage_timings = {}
        errors = []
        status = "SUCCESS"

        rows_extracted = 0
        rows_cleaned = 0
        rows_transformed = 0
        rows_loaded = 0
        rows_rejected = 0
        raw_quality_score = 100.0
        transformed_quality_score = 100.0

        try:
            # 1. Extraction Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 1/5] Extracting raw data from %s...", filename)
            raw_df = self.extractor.extract(filename)
            rows_extracted = len(raw_df)
            stage_timings["extract"] = (datetime.datetime.utcnow() - t0).total_seconds()
            self.logger.info("Extraction complete. Extracted %d rows.", rows_extracted)

            if raw_df.empty:
                raise ValueError("No records found in the input data file.")

            # 2. Raw Data Quality Validation Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 2/5] Running raw data validation...")
            raw_report = self.validator.validate(raw_df, stage="raw")
            raw_quality_score = raw_report.quality_score
            stage_timings["raw_validation"] = (datetime.datetime.utcnow() - t0).total_seconds()
            
            # Save raw quality report to disk
            report_dir = Path(self.config.DATA_DIR) / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            raw_report.to_json(report_dir / f"dq_report_raw_{self.run_id}.json")

            # Check threshold (fail if critical checks failed)
            if raw_report.failed > 0:
                self.logger.error("Raw data validation failed critical checks. Quality Score: %.2f%%", raw_quality_score)
                status = "QUALITY_FAILURE"
                errors.append(f"Raw validation has {raw_report.failed} critical failures.")

            # 3. Cleaning Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 3/5] Cleaning data...")
            cleaned_df = self.cleaner.clean(raw_df)
            rows_cleaned = len(cleaned_df)
            rows_rejected = rows_extracted - rows_cleaned
            stage_timings["clean"] = (datetime.datetime.utcnow() - t0).total_seconds()
            self.logger.info("Cleaning complete. Cleaned: %d, Rejected: %d", rows_cleaned, rows_rejected)

            # Save clean data for reference / auditing
            clean_dir = Path(self.config.DATA_DIR) / "clean"
            clean_dir.mkdir(parents=True, exist_ok=True)
            cleaned_df.to_csv(clean_dir / f"clean_sales_{self.run_id}.csv", index=False)

            # 4. Transformation Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 4/5] Transforming data and engineering features...")
            transformed_df = self.transformer.transform(cleaned_df)
            rows_transformed = len(transformed_df)
            stage_timings["transform"] = (datetime.datetime.utcnow() - t0).total_seconds()
            self.logger.info("Transformation complete. Transformed %d rows.", rows_transformed)

            # Save processed data
            processed_dir = Path(self.config.DATA_DIR) / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            transformed_df.to_csv(processed_dir / f"processed_sales_{self.run_id}.csv", index=False)

            # 5. Transformed Data Quality Validation Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 5/5] Running transformed validation...")
            transformed_report = self.validator.validate(transformed_df, stage="transformed")
            transformed_quality_score = transformed_report.quality_score
            stage_timings["transformed_validation"] = (datetime.datetime.utcnow() - t0).total_seconds()
            
            transformed_report.to_json(report_dir / f"dq_report_transformed_{self.run_id}.json")
            
            if transformed_report.failed > 0:
                self.logger.warning("Transformed data validation failed critical checks. Proceeding with caution.")
                if status == "SUCCESS":
                    status = "QUALITY_FAILURE"
                errors.append(f"Transformed validation has {transformed_report.failed} critical failures.")

            # 6. Database Loading Stage
            t0 = datetime.datetime.utcnow()
            self.logger.info("[ETL Stage 6/5] Loading data into database dimensions & facts...")
            load_metrics = self.loader.load_all(transformed_df)
            rows_loaded = load_metrics.get("fact_sales", 0)
            stage_timings["load"] = (datetime.datetime.utcnow() - t0).total_seconds()
            self.logger.info("Database load complete. Facts loaded: %d", rows_loaded)

        except Exception as exc:
            status = "FAILED"
            errors.append(str(exc))
            self.logger.exception("ETL pipeline run failed.")

        end_time = datetime.datetime.utcnow()
        result = PipelineResult(
            run_id=self.run_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            rows_extracted=rows_extracted,
            rows_cleaned=rows_cleaned,
            rows_transformed=rows_transformed,
            rows_loaded=rows_loaded,
            rows_rejected=rows_rejected,
            raw_quality_score=raw_quality_score,
            transformed_quality_score=transformed_quality_score,
            stage_timings=stage_timings,
            errors=errors
        )
        self.logger.info("Pipeline completed. Summary: \n%s", result.summary())
        return result
