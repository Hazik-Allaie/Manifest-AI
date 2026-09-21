# Manifest AI — Production Deployment Log (Unit 14)

**Deployment Date:** 2026-09-21T00:12:35+08:00 (UTC 2026-09-20T16:12:35Z)  
**Deployed By:** Antigravity AI  
**Deployment Target:** Google Cloud Platform (Cloud Run + Firebase Hosting)  
**Project ID:** `manifest-ai-509207`  
**Region:** `asia-southeast1`  

---

## 1. Deployed Endpoints & Live URLs

| Component | Target Platform | Live Public URL | Health / Verification Status |
| :--- | :--- | :--- | :--- |
| **Backend API** | **Google Cloud Run** | `https://manifest-ai-337850345503.asia-southeast1.run.app` | `200 OK` (`/health` healthy, 520 emails active) |
| **Frontend App** | **Firebase Hosting** | `https://manifest-ai-509207.web.app` | `200 OK` (Live CDN, fully connected to Cloud Run) |
| **Frontend Alias**| **Firebase Hosting** | `https://manifest-ai-509207.firebaseapp.com` | `200 OK` (Live CDN alias) |

---

## 2. Hosting Selection Rationale

**Hosting Choice:** **Firebase Hosting (Option 2)**  
**Reasoning & Decision:**
- The user explicitly selected Firebase Hosting to keep the entire Manifest AI stack consolidated within a single Google Cloud Platform project (`manifest-ai-509207`) alongside Cloud Run, Cloud Firestore, and Google Cloud Vertex AI (`gemini-2.5-flash`).
- Firebase Hosting rewrites (`/api/**` and `/health` &rarr; `manifest-ai` Cloud Run service in `asia-southeast1`) completely eliminate CORS issues and separate endpoint origins.
- Single unified IAM, Google Cloud billing, and monitoring console.

---

## 3. Configuration & Infrastructure Details

### 3.1 Backend (Google Cloud Run)
- **Service Name:** `manifest-ai`
- **Revision:** `manifest-ai-00003-5gl`
- **CPU / Memory:** 2 vCPU / 2GiB RAM
- **Timeout:** 300s
- **Security:** Non-root user (`manifest:manifest` UID 1000)
- **CORS:** Enabled with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`
- **Environment Variables:**
  - `MANIFEST_GCP_PROJECT_ID=manifest-ai-509207`
  - `MANIFEST_GCP_REGION=asia-southeast1`
  - `MANIFEST_VERTEX_MODEL=gemini-2.5-flash`
  - `MANIFEST_FIRESTORE_DB=(default)`
  - `MANIFEST_PUBSUB_TOPIC=new-email-events`

### 3.2 Frontend (Firebase Hosting)
- **Root Directory:** `dashboard/frontend`
- **Rewrites Configured:**
  - `{"source": "/api/**", "run": {"serviceId": "manifest-ai", "region": "asia-southeast1"}}`
  - `{"source": "/health", "run": {"serviceId": "manifest-ai", "region": "asia-southeast1"}}`
- **Static Assets:** `index.html`, `styles.css`, `app.js`, `mock_dashboard_data.json`

---

## 4. Deployment Resolution & Issue Log

1. **Cloud Build API Enablement:** Initial `gcloud builds submit` prompted to enable `cloudbuild.googleapis.com`. Once enabled, container was built and deployed directly through Cloud Run source build against Artifact Registry (`asia-southeast1-docker.pkg.dev/manifest-ai-509207/cloud-run-source-deploy`).
2. **Dataset Bundling:** Created explicit `.gcloudignore` ensuring `submission.json`, `submission_basic.json`, and `data-basic/` were included in the container build.
3. **Dynamic API URL Resolution:** Configured `getApiBaseUrl()` in `app.js` with fallback to same-origin rewrites for Firebase Hosting and direct Cloud Run endpoint routing.

---

## 5. Exit Criteria Verification

- [x] Backend is live on Cloud Run (`https://manifest-ai-337850345503.asia-southeast1.run.app`) and reachable.
- [x] Frontend is live on Firebase Hosting (`https://manifest-ai-509207.web.app`) and reachable.
- [x] Frontend successfully loads real processed data (520 items) from the live backend.
- [x] All 8 core views (§2.1–§2.8) verified and operating with zero console errors.

*Unit 14 complete. Proceeding to Unit 15 (E2E Functional Test).*
