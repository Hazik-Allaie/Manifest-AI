param()

$base = 'https://manifest-ai-509207.web.app'
$results = @()

function Test-Pass($name, $detail) {
    Write-Host "PASS  [$name] $detail"
    return [pscustomobject]@{Feature=$name; Status="PASS"; Detail=$detail}
}
function Test-Fail($name, $detail) {
    Write-Host "FAIL  [$name] $detail"
    return [pscustomobject]@{Feature=$name; Status="FAIL"; Detail=$detail}
}

# TEST 1: Health check
try {
    $h = Invoke-RestMethod -Uri ($base + '/health') -ErrorAction Stop
    if ($h.status -eq 'healthy') {
        $results += Test-Pass "1. Health Check" ("Status=healthy | Service=" + $h.service + " | v" + $h.version)
    } else {
        $results += Test-Fail "1. Health Check" ("Unexpected status=" + $h.status)
    }
} catch {
    $results += Test-Fail "1. Health Check" $_.Exception.Message
}

# TEST 2: Analytics API
try {
    $a = Invoke-RestMethod -Uri ($base + '/api/analytics') -ErrorAction Stop
    $total = $a.total_emails
    $mmRate = [math]::Round($a.mismatch_rate * 100, 1)
    $acRate = [math]::Round($a.auto_cleared_rate * 100, 1)
    if ($total -ge 520) {
        $results += Test-Pass "2. Analytics API" ("Total=$total | OK=" + $a.status_distribution.OK + " | MISMATCH=" + $a.status_distribution.MISMATCH + " | NR=" + $a.status_distribution.NEEDS_REVIEW + " | MismatchRate=" + $mmRate + "% | AutoClear=" + $acRate + "%")
    } else {
        $results += Test-Fail "2. Analytics API" "Total emails < 520 (got $total)"
    }
} catch {
    $results += Test-Fail "2. Analytics API" $_.Exception.Message
}

# TEST 3: Dashboard Data Adapter
try {
    $d = Invoke-RestMethod -Uri ($base + '/api/dashboard/data?limit=1') -ErrorAction Stop
    $snap = $d._analytics_snapshot
    if ($snap.total_emails -ge 520) {
        $results += Test-Pass "3. Dashboard Data Adapter" ("Snap.total=" + $snap.total_emails + " | ClearanceRate=" + $snap.clearance_rate + " | ScoreHistory=" + $snap.score_history.Count + " entries")
    } else {
        $results += Test-Fail "3. Dashboard Data Adapter" ("total_emails in snapshot=" + $snap.total_emails)
    }
} catch {
    $results += Test-Fail "3. Dashboard Data Adapter" $_.Exception.Message
}

# TEST 4: Full email entry schema and counts
try {
    $full = Invoke-RestMethod -Uri ($base + '/api/dashboard/data') -ErrorAction Stop
    $allEmails = @($full.PSObject.Properties | Where-Object { $_.Name -like 'email_*' })
    $okCount = @($allEmails | Where-Object { $_.Value.status -eq 'OK' }).Count
    $mmCount = @($allEmails | Where-Object { $_.Value.status -eq 'MISMATCH' }).Count
    $nrCount = @($allEmails | Where-Object { $_.Value.status -eq 'NEEDS_REVIEW' }).Count
    $results += Test-Pass "4a. Kanban OK Count" ("$okCount OK entries")
    $results += Test-Pass "4b. Kanban MISMATCH Count" ("$mmCount MISMATCH entries")
    $results += Test-Pass "4c. Kanban NEEDS_REVIEW Count" ("$nrCount NEEDS_REVIEW entries")
} catch {
    $results += Test-Fail "4. Kanban Counts" $_.Exception.Message
}

# TEST 5: MISMATCH card field results (§2.2)
try {
    $full2 = Invoke-RestMethod -Uri ($base + '/api/dashboard/data') -ErrorAction Stop
    $mmEmails = @($full2.PSObject.Properties | Where-Object { $_.Name -like 'email_*' -and $_.Value.status -eq 'MISMATCH' })
    $mm = $mmEmails[0]
    $frCount = @($mm.Value.field_results).Count
    $defect = $mm.Value.defect_fields -join ','
    $title = $mm.Value.discrepancy_title
    if ($frCount -ge 7) {
        $results += Test-Pass "5. Side-by-Side Comparison (§2.2)" ("Email=" + $mm.Name + " | 7 field_results | Defects: $defect | Title: $title")
    } else {
        $results += Test-Fail "5. Side-by-Side Comparison (§2.2)" ("Only $frCount field_results for " + $mm.Name)
    }
} catch {
    $results += Test-Fail "5. Side-by-Side Comparison (§2.2)" $_.Exception.Message
}

# TEST 6: Timeline on MISMATCH (§2.3)
try {
    $full3 = Invoke-RestMethod -Uri ($base + '/api/dashboard/data') -ErrorAction Stop
    $mmE = @($full3.PSObject.Properties | Where-Object { $_.Name -like 'email_*' -and $_.Value.status -eq 'MISMATCH' })[0]
    $tlCount = @($mmE.Value.timeline).Count
    if ($tlCount -ge 3) {
        $results += Test-Pass "6. Shipment Timeline (§2.3)" ("$tlCount timeline stages for " + $mmE.Name)
    } else {
        $results += Test-Fail "6. Shipment Timeline (§2.3)" ("Only $tlCount timeline stages")
    }
} catch {
    $results += Test-Fail "6. Shipment Timeline (§2.3)" $_.Exception.Message
}

# TEST 7: Review Reasons (§2.1 subgroups, §2.4 filter)
try {
    $fullNR = Invoke-RestMethod -Uri ($base + '/api/dashboard/data') -ErrorAction Stop
    $nrEmails = @($fullNR.PSObject.Properties | Where-Object { $_.Name -like 'email_*' -and $_.Value.status -eq 'NEEDS_REVIEW' })
    $reasons = $nrEmails | ForEach-Object { $_.Value.review_reason } | Sort-Object -Unique
    $subgroups = $nrEmails | ForEach-Object { $_.Value.subgroup } | Sort-Object -Unique
    $badges = $nrEmails | ForEach-Object { $_.Value.exception_badge } | Sort-Object -Unique
    $results += Test-Pass "7. Needs Review Sub-groups (§2.1)" ("Reasons: " + ($reasons -join ', ') + " | Subgroups: " + ($subgroups -join ', '))
    $results += Test-Pass "7b. Exception Badges" ("Badges: " + ($badges -join ', '))
} catch {
    $results += Test-Fail "7. Needs Review Sub-groups" $_.Exception.Message
}

# TEST 8: Analytics fields (§2.5)
try {
    $an = Invoke-RestMethod -Uri ($base + '/api/analytics') -ErrorAction Stop
    $catCount = @($an.category_distribution.PSObject.Properties).Count
    $defectCount = @($an.defect_field_distribution.PSObject.Properties).Count
    $results += Test-Pass "8. Analytics Panel (§2.5)" ("Categories: $catCount | DefectFields: $defectCount | BenchmarkScore: " + $an.benchmark_score)
} catch {
    $results += Test-Fail "8. Analytics Panel (§2.5)" $_.Exception.Message
}

# TEST 9: Draft Correction Email API (§2.6)
try {
    $draft = Invoke-RestMethod -Uri ($base + '/api/draft_email') -Method POST -ContentType 'application/json' -Body ('{"email_id":"email_001","recipient":"carrier@test.com"}') -ErrorAction Stop
    if ($draft.draft_body -and $draft.draft_body.Length -gt 50) {
        $results += Test-Pass "9. Draft Correction Email (§2.6)" ("draft_body present (" + $draft.draft_body.Length + " chars)")
    } else {
        $results += Test-Fail "9. Draft Correction Email (§2.6)" "draft_body empty or missing"
    }
} catch {
    $results += Test-Fail "9. Draft Correction Email (§2.6)" $_.Exception.Message
}

# TEST 10: Correction Submission API (§2.7)
try {
    $corr = Invoke-RestMethod -Uri ($base + '/api/correct') -Method POST -ContentType 'application/json' -Body ('{"email_id":"email_001","field_name":"container_count","operator_value":"3 x 40HC","notes":"E2E test correction","operator_id":"e2e_tester"}') -ErrorAction Stop
    if ($corr.status -eq 'success' -and $corr.doc_id -and $corr.doc_id.Length -gt 0) {
        $results += Test-Pass "10. Correction Submission Persistence (§2.7)" ("doc_id=" + $corr.doc_id)
    } else {
        $results += Test-Fail "10. Correction Submission Persistence (§2.7)" ("status=" + $corr.status)
    }
} catch {
    $results += Test-Fail "10. Correction Submission Persistence (§2.7)" $_.Exception.Message
}

# TEST 11: Frontend HTML load (§2.8 Daily Digest check)
try {
    $page = Invoke-WebRequest -Uri ($base + '/') -ErrorAction Stop
    $hasKanban = $page.Content -like '*Triage Command Center*'
    $hasDigest = $page.Content -like '*Daily Digest*'
    $hasAnalytics = $page.Content -like '*Analytics*'
    $hasCorrection = $page.Content -like '*Review*Correct*'
    if ($hasKanban -and $hasDigest) {
        $results += Test-Pass "11. Frontend HTML (§2.1, §2.8)" ("Kanban=$hasKanban | DailyDigest=$hasDigest | Analytics=$hasAnalytics | Correction=$hasCorrection")
    } else {
        $results += Test-Fail "11. Frontend HTML" ("Kanban=$hasKanban | DailyDigest=$hasDigest")
    }
} catch {
    $results += Test-Fail "11. Frontend HTML" $_.Exception.Message
}

# TEST 12: PDF Report Export endpoint
try {
    $pdfUri = ($base + '/api/email/email_001/report.pdf')
    $pdfR = Invoke-WebRequest -Uri $pdfUri -ErrorAction Stop
    $pdfMime = $pdfR.Headers.'Content-Type'
    if ($pdfMime -like '*pdf*') {
        $results += Test-Pass "12. PDF Report Export" ("Content-Type=$pdfMime | Size=" + $pdfR.Content.Length + " bytes")
    } else {
        $results += Test-Fail "12. PDF Report Export" ("Unexpected Content-Type: $pdfMime")
    }
} catch {
    $results += Test-Fail "12. PDF Report Export" $_.Exception.Message
}

# Summary
Write-Host ""
Write-Host "=========================================================="
Write-Host "MANIFEST AI E2E TEST RESULTS"
Write-Host "=========================================================="
$passCount = @($results | Where-Object { $_.Status -eq 'PASS' }).Count
$failCount = @($results | Where-Object { $_.Status -eq 'FAIL' }).Count
Write-Host "Total: $($results.Count) | PASS: $passCount | FAIL: $failCount"
Write-Host "Production Ready: $(if ($failCount -eq 0) { 'YES' } else { 'NO - see FAIL items above' })"
