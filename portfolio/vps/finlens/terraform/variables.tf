variable "aws_region" {
  type        = string
  description = "Primary AWS region for FinLens resources."
}

variable "bucket_prefix" {
  type        = string
  description = "Bucket prefix for FinLens buckets."
  default     = "finlens"
}
