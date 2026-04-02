<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>CDAA Integration Test Architecture</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f1117; color: #e2e8f0; padding: 24px; }
  h1 { font-size: 1.1rem; font-weight: 600; color: #94a3b8; margin-bottom: 20px; letter-spacing: 0.05em; text-transform: uppercase; }
  h2 { font-size: 0.85rem; font-weight: 600; color: #64748b; margin-bottom: 10px; letter-spacing: 0.05em; text-transform: uppercase; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .card { background: #1e2330; border: 1px solid #2d3448; border-radius: 8px; padding: 20px; }
  .card.full { grid-column: 1 / -1; }
  .mermaid { background: #1e2330; }
  .legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #94a3b8; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .tag { font-size: 0.7rem; padding: 2px 7px; border-radius: 9999px; font-weight: 600; }
  .tag-tf   { background: #1e3a5f; color: #60a5fa; }
  .tag-fix  { background: #1a3a2e; color: #4ade80; }
  .tag-test { background: #3a1a1a; color: #f87171; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th { text-align: left; padding: 6px 10px; color: #64748b; border-bottom: 1px solid #2d3448; font-weight: 500; }
  td { padding: 6px 10px; border-bottom: 1px solid #1a1f2e; vertical-align: top; }
  td:first-child { color: #94a3b8; white-space: nowrap; }
  .arrow { color: #60a5fa; }
  .warn { color: #f59e0b; font-size: 0.78rem; }
  code { background: #2d3448; padding: 1px 5px; border-radius: 3px; font-size: 0.8rem; color: #7dd3fc; }
</style>
</head>
<body>
<h1>CDAA — Integration Test Architecture (localstack)</h1>

<div class="grid">

  <!-- Full-width: infra overview -->
  <div class="card full">
    <h2>Localstack resources</h2>
    <div class="mermaid">
flowchart LR
    subgraph TF["Terraform-deployed"]
        SH["Lambda\nslack-access-request-handler"]
        CTL["Lambda\nlog-ctl-forwarder"]
        RECON["Lambda\ndaily-reconciliation"]
        DDB["DynamoDB\naccess-requests"]
        SSM["SSM\n/audit/cdaa-test/*"]
        SH --- DDB
        SH --- SSM
        RECON --- DDB
        RECON --- SSM
        CTL --- SSM
    end

    subgraph FIX["Fixture-deployed (test-only)"]
        JSTUB["Lambda\njira-stub"]
        JCAP["DynamoDB\njira-captures"]
        JSTUB --> JCAP
    end

    RECON -->|lambda.invoke| JSTUB

    subgraph NOTLS["Not in localstack community"]
        CTL_LAKE["CloudTrail Lake\nstart_query / get_query_results"]
    end

    RECON -.->|blocked| CTL_LAKE
    CTL -.->|blocked| CTL_LAKE

    subgraph PYTEST["pytest"]
        T["test code\nboto3 → localstack"]
    end

    T -->|invoke| SH
    T -->|invoke| CTL
    T -->|invoke| RECON
    T -->|read| DDB
    T -->|read| JCAP
    </div>
    <div class="legend">
      <div class="legend-item"><div class="dot" style="background:#60a5fa"></div>solid = real localstack call</div>
      <div class="legend-item"><div class="dot" style="background:#94a3b8; opacity:.4"></div>dashed = not supported, needs workaround</div>
    </div>
  </div>

  <!-- Cases 1-5 -->
  <div class="card">
    <h2>Cases 1–5 · Slack handler + CTL forwarder</h2>
    <table>
      <thead><tr><th>Step</th><th>Call</th></tr></thead>
      <tbody>
        <tr><td>Arrange</td><td>write SSM test values via fixture</td></tr>
        <tr><td>Act</td><td><code>lambda.invoke(SLACK_HANDLER_FN, payload)</code></td></tr>
        <tr><td>Assert</td><td><code>dynamodb.Table.get_item(request_id)</code></td></tr>
        <tr><td></td><td>check response envelope <code>statusCode</code></td></tr>
        <tr><td>CTL forwarder</td><td>invoke returns <code>{"emitted": N}</code>; <code>put_audit_events</code> fails silently (localstack) — assert on <code>emitted</code> count only</td></tr>
      </tbody>
    </table>
    <p class="warn" style="margin-top:10px">No CloudTrail Lake dependency — straightforward e2e.</p>
  </div>

  <!-- Cases 6-8 -->
  <div class="card">
    <h2>Cases 6–8 · Reconciliation</h2>
    <table>
      <thead><tr><th>Step</th><th>Call</th></tr></thead>
      <tbody>
        <tr><td>Arrange</td><td>seed <code>access-requests</code> DynamoDB via boto3</td></tr>
        <tr><td>Arrange</td><td>deploy <code>jira-stub</code> Lambda (fixture)</td></tr>
        <tr><td>Act</td><td><code>lambda.invoke(RECONCILIATION_FN, event)</code></td></tr>
        <tr><td>Assert violations</td><td>scan <code>jira-captures</code> table; check payload summary, user, violation type</td></tr>
        <tr><td>Assert no violation</td><td><code>jira-captures</code> table is empty</td></tr>
      </tbody>
    </table>
    <p class="warn" style="margin-top:10px">⚠ CloudTrail Lake: reconciliation calls <code>cloudtrail.start_query()</code> which localstack community does not support. See below.</p>
  </div>

  <!-- CloudTrail Lake problem -->
  <div class="card full">
    <h2>The CloudTrail Lake gap — options</h2>
    <table>
      <thead><tr><th>Option</th><th>How</th><th>Pros</th><th>Cons</th></tr></thead>
      <tbody>
        <tr>
          <td><strong>A. Event override</strong></td>
          <td>Add a <code>cloudtrail_events</code> key to the Lambda event payload; reconciliation skips the query and uses that list directly.</td>
          <td>Zero infra, fully e2e Lambda invocation, no code complexity</td>
          <td>Requires a small change to <code>daily_reconciliation.py</code> to accept injected events (test-only branch guarded by env var or event key)</td>
        </tr>
        <tr>
          <td><strong>B. pytest-httpserver</strong></td>
          <td>Stand up a local HTTP server that mimics the CloudTrail Lake API. Set <code>AWS_ENDPOINT_URL</code> in the Lambda env to point the boto3 client there.</td>
          <td>No code changes, pure infra</td>
          <td>Must replicate the CloudTrail Lake query/result API shape; the Lambda env var needs to be overridable per-test (update Lambda config before each invocation)</td>
        </tr>
        <tr>
          <td><strong>C. Localstack Pro</strong></td>
          <td>Pro tier supports CloudTrail Lake. Seed event data stores directly.</td>
          <td>Most realistic; no workarounds</td>
          <td>Paid; adds an external dependency to the test setup</td>
        </tr>
      </tbody>
    </table>
  </div>

</div>

<script>mermaid.initialize({ theme: "dark", startOnLoad: true });</script>
</body>
</html>
