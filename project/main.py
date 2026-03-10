"""Entrypoint for OH MCD Submission Counts Automation."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from project.agent.decision_engine import DecisionEngine
from project.agent.scheduler import SchedulerService
from project.database.query_runner import DatabaseConfig, QueryRunner
from project.email.email_sender import EmailSender
from project.excel.excel_writer import ExcelWriter
from project.report.report_generator import ReportGenerator
from project.vendors.vendor_scanner import VendorScanner


def load_config(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def setup_logging(log_file: str, level: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


class AutomationApp:
    """Coordinates complete workflow steps for OH MCD report automation."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        db_conf = config["database"]
        self.query_runner = QueryRunner(
            DatabaseConfig(
                driver=db_conf["driver"],
                server=db_conf["server"],
                database=db_conf["database"],
                trusted_connection=db_conf.get("trusted_connection", True),
                query=db_conf["query"],
            )
        )

        self.excel_writer = ExcelWriter(
            workbook_path=config["excel"]["workbook_path"],
            worksheet_prefix=config["excel"]["worksheet_prefix"],
        )
        self.vendor_scanner = VendorScanner(
            vendor_roots=config["vendors"]["roots"],
            allowed_extensions=config["vendors"]["allowed_extensions"],
        )
        self.report_generator = ReportGenerator(
            anomaly_threshold_pct=float(config["app"].get("anomaly_threshold_pct", 50))
        )
        email_cfg = config["email"]
        self.email_sender = EmailSender(
            smtp_server=email_cfg["smtp_server"],
            smtp_port=int(email_cfg["smtp_port"]),
            sender=email_cfg["sender"],
            recipients=email_cfg["recipients"],
            subject=email_cfg["subject"],
        )
        self.decision_engine = DecisionEngine(config["state"]["state_file"])

    def run_workflow(self, force_run: bool = False) -> None:
        """Execute end-to-end reporting pipeline."""
        self.logger.info("Starting workflow. force_run=%s", force_run)
        dataframe = self.query_runner.run_submission_query()

        decision, previous_total = self.decision_engine.evaluate(dataframe, force_run=force_run)
        if not decision.should_run:
            self.logger.info("Skipping workflow: %s", decision.reason)
            return

        worksheet_name = self.excel_writer.write_results(dataframe, datetime.now())
        vendor_results = self.vendor_scanner.scan()
        summary = self.report_generator.build_summary(
            dataframe=dataframe,
            worksheet_name=worksheet_name,
            vendor_results=vendor_results,
            previous_encounter_total=previous_total,
        )
        email_body = self.report_generator.render_email_body(summary)

        self.email_sender.send(email_body, self.config["excel"]["workbook_path"])
        self.decision_engine.store_encounter_total(summary.encounter_count)

        self.logger.info("Workflow completed. Reason=%s", decision.reason)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OH MCD Submission Counts Automation")
    parser.add_argument("--config", default="project/config/config.yaml", help="Path to config YAML")
    parser.add_argument(
        "--mode",
        choices=["once", "daemon", "scheduled", "poll"],
        default="once",
        help="Run mode: once executes immediately; daemon runs scheduler loop",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    setup_logging(config["logging"]["log_file"], config["logging"]["level"])

    app = AutomationApp(config)

    if args.mode == "once":
        app.run_workflow(force_run=True)
        return
    if args.mode == "scheduled":
        app.run_workflow(force_run=True)
        return
    if args.mode == "poll":
        app.run_workflow(force_run=False)
        return

    scheduler_service = SchedulerService(
        weekly_runs=config["schedule"]["weekly_runs"],
        poll_interval_minutes=int(config["app"]["poll_interval_minutes"]),
    )
    scheduler_service.register_jobs(
        scheduled_workflow=lambda: app.run_workflow(force_run=True),
        polling_workflow=lambda: app.run_workflow(force_run=False),
    )
    scheduler_service.run_forever()


if __name__ == "__main__":
    main()
