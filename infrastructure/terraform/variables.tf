variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "housef3"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "localhost:3000"  # Default for local development
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "eu-west-2"  # London
}

variable "frontend_domain" {
  description = "Domain name for the frontend application"
  type        = string
  default     = null
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
} 