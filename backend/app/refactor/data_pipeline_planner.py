"""Data pipeline modernization planner — Gap 6.

Walks a legacy codebase, detects pattern signatures of the "flat-file
batch + manual reconciliation" era that still dominates enterprise
legacy stacks, and produces a phased modernization plan recommending
AWS-native event-driven replacements (S3 events, EventBridge Scheduler,
Transfer Family, Kinesis / MSK, DMS) with schema inference when the
file format is tractable.

Motivation: real enterprise legacy systems ingest data from flat files
(CSV, pipe-delimited, fixed-width, XML), run batch jobs on cron or
Windows Task Scheduler, trigger reconciliation manually via UI buttons,
and write to databases with BULK INSERT. They have zero streaming
infrastructure, zero schema registry, and monthly-or-slower latency.
The modernization target state is event-driven: data lands in S3,
triggers a Lambda, which produces to Kinesis or MSK, which fans out
to downstream consumers with a schema registry enforcing contracts.

This planner takes a path to an ingested repo and produces:
    - a list of ``PipelineDetection`` findings (one per detected pattern)
    - a ``DataPipelinePlan`` with ordered ``ModernizationStep`` items
      each carrying strategy, AWS service recommendations, effort, risk,
      and rollback guidance
    - a Markdown summary for stakeholder review

The planner is DETECTION-ONLY. It does not write code and does not
provision infrastructure. The generated recommendations are consumed
by the IaC generator (Gap 4) to scaffold the target stack and by the
compliance enforcer (Gap 7) to enforce encryption at source on the
new event-driven pipelines.

Related gaps:
- Gap 1 (multi_lang_scanner): used upstream to walk the repo
- Gap 3 (strangler_planner): phases here feed into the strangler plan
  as the "data-layer" extraction track
- Gap 4 (iac_generator): consumes this planner's output to scaffold
  Terraform modules for MSK, Kinesis, S3 events, etc.
- Gap 5 (gitflow_generator): governance for the pipeline repo
- Gap 7 (compliance_enforcer): wraps the new pipelines in encryption
  and audit middleware

Scope boundary: this module does NOT modernize the pipelines itself.
It identifies them, classifies them, and recommends the target stack.
Actual code migration is out of scope — that is a downstream step in
the refactor engine.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Detection rules ────────────────────────────────────────────────────────
#
# Each rule is a tuple of (pattern_type, regex, languages, description).
# Patterns are compiled lazily. We prefer precise regexes over broad ones
# so false positives stay low; a separate absence-signal pass catches
# things the regex list cannot.

_DETECTION_RULES: list[tuple[str, str, list[str], str]] = [
    # ── File-based ingestion ──────────────────────────────────────────────
    (
        "file_read_csv",
        r"(?i)\b(pd\.read_csv|csv\.(reader|DictReader)|File\.ReadAllText|StreamReader\s*\()",
        ["python", "csharp", "vb"],
        "Direct CSV file read without streaming",
    ),
    (
        "file_read_pipe_delimited",
        r"""(?i)\.Split\s*\(\s*["']\|["']\s*\)""",
        ["python", "csharp", "java", "vb"],
        "Pipe-delimited file parsing (common in legacy EDI / banking)",
    ),
    (
        "file_read_fixed_width",
        r"(?i)(\.Substring\s*\(\s*\d+\s*,\s*\d+\s*\).*\.Substring\s*\(\s*\d+\s*,\s*\d+\s*\))",
        ["python", "csharp", "vb"],
        "Fixed-width record parsing (legacy mainframe export format)",
    ),
    (
        "file_read_xml_load",
        r"(?i)(XmlDocument\.Load|XDocument\.Load|ElementTree\.parse|etree\.parse)\s*\(",
        ["python", "csharp", "java"],
        "XML file load — often a batch reconciliation feed",
    ),
    (
        "file_read_cobol",
        r"(?im)^\s*OPEN\s+(INPUT|I-O|OUTPUT)\s+[\w-]+",
        ["cobol"],
        "COBOL sequential/VSAM file OPEN — mainframe batch job signature",
    ),
    (
        "file_read_bulk_insert",
        r"(?i)\b(BULK\s+INSERT|SqlBulkCopy|LOAD\s+DATA\s+INFILE|COPY\s+\w+\s+FROM)",
        ["sql", "csharp", "python"],
        "Bulk DB insert from file — zero streaming, blocking, no retry",
    ),
    # ── Scheduled batch triggers ──────────────────────────────────────────
    (
        "scheduler_cron_string",
        r"""(?m)^\s*["']?(\*|\d+|\*/\d+)\s+(\*|\d+|\*/\d+)\s+(\*|\d+|\*/\d+)\s+(\*|\d+|\*/\d+)\s+(\*|\d+|\*/\d+|MON|TUE|WED|THU|FRI|SAT|SUN)["']?""",
        ["python", "yaml", "json", "csharp"],
        "Cron expression literal — batch job scheduled trigger",
    ),
    (
        "scheduler_quartz",
        r"(?i)(QuartzNet|ScheduleJob|IJob\b|IScheduler\b|CronTrigger\b)",
        ["csharp"],
        "Quartz.NET scheduler — legacy .NET batch framework",
    ),
    (
        "scheduler_hangfire",
        r"(?i)(RecurringJob\.AddOrUpdate|BackgroundJob\.Enqueue\s*\(.*batch)",
        ["csharp"],
        "Hangfire background scheduler — often wraps manual batch jobs",
    ),
    (
        "scheduler_spring",
        r"(?i)@Scheduled\s*\(",
        ["java"],
        "Spring @Scheduled annotation — batch trigger",
    ),
    (
        "scheduler_apscheduler",
        r"(?i)(BackgroundScheduler|BlockingScheduler|scheduler\.add_job)",
        ["python"],
        "Python APScheduler — batch job definition",
    ),
    (
        "scheduler_celery_beat",
        r"(?i)(celery[- ]beat|CELERY_BEAT_SCHEDULE|beat_schedule\s*=)",
        ["python"],
        "Celery beat — recurring task definition",
    ),
    (
        "scheduler_task_scheduler_xml",
        r"(?i)<Task\s+version=.*TaskScheduler",
        ["xml"],
        "Windows Task Scheduler XML export",
    ),
    # ── Manual trigger patterns ───────────────────────────────────────────
    (
        "manual_trigger_ui_button",
        r"(?i)(onclick|btnRunBatch|RunReconciliation|StartBatch)[\w_]*\s*=?\s*[\"']?\w+\s*\(",
        ["csharp", "vb", "javascript"],
        "UI button handler invokes batch — user-driven trigger, no automation",
    ),
    (
        "manual_trigger_excel_macro",
        r"(?i)(Workbook_Open|Sub\s+RunBatch|Application\.Run)",
        ["vb"],
        "Excel VBA macro triggers batch — user-driven, no audit trail",
    ),
    # ── File transfer protocols ───────────────────────────────────────────
    (
        "ftp_client",
        r"(?i)(ftplib|FtpWebRequest|SftpClient|paramiko|ssh2\.SftpClient)",
        ["python", "csharp", "javascript"],
        "FTP/SFTP client — legacy file drop ingestion",
    ),
    (
        "as2_gateway",
        r"(?i)(as2gateway|mendelson|oftp2|EDIFACT)",
        ["python", "csharp", "java"],
        "EDI / AS2 gateway — vendor-specific legacy EDI",
    ),
    (
        "mainframe_jcl",
        r"(?im)^//\s*\S+\s+JOB\b|^//STEP\d+\s+EXEC\b",
        ["jcl"],
        "JCL job control — mainframe batch orchestration",
    ),
    # ── Absent streaming signals (checked separately, not as regex matches)
    # See ``_check_streaming_absence`` for the absence-detection pass.
]


# Compile rules lazily on first use
_COMPILED_RULES: list[tuple[str, re.Pattern, list[str], str]] | None = None


def _get_compiled_rules() -> list[tuple[str, re.Pattern, list[str], str]]:
    global _COMPILED_RULES
    if _COMPILED_RULES is None:
        compiled = []
        for pattern_type, regex, langs, desc in _DETECTION_RULES:
            try:
                compiled.append((pattern_type, re.compile(regex), langs, desc))
            except re.error as exc:
                logger.warning("Invalid regex for %s: %s", pattern_type, exc)
        _COMPILED_RULES = compiled
    return _COMPILED_RULES


# ── Streaming absence signals ──────────────────────────────────────────────
#
# If a file doing batch work imports NONE of these libraries, it is
# eligible for modernization to an event-driven target. Presence of any
# of these suggests the codebase already has streaming infrastructure
# and we should not recommend modernization for that specific file.

_STREAMING_IMPORTS_PYTHON = {
    "kafka", "aiokafka", "kafka-python", "confluent_kafka",
    "boto3.client('kinesis')", "boto3.resource('kinesis')",
    "aws_lambda_powertools.utilities.streaming",
}
_STREAMING_IMPORTS_CSHARP = {
    "Confluent.Kafka", "Amazon.Kinesis", "Amazon.MSK",
    "Microsoft.Azure.EventHubs", "Azure.Messaging.EventHubs",
}
_STREAMING_IMPORTS_JAVA = {
    "org.apache.kafka", "software.amazon.awssdk.services.kinesis",
    "software.amazon.awssdk.services.kafka",
    "io.confluent.kafka.serializers",
}


def _has_streaming_imports(content: str, language: str) -> bool:
    """Return True if the file imports known streaming libraries.

    Presence means the file is already (or partially) event-driven and
    does NOT need modernization for that specific capability.
    """
    if language == "python":
        return any(imp.split(".")[0] in content for imp in _STREAMING_IMPORTS_PYTHON)
    if language == "csharp":
        return any(imp in content for imp in _STREAMING_IMPORTS_CSHARP)
    if language == "java":
        return any(imp in content for imp in _STREAMING_IMPORTS_JAVA)
    return False


# ── Language inference ────────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".cs": "csharp",
    ".vb": "vb",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".cbl": "cobol",
    ".cob": "cobol",
    ".cpy": "cobol",
    ".jcl": "jcl",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".sql": "sql",
    ".ps1": "powershell",
}


def _infer_language(file_path: Path) -> str:
    return _EXT_TO_LANG.get(file_path.suffix.lower(), "")


# ── Severity classification ───────────────────────────────────────────────
#
# Severity reflects the remediation priority: how much operational or
# financial risk does this detection carry if left unmodernized?

_SEVERITY_BY_PATTERN: dict[str, str] = {
    # Critical: data loss risk, no recovery path, no audit
    "manual_trigger_ui_button": "critical",
    "manual_trigger_excel_macro": "critical",
    "file_read_bulk_insert": "critical",
    # High: scheduled but fragile, no retry, blocking
    "scheduler_cron_string": "high",
    "scheduler_quartz": "high",
    "scheduler_task_scheduler_xml": "high",
    "file_read_cobol": "high",
    "mainframe_jcl": "high",
    "ftp_client": "high",
    "as2_gateway": "high",
    # Medium: batch with some resilience but no streaming alternative
    "scheduler_hangfire": "medium",
    "scheduler_spring": "medium",
    "scheduler_apscheduler": "medium",
    "scheduler_celery_beat": "medium",
    "file_read_csv": "medium",
    "file_read_pipe_delimited": "medium",
    "file_read_fixed_width": "medium",
    "file_read_xml_load": "medium",
}


def _classify_severity(pattern_type: str) -> str:
    return _SEVERITY_BY_PATTERN.get(pattern_type, "low")


# ── Latency classification ────────────────────────────────────────────────
#
# Latency class drives the target-state recommendation. Manual triggers
# could become real-time with an event-driven refactor; existing cron
# jobs at nightly cadence are fine as scheduled Lambdas, not streams.

_LATENCY_BY_PATTERN: dict[str, str] = {
    "manual_trigger_ui_button": "batch_manual",
    "manual_trigger_excel_macro": "batch_manual",
    "file_read_bulk_insert": "batch_manual",
    "scheduler_cron_string": "batch_scheduled",
    "scheduler_quartz": "batch_scheduled",
    "scheduler_hangfire": "batch_scheduled",
    "scheduler_spring": "batch_scheduled",
    "scheduler_apscheduler": "batch_scheduled",
    "scheduler_celery_beat": "batch_scheduled",
    "scheduler_task_scheduler_xml": "batch_scheduled",
    "file_read_csv": "batch_scheduled",
    "file_read_pipe_delimited": "batch_scheduled",
    "file_read_fixed_width": "batch_scheduled",
    "file_read_xml_load": "batch_scheduled",
    "file_read_cobol": "batch_overnight",
    "mainframe_jcl": "batch_overnight",
    "ftp_client": "batch_scheduled",
    "as2_gateway": "batch_scheduled",
}


def _classify_latency(pattern_type: str) -> str:
    return _LATENCY_BY_PATTERN.get(pattern_type, "batch_scheduled")


# ── AWS target recommendation ─────────────────────────────────────────────
#
# For each detection we recommend a concrete AWS-native modernization
# target. The recommendation is a triple of (primary_service, trigger_mechanism,
# downstream_consumer) so the IaC generator (Gap 4) can scaffold the
# right Terraform modules.

_TARGET_BY_PATTERN: dict[str, dict[str, str]] = {
    "manual_trigger_ui_button": {
        "primary": "API Gateway + Lambda",
        "trigger": "API call (with auto-trigger on upstream event)",
        "downstream": "EventBridge → SNS/SQS fanout",
        "rationale": (
            "Replace the UI button with an API endpoint that is also "
            "invoked automatically when upstream data becomes available. "
            "The button becomes a manual override, not the primary path."
        ),
    },
    "manual_trigger_excel_macro": {
        "primary": "API Gateway + Lambda",
        "trigger": "File upload to S3 replaces the Excel workflow",
        "downstream": "EventBridge → downstream Lambda",
        "rationale": (
            "Excel macros as triggers are brittle and audit-unfriendly. "
            "Replace with an S3 upload UI that fires an EventBridge "
            "rule. The macro-based validation logic moves into the "
            "Lambda handler."
        ),
    },
    "file_read_bulk_insert": {
        "primary": "Kinesis Firehose + Glue Schema Registry",
        "trigger": "S3 ObjectCreated event",
        "downstream": "Redshift / Data Lake via Firehose delivery stream",
        "rationale": (
            "BULK INSERT from flat file blocks the database and has no "
            "retry. Ingest into S3 instead, let Firehose stream to the "
            "target warehouse with schema registry enforcement."
        ),
    },
    "scheduler_cron_string": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Cron or rate expression in EventBridge",
        "downstream": "Step Functions if multi-step",
        "rationale": (
            "Crontab-scheduled batch jobs become EventBridge Scheduler "
            "rules with native retry, DLQ, and CloudWatch observability."
        ),
    },
    "scheduler_quartz": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "Step Functions for orchestration",
        "rationale": (
            "Quartz.NET is tightly coupled to the .NET app lifecycle. "
            "Move orchestration out to EventBridge so scheduling is "
            "infrastructure, not application code."
        ),
    },
    "scheduler_hangfire": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "SQS for job queue",
        "rationale": (
            "Hangfire job storage (usually SQL Server) becomes a single "
            "point of failure. EventBridge + SQS replaces the whole "
            "job storage layer."
        ),
    },
    "scheduler_spring": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "SQS for decoupled execution",
        "rationale": (
            "@Scheduled inside the Spring container ties scheduling to "
            "app uptime. Move to EventBridge so jobs run even when the "
            "app is scaling / updating."
        ),
    },
    "scheduler_apscheduler": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "SQS",
        "rationale": (
            "APScheduler runs inside the Python process. Moving to "
            "EventBridge makes scheduling durable across deployments."
        ),
    },
    "scheduler_celery_beat": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "SQS replaces Celery queue",
        "rationale": (
            "Celery + Redis as a scheduler is operable but adds infra. "
            "EventBridge + Lambda + SQS removes the Redis dependency."
        ),
    },
    "scheduler_task_scheduler_xml": {
        "primary": "EventBridge Scheduler + Lambda",
        "trigger": "Rate or cron expression",
        "downstream": "SQS / SNS",
        "rationale": (
            "Windows Task Scheduler is tied to a specific EC2. Moving "
            "to EventBridge removes host affinity."
        ),
    },
    "file_read_csv": {
        "primary": "S3 + Lambda",
        "trigger": "S3 ObjectCreated event",
        "downstream": "Kinesis Data Streams or Firehose",
        "rationale": (
            "CSV file ingestion becomes event-driven via S3 upload. "
            "The Lambda can parse + validate + produce to Kinesis for "
            "real-time downstream consumers."
        ),
    },
    "file_read_pipe_delimited": {
        "primary": "S3 + Lambda + Glue Schema Registry",
        "trigger": "S3 ObjectCreated event",
        "downstream": "Kinesis Data Streams",
        "rationale": (
            "Pipe-delimited formats usually lack a schema file. Infer "
            "schema on first ingestion and register it in Glue so "
            "downstream consumers get a typed contract."
        ),
    },
    "file_read_fixed_width": {
        "primary": "S3 + Lambda + Glue Schema Registry",
        "trigger": "S3 ObjectCreated event",
        "downstream": "Kinesis Data Streams",
        "rationale": (
            "Fixed-width parsing is fragile and format-drift-prone. "
            "Register the byte offsets in Glue once and validate on "
            "every ingestion."
        ),
    },
    "file_read_xml_load": {
        "primary": "S3 + Lambda + XSD validation",
        "trigger": "S3 ObjectCreated event",
        "downstream": "EventBridge → SNS fanout",
        "rationale": (
            "XML feeds often have a published XSD. Validate on ingestion "
            "and fail fast instead of discovering errors downstream."
        ),
    },
    "file_read_cobol": {
        "primary": "DMS + Kinesis Data Streams",
        "trigger": "CDC on the underlying dataset or mainframe file arrival",
        "downstream": "Kinesis to Data Lake",
        "rationale": (
            "Mainframe COBOL file I/O cannot be refactored without "
            "rewriting the mainframe code. Wrap it: let DMS or a CDC "
            "layer stream the same data off the dataset in real-time "
            "while the COBOL code stays in place."
        ),
    },
    "mainframe_jcl": {
        "primary": "MQ / Kinesis bridge",
        "trigger": "JCL step completion triggers a bridge job",
        "downstream": "Data Lake",
        "rationale": (
            "JCL batch step cannot be replaced. Add a bridge step that "
            "publishes the step outcome to Kinesis, so downstream "
            "systems become event-driven even though the mainframe "
            "stays batch."
        ),
    },
    "ftp_client": {
        "primary": "AWS Transfer Family + S3 + EventBridge",
        "trigger": "SFTP drop lands in S3, fires EventBridge rule",
        "downstream": "Lambda → Kinesis",
        "rationale": (
            "Replace the custom FTP client with AWS Transfer Family. "
            "Files land directly in S3, triggering the downstream "
            "pipeline with native retry and observability."
        ),
    },
    "as2_gateway": {
        "primary": "AWS Transfer Family (AS2) + S3",
        "trigger": "AS2 transfer lands in S3, fires EventBridge rule",
        "downstream": "Lambda → Kinesis",
        "rationale": (
            "AWS Transfer Family supports AS2 natively. Replace the "
            "Mendelson/OFTP2 gateway with managed infrastructure."
        ),
    },
}


def _recommend_target(pattern_type: str) -> dict[str, str]:
    return _TARGET_BY_PATTERN.get(
        pattern_type,
        {
            "primary": "EventBridge + Lambda",
            "trigger": "Event source TBD",
            "downstream": "SQS / Kinesis",
            "rationale": "Generic recommendation — detection pattern not mapped.",
        },
    )


# ── Effort classification ─────────────────────────────────────────────────

_EFFORT_BY_PATTERN: dict[str, str] = {
    "manual_trigger_ui_button": "M",
    "manual_trigger_excel_macro": "L",
    "file_read_bulk_insert": "M",
    "scheduler_cron_string": "S",
    "scheduler_quartz": "M",
    "scheduler_hangfire": "M",
    "scheduler_spring": "S",
    "scheduler_apscheduler": "S",
    "scheduler_celery_beat": "M",
    "scheduler_task_scheduler_xml": "S",
    "file_read_csv": "S",
    "file_read_pipe_delimited": "M",
    "file_read_fixed_width": "M",
    "file_read_xml_load": "M",
    "file_read_cobol": "XL",  # cannot refactor, must wrap
    "mainframe_jcl": "XL",
    "ftp_client": "M",
    "as2_gateway": "L",
}

_EFFORT_TO_DAYS: dict[str, int] = {
    "S": 2,
    "M": 5,
    "L": 10,
    "XL": 20,
}


def _classify_effort(pattern_type: str) -> str:
    return _EFFORT_BY_PATTERN.get(pattern_type, "M")


# ── Dataclasses ───────────────────────────────────────────────────────────


@dataclass
class PipelineDetection:
    """A single detected legacy batch pattern."""

    pattern_type: str
    file_path: str
    line_number: int
    severity: str         # critical / high / medium / low
    latency_class: str    # batch_manual / batch_scheduled / batch_overnight
    description: str
    matched_snippet: str
    language: str
    has_streaming_nearby: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModernizationStep:
    """A single step in the modernization plan for one or more detections."""

    index: int
    title: str
    pattern_type: str
    detections: list[PipelineDetection] = field(default_factory=list)
    target_primary: str = ""
    target_trigger: str = ""
    target_downstream: str = ""
    rationale: str = ""
    effort_class: str = "M"      # S / M / L / XL
    effort_days: int = 0
    risk: str = "medium"          # low / medium / high
    rollback: str = ""

    @property
    def detection_count(self) -> int:
        return len(self.detections)

    @property
    def max_severity(self) -> str:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if not self.detections:
            return "low"
        return min(self.detections, key=lambda d: order.get(d.severity, 4)).severity

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "pattern_type": self.pattern_type,
            "detection_count": self.detection_count,
            "max_severity": self.max_severity,
            "target": {
                "primary": self.target_primary,
                "trigger": self.target_trigger,
                "downstream": self.target_downstream,
            },
            "rationale": self.rationale,
            "effort_class": self.effort_class,
            "effort_days": self.effort_days,
            "risk": self.risk,
            "rollback": self.rollback,
            "detections": [d.to_dict() for d in self.detections],
        }


@dataclass
class DataPipelinePlan:
    """Full modernization plan for a repo / app."""

    app_name: str
    app_path: str
    scanned_files: int = 0
    total_detections: int = 0
    steps: list[ModernizationStep] = field(default_factory=list)
    narrative: str = ""
    scan_wall_time_seconds: float = 0.0

    @property
    def total_effort_days(self) -> int:
        return sum(s.effort_days for s in self.steps)

    @property
    def severity_counts(self) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for step in self.steps:
            for det in step.detections:
                counts[det.severity] = counts.get(det.severity, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "app_path": self.app_path,
            "scanned_files": self.scanned_files,
            "total_detections": self.total_detections,
            "total_effort_days": self.total_effort_days,
            "severity_counts": self.severity_counts,
            "scan_wall_time_seconds": round(self.scan_wall_time_seconds, 3),
            "steps": [s.to_dict() for s in self.steps],
            "narrative": self.narrative,
        }


# ── Detector ──────────────────────────────────────────────────────────────


# File extensions we actually read. Everything else is skipped.
_SCANNABLE_EXTS = set(_EXT_TO_LANG.keys())

# Directories we skip outright — build outputs, VCS, dependencies, etc.
_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "bower_components",
    "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache",
    "bin", "obj", "target",        # C#, Java build outputs
    "build", "dist", "out",
    ".next", ".nuxt", ".vercel",
    "coverage", ".coverage",
}

# File size cap to avoid OOM on generated / minified files
_MAX_FILE_BYTES = 2_000_000       # 2 MB


class DataPipelineDetector:
    """Walks a repo and applies the detection rules to every eligible file."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def scan(self) -> list[PipelineDetection]:
        """Return all detections across the repo.

        Walks ``self.root`` recursively, skipping ``_SKIP_DIRS`` and
        binary files, applies each regex rule that is registered for
        the file's language, and records the line number + matched
        snippet for every hit.
        """
        if not self.root.exists():
            raise FileNotFoundError(f"Repo root does not exist: {self.root}")

        detections: list[PipelineDetection] = []
        rules = _get_compiled_rules()

        for path in self._iter_files():
            language = _infer_language(path)
            if not language:
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                logger.debug("Skipping unreadable file %s: %s", path, exc)
                continue

            if len(text.encode("utf-8", errors="ignore")) > _MAX_FILE_BYTES:
                logger.debug("Skipping oversized file %s", path)
                continue

            has_streaming = _has_streaming_imports(text, language)

            for pattern_type, pattern, langs, desc in rules:
                if language not in langs:
                    continue
                for match in pattern.finditer(text):
                    line_number = text.count("\n", 0, match.start()) + 1
                    snippet = match.group(0)[:200].replace("\n", " ")
                    detections.append(
                        PipelineDetection(
                            pattern_type=pattern_type,
                            file_path=str(path.relative_to(self.root)).replace("\\", "/"),
                            line_number=line_number,
                            severity=_classify_severity(pattern_type),
                            latency_class=_classify_latency(pattern_type),
                            description=desc,
                            matched_snippet=snippet,
                            language=language,
                            has_streaming_nearby=has_streaming,
                        )
                    )

        return detections

    def _iter_files(self):
        """Generator over files eligible for scanning."""
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _SCANNABLE_EXTS:
                continue
            yield path


# ── Planner ───────────────────────────────────────────────────────────────


# Severity weight for plan ordering — highest severity first
_SEVERITY_WEIGHT = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_plan(
    app_name: str,
    app_path: str,
    detections: list[PipelineDetection],
) -> DataPipelinePlan:
    """Group detections by pattern_type and produce an ordered plan.

    The planner does not care about *where* in the code a pattern was
    found — it cares about *what kind* of pattern it is, so the
    recommendation can be applied once at the infrastructure level.
    Grouping by pattern_type means a repo with 50 cron jobs gets one
    modernization step, not 50.

    Phases are ordered by max severity first, then by pattern type so
    the output is deterministic.
    """
    plan = DataPipelinePlan(
        app_name=app_name,
        app_path=app_path,
        total_detections=len(detections),
    )

    # Group by pattern_type
    groups: dict[str, list[PipelineDetection]] = {}
    for det in detections:
        groups.setdefault(det.pattern_type, []).append(det)

    # Build steps for each group
    steps: list[ModernizationStep] = []
    for pattern_type, dets in groups.items():
        target = _recommend_target(pattern_type)
        effort_class = _classify_effort(pattern_type)
        step = ModernizationStep(
            index=0,  # set below after sort
            title=_step_title(pattern_type, len(dets)),
            pattern_type=pattern_type,
            detections=dets,
            target_primary=target["primary"],
            target_trigger=target["trigger"],
            target_downstream=target["downstream"],
            rationale=target["rationale"],
            effort_class=effort_class,
            effort_days=_EFFORT_TO_DAYS.get(effort_class, 5) * max(1, len(dets) // 10),
            risk=_risk_for_pattern(pattern_type),
            rollback=_rollback_for_pattern(pattern_type),
        )
        steps.append(step)

    # Sort by max severity, then pattern_type for determinism
    steps.sort(
        key=lambda s: (_SEVERITY_WEIGHT.get(s.max_severity, 4), s.pattern_type)
    )
    for idx, step in enumerate(steps, start=1):
        step.index = idx

    plan.steps = steps
    plan.narrative = _narrative(plan)
    return plan


def _step_title(pattern_type: str, count: int) -> str:
    readable = pattern_type.replace("_", " ").title()
    return f"Modernize {readable} ({count} detection{'s' if count != 1 else ''})"


def _risk_for_pattern(pattern_type: str) -> str:
    if pattern_type in ("file_read_cobol", "mainframe_jcl"):
        return "high"  # cannot be refactored, wrapping is the safest route
    if pattern_type.startswith("manual_trigger"):
        return "medium"
    if pattern_type.startswith("scheduler_"):
        return "low"
    return "medium"


def _rollback_for_pattern(pattern_type: str) -> str:
    if pattern_type in ("file_read_cobol", "mainframe_jcl"):
        return (
            "Wrap-not-replace: the legacy mainframe code stays in place. "
            "Rollback means disabling the bridge job; no legacy changes "
            "to revert."
        )
    if pattern_type.startswith("manual_trigger"):
        return (
            "Feature-flag the new API endpoint. The UI button remains "
            "live until the flag flips to auto-trigger. Rollback: flip "
            "the flag off."
        )
    if pattern_type.startswith("scheduler_"):
        return (
            "Dual-schedule: run the new EventBridge rule alongside the "
            "legacy cron/Quartz job for one cycle. Compare outputs, "
            "disable the legacy schedule once verified."
        )
    if pattern_type.startswith("file_read_"):
        return (
            "Dual-write: the legacy file reader stays, the new S3 + "
            "Lambda pipeline writes to a staging table. Verify parity, "
            "cut over, disable the legacy path."
        )
    return "Standard feature-flag rollout with parity verification."


def _narrative(plan: DataPipelinePlan) -> str:
    """Human-readable summary paragraph for the plan."""
    if plan.total_detections == 0:
        return (
            f"Scanned {plan.scanned_files} files in {plan.app_name} and "
            "found no legacy batch pipeline patterns. The app appears "
            "to already use event-driven or streaming ingestion, OR "
            "the detection rules do not cover this stack. Review "
            "manually if in doubt."
        )

    counts = plan.severity_counts
    crit = counts.get("critical", 0)
    high = counts.get("high", 0)
    total = plan.total_detections
    steps = len(plan.steps)
    days = plan.total_effort_days

    parts = [
        f"Scanned {plan.scanned_files} files in {plan.app_name} and "
        f"identified {total} legacy batch pipeline pattern{'s' if total != 1 else ''} "
        f"grouped into {steps} modernization step{'s' if steps != 1 else ''}."
    ]
    if crit > 0:
        parts.append(
            f"{crit} critical finding{'s' if crit != 1 else ''} — manual "
            "triggers or BULK INSERT patterns that block operational "
            "stability and must be addressed first."
        )
    if high > 0:
        parts.append(
            f"{high} high-severity finding{'s' if high != 1 else ''} — "
            "scheduled batch jobs, mainframe file reads, and file "
            "transfer protocols that are modernization targets for "
            "EventBridge Scheduler, DMS, or AWS Transfer Family."
        )
    parts.append(
        f"Total estimated effort: {days} days. See the per-step "
        "rationale and rollback guidance for execution order."
    )
    return " ".join(parts)


# ── Markdown renderer ─────────────────────────────────────────────────────


def render_markdown(plan: DataPipelinePlan) -> str:
    """Render a stakeholder-facing markdown report of the plan."""
    lines: list[str] = []
    lines.append(f"# Data pipeline modernization plan — {plan.app_name}")
    lines.append("")
    lines.append(f"**App path:** `{plan.app_path}`  ")
    lines.append(f"**Scanned files:** {plan.scanned_files}  ")
    lines.append(f"**Detections:** {plan.total_detections}  ")
    lines.append(f"**Modernization steps:** {len(plan.steps)}  ")
    lines.append(f"**Estimated effort:** {plan.total_effort_days} days  ")

    counts = plan.severity_counts
    sev_line = " · ".join(
        f"{sev}: {counts.get(sev, 0)}" for sev in ("critical", "high", "medium", "low")
    )
    lines.append(f"**Severity breakdown:** {sev_line}  ")
    lines.append("")
    lines.append("## Narrative")
    lines.append("")
    lines.append(plan.narrative)
    lines.append("")

    if not plan.steps:
        return "\n".join(lines) + "\n"

    lines.append("## Modernization steps")
    lines.append("")

    for step in plan.steps:
        lines.append(f"### Step {step.index} — {step.title}")
        lines.append("")
        lines.append(f"**Max severity:** `{step.max_severity}`  ")
        lines.append(f"**Risk:** `{step.risk}`  ")
        lines.append(f"**Effort:** {step.effort_class} (~{step.effort_days} days)  ")
        lines.append(f"**Detections in this group:** {step.detection_count}")
        lines.append("")
        lines.append("#### Target state")
        lines.append("")
        lines.append(f"- **Primary service**: {step.target_primary}")
        lines.append(f"- **Trigger**: {step.target_trigger}")
        lines.append(f"- **Downstream**: {step.target_downstream}")
        lines.append("")
        lines.append("#### Rationale")
        lines.append("")
        lines.append(step.rationale)
        lines.append("")
        lines.append("#### Rollback strategy")
        lines.append("")
        lines.append(step.rollback)
        lines.append("")

        # Show up to 10 detections per step
        if step.detections:
            lines.append("#### Sample detections")
            lines.append("")
            lines.append("| File | Line | Snippet |")
            lines.append("|---|---|---|")
            for det in step.detections[:10]:
                snippet = det.matched_snippet.replace("|", "\\|")[:80]
                lines.append(f"| `{det.file_path}` | {det.line_number} | `{snippet}` |")
            if step.detection_count > 10:
                lines.append(
                    f"| ... | ... | _{step.detection_count - 10} more_ |"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Generated by NexusForge Data Pipeline Planner (Gap 6). "
        "See `backend/app/refactor/data_pipeline_planner.py` for "
        "detection rules and classification logic._"
    )
    lines.append("")
    return "\n".join(lines)


# ── Public entry point ────────────────────────────────────────────────────


def plan_data_pipelines(app_name: str, app_path: str) -> DataPipelinePlan:
    """End-to-end: walk the repo, detect patterns, produce a plan.

    This is the function the FastAPI route calls.
    """
    import time

    start = time.monotonic()
    root = Path(app_path)
    detector = DataPipelineDetector(root)
    detections = detector.scan()

    plan = build_plan(app_name=app_name, app_path=app_path, detections=detections)
    plan.scan_wall_time_seconds = time.monotonic() - start

    # Count scanned files
    scanned = sum(1 for _ in detector._iter_files())
    plan.scanned_files = scanned
    # Refresh narrative now that scanned_files is set
    plan.narrative = _narrative(plan)

    return plan
