# ==============================================================================
# Disaster Recovery and Backup Strategy for 99.99% Uptime
# ==============================================================================

# ==============================================================================
# Multi-Region Backup Configuration
# ==============================================================================
variable "backup_region" {
  description = "Secondary region for disaster recovery"
  type        = string
  default     = "us-east-1"
}

# Secondary provider for DR region
provider "aws" {
  alias  = "backup"
  region = var.backup_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "Klerno Labs"
      ManagedBy   = "Terraform"
      Purpose     = "Disaster Recovery"
    }
  }
}

# ==============================================================================
# Database Backup and Point-in-Time Recovery
# ==============================================================================

# Automated backups are already configured in main RDS instance
# Additional manual snapshot for disaster recovery
resource "aws_db_snapshot" "manual_backup" {
  db_instance_identifier = aws_db_instance.main.id
  db_snapshot_identifier = "klerno-manual-backup-${var.environment}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  tags = {
    Name = "klerno-manual-backup-${var.environment}"
    Type = "Manual"
  }
}

# Cross-region automated backup using AWS Backup
resource "aws_backup_vault" "main" {
  name        = "klerno-backup-vault-${var.environment}"
  kms_key_arn = aws_kms_key.backup.arn
  
  tags = {
    Name = "klerno-backup-vault-${var.environment}"
  }
}

resource "aws_backup_vault" "cross_region" {
  provider = aws.backup
  
  name        = "klerno-backup-vault-${var.environment}-cross-region"
  kms_key_arn = aws_kms_key.backup_cross_region.arn
  
  tags = {
    Name = "klerno-backup-vault-${var.environment}-cross-region"
  }
}

# KMS Keys for backup encryption
resource "aws_kms_key" "backup" {
  description             = "KMS key for Klerno backup encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "klerno-backup-key-${var.environment}"
  }
}

resource "aws_kms_alias" "backup" {
  name          = "alias/klerno-backup-${var.environment}"
  target_key_id = aws_kms_key.backup.key_id
}

resource "aws_kms_key" "backup_cross_region" {
  provider = aws.backup
  
  description             = "KMS key for Klerno cross-region backup encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "klerno-backup-key-${var.environment}-cross-region"
  }
}

resource "aws_kms_alias" "backup_cross_region" {
  provider = aws.backup
  
  name          = "alias/klerno-backup-${var.environment}-cross-region"
  target_key_id = aws_kms_key.backup_cross_region.key_id
}

# Backup plan for RDS
resource "aws_backup_plan" "main" {
  name = "klerno-backup-plan-${var.environment}"
  
  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * * *)"  # Daily at 5 AM UTC
    
    start_window = 60  # Start within 1 hour
    completion_window = 300  # Complete within 5 hours
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = 365
    }
    
    # Cross-region copy
    copy_action {
      destination_vault_arn = aws_backup_vault.cross_region.arn
      
      lifecycle {
        cold_storage_after = 30
        delete_after       = 365
      }
    }
    
    recovery_point_tags = {
      Environment = var.environment
      Frequency   = "Daily"
    }
  }
  
  rule {
    rule_name         = "weekly_backups"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 6 ? * SUN *)"  # Weekly on Sunday at 6 AM UTC
    
    start_window = 60
    completion_window = 480  # 8 hours for weekly backup
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = 2555  # 7 years
    }
    
    copy_action {
      destination_vault_arn = aws_backup_vault.cross_region.arn
      
      lifecycle {
        cold_storage_after = 30
        delete_after       = 2555
      }
    }
    
    recovery_point_tags = {
      Environment = var.environment
      Frequency   = "Weekly"
    }
  }
  
  tags = {
    Name = "klerno-backup-plan-${var.environment}"
  }
}

# IAM role for AWS Backup
resource "aws_iam_role" "backup" {
  name = "klerno-backup-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "backup_restores" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# Backup selection for RDS
resource "aws_backup_selection" "rds" {
  iam_role_arn = aws_iam_role.backup.arn
  name         = "klerno-rds-backup-selection-${var.environment}"
  plan_id      = aws_backup_plan.main.id
  
  resources = [
    aws_db_instance.main.arn
  ]
  
  condition {
    string_equals {
      key   = "aws:ResourceTag/Environment"
      value = var.environment
    }
  }
}

# ==============================================================================
# Cross-Region Replication for Static Assets
# ==============================================================================
resource "aws_s3_bucket" "static_assets_replica" {
  provider = aws.backup
  
  bucket = "klerno-static-assets-replica-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name = "klerno-static-assets-replica-${var.environment}"
  }
}

resource "aws_s3_bucket_versioning" "static_assets" {
  bucket = aws_s3_bucket.static_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "static_assets_replica" {
  provider = aws.backup
  
  bucket = aws_s3_bucket.static_assets_replica.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_replication_configuration" "static_assets" {
  role   = aws_iam_role.s3_replication.arn
  bucket = aws_s3_bucket.static_assets.id
  
  rule {
    id     = "replicate_all"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.static_assets_replica.arn
      storage_class = "STANDARD_IA"
    }
  }
  
  depends_on = [aws_s3_bucket_versioning.static_assets]
}

# IAM role for S3 replication
resource "aws_iam_role" "s3_replication" {
  name = "klerno-s3-replication-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "s3_replication" {
  name = "klerno-s3-replication-policy-${var.environment}"
  role = aws_iam_role.s3_replication.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${aws_s3_bucket.static_assets.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.static_assets.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${aws_s3_bucket.static_assets_replica.arn}/*"
      }
    ]
  })
}

# ==============================================================================
# Disaster Recovery Infrastructure (Standby)
# ==============================================================================

# VPC in backup region
module "vpc_backup" {
  source = "terraform-aws-modules/vpc/aws"
  
  providers = {
    aws = aws.backup
  }
  
  name = "klerno-vpc-backup-${var.environment}"
  cidr = "10.1.0.0/16"  # Different CIDR from primary
  
  azs             = ["${var.backup_region}a", "${var.backup_region}b"]
  private_subnets = ["10.1.1.0/24", "10.1.2.0/24"]
  public_subnets  = ["10.1.101.0/24", "10.1.102.0/24"]
  
  enable_nat_gateway   = true
  enable_vpn_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "klerno-vpc-backup-${var.environment}"
  }
}

# RDS Read Replica in backup region
resource "aws_db_instance" "cross_region_replica" {
  provider = aws.backup
  
  identifier = "klerno-db-cross-region-replica-${var.environment}"
  
  replicate_source_db = aws_db_instance.main.arn
  instance_class      = "db.r6g.large"
  
  vpc_security_group_ids = [aws_security_group.rds_backup.id]
  db_subnet_group_name   = aws_db_subnet_group.backup.name
  
  skip_final_snapshot = true
  
  tags = {
    Name = "klerno-db-cross-region-replica-${var.environment}"
  }
  
  depends_on = [aws_db_subnet_group.backup]
}

# DB subnet group in backup region
resource "aws_db_subnet_group" "backup" {
  provider = aws.backup
  
  name       = "klerno-db-subnet-backup-${var.environment}"
  subnet_ids = module.vpc_backup.private_subnets
  
  tags = {
    Name = "klerno-db-subnet-backup-${var.environment}"
  }
}

# Security group for RDS in backup region
resource "aws_security_group" "rds_backup" {
  provider = aws.backup
  
  name_prefix = "klerno-rds-backup-${var.environment}"
  vpc_id      = module.vpc_backup.vpc_id
  
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [module.vpc_backup.vpc_cidr_block]
  }
  
  tags = {
    Name = "klerno-rds-backup-sg-${var.environment}"
  }
}

# ==============================================================================
# Route 53 Health Checks and Failover
# ==============================================================================
resource "aws_route53_record" "primary" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "app.${var.domain_name}"
  type    = "A"
  
  set_identifier = "primary"
  
  failover_routing_policy {
    type = "PRIMARY"
  }
  
  health_check_id = aws_route53_health_check.main.id
  
  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = true
  }
}

# Placeholder for secondary record (would point to DR environment)
# resource "aws_route53_record" "secondary" {
#   zone_id = data.aws_route53_zone.main.zone_id
#   name    = "app.${var.domain_name}"
#   type    = "A"
#   
#   set_identifier = "secondary"
#   
#   failover_routing_policy {
#     type = "SECONDARY"
#   }
#   
#   alias {
#     name                   = aws_cloudfront_distribution.backup.domain_name
#     zone_id                = aws_cloudfront_distribution.backup.hosted_zone_id
#     evaluate_target_health = false
#   }
# }

# ==============================================================================
# Automated Recovery Procedures
# ==============================================================================

# Lambda function for automated failover
resource "aws_lambda_function" "disaster_recovery" {
  filename         = "disaster_recovery.zip"
  function_name    = "klerno-disaster-recovery-${var.environment}"
  role            = aws_iam_role.lambda_disaster_recovery.arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.disaster_recovery_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = 300
  
  environment {
    variables = {
      ENVIRONMENT = var.environment
      PRIMARY_REGION = var.region
      BACKUP_REGION = var.backup_region
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }
  
  tags = {
    Name = "klerno-disaster-recovery-${var.environment}"
  }
}

# Lambda deployment package
data "archive_file" "disaster_recovery_zip" {
  type        = "zip"
  output_path = "disaster_recovery.zip"
  
  source {
    content = <<EOF
import json
import boto3
import os

def handler(event, context):
    """
    Automated disaster recovery handler
    Triggered by CloudWatch alarms for critical failures
    """
    print(f"Disaster recovery triggered: {json.dumps(event)}")
    
    sns = boto3.client('sns')
    
    # Send alert
    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject=f"DISASTER RECOVERY TRIGGERED - {os.environ['ENVIRONMENT']}",
        Message=f"Automated disaster recovery procedure initiated.\nEvent: {json.dumps(event, indent=2)}"
    )
    
    # Add automated recovery procedures here
    # - Promote read replica to primary
    # - Switch DNS records
    # - Scale up backup infrastructure
    
    return {
        'statusCode': 200,
        'body': json.dumps('Disaster recovery procedure initiated')
    }
EOF
    filename = "index.py"
  }
}

# IAM role for disaster recovery Lambda
resource "aws_iam_role" "lambda_disaster_recovery" {
  name = "klerno-lambda-disaster-recovery-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_disaster_recovery_basic" {
  role       = aws_iam_role.lambda_disaster_recovery.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_disaster_recovery" {
  name = "klerno-lambda-disaster-recovery-policy-${var.environment}"
  role = aws_iam_role.lambda_disaster_recovery.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds:PromoteReadReplica",
          "rds:ModifyDBInstance"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets"
        ]
        Resource = data.aws_route53_zone.main.arn
      }
    ]
  })
}

# CloudWatch alarm to trigger disaster recovery
resource "aws_cloudwatch_metric_alarm" "disaster_recovery_trigger" {
  alarm_name          = "klerno-disaster-recovery-trigger-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "1"
  alarm_description   = "Trigger disaster recovery when no healthy hosts"
  alarm_actions       = [
    aws_sns_topic.alerts.arn,
    aws_lambda_function.disaster_recovery.arn
  ]
  treat_missing_data = "breaching"
  
  dimensions = {
    TargetGroup  = aws_lb_target_group.app.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = {
    Name = "klerno-disaster-recovery-trigger-${var.environment}"
  }
}

# Permission for CloudWatch to invoke Lambda
resource "aws_lambda_permission" "disaster_recovery_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.disaster_recovery.function_name
  principal     = "alarms.amazonaws.com"
  source_arn    = aws_cloudwatch_metric_alarm.disaster_recovery_trigger.arn
}