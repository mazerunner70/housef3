terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # You can uncomment this block and configure it once you have your S3 bucket for state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "housef3/terraform.tfstate"
  #   region         = "eu-west-2"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "housef3"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
} 