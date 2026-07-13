terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH into the instance"
  type        = string
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH"
  type        = string
  default     = null
}

variable "repo_url" {
  description = "Git repository URL to clone on the EC2 instance"
  type        = string
  default     = "https://github.com/EmmanSkout/PyGateway.git"
}

variable "app_dir" {
  description = "Directory name for the cloned app on the instance"
  type        = string
  default     = "PyGateway"
}

variable "allowed_algos" {
  description = "Allowed algorithms for the API"
  type        = string
  default     = "[\"fixed_window\",\"sliding_window\",\"token_bucket\"]"
}

variable "fixed_window_length" {
  description = "Fixed window length in seconds"
  type        = number
  default     = 10
}

variable "redis_host" {
  description = "Redis host for the app"
  type        = string
  default     = "redis"
}

variable "redis_port" {
  description = "Redis port for the app"
  type        = number
  default     = 6379
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_ssm" {
  name               = "pygateway-ec2-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ec2_ssm_core" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "pygateway-ec2-instance-profile"
  role = aws_iam_role.ec2_ssm.name
}

resource "aws_security_group" "app" {
  name        = "pygateway-ec2-sg"
  description = "Allow SSH and HTTP for PyGateway"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "pygateway-ec2-sg"
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data = <<-EOT
#!/bin/bash
set -euxo pipefail

retry() {
  local retries=10
  local wait_seconds=6
  local attempt=1
  until "$@"; do
    if [ "$attempt" -ge "$retries" ]; then
      echo "Command failed after $${retries} attempts: $*"
      return 1
    fi
    echo "Attempt $${attempt}/$${retries} failed. Retrying in $${wait_seconds}s: $*"
    sleep "$wait_seconds"
    attempt=$((attempt + 1))
  done
}

retry dnf update -y
retry dnf install -y docker git

if ! command -v curl >/dev/null 2>&1; then
  retry dnf install -y curl-minimal
fi

systemctl enable --now docker
usermod -aG docker ec2-user

for i in $(seq 1 20); do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

docker info >/dev/null 2>&1

if ! docker compose version >/dev/null 2>&1; then
  retry dnf install -y docker-compose-plugin || true
fi

if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/libexec/docker/cli-plugins
  ARCH="$(uname -m)"
  if [ "$ARCH" = "x86_64" ]; then
    COMPOSE_ARCH="x86_64"
  elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    COMPOSE_ARCH="aarch64"
  else
    COMPOSE_ARCH="x86_64"
  fi

  retry curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-$${COMPOSE_ARCH}" -o /usr/local/libexec/docker/cli-plugins/docker-compose
  chmod +x /usr/local/libexec/docker/cli-plugins/docker-compose
fi

cd /home/ec2-user
if [ ! -d "${var.app_dir}" ]; then
  retry sudo -u ec2-user git clone ${var.repo_url} ${var.app_dir}
fi

cd /home/ec2-user/${var.app_dir}

cat > /home/ec2-user/${var.app_dir}/.env <<EOF
ALLOWED_ALGOS=${var.allowed_algos}
FIXED_WINDOW_LENGTH=${var.fixed_window_length}
REDIS_HOST=${var.redis_host}
REDIS_PORT=${var.redis_port}
EOF

chown ec2-user:ec2-user /home/ec2-user/${var.app_dir}/.env

retry docker compose up -d --build
  EOT

  tags = {
    Name = "pygateway-ec2"
  }
}

output "instance_id" {
  value       = aws_instance.app.id
  description = "EC2 instance id"
}

output "public_ip" {
  value       = aws_instance.app.public_ip
  description = "Public IPv4 address"
}

output "app_url" {
  value       = "http://${aws_instance.app.public_ip}"
  description = "Public URL for PyGateway via Nginx"
}
