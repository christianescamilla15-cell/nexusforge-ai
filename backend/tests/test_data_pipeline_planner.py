"""Tests for Gap 6 — Data pipeline modernization planner.

Covers the detection rules, classification, plan construction, and
markdown rendering. All tests run against synthetic in-memory content
written to a tempdir — no real repo needed, no external services.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.refactor.data_pipeline_planner import (
    DataPipelineDetector,
    DataPipelinePlan,
    ModernizationStep,
    PipelineDetection,
    _classify_effort,
    _classify_latency,
    _classify_severity,
    _has_streaming_imports,
    _infer_language,
    _recommend_target,
    build_plan,
    plan_data_pipelines,
    render_markdown,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A minimal fake repo root. Individual tests write their own files."""
    return tmp_path


def _write(root: Path, rel_path: str, content: str) -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ── Language inference ────────────────────────────────────────────────────


def test_infer_language_python():
    assert _infer_language(Path("src/foo.py")) == "python"


def test_infer_language_csharp():
    assert _infer_language(Path("App/Batch.cs")) == "csharp"


def test_infer_language_cobol():
    assert _infer_language(Path("legacy/job.cbl")) == "cobol"


def test_infer_language_jcl():
    assert _infer_language(Path("mainframe/run.jcl")) == "jcl"


def test_infer_language_unknown_extension():
    assert _infer_language(Path("notes.docx")) == ""


# ── Severity / latency / effort classification ────────────────────────────


def test_severity_manual_trigger_is_critical():
    assert _classify_severity("manual_trigger_ui_button") == "critical"
    assert _classify_severity("file_read_bulk_insert") == "critical"


def test_severity_cron_is_high():
    assert _classify_severity("scheduler_cron_string") == "high"
    assert _classify_severity("mainframe_jcl") == "high"


def test_severity_csv_read_is_medium():
    assert _classify_severity("file_read_csv") == "medium"


def test_severity_unknown_pattern_defaults_low():
    assert _classify_severity("made_up_pattern") == "low"


def test_latency_cobol_is_overnight():
    assert _classify_latency("file_read_cobol") == "batch_overnight"
    assert _classify_latency("mainframe_jcl") == "batch_overnight"


def test_latency_manual_is_batch_manual():
    assert _classify_latency("manual_trigger_ui_button") == "batch_manual"


def test_effort_cobol_is_xl():
    assert _classify_effort("file_read_cobol") == "XL"
    assert _classify_effort("mainframe_jcl") == "XL"


def test_effort_csv_is_small():
    assert _classify_effort("file_read_csv") == "S"


# ── Streaming absence detection ───────────────────────────────────────────


def test_streaming_absence_python_no_imports():
    assert _has_streaming_imports("import os\nimport json\n", "python") is False


def test_streaming_absence_python_with_kafka():
    assert _has_streaming_imports("from kafka import KafkaProducer\n", "python") is True


def test_streaming_absence_csharp_with_kafka():
    code = "using Confluent.Kafka;\nclass Foo {}"
    assert _has_streaming_imports(code, "csharp") is True


def test_streaming_absence_csharp_plain():
    code = "using System;\nclass Foo {}"
    assert _has_streaming_imports(code, "csharp") is False


def test_streaming_absence_unknown_language_returns_false():
    assert _has_streaming_imports("any content", "rust") is False


# ── Target recommendation ─────────────────────────────────────────────────


def test_target_for_cron_is_eventbridge():
    target = _recommend_target("scheduler_cron_string")
    assert "EventBridge" in target["primary"]
    assert target["downstream"]


def test_target_for_cobol_is_dms_bridge():
    target = _recommend_target("file_read_cobol")
    assert "DMS" in target["primary"] or "Kinesis" in target["primary"]
    assert "wrap" in target["rationale"].lower() or "stream" in target["rationale"].lower()


def test_target_for_ftp_is_transfer_family():
    target = _recommend_target("ftp_client")
    assert "Transfer Family" in target["primary"]


def test_target_for_unknown_pattern_returns_generic():
    target = _recommend_target("made_up_pattern")
    assert target["primary"]
    assert "Generic" in target["rationale"] or "TBD" in target["trigger"]


# ── DataPipelineDetector ──────────────────────────────────────────────────


def test_detector_raises_on_missing_root(tmp_path: Path):
    detector = DataPipelineDetector(tmp_path / "does-not-exist")
    with pytest.raises(FileNotFoundError):
        detector.scan()


def test_detector_empty_repo_returns_empty(tmp_repo: Path):
    detector = DataPipelineDetector(tmp_repo)
    assert detector.scan() == []


def test_detects_python_csv_read(tmp_repo: Path):
    _write(tmp_repo, "src/ingest.py", """
import pandas as pd

def load_orders():
    df = pd.read_csv('/data/orders.csv')
    return df
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "file_read_csv" in types


def test_detects_csharp_bulk_insert(tmp_repo: Path):
    _write(tmp_repo, "App/Batch.cs", """
using System.Data.SqlClient;

public class Batch
{
    public void Run()
    {
        // BULK INSERT from staging
        var cmd = new SqlCommand("BULK INSERT Orders FROM 'C:\\\\drops\\\\orders.dat'");
    }
}
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "file_read_bulk_insert" in types


def test_detects_cobol_file_open(tmp_repo: Path):
    _write(tmp_repo, "mainframe/job.cbl", """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MONTHLY-BATCH.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
       PROCEDURE DIVISION.
           OPEN INPUT CUSTOMER-FILE.
           READ CUSTOMER-FILE.
           CLOSE CUSTOMER-FILE.
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "file_read_cobol" in types


def test_detects_jcl_job(tmp_repo: Path):
    _write(tmp_repo, "mainframe/run.jcl", """
//PAYROLL JOB (ACCT),'PAYROLL RUN',CLASS=A,MSGCLASS=A
//STEP1 EXEC PGM=IEBGENER
//SYSIN DD DUMMY
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "mainframe_jcl" in types


def test_detects_quartz_scheduler(tmp_repo: Path):
    _write(tmp_repo, "Jobs/NightlyJob.cs", """
using Quartz;

public class NightlyJob : IJob
{
    public Task Execute(IJobExecutionContext context) => Task.CompletedTask;
}
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "scheduler_quartz" in types


def test_detects_hangfire_recurring(tmp_repo: Path):
    _write(tmp_repo, "Services/JobSetup.cs", """
using Hangfire;

public class JobSetup
{
    public void Configure()
    {
        RecurringJob.AddOrUpdate("daily-batch", () => RunBatch(), Cron.Daily);
    }
}
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "scheduler_hangfire" in types


def test_detects_ftp_client_python(tmp_repo: Path):
    _write(tmp_repo, "src/transfer.py", """
import ftplib

def fetch_file():
    ftp = ftplib.FTP('host')
    ftp.login('u', 'p')
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "ftp_client" in types


def test_detects_pipe_delimited_split(tmp_repo: Path):
    _write(tmp_repo, "App/Parser.cs", """
public class Parser
{
    public string[] Parse(string line) => line.Split("|");
}
""")
    detections = DataPipelineDetector(tmp_repo).scan()
    types = {d.pattern_type for d in detections}
    assert "file_read_pipe_delimited" in types


def test_skips_node_modules(tmp_repo: Path):
    _write(tmp_repo, "src/ingest.py", "import pandas as pd\npd.read_csv('x.csv')\n")
    _write(tmp_repo, "node_modules/bad.py", "import pandas as pd\npd.read_csv('x.csv')\n")
    detections = DataPipelineDetector(tmp_repo).scan()
    # Only src/ should be scanned, not node_modules
    file_paths = {d.file_path for d in detections}
    assert "src/ingest.py" in file_paths
    assert not any("node_modules" in p for p in file_paths)


def test_skips_binary_and_unscannable_extensions(tmp_repo: Path):
    _write(tmp_repo, "src/data.bin", "binary content pd.read_csv not real")
    _write(tmp_repo, "src/notes.md", "# pd.read_csv in docs")
    detections = DataPipelineDetector(tmp_repo).scan()
    # .bin and .md should be skipped
    assert detections == []


# ── build_plan ────────────────────────────────────────────────────────────


def _mk_detection(pattern_type: str, file_path: str = "x.py", line: int = 1) -> PipelineDetection:
    return PipelineDetection(
        pattern_type=pattern_type,
        file_path=file_path,
        line_number=line,
        severity=_classify_severity(pattern_type),
        latency_class=_classify_latency(pattern_type),
        description="test",
        matched_snippet="snippet",
        language="python",
    )


def test_build_plan_empty_detections():
    plan = build_plan("alpha", "/tmp/alpha", [])
    assert plan.total_detections == 0
    assert plan.steps == []
    assert "no legacy batch" in plan.narrative.lower()


def test_build_plan_groups_by_pattern_type():
    dets = [
        _mk_detection("file_read_csv", "a.py", 10),
        _mk_detection("file_read_csv", "b.py", 20),
        _mk_detection("scheduler_cron_string", "c.py", 30),
    ]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    # Should produce 2 steps (one per pattern_type), each with the right count
    assert len(plan.steps) == 2
    by_type = {s.pattern_type: s for s in plan.steps}
    assert by_type["file_read_csv"].detection_count == 2
    assert by_type["scheduler_cron_string"].detection_count == 1


def test_build_plan_orders_by_severity():
    dets = [
        _mk_detection("file_read_csv"),            # medium
        _mk_detection("manual_trigger_ui_button"), # critical
        _mk_detection("scheduler_cron_string"),    # high
    ]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    # Critical first, then high, then medium
    assert plan.steps[0].pattern_type == "manual_trigger_ui_button"
    assert plan.steps[1].pattern_type == "scheduler_cron_string"
    assert plan.steps[2].pattern_type == "file_read_csv"


def test_build_plan_attaches_target_recommendation():
    dets = [_mk_detection("file_read_csv")]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    step = plan.steps[0]
    assert "S3" in step.target_primary
    assert step.target_trigger
    assert step.target_downstream


def test_build_plan_total_effort_days_sums():
    dets = [
        _mk_detection("scheduler_cron_string"),  # S => 2 days
        _mk_detection("ftp_client"),              # M => 5 days
        _mk_detection("file_read_cobol"),         # XL => 20 days
    ]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    assert plan.total_effort_days == 2 + 5 + 20


def test_build_plan_severity_counts():
    dets = [
        _mk_detection("manual_trigger_ui_button"),  # critical
        _mk_detection("scheduler_cron_string"),     # high
        _mk_detection("scheduler_cron_string"),     # high
        _mk_detection("file_read_csv"),             # medium
    ]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    counts = plan.severity_counts
    assert counts["critical"] == 1
    assert counts["high"] == 2
    assert counts["medium"] == 1
    assert counts["low"] == 0


# ── Rollback strategies ───────────────────────────────────────────────────


def test_rollback_cobol_is_wrap_not_replace():
    dets = [_mk_detection("file_read_cobol")]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    assert "wrap" in plan.steps[0].rollback.lower()


def test_rollback_scheduler_is_dual_schedule():
    dets = [_mk_detection("scheduler_cron_string")]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    assert "dual" in plan.steps[0].rollback.lower()


def test_rollback_manual_trigger_is_feature_flag():
    dets = [_mk_detection("manual_trigger_ui_button")]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    assert "flag" in plan.steps[0].rollback.lower()


# ── Markdown rendering ────────────────────────────────────────────────────


def test_render_markdown_empty_plan():
    plan = build_plan("alpha", "/tmp/alpha", [])
    md = render_markdown(plan)
    assert "# Data pipeline modernization plan" in md
    assert "alpha" in md
    assert "0" in md  # zero detections


def test_render_markdown_includes_narrative():
    dets = [_mk_detection("scheduler_cron_string")]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    md = render_markdown(plan)
    assert "## Narrative" in md
    assert "## Modernization steps" in md


def test_render_markdown_includes_step_details():
    dets = [_mk_detection("file_read_csv", "data/loader.py", 42)]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    md = render_markdown(plan)
    assert "Modernize File Read Csv" in md
    assert "data/loader.py" in md
    assert "Target state" in md
    assert "Rationale" in md
    assert "Rollback strategy" in md


def test_render_markdown_caps_sample_detections_at_10():
    dets = [_mk_detection("file_read_csv", f"file{i}.py", i) for i in range(20)]
    plan = build_plan("alpha", "/tmp/alpha", dets)
    md = render_markdown(plan)
    # Should show 10 rows + a "... 10 more" row
    assert "10 more" in md


# ── plan_data_pipelines end-to-end ────────────────────────────────────────


def test_plan_data_pipelines_end_to_end(tmp_repo: Path):
    _write(tmp_repo, "src/ingest.py", "import pandas as pd\npd.read_csv('/data/x.csv')\n")
    _write(tmp_repo, "src/transfer.py", "import ftplib\nftp = ftplib.FTP('h')\n")
    _write(tmp_repo, "Jobs/Night.cs", "using Quartz;\nclass J : IJob {}\n")

    plan = plan_data_pipelines(app_name="alpha", app_path=str(tmp_repo))
    assert plan.app_name == "alpha"
    assert plan.total_detections >= 3
    assert plan.scanned_files >= 3
    assert plan.scan_wall_time_seconds >= 0
    assert plan.steps  # at least one step
    # Ensure plan.to_dict() is JSON-serializable
    as_dict = plan.to_dict()
    json.dumps(as_dict)


def test_plan_data_pipelines_empty_repo(tmp_repo: Path):
    plan = plan_data_pipelines(app_name="alpha", app_path=str(tmp_repo))
    assert plan.total_detections == 0
    assert plan.steps == []
    assert "no legacy batch" in plan.narrative.lower()


def test_plan_data_pipelines_severity_ordering(tmp_repo: Path):
    # Mix: one critical (manual trigger) + one medium (csv)
    _write(tmp_repo, "ui.cs", 'public void OnClick() { btnRunBatch="BtnRunBatch(x)"; }')
    _write(tmp_repo, "loader.py", "pd.read_csv('/x')")

    plan = plan_data_pipelines(app_name="alpha", app_path=str(tmp_repo))
    # Find steps in order
    if len(plan.steps) >= 2:
        # Critical should come before medium
        severities = [s.max_severity for s in plan.steps]
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        assert all(
            order[severities[i]] <= order[severities[i + 1]]
            for i in range(len(severities) - 1)
        )


def test_plan_dict_round_trip(tmp_repo: Path):
    _write(tmp_repo, "a.py", "pd.read_csv('x.csv')\n")
    plan = plan_data_pipelines(app_name="alpha", app_path=str(tmp_repo))
    d = plan.to_dict()
    # Key fields present
    assert "app_name" in d
    assert "scanned_files" in d
    assert "total_detections" in d
    assert "total_effort_days" in d
    assert "severity_counts" in d
    assert "steps" in d
    assert "narrative" in d
    # Should round-trip through JSON without error
    assert json.loads(json.dumps(d)) == d
