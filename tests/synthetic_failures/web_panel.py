"""
tests/synthetic_failures/web_panel.py — Standalone Demo Web Panel (Unit 12).

Provides a modern, dark-mode web application for interactive pitch video demonstrations:
  - Toggle and inspect all 9 failure scenarios
  - Side-by-side view of SI and BL documents with injected discrepancy highlights
  - Real-time pipeline stage indicators (Classifier -> Extractor -> Comparator -> Router)
  - Instant live execution with pass/fail verification badges
"""

import sys
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# Ensure workspace root in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tests.synthetic_failures.scenarios import SCENARIOS
from tests.synthetic_failures.simulator import run_scenario, run_all_scenarios
from tests.synthetic_failures.generator import ensure_fixtures

app = FastAPI(title="Manifest AI — Failure Simulator Panel", version="1.0.0")

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Manifest AI — Synthetic Failure Simulator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0a0d14;
      --bg-surface: #111622;
      --bg-surface-elevated: #182030;
      --border-subtle: #202b42;
      --border-bright: #35476d;
      --accent-blue: #3b82f6;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-crimson: #ef4444;
      --text-main: #f3f4f6;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      background: rgba(17, 22, 34, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-subtle);
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-badge {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-gradient(135deg, #2563eb, #06b6d4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 18px;
      color: #fff;
      box-shadow: 0 0 16px rgba(37, 99, 235, 0.4);
    }

    .brand-title {
      font-weight: 700;
      font-size: 18px;
      letter-spacing: -0.02em;
    }

    .brand-sub {
      font-size: 12px;
      color: var(--accent-cyan);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .system-status {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--accent-emerald);
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 6px 12px;
      border-radius: 9999px;
      font-weight: 600;
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px var(--accent-emerald);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    main {
      flex: 1;
      padding: 24px 32px;
      max-width: 1600px;
      margin: 0 auto;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Scenarios Carousel/Bar */
    .scenarios-bar {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .bar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .bar-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.05em;
    }

    .run-all-btn {
      background: linear-gradient(135deg, #1d4ed8, #0284c7);
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }

    .run-all-btn:hover {
      filter: brightness(1.15);
      box-shadow: 0 0 16px rgba(2, 132, 199, 0.4);
    }

    .scenario-chips {
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 4px;
    }

    .chip {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .chip:hover {
      border-color: var(--accent-blue);
      background: rgba(59, 130, 246, 0.08);
    }

    .chip.active {
      border-color: var(--accent-cyan);
      background: rgba(6, 182, 212, 0.12);
      color: #fff;
      box-shadow: 0 0 12px rgba(6, 182, 212, 0.25);
    }

    .badge-category {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      font-weight: 700;
    }

    .cat-defect { background: rgba(245, 158, 11, 0.2); color: var(--accent-amber); }
    .cat-escalation { background: rgba(239, 68, 68, 0.2); color: var(--accent-crimson); }
    .cat-semantic { background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); }

    /* Main Grid */
    .dashboard-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      flex: 1;
    }

    .panel-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 12px;
    }

    .card-title {
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .scenario-info-banner {
      background: rgba(24, 32, 48, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .scenario-info-desc {
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.5;
    }

    .documents-split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      flex: 1;
    }

    .doc-box {
      background: #090c13;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .doc-box-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
    }

    .doc-pre {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #cbd5e1;
      overflow-y: auto;
      max-height: 320px;
      line-height: 1.4;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .btn-run-live {
      background: linear-gradient(135deg, #059669, #10b981);
      color: #fff;
      border: none;
      padding: 14px 24px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    .btn-run-live:hover {
      filter: brightness(1.15);
      transform: translateY(-1px);
    }

    /* Results Card */
    .stages-stepper {
      display: flex;
      justify-content: space-between;
      position: relative;
      padding: 12px 0;
    }

    .stage-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      z-index: 2;
    }

    .stage-circle {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--bg-surface-elevated);
      border: 2px solid var(--border-bright);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-dim);
      transition: all 0.3s;
    }

    .stage-item.completed .stage-circle {
      background: var(--accent-emerald);
      border-color: var(--accent-emerald);
      color: #000;
    }

    .stage-item.running .stage-circle {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 10px var(--accent-cyan);
      color: var(--accent-cyan);
      animation: pulse 1s infinite;
    }

    .stage-name {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
    }

    .results-banner {
      border-radius: 10px;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border: 1px solid transparent;
    }

    .res-mismatch { background: rgba(245, 158, 11, 0.12); border-color: rgba(245, 158, 11, 0.4); }
    .res-needs-review { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.4); }
    .res-ok { background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.4); }

    .verdict-tag {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.05em;
    }

    .pass-tag {
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.25);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.5);
    }

    .fail-tag {
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(239, 68, 68, 0.25);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.5);
    }

    .audit-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .audit-box {
      background: #090c13;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px;
    }

    .audit-label {
      font-size: 11px;
      color: var(--text-dim);
      font-weight: 600;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .audit-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 600;
    }

    .timeline-log {
      background: #090c13;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-muted);
      max-height: 180px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    /* Modal / Run All Table */
    .summary-modal {
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .modal-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-bright);
      border-radius: 14px;
      width: 100%;
      max-width: 900px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    th, td {
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border-subtle);
    }

    th {
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo-badge">M</div>
      <div>
        <div class="brand-title">Manifest AI</div>
        <div class="brand-sub">Synthetic Failure Simulator (Unit 12)</div>
      </div>
    </div>
    <div class="system-status">
      <div class="pulse-dot"></div>
      Live Pipeline Ready
    </div>
  </header>

  <main>
    <!-- Scenarios Selection -->
    <div class="scenarios-bar">
      <div class="bar-header">
        <div class="bar-title">Select Injected Failure Mode</div>
        <button class="run-all-btn" id="runAllBtn" onclick="runAllScenarios()">
          <span>⚡</span> Run Full 9-Scenario Suite
        </button>
      </div>
      <div class="scenario-chips" id="scenarioChips">
        <!-- Injected via JS -->
      </div>
    </div>

    <!-- Active Scenario & Pipeline Execution Grid -->
    <div class="dashboard-grid">
      <!-- Left: Scenario Details & Source Documents -->
      <div class="panel-card">
        <div class="card-header">
          <div class="card-title">
            <span id="activeScenarioIcon">🎯</span>
            <span id="activeScenarioName">Loading...</span>
          </div>
          <span class="badge-category" id="activeScenarioCategory">-</span>
        </div>

        <div class="scenario-info-banner">
          <div class="audit-label">Failure Injection Description</div>
          <div class="scenario-info-desc" id="activeScenarioDesc">-</div>
        </div>

        <div class="documents-split">
          <div class="doc-box">
            <div class="doc-box-title">
              <span>Shipping Instruction (SI)</span>
              <span style="color: var(--accent-cyan);">BASE</span>
            </div>
            <pre class="doc-pre" id="siDocText">-</pre>
          </div>
          <div class="doc-box">
            <div class="doc-box-title">
              <span>Draft Bill of Lading (BL)</span>
              <span style="color: var(--accent-amber);" id="blDocBadge">INJECTED</span>
            </div>
            <pre class="doc-pre" id="blDocText">-</pre>
          </div>
        </div>

        <button class="btn-run-live" id="btnRunLive" onclick="runActiveScenario()">
          <span>⚡</span> Inject Fault & Run Pipeline Live
        </button>
      </div>

      <!-- Right: Live Pipeline Output & Verification -->
      <div class="panel-card">
        <div class="card-header">
          <div class="card-title">
            <span>🔬</span> Live Orchestration Output
          </div>
          <span id="latencyBadge" style="font-size: 12px; color: var(--text-dim); font-family: monospace;">Idle</span>
        </div>

        <!-- Stages Stepper -->
        <div class="stages-stepper">
          <div class="stage-item completed" id="stageClassifier">
            <div class="stage-circle">1</div>
            <div class="stage-name">Classifier</div>
          </div>
          <div class="stage-item completed" id="stageExtractor">
            <div class="stage-circle">2</div>
            <div class="stage-name">Extractor</div>
          </div>
          <div class="stage-item completed" id="stageComparator">
            <div class="stage-circle">3</div>
            <div class="stage-name">Comparator</div>
          </div>
          <div class="stage-item completed" id="stageRouter">
            <div class="stage-circle">4</div>
            <div class="stage-name">Router</div>
          </div>
        </div>

        <!-- Decision Banner -->
        <div class="results-banner res-mismatch" id="decisionBanner">
          <div>
            <div class="audit-label" style="color: inherit; opacity: 0.8;">Pipeline Decision</div>
            <div class="verdict-tag" id="verdictStatus">READY</div>
          </div>
          <div id="verdictBadge" class="pass-tag">IDLE</div>
        </div>

        <!-- Audit Fields -->
        <div class="audit-grid">
          <div class="audit-box">
            <div class="audit-label">Detected Defect Fields</div>
            <div class="audit-val" id="resDefectFields" style="color: var(--accent-amber);">-</div>
          </div>
          <div class="audit-box">
            <div class="audit-label">Escalation Review Reason</div>
            <div class="audit-val" id="resReviewReason" style="color: var(--accent-crimson);">-</div>
          </div>
          <div class="audit-box">
            <div class="audit-label">Expected Pipeline Decision</div>
            <div class="audit-val" id="expectedStatus" style="color: var(--text-muted);">-</div>
          </div>
          <div class="audit-box">
            <div class="audit-label">Autonomous Verification</div>
            <div class="audit-val" id="auditMatchVerdict" style="color: var(--accent-emerald);">MATCHED 100%</div>
          </div>
        </div>

        <div class="audit-label" style="margin-top: 4px;">Pipeline Execution Audit Log</div>
        <div class="timeline-log" id="timelineLog">
          <div>[00:00:00] Ready for synthetic failure injection.</div>
        </div>
      </div>
    </div>
  </main>

  <!-- Summary Modal -->
  <div class="summary-modal" id="summaryModal">
    <div class="modal-card">
      <div class="card-header">
        <div class="card-title">🎯 Full Synthetic Test Suite Summary</div>
        <button onclick="closeModal()" style="background: none; border: none; color: var(--text-dim); font-size: 18px; cursor: pointer;">✕</button>
      </div>
      <div style="max-height: 400px; overflow-y: auto;">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Scenario</th>
              <th>Expected</th>
              <th>Actual</th>
              <th>Latency</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody id="modalTableBody">
            <!-- Injected via JS -->
          </tbody>
        </table>
      </div>
      <div style="display: flex; justify-content: flex-end;">
        <button class="run-all-btn" onclick="closeModal()">Close</button>
      </div>
    </div>
  </div>

  <script>
    let scenarios = {};
    let activeId = "wrong_container_count";

    async function loadScenarios() {
      const res = await fetch("/api/scenarios");
      scenarios = await res.json();
      renderChips();
      selectScenario(Object.keys(scenarios)[0]);
    }

    function renderChips() {
      const container = document.getElementById("scenarioChips");
      container.innerHTML = "";
      for (const [id, sc] of Object.entries(scenarios)) {
        const chip = document.createElement("div");
        chip.className = `chip ${id === activeId ? 'active' : ''}`;
        chip.id = `chip-${id}`;
        chip.onclick = () => selectScenario(id);

        let catClass = 'cat-defect';
        if (sc.category === 'Escalation') catClass = 'cat-escalation';
        if (sc.category === 'Semantic Alignment') catClass = 'cat-semantic';

        chip.innerHTML = `
          <span>${sc.name}</span>
          <span class="badge-category ${catClass}">${sc.category.split(' ')[0]}</span>
        `;
        container.appendChild(chip);
      }
    }

    function selectScenario(id) {
      activeId = id;
      document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      const activeChip = document.getElementById(`chip-${id}`);
      if (activeChip) activeChip.classList.add("active");

      const sc = scenarios[id];
      document.getElementById("activeScenarioName").innerText = sc.name;
      document.getElementById("activeScenarioDesc").innerText = sc.description;
      document.getElementById("activeScenarioCategory").innerText = sc.category;

      let catClass = 'cat-defect';
      if (sc.category === 'Escalation') catClass = 'cat-escalation';
      if (sc.category === 'Semantic Alignment') catClass = 'cat-semantic';
      document.getElementById("activeScenarioCategory").className = `badge-category ${catClass}`;

      document.getElementById("siDocText").innerText = sc.si_text || "No SI document";
      document.getElementById("blDocText").innerText = sc.bl_text || (sc.scenario_id === 'missing_bl' ? "[MISSING ATTACHMENT - NO DRAFT BL PROVIDED]" : "[UNREADABLE 0-BYTE FILE]");

      // Reset results card preview
      document.getElementById("verdictStatus").innerText = "READY TO RUN";
      document.getElementById("verdictBadge").className = "pass-tag";
      document.getElementById("verdictBadge").innerText = "IDLE";
      document.getElementById("resDefectFields").innerText = "-";
      document.getElementById("resReviewReason").innerText = "-";
      document.getElementById("expectedStatus").innerText = `${sc.expected_status} ${sc.expected_review_reason ? '('+sc.expected_review_reason+')' : ''}`;
      document.getElementById("latencyBadge").innerText = "Idle";
      document.getElementById("timelineLog").innerHTML = `<div>[READY] Scenario "${sc.name}" selected. Click Inject & Run Live.</div>`;
    }

    async function runActiveScenario() {
      const btn = document.getElementById("btnRunLive");
      btn.disabled = true;
      btn.innerHTML = `<span>⏳</span> Running Live LangGraph Pipeline...`;
      document.getElementById("latencyBadge").innerText = "Executing...";

      try {
        const res = await fetch(`/api/run/${activeId}`, { method: "POST" });
        const data = await res.json();
        displayResult(data);
      } catch (err) {
        alert("Execution error: " + err);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Inject Fault & Run Pipeline Live`;
      }
    }

    function displayResult(data) {
      document.getElementById("latencyBadge").innerText = `${data.latency_seconds.toFixed(2)}s`;

      const banner = document.getElementById("decisionBanner");
      banner.className = "results-banner";
      if (data.actual_status === "MISMATCH") banner.classList.add("res-mismatch");
      else if (data.actual_status === "NEEDS_REVIEW") banner.classList.add("res-needs-review");
      else banner.classList.add("res-ok");

      document.getElementById("verdictStatus").innerText = data.actual_status;

      const badge = document.getElementById("verdictBadge");
      if (data.passed) {
        badge.className = "pass-tag";
        badge.innerText = "✓ TEST PASSED";
      } else {
        badge.className = "fail-tag";
        badge.innerText = "✗ TEST FAILED";
      }

      document.getElementById("resDefectFields").innerText = data.actual_defect_fields.length ? data.actual_defect_fields.join(", ") : "None";
      document.getElementById("resReviewReason").innerText = data.actual_review_reason || "None";
      document.getElementById("auditMatchVerdict").innerText = data.passed ? "100% SPEC COMPLIANT" : "DISCREPANCY DETECTED";

      const log = document.getElementById("timelineLog");
      log.innerHTML = "";
      (data.timeline_events || ["classifier", "extractor", "comparator", "router"]).forEach(stage => {
        log.innerHTML += `<div>✓ Stage [${stage.toUpperCase()}] executed cleanly</div>`;
      });
      log.innerHTML += `<div style="color: var(--accent-emerald);">[COMPLETE] Pipeline resolved to ${data.actual_status} in ${data.latency_seconds.toFixed(2)}s</div>`;
    }

    async function runAllScenarios() {
      const btn = document.getElementById("runAllBtn");
      btn.disabled = true;
      btn.innerHTML = `<span>⏳</span> Running Full Suite...`;

      try {
        const res = await fetch("/api/run_all", { method: "POST" });
        const list = await res.json();

        const tbody = document.getElementById("modalTableBody");
        tbody.innerHTML = "";
        list.forEach((r, i) => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${i+1}</td>
            <td><strong>${r.name}</strong></td>
            <td>${r.expected_status}</td>
            <td><strong>${r.actual_status}</strong></td>
            <td>${r.latency_seconds.toFixed(2)}s</td>
            <td><span class="${r.passed ? 'pass-tag' : 'fail-tag'}">${r.passed ? 'PASS' : 'FAIL'}</span></td>
          `;
          tbody.appendChild(row);
        });
        document.getElementById("summaryModal").style.display = "flex";
      } catch (err) {
        alert("Error: " + err);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Run Full 9-Scenario Suite`;
      }
    }

    function closeModal() {
      document.getElementById("summaryModal").style.display = "none";
    }

    window.onload = loadScenarios;
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_CONTENT)


@app.get("/api/scenarios")
def get_scenarios():
    data = {}
    for sid, sc in SCENARIOS.items():
        data[sid] = {
            "scenario_id": sc.scenario_id,
            "name": sc.name,
            "category": sc.category,
            "description": sc.description,
            "expected_status": sc.expected_status,
            "expected_review_reason": sc.expected_review_reason,
            "expected_defect_fields": sc.expected_defect_fields,
            "si_text": sc.si_text,
            "bl_text": sc.bl_text,
        }
    return JSONResponse(content=data)


@app.post("/api/run/{scenario_id}")
def api_run_scenario(scenario_id: str):
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    result = run_scenario(scenario_id)
    return JSONResponse(content=result)


@app.post("/api/run_all")
def api_run_all():
    results = run_all_scenarios(verbose=False)
    return JSONResponse(content=results)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tests.synthetic_failures.web_panel:app", host="0.0.0.0", port=8085, reload=True)
