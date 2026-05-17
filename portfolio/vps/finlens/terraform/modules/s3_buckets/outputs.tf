output "bucket_names" {
  value = {
    raw     = aws_s3_bucket.raw.bucket
    dlq     = aws_s3_bucket.dlq.bucket
    marts   = aws_s3_bucket.marts.bucket
    docs    = aws_s3_bucket.docs.bucket
    tfstate = aws_s3_bucket.tfstate.bucket
  }
}
