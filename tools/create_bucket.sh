#!/bin/bash
# Création du bucket S3 'cdsd-kayak-datalake' dans eu-west-3
# Prérequis : credentials AWS valides dans .env ou dans ~/.aws/credentials
# Usage : bash tools/create_bucket.sh  (depuis la racine du projet ou n'importe où)
set -e

# Chemin absolu vers .env, indépendant du répertoire d'appel
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../.env"

echo "Try to create ${S3_BUCKET} in region ${AWS_REGION}"

AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
AWS_DEFAULT_REGION=${AWS_REGION:-eu-west-3} \
aws s3api create-bucket \
    --bucket "${S3_BUCKET:-cdsd-kayak-datalake}" \
    --region "${AWS_REGION:-eu-west-3}" \
    --create-bucket-configuration LocationConstraint="${AWS_REGION:-eu-west-3}"
