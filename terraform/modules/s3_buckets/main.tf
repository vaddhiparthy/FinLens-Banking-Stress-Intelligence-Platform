resource "aws_s3_bucket" "raw" {
  bucket = "${var.bucket_prefix}-raw"
}

resource "aws_s3_bucket" "dlq" {
  bucket = "${var.bucket_prefix}-dlq"
}

resource "aws_s3_bucket" "marts" {
  bucket = "${var.bucket_prefix}-marts"
}

resource "aws_s3_bucket" "docs" {
  bucket = "${var.bucket_prefix}-docs"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.bucket_prefix}-tfstate"
}
