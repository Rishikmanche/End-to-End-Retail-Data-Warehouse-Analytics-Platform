"""ETL Pipeline CLI execution script.

Parses arguments and runs the ETLPipeline, printing run results and exit codes.
"""

from __future__ import annotations

import argparse
import sys

from src.config.config import get_settings
from src.etl.pipeline import ETLPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """CLI execution entry point."""
    parser = argparse.ArgumentParser(description="Run the Retail Analytics Platform ETL pipeline.")
    parser.add_argument(
        "--file",
        type=str,
        default="superstore_sales.csv",
        help="Raw data CSV filename located inside data/raw/ directory."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validations only without cleaning, transforming, or loading."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extract and transform stages without writing to database."
    )
    
    args = parser.parse_args()
    settings = get_settings()

    logger.info("Initializing ETL Pipeline execution...")
    
    try:
        pipeline = ETLPipeline(settings)
        
        if args.validate_only:
            logger.info("Executing VALIDATION-ONLY check...")
            # For validation-only, we just extract raw and validate
            raw_df = pipeline.extractor.extract(args.file)
            report = pipeline.validator.validate(raw_df, stage="raw")
            print(report.summary())
            if report.failed > 0:
                sys.exit(2)
            sys.exit(0)

        # Run pipeline
        # Currently, dry-run is handled inside pipeline (can skip load stage)
        # If dry-run, we intercept loader execution in this CLI or pass a dry-run flag.
        # Since ETLPipeline.run() is our main orchestrator, let's execute it.
        # Note: If dry-run is requested, we can mock or skip load stage inside pipeline, 
        # but let's run the normal pipeline and log dry-run warning if we don't have dry-run implemented.
        if args.dry_run:
            logger.info("Executing DRY-RUN execution...")
            raw_df = pipeline.extractor.extract(args.file)
            cleaned_df = pipeline.cleaner.clean(raw_df)
            transformed_df = pipeline.transformer.transform(cleaned_df)
            report = pipeline.validator.validate(transformed_df, stage="transformed")
            print("=== DRY RUN COMPLETED ===")
            print(f"Rows extracted: {len(raw_df)}")
            print(f"Rows cleaned: {len(cleaned_df)}")
            print(f"Rows transformed: {len(transformed_df)}")
            print(f"Quality Score: {report.quality_score:.2f}%")
            if report.failed > 0:
                sys.exit(2)
            sys.exit(0)

        result = pipeline.run(args.file)
        print(result.summary())
        
        if result.status == "QUALITY_FAILURE":
            logger.warning("Pipeline completed with quality warning failures.")
            sys.exit(2)
        elif result.status == "FAILED":
            logger.error("Pipeline run failed.")
            sys.exit(1)
            
        sys.exit(0)

    except Exception as exc:
        logger.error("Fatal error during CLI execution: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
