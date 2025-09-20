terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# EKS Cluster
resource "aws_eks_cluster" "klerno_cluster" {
  name     = "klerno-cluster"
  role_arn = aws_iam_role.eks_role.arn
  version  = "1.27"

  vpc_config {
    subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  }
}

# IAM Role for EKS
resource "aws_iam_role" "eks_role" {
  name = "klerno-eks-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

# RDS Database
resource "aws_db_instance" "klerno_db" {
  identifier     = "klerno-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_encrypted = true
  
  db_name  = "klerno"
  username = "klerno_user"
  password = var.db_password
  
  skip_final_snapshot = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}
