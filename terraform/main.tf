module "s3_buckets" {
  source        = "./modules/s3_buckets"
  bucket_prefix = var.bucket_prefix
}
