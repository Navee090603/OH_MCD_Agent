# OH MCD Submission Counts Automation

Production-grade Python automation for Ohio Medicaid submission reporting.

## 1) Project architecture

```text
project/
  agent/
    scheduler.py
    decision_engine.py
  database/
    query_runner.py
  excel/
    excel_writer.py
  vendors/
    vendor_scanner.py
  report/
    report_generator.py
  email/
    email_sender.py
  config/
    config.yaml
  logs/
    automation.log
  main.py
```

### Component design
- **Scheduler (`agent/scheduler.py`)**: registers weekly expected batch windows plus polling cadence for unexpected runs.
- **Decision engine (`agent/decision_engine.py`)**: compares newest `transmissionfilename` to persisted state and decides whether to run.
- **Database runner (`database/query_runner.py`)**: executes SQL Server query via `pyodbc` and returns DataFrame.
- **Excel writer (`excel/excel_writer.py`)**: creates one new worksheet per run (`Submission_YYYY_MM_DD`) and writes results.
- **Vendor scanner (`vendors/vendor_scanner.py`)**: finds latest attestation file from each vendor path and flags missing files.
- **Report generator (`report/report_generator.py`)**: builds business summary metrics and anomaly detection alerts.
- **Email sender (`email/email_sender.py`)**: sends summary email and attaches updated workbook.
- **Main orchestrator (`main.py`)**: coordinates end-to-end workflow with robust logging/error propagation.

## 2) Setup instructions

### Prerequisites
- Python 3.11
- Windows Server machine with network access to:
  - SQL Server `prd_162.sql.caresource.corp`
  - Shared drives for vendor attestations
  - SMTP relay server

### Install dependencies
```bash
python -m venv .venv
.venv\Scripts\activate
pip install pandas pyodbc openpyxl schedule pyyaml
```

### Configure
1. Edit `project/config/config.yaml`:
   - SQL driver/server/database/query
   - Excel workbook path
   - Vendor directories
   - SMTP sender/recipients
   - Weekly schedule and polling interval
2. Ensure SQL driver (ODBC Driver 17+) is installed.

### Run modes
```bash
python -m project.main --mode once
python -m project.main --mode scheduled
python -m project.main --mode poll
python -m project.main --mode daemon
```

- `once`: force full workflow execution immediately.
- `scheduled`: same as once, intended for scheduled trigger wrappers.
- `poll`: run only if new transmissions detected.
- `daemon`: long-running process with both fixed schedule and polling detection.

## 3) Example logs

```log
2026-01-07 19:00:01,114 | INFO | AutomationApp | Starting workflow. force_run=True
2026-01-07 19:00:08,992 | INFO | project.database.query_runner | Retrieved 18 rows from SQL Server
2026-01-07 19:00:09,146 | INFO | project.excel.excel_writer | Wrote 18 rows to worksheet Submission_2026_01_07
2026-01-07 19:00:09,311 | WARNING | project.vendors.vendor_scanner | No attestation files found for vendor DentaQuest under //day04/.../Ohio
2026-01-07 19:00:09,518 | WARNING | project.report.report_generator | Encounter count anomaly detected. Current=52410, Previous=24990, Delta=109.7%
2026-01-07 19:00:09,799 | INFO | project.email.email_sender | Email sent to ['business-team@caresource.corp']
2026-01-07 19:00:09,805 | INFO | AutomationApp | Workflow completed. Reason=Scheduled batch window
```

## 4) Deploy on Windows Task Scheduler

### Option A (recommended): polling + scheduled triggers per run
Create two tasks:

1. **OH_MCD_Expected_Batches**
   - Triggers:
     - Weekly Sunday 7:00 PM
     - Weekly Monday 4:00 PM
     - Weekly Tuesday 7:00 PM
     - Weekly Wednesday 7:00 PM
   - Action:
     ```
     Program/script: C:\Python311\python.exe
     Add arguments: -m project.main --mode scheduled --config project/config/config.yaml
     Start in: C:\OH_MCD_Agent
     ```

2. **OH_MCD_Unscheduled_Poll**
   - Trigger: repeat every 15 minutes (or config value)
   - Action:
     ```
     Program/script: C:\Python311\python.exe
     Add arguments: -m project.main --mode poll --config project/config/config.yaml
     Start in: C:\OH_MCD_Agent
     ```

### Option B: daemon process
Run one service-like task at startup:
```text
Program/script: C:\Python311\python.exe
Add arguments: -m project.main --mode daemon --config project/config/config.yaml
Start in: C:\OH_MCD_Agent
```

## 5) Operational notes
- Missing vendor files do not block report delivery; they are logged and included as `MISSING` in email.
- Unexpected batching is identified when a new `transmissionfilename` appears compared to state file.
- State persisted in `project/logs/automation_state.json` for change detection and anomaly baseline.
