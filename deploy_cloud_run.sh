#!/usr/bin/env bash
# Manifest AI — One-Click Google Cloud Run Deployment Script
set -e

SERVICE_NAME="manifest-ai"
PROJECT_ID="manifest-ai-509207"
REGION="asia-southeast1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "================================================================="
echo "  Deploying Manifest AI to Google Cloud Run"
echo "  Project: ${PROJECT_ID} | Region: ${REGION}"
echo "================================================================="

# 1. Build container using Google Cloud Build
echo "[1/3] Building container image with Google Cloud Build..."
gcloud builds submit --project "${PROJECT_ID}" --tag "${IMAGE_NAME}" .

# 2. Deploy to Cloud Run
echo "[2/3] Deploying to Cloud Run service '${SERVICE_NAME}'..."
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --image "${IMAGE_NAME}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "MANIFEST_GCP_PROJECT_ID=${PROJECT_ID},MANIFEST_GCP_REGION=${REGION},MANIFEST_VERTEX_MODEL=gemini-2.5-flash,MANIFEST_FIRESTORE_DB=(default),MANIFEST_PUBSUB_TOPIC=new-email-events"

# 3. Retrieve service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')

echo "================================================================="
echo "  Deployment Complete!"
echo "  Public Service URL: ${SERVICE_URL}"
echo "  Health Endpoint:    ${SERVICE_URL}/health"
echo "  Dashboard Home:     ${SERVICE_URL}/"
echo "================================================================="
