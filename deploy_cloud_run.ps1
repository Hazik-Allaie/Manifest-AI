# Manifest AI — One-Click Google Cloud Run Deployment Script (PowerShell)
$ErrorActionPreference = "Stop"

$ServiceName = "manifest-ai"
$ProjectId = "manifest-ai-509207"
$Region = "asia-southeast1"
$ImageName = "gcr.io/$ProjectId/${ServiceName}:latest"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Deploying Manifest AI to Google Cloud Run" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId | Region: $Region" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Build container using Google Cloud Build
Write-Host "[1/3] Building container image with Google Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --project $ProjectId --tag $ImageName .

# 2. Deploy to Cloud Run
Write-Host "[2/3] Deploying to Cloud Run service '$ServiceName'..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
  --project $ProjectId `
  --image $ImageName `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars "MANIFEST_GCP_PROJECT_ID=$ProjectId,MANIFEST_GCP_REGION=$Region,MANIFEST_VERTEX_MODEL=gemini-2.5-flash,MANIFEST_FIRESTORE_DB=(default),MANIFEST_PUBSUB_TOPIC=new-email-events"

# 3. Retrieve service URL
$ServiceUrl = gcloud run services describe $ServiceName --project $ProjectId --region $Region --format='value(status.url)'

Write-Host "=================================================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "  Public Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host "  Health Endpoint:    $ServiceUrl/health" -ForegroundColor Green
Write-Host "  Dashboard Home:     $ServiceUrl/" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
