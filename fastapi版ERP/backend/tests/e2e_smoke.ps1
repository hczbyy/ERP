# OpenERP End-to-End smoke test (PowerShell)
# Covers: login -> purchase order -> approve -> receive -> stock check
#         -> sales order -> approve -> ship -> receivable/payable -> settle
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
$pass = 0; $fail = 0

function Step([string]$name, [scriptblock]$block) {
    try {
        & $block | Out-Null
        Write-Host "PASS  $name" -ForegroundColor Green
        $script:pass++
    } catch {
        Write-Host "FAIL  $name : $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
    }
}

function Login([string]$u, [string]$p) {
    $r = Invoke-RestMethod -Uri "$base/api/auth/login" -Method Post -ContentType "application/json" -Body (@{username=$u; password=$p} | ConvertTo-Json)
    if ($r.code -ne 0) { throw "login failed: $($r.message)" }
    return @{ Authorization = "Bearer $($r.data.token)" }
}

function ApiGet($h, [string]$path) {
    $r = Invoke-RestMethod -Uri "$base$path" -Headers $h -Method Get
    if ($r.code -ne 0) { throw "GET $path : $($r.message)" }
    return $r.data
}

function ApiPost($h, [string]$path, $body) {
    $r = Invoke-RestMethod -Uri "$base$path" -Headers $h -Method Post -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 6)
    if ($r.code -ne 0) { throw "POST $path : $($r.message)" }
    return $r.data
}

Step "login admin" { $script:H = Login "admin" "admin123" }
Step "login wrong password rejected" {
    try { Login "admin" "wrong-pass"; throw "should reject" } catch { if ($_.Exception.Message -notmatch "should reject") { throw } }
}

$h = $null
Step "master: products/customers/suppliers/warehouses" {
    $script:H = $H
    $p = ApiGet $H "/api/master/products/all"; if ($p.Count -lt 10) { throw "products < 10" }
    $c = ApiGet $H "/api/master/customers/all"; if ($c.Count -lt 3) { throw "customers < 3" }
    $s = ApiGet $H "/api/master/suppliers/all"; if ($s.Count -lt 3) { throw "suppliers < 3" }
    $w = ApiGet $H "/api/master/warehouses"; if ($w.Count -lt 2) { throw "warehouses < 2" }
    $script:P1 = $p[0].id; $script:P2 = $p[1].id
    $script:C1 = $c[0].id; $script:S1 = $s[0].id; $script:W1 = $w[0].id
}

Step "create purchase order (draft)" {
    $d = ApiPost $H "/api/purchase/orders" @{ supplier_id=$S1; warehouse_id=$W1; remark="e2e"; items=@(@{product_id=$P1; qty=10; price=100}, @{product_id=$P2; qty=5; price=200}) }
    if ($d.status -ne "draft") { throw "status not draft" }
    if ($d.total_amount -ne 2000) { throw "total wrong: $($d.total_amount)" }
    $script:PO = $d.id
}

Step "approve + cancel reject (completed order)" {
    $d = ApiPost $H "/api/purchase/orders/$PO/approve" @{}
    if ($d.status -ne "approved") { throw "not approved" }
    try { ApiPost $H "/api/purchase/orders/$PO/cancel" @{reason="x"} | Out-Null; throw "should reject cancel after receive" } catch { if ($_.Exception.Message -notmatch "should reject") { throw } }
}

Step "receive all -> stock up + payable created" {
    $before = (ApiGet $H "/api/inventory/stocks?warehouse_id=$W1&page_size=100").items | Where-Object { $_.product_id -eq $P1 } | Select-Object -First 1
    $d = ApiPost $H "/api/purchase/orders/$PO/receive" @{ items=@(@{product_id=$P1; qty=10; price=100}, @{product_id=$P2; qty=5; price=200}) }
    if ($d.total_amount -ne 2000) { throw "receive amount wrong" }
    $after = (ApiGet $H "/api/inventory/stocks?warehouse_id=$W1&page_size=100").items | Where-Object { $_.product_id -eq $P1 } | Select-Object -First 1
    if (($after.qty - $before.qty) -ne 10) { throw "stock delta wrong" }
    $pay = ApiGet $H "/api/finance/payables?page_size=5"
    if ($pay.items.Count -lt 1) { throw "no payable" }
    $script:PAY = $pay.items[0].id
    $script:PAY_NO = $pay.items[0].payable_no
    $script:PAY_BAL = $pay.items[0].balance
}

Step "over-receive rejected" {
    try { ApiPost $H "/api/purchase/orders/$PO/receive" @{ items=@(@{product_id=$P1; qty=999}) } | Out-Null; throw "should reject over-receive" } catch { if ($_.Exception.Message -notmatch "should reject") { throw } }
}

Step "create + approve sales order" {
    $d = ApiPost $H "/api/sales/orders" @{ customer_id=$C1; warehouse_id=$W1; remark="e2e"; items=@(@{product_id=$P1; qty=6; price=150}) }
    if ($d.total_amount -ne 900) { throw "so total wrong" }
    $script:SO = $d.id
    $d2 = ApiPost $H "/api/sales/orders/$SO/approve" @{}
    if ($d2.status -ne "approved") { throw "not approved" }
}

Step "ship 6 -> stock down + receivable created" {
    $d = ApiPost $H "/api/sales/orders/$SO/ship" @{ items=@(@{product_id=$P1; qty=6; price=150}) }
    if ($d.total_amount -ne 900) { throw "ship amount wrong" }
    $rec = ApiGet $H "/api/finance/receivables?page_size=5"
    if ($rec.items.Count -lt 1) { throw "no receivable" }
    $script:REC = $rec.items[0].id
    $script:REC_NO = $rec.items[0].receivable_no
}

Step "ship over stock rejected" {
    try { ApiPost $H "/api/sales/orders/$SO/ship" @{ items=@(@{product_id=$P1; qty=9999}) } | Out-Null; throw "should reject" } catch { if ($_.Exception.Message -notmatch "should reject") { throw } }
}

Step "partial settle + over-settle rejected" {
    $d = ApiPost $H "/api/finance/receipts" @{ receivable_id=$REC; amount=500; pay_method="bank" }
    if ($d.receipt_no -notmatch "^RC") { throw "receipt no wrong" }
    $rec = (ApiGet $H "/api/finance/receivables?keyword=$REC_NO").items[0]
    if ($rec.status -ne "partial") { throw "status not partial" }
    try { ApiPost $H "/api/finance/receipts" @{ receivable_id=$REC; amount=9999 } | Out-Null; throw "should reject over-settle" } catch { if ($_.Exception.Message -notmatch "should reject") { throw } }
}

Step "settle receivable fully" {
    $d = ApiPost $H "/api/finance/receipts" @{ receivable_id=$REC; amount=400 }
    $rec = (ApiGet $H "/api/finance/receivables?keyword=$REC_NO").items[0]
    if ($rec.status -ne "settled") { throw "not settled" }
}

Step "settle payable fully" {
    $d = ApiPost $H "/api/finance/payments" @{ payable_id=$PAY; amount=$PAY_BAL }
    $pay = (ApiGet $H "/api/finance/payables?keyword=$PAY_NO").items[0]
    if ($pay.status -ne "settled") { throw "payable not settled" }
}

Step "stock transfer between warehouses" {
    $d = ApiPost $H "/api/inventory/transfers" @{ from_warehouse_id=$W1; to_warehouse_id=2; items=@(@{product_id=$P2; qty=2}) }
    if ($d.transfer_no -notmatch "^TR") { throw "transfer no wrong" }
}

Step "stock check cycle" {
    $c = ApiPost $H "/api/inventory/checks" @{ warehouse_id=$W1; product_ids=@($P2) }
    $cid = $c.id
    ApiPut $H "/api/inventory/checks/$cid" @{ items=@(@{product_id=$P2; actual_qty=0}) } | Out-Null
    ApiPost $H "/api/inventory/checks/$cid/done" @{} | Out-Null
}

Step "audit log recorded" {
    $logs = ApiGet $H "/api/system/audit-logs?page_size=50"
    if ($logs.items.Count -lt 10) { throw "audit logs too few: $($logs.items.Count)" }
}

Step "RBAC: auditor cannot manage products" {
    $h2 = Login "auditor" "demo123"
    try {
        Invoke-RestMethod -Uri "$base/api/master/products" -Headers $h2 -Method Post -ContentType "application/json" -Body (@{code="X1";name="x"} | ConvertTo-Json) | Out-Null
        throw "should be forbidden"
    } catch {
        if ($_.Exception.Response.StatusCode -ne 403) { throw "expected 403, got $($_.Exception.Response.StatusCode)" }
    }
}

Step "RBAC: keeper cannot create purchase order" {
    $h3 = Login "keeper" "demo123"
    try {
        Invoke-RestMethod -Uri "$base/api/purchase/orders" -Headers $h3 -Method Post -ContentType "application/json" -Body (@{supplier_id=1;warehouse_id=1;items=@()} | ConvertTo-Json -Depth 5) | Out-Null
        throw "should be forbidden"
    } catch {
        if ($_.Exception.Response.StatusCode -ne 403) { throw "expected 403, got $($_.Exception.Response.StatusCode)" }
    }
}

Step "dashboard summary + trend + top" {
    $s = ApiGet $H "/api/dashboard/summary"
    if ($s.today_sales -lt 0) { throw "summary wrong" }
    $t = ApiGet $H "/api/dashboard/sales-trend?days=7"
    if ($t.labels.Count -ne 7) { throw "trend labels != 7" }
    $top = ApiGet $H "/api/dashboard/top-products?limit=5"
    if ($top.Count -lt 1) { throw "top products empty" }
}

function ApiPut($h, [string]$path, $body) {
    $r = Invoke-RestMethod -Uri "$base$path" -Headers $h -Method Put -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 6)
    if ($r.code -ne 0) { throw "PUT $path : $($r.message)" }
    return $r.data
}

Write-Host ""
Write-Host "============================================"
Write-Host "E2E result: PASS=$pass FAIL=$fail"
Write-Host "============================================"
if ($fail -gt 0) { exit 1 }