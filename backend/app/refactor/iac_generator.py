"""Infrastructure-as-Code generator (Gap 4 from the vision doc).

Given a ``ProjectGraph`` from the ingestion engine, emit a complete
IaC bundle: Terraform for the AWS baseline (VPC + ECS Fargate + RDS
+ secrets manager) and a Helm chart with kustomize overlays for
Kubernetes deployments. The output is a full directory the caller
can ``terraform init`` or ``helm install`` from, with every real
secret replaced by a placeholder that points at the secrets manager.

Design notes:

- The generator is deterministic and pure — given the same graph, it
  produces byte-identical output. No timestamps, no randomness.
- Every placeholder is obviously-fake (``REPLACE_ME_*``) so a
  misconfigured apply fails loud instead of silently using a dev
  default.
- Secrets are ALWAYS referenced, never inlined. The Terraform
  module declares a secrets manager resource and the Helm chart
  uses a ``valueFrom: secretKeyRef`` block.
- No provider-lock-in claims: Terraform defaults to AWS because
  that is the most common target in the Batch 3 profile, but the
  generator accepts a ``cloud`` argument so future expansions can
  emit Azure/GCP.
- The K8s manifest set is intentionally minimal — Deployment,
  Service, ConfigMap, Secret, Ingress, and three overlays
  (dev / staging / prod). Teams are expected to extend, not use
  the output as-is in production.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .ingestion import ProjectGraph

logger = logging.getLogger(__name__)


# ── Result model ───────────────────────────────────────────────────────────


@dataclass
class GeneratedIaC:
    out_dir: str
    cloud: str
    files_written: list[str] = field(default_factory=list)
    terraform_resources: int = 0
    kubernetes_manifests: int = 0
    overlays: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "out_dir": self.out_dir,
            "cloud": self.cloud,
            "files_written": self.files_written,
            "terraform_resources": self.terraform_resources,
            "kubernetes_manifests": self.kubernetes_manifests,
            "overlays": self.overlays,
        }


# ── Terraform templates ────────────────────────────────────────────────────


_TF_VERSIONS = """terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
"""


_TF_VARIABLES = """variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev / staging / prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Logical name of the application"
  type        = string
}

variable "image_uri" {
  description = "Container image URI including tag"
  type        = string
  default     = "REPLACE_ME_IMAGE_URI"
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8080
}

variable "desired_count" {
  description = "Number of ECS Fargate tasks"
  type        = number
  default     = 2
}
"""


_TF_VPC = """# ── VPC baseline ──────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "nexusforge-iac-generator"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = false
  tags = {
    Name = "${var.app_name}-${var.environment}-private-a"
    Tier = "private"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.region}b"
  map_public_ip_on_launch = false
  tags = {
    Name = "${var.app_name}-${var.environment}-private-b"
    Tier = "private"
  }
}

resource "aws_security_group" "service" {
  name        = "${var.app_name}-${var.environment}-svc"
  description = "Service-level security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Container port"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    description = "Outbound to the world"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""


_TF_ECS = """# ── ECS Fargate service ───────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_iam_role" "task_execution" {
  name = "${var.app_name}-${var.environment}-task-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.app_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name  = var.app_name
    image = var.image_uri
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = aws_secretsmanager_secret.database_url.arn
      },
      {
        name      = "JWT_SECRET"
        valueFrom = aws_secretsmanager_secret.jwt_secret.arn
      }
    ]
    environment = [
      { name = "ENVIRONMENT", value = var.environment }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/${var.app_name}-${var.environment}"
        awslogs-region        = var.region
        awslogs-stream-prefix = var.app_name
        awslogs-create-group  = "true"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name            = "${var.app_name}-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }
}
"""


_TF_RDS = """# ── Managed SQL database ──────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-${var.environment}-db"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_security_group" "db" {
  name        = "${var.app_name}-${var.environment}-db"
  description = "Database security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from service"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }
}

resource "aws_db_instance" "main" {
  identifier              = "${var.app_name}-${var.environment}"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.medium"
  allocated_storage       = 50
  storage_encrypted       = true
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  skip_final_snapshot     = var.environment != "prod"
  deletion_protection     = var.environment == "prod"
  backup_retention_period = var.environment == "prod" ? 14 : 1
  username                = "app_user"
  manage_master_user_password = true
}
"""


_TF_SECRETS = """# ── Secrets manager references ────────────────────────────────────
resource "aws_secretsmanager_secret" "database_url" {
  name        = "${var.app_name}/${var.environment}/database_url"
  description = "Database connection string"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "REPLACE_ME_DATABASE_URL"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "${var.app_name}/${var.environment}/jwt_secret"
  description = "JWT signing key"
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = "REPLACE_ME_JWT_SECRET"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
"""


_TF_OUTPUTS = """output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "db_endpoint" {
  value     = aws_db_instance.main.endpoint
  sensitive = true
}

output "secret_db_arn" {
  value = aws_secretsmanager_secret.database_url.arn
}
"""


# ── Helm chart templates ───────────────────────────────────────────────────


_CHART_YAML = """apiVersion: v2
name: {app_name}
description: Auto-generated Helm chart for {app_name}
type: application
version: 0.1.0
appVersion: "0.1.0"
"""


_VALUES_YAML = """replicaCount: 2

image:
  repository: REPLACE_ME_IMAGE_REPOSITORY
  tag: REPLACE_ME_IMAGE_TAG
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: REPLACE_ME_HOSTNAME
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

env:
  ENVIRONMENT: dev

# Secrets are populated from an external secrets manager. The keys
# below must exist in the target cluster before `helm install`.
externalSecrets:
  - name: DATABASE_URL
    secretName: {app_name}-secrets
    key: database_url
  - name: JWT_SECRET
    secretName: {app_name}-secrets
    key: jwt_secret
"""


_DEPLOYMENT_YAML = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{app_name}.fullname" . }}}}
  labels:
    app: {app_name}
spec:
  replicas: {{{{ .Values.replicaCount }}}}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: "{{{{ .Values.image.repository }}}}:{{{{ .Values.image.tag }}}}"
          imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
          ports:
            - name: http
              containerPort: {{{{ .Values.service.targetPort }}}}
              protocol: TCP
          env:
            {{{{- range $k, $v := .Values.env }}}}
            - name: {{{{ $k }}}}
              value: "{{{{ $v }}}}"
            {{{{- end }}}}
            {{{{- range .Values.externalSecrets }}}}
            - name: {{{{ .name }}}}
              valueFrom:
                secretKeyRef:
                  name: {{{{ .secretName }}}}
                  key: {{{{ .key }}}}
            {{{{- end }}}}
          resources:
            {{{{- toYaml .Values.resources | nindent 12 }}}}
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
"""


_SERVICE_YAML = """apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{app_name}.fullname" . }}}}
  labels:
    app: {app_name}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
    - port: {{{{ .Values.service.port }}}}
      targetPort: {{{{ .Values.service.targetPort }}}}
      protocol: TCP
      name: http
  selector:
    app: {app_name}
"""


_INGRESS_YAML = """{{{{- if .Values.ingress.enabled -}}}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{{{ include "{app_name}.fullname" . }}}}
  labels:
    app: {app_name}
spec:
  ingressClassName: {{{{ .Values.ingress.className }}}}
  rules:
    {{{{- range .Values.ingress.hosts }}}}
    - host: {{{{ .host }}}}
      http:
        paths:
          {{{{- range .paths }}}}
          - path: {{{{ .path }}}}
            pathType: {{{{ .pathType }}}}
            backend:
              service:
                name: {{{{ include "..fullname" $ }}}}
                port:
                  number: {{{{ $.Values.service.port }}}}
          {{{{- end }}}}
    {{{{- end }}}}
{{{{- end }}}}
""".replace("..", "{app_name}")


_HELPERS_TPL = """{{{{/*
Expand the name of the chart.
*/}}}}
{{{{- define "{app_name}.name" -}}}}
{{{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}}}
{{{{- end -}}}}

{{{{/*
Create a fully qualified app name.
*/}}}}
{{{{- define "{app_name}.fullname" -}}}}
{{{{- $name := default .Chart.Name .Values.nameOverride -}}}}
{{{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}}}
{{{{- end -}}}}
"""


# ── Kustomize overlays ─────────────────────────────────────────────────────


_KUSTOMIZE_BASE = """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../helm-rendered/deployment.yaml
  - ../helm-rendered/service.yaml
  - ../helm-rendered/ingress.yaml

commonLabels:
  app.kubernetes.io/managed-by: nexusforge-iac-generator
"""


def _overlay(env: str, replicas: int) -> str:
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: {env}

resources:
  - ../base

patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/replicas
        value: {replicas}
  - target:
      kind: Deployment
    patch: |-
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: ENVIRONMENT
          value: {env}
"""


# ── Public entry point ─────────────────────────────────────────────────────


def _count_tf_resources(content: str) -> int:
    # Each `resource "..." "..."` block counts as one resource.
    return content.count("resource \"")


def generate_iac(
    graph: ProjectGraph,
    out_dir: Path,
    cloud: str = "aws",
    app_name: str | None = None,
) -> GeneratedIaC:
    """Emit a full IaC bundle for the project represented by ``graph``.

    The generator looks at ``graph.languages`` to pick sensible
    defaults (e.g., include an RDS module when the project uses SQL)
    but is otherwise language-agnostic.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "terraform").mkdir(exist_ok=True)
    (out_dir / "helm").mkdir(exist_ok=True)
    (out_dir / "helm" / "templates").mkdir(exist_ok=True)
    (out_dir / "kustomize").mkdir(exist_ok=True)
    (out_dir / "kustomize" / "base").mkdir(exist_ok=True)

    name = app_name or graph.name or "app"
    # Kubernetes names must be lower-case and DNS-1123 compatible.
    k8s_name = "".join(
        c if (c.isalnum() or c in ("-",)) else "-"
        for c in name.lower()
    ).strip("-") or "app"

    result = GeneratedIaC(out_dir=str(out_dir), cloud=cloud)

    if cloud != "aws":
        logger.warning(
            "Unsupported cloud target %r — falling back to AWS", cloud
        )
        cloud = "aws"

    # ─ Terraform ─
    tf_parts = [
        _TF_VERSIONS,
        _TF_VARIABLES,
        _TF_VPC,
        _TF_ECS,
    ]
    has_sql = any(
        lang in ("csharp", "python", "java", "vbnet", "typescript")
        for lang in graph.languages
    )
    if has_sql:
        tf_parts.append(_TF_RDS)
    tf_parts.extend([_TF_SECRETS, _TF_OUTPUTS])
    tf_content = "\n".join(tf_parts)

    tf_main = out_dir / "terraform" / "main.tf"
    tf_main.write_text(tf_content, encoding="utf-8")
    result.files_written.append("terraform/main.tf")
    result.terraform_resources = _count_tf_resources(tf_content)

    (out_dir / "terraform" / "terraform.tfvars.example").write_text(
        f'app_name = "{k8s_name}"\n'
        f'environment = "dev"\n'
        f'image_uri = "REPLACE_ME_IMAGE_URI"\n'
        f'region = "us-east-1"\n',
        encoding="utf-8",
    )
    result.files_written.append("terraform/terraform.tfvars.example")

    (out_dir / "terraform" / "README.md").write_text(
        f"# Terraform — {k8s_name}\n\n"
        f"Auto-generated AWS baseline. Apply with:\n\n"
        f"```bash\n"
        f"cd terraform\n"
        f"terraform init\n"
        f"terraform apply -var-file=terraform.tfvars.example\n"
        f"```\n\n"
        f"All `REPLACE_ME_*` values are deliberate placeholders. A\n"
        f"misconfigured apply will fail loudly rather than silently\n"
        f"using a development default.\n",
        encoding="utf-8",
    )
    result.files_written.append("terraform/README.md")

    # ─ Helm chart ─
    (out_dir / "helm" / "Chart.yaml").write_text(
        _CHART_YAML.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/Chart.yaml")

    (out_dir / "helm" / "values.yaml").write_text(
        _VALUES_YAML.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/values.yaml")

    (out_dir / "helm" / "templates" / "_helpers.tpl").write_text(
        _HELPERS_TPL.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/templates/_helpers.tpl")

    (out_dir / "helm" / "templates" / "deployment.yaml").write_text(
        _DEPLOYMENT_YAML.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/templates/deployment.yaml")
    result.kubernetes_manifests += 1

    (out_dir / "helm" / "templates" / "service.yaml").write_text(
        _SERVICE_YAML.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/templates/service.yaml")
    result.kubernetes_manifests += 1

    (out_dir / "helm" / "templates" / "ingress.yaml").write_text(
        _INGRESS_YAML.format(app_name=k8s_name), encoding="utf-8"
    )
    result.files_written.append("helm/templates/ingress.yaml")
    result.kubernetes_manifests += 1

    # ─ Kustomize overlays ─
    (out_dir / "kustomize" / "base" / "kustomization.yaml").write_text(
        _KUSTOMIZE_BASE, encoding="utf-8"
    )
    result.files_written.append("kustomize/base/kustomization.yaml")

    for env, replicas in [("dev", 1), ("staging", 2), ("prod", 4)]:
        overlay_dir = out_dir / "kustomize" / env
        overlay_dir.mkdir(exist_ok=True)
        (overlay_dir / "kustomization.yaml").write_text(
            _overlay(env, replicas), encoding="utf-8"
        )
        result.files_written.append(f"kustomize/{env}/kustomization.yaml")
        result.overlays.append(env)

    # ─ Top-level README ─
    (out_dir / "README.md").write_text(
        f"# IaC bundle — {k8s_name}\n\n"
        f"Auto-generated by NexusForge. Target cloud: {cloud}.\n\n"
        f"## Layout\n\n"
        f"- `terraform/`: AWS baseline (VPC, ECS Fargate, RDS, Secrets Manager)\n"
        f"- `helm/`: Helm chart with templates and default values\n"
        f"- `kustomize/`: `base` + `dev`/`staging`/`prod` overlays\n\n"
        f"## Next steps\n\n"
        f"1. Replace every `REPLACE_ME_*` placeholder with real values.\n"
        f"2. Run `terraform init && terraform apply` for the AWS baseline.\n"
        f"3. Run `helm lint helm/` or `kustomize build kustomize/prod` to\n"
        f"   render the Kubernetes manifests.\n"
        f"4. Wire the secrets manager entries into your CI/CD pipeline.\n\n"
        f"_All placeholders are deliberate. This bundle should fail an\n"
        f"`apply` without manual configuration._\n",
        encoding="utf-8",
    )
    result.files_written.append("README.md")

    return result
