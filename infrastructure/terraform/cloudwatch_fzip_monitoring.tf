# =========================================
# CLOUDWATCH MONITORING FOR FZIP OPERATIONS
# =========================================
# This file contains CloudWatch dashboards, alarms, and log groups
# for monitoring FZIP import/export operations.

# =========================================
# CLOUDWATCH LOG GROUPS
# =========================================

data "aws_cloudwatch_log_group" "fzip_operations" {
  name = "/aws/lambda/${var.project_name}-${var.environment}-fzip-operations"
}

# =========================================
# CLOUDWATCH DASHBOARD
# =========================================

resource "aws_cloudwatch_dashboard" "fzip_operations" {
  dashboard_name = "${var.project_name}-${var.environment}-fzip-operations"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupCount", "Result", "Success"],
            [".", ".", ".", "Total"],
            [".", "BackupSuccessRate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Backup Success Rate"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupDuration", "Success", "true", "BackupType", "complete"],
            ["...", "false", ".", "."],
            ["...", "true", ".", "accounts_only"],
            ["...", "true", ".", "transactions_only"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Backup Duration"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupPackageSize", "BackupType", "complete"],
            ["...", "accounts_only"],
            ["...", "transactions_only"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Backup Package Size"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupDataVolume", "EntityType", "accounts"],
            ["...", "transactions"],
            ["...", "categories"],
            ["...", "file_maps"],
            ["...", "transaction_files"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Backup Data Volume by Entity Type"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupErrors", "ErrorType", "ValidationError"],
            ["...", "DatabaseError"],
            ["...", "S3Error"],
            ["...", "PackagingError"],
            ["...", "TimeoutError"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Backup Errors by Type"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          query  = "SOURCE '${data.aws_cloudwatch_log_group.fzip_operations.name}'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100"
          region = "us-east-1"
          title  = "Recent FZIP Operations Errors"
          view   = "table"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "RestoreCount", "Result", "Success"],
            [".", ".", ".", "Total"],
            [".", "RestoreSuccessRate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Restore Success Rate"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["HouseF3/FZIP", "RestoreDuration", "Success", "true"],
            ["...", "false"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "FZIP Restore Duration"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 24
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupValidationScore", "Quality", "excellent"],
            [".", ".", ".", "good"],
            [".", ".", ".", "fair"],
            [".", ".", ".", "poor"]
          ],
          view    = "timeSeries",
          stacked = true,
          region  = "us-east-1",
          title   = "Backup Validation Quality",
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 24
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["HouseF3/FZIP", "BackupIntegrityFailures"],
            [".", "BackupCompletenessFailures"]
          ],
          view    = "timeSeries",
          stacked = false,
          region  = "us-east-1",
          title   = "Backup Validation Failures",
          period  = 300,
          stat    = "Sum"
        }
      }
    ]
  })
}

# =========================================
# CLOUDWATCH ALARMS
# =========================================

# High error rate alarm - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_backup_high_error_rate" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-backup-high-error-rate"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "BackupErrors"
#   namespace           = "HouseF3/FZIP"
#   period              = "300"
#   statistic           = "Sum"
#   threshold           = "5"
#   alarm_description   = "This metric monitors FZIP backup error rate"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# Long processing time alarm - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_backup_long_duration" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-backup-long-duration"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "BackupDuration"
#   namespace           = "HouseF3/FZIP"
#   period              = "300"
#   statistic           = "Average"
#   threshold           = "300" # 5 minutes
#   alarm_description   = "This metric monitors FZIP backup processing time"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   dimensions = {
#     Success = "true"
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# Low success rate alarm - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_backup_low_success_rate" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-backup-low-success-rate"
#   comparison_operator = "LessThanThreshold"
#   evaluation_periods  = "3"
#   metric_name         = "BackupSuccessRate"
#   namespace           = "HouseF3/FZIP"
#   period              = "900" # 15 minutes
#   statistic           = "Average"
#   threshold           = "90" # 90% success rate
#   alarm_description   = "This metric monitors FZIP backup success rate"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]
#   treat_missing_data  = "notBreaching"

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# Lambda function errors alarm - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_lambda_errors" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-lambda-errors"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "Errors"
#   namespace           = "AWS/Lambda"
#   period              = "300"
#   statistic           = "Sum"
#   threshold           = "3"
#   alarm_description   = "This metric monitors FZIP Lambda function errors"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   dimensions = {
#     FunctionName = "${var.project_name}-${var.environment}-fzip-operations"
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# Lambda function duration alarm - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_lambda_duration" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-lambda-duration"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "Duration"
#   namespace           = "AWS/Lambda"
#   period              = "300"
#   statistic           = "Average"
#   threshold           = "600000" # 10 minutes in milliseconds
#   alarm_description   = "This metric monitors FZIP Lambda function duration"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   dimensions = {
#     FunctionName = "${var.project_name}-${var.environment}-fzip-operations"
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# High error rate alarm for restore - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_restore_high_error_rate" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-restore-high-error-rate"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "RestoreErrors"
#   namespace           = "HouseF3/FZIP"
#   period              = "300"
#   statistic           = "Sum"
#   threshold           = "3"
#   alarm_description   = "This metric monitors FZIP restore error rate"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# Long processing time alarm for restore - DISABLED
# resource "aws_cloudwatch_metric_alarm" "fzip_restore_long_duration" {
#   alarm_name          = "${var.project_name}-${var.environment}-fzip-restore-long-duration"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "RestoreDuration"
#   namespace           = "HouseF3/FZIP"
#   period              = "300"
#   statistic           = "Average"
#   threshold           = "600" # 10 minutes
#   alarm_description   = "This metric monitors FZIP restore processing time"
#   alarm_actions       = [aws_sns_topic.fzip_alerts.arn]

#   dimensions = {
#     Success = "true"
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#     Component   = "fzip-monitoring"
#     ManagedBy   = "terraform"
#   }
# }

# =========================================
# SNS TOPIC FOR ALERTS
# =========================================

resource "aws_sns_topic" "fzip_alerts" {
  name              = "${var.project_name}-${var.environment}-fzip-alerts"
  kms_master_key_id = "alias/aws/sns" # Use AWS managed key for SNS encryption

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "fzip-monitoring"
    ManagedBy   = "terraform"
  }
}

# SNS topic policy
resource "aws_sns_topic_policy" "fzip_alerts_policy" {
  arn = aws_sns_topic.fzip_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.fzip_alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# Optional: Email subscription (commented out - requires manual confirmation)
# resource "aws_sns_topic_subscription" "fzip_alerts_email" {
#   topic_arn = aws_sns_topic.fzip_alerts.arn
#   protocol  = "email"
#   endpoint  = "your-email@example.com"
# }

# =========================================
# DATA SOURCES
# =========================================

data "aws_caller_identity" "current" {}

# =========================================
# OUTPUTS
# =========================================

output "fzip_dashboard_url" {
  description = "URL to the FZIP operations CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.fzip_operations.dashboard_name}"
}

output "fzip_alerts_topic_arn" {
  description = "ARN of the FZIP alerts SNS topic"
  value       = aws_sns_topic.fzip_alerts.arn
}

output "fzip_log_group_name" {
  description = "Name of the FZIP operations log group"
  value       = data.aws_cloudwatch_log_group.fzip_operations.name
}

data "aws_region" "current" {}