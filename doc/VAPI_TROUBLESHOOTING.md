# Vapi Integration Troubleshooting Guide

## Quick Diagnosis

### Check Current Configuration Status

```bash
# Check Fly.io logs for recent requests
fly logs --app haes-hvac -n 100 | grep -E "vapi|POST|401|422"

# Check health endpoint
curl https://haes-hvac.fly.dev/vapi/server/health

# Verify secrets are set
fly secrets list --app haes-hvac | grep VAPI
```

---

## Common Issues & Solutions

### Issue 1: "No result returned" Error in Vapi

**Symptoms:**
- Vapi shows "No result returned" error
- Tool call appears to fail silently
- Customer hears error message

**Diagnosis:**
```bash
fly logs --app haes-hvac | grep "vapi/server"
```

**Possible Causes:**

#### A) Vapi is calling the wrong endpoint

**Log shows:** `POST /vapi/tools/hael_route | status=422`

**Solution:** Update Vapi assistant to use Server URL integration
```bash
python scripts/configure_vapi_assistant.py
```

#### B) Missing webhook signature

**Log shows:** `Missing webhook signature in production | status=401`

**Solution:** Set the Server URL Secret in Vapi Dashboard
1. Go to Vapi Dashboard > Assistants > Riley
2. Set **Server URL Secret** to match your `VAPI_WEBHOOK_SECRET`
3. Get the secret from Fly.io:
   ```bash
   fly secrets list --app haes-hvac | grep VAPI_WEBHOOK_SECRET
   ```

#### C) Invalid webhook signature

**Log shows:** `Invalid webhook signature | status=401`

**Solution:** Verify secrets match
```bash
# Check Fly.io secret
fly secrets list --app haes-hvac | grep VAPI_WEBHOOK_SECRET

# Check Vapi Dashboard
# Go to Assistants > Riley > Server URL Secret
# They must match exactly
```

#### D) Backend error or timeout

**Log shows:** Exception or 500 error

**Solution:** Check detailed logs
```bash
fly logs --app haes-hvac | grep -A 10 "ERROR\|Exception"
```

---

### Issue 2: 401 Unauthorized Errors

**Symptoms:**
- All requests to `/vapi/server` return 401
- Logs show "Missing webhook signature"

**Root Cause:** Signature verification is enforced in production but Vapi isn't sending signatures

**Solutions:**

#### Option A: Configure Server URL Secret (Recommended)
```bash
# 1. Get your webhook secret
fly secrets list --app haes-hvac | grep VAPI_WEBHOOK_SECRET

# 2. Update Vapi assistant
python scripts/configure_vapi_assistant.py

# 3. Or manually in Vapi Dashboard:
#    - Go to Assistants > Riley
#    - Set "Server URL Secret" to the value from step 1
```

#### Option B: Temporarily disable signature verification (NOT recommended for production)
```bash
# Remove VAPI_WEBHOOK_SECRET (makes verification optional in production)
fly secrets unset VAPI_WEBHOOK_SECRET --app haes-hvac

# Note: This reduces security. Only use for testing.
```

---

### Issue 3: 422 Unprocessable Entity

**Symptoms:**
- Request reaches backend but fails validation
- Status code 422

**Root Cause:** Request body doesn't match expected schema

**Diagnosis:**
```bash
# Check what endpoint is being called
fly logs --app haes-hvac | grep "422"
```

**Solutions:**

#### If calling `/vapi/tools/hael_route`:
This is the old legacy endpoint. Update to Server URL:
```bash
python scripts/configure_vapi_assistant.py
```

#### If calling `/vapi/server`:
Check the request payload format. Should be:
```json
{
  "message": {
    "type": "tool-calls",
    "call": { "id": "..." },
    "toolCallList": [
      {
        "id": "tc_001",
        "name": "hael_route",
        "parameters": {
          "user_text": "...",
          "conversation_context": "..."
        }
      }
    ]
  }
}
```

---

### Issue 4: Tool Not Executing

**Symptoms:**
- Call connects but tool never fires
- Riley doesn't route to backend

**Diagnosis:**
Check if tool is attached to assistant:
```bash
# Use Vapi API to check
curl -X GET "https://api.vapi.ai/assistant/$VAPI_ASSISTANT_ID" \
  -H "Authorization: Bearer $VAPI_API_KEY" | jq '.model.tools'
```

**Solutions:**

1. **Reconfigure assistant:**
   ```bash
   python scripts/configure_vapi_assistant.py
   ```

2. **Manually verify in Vapi Dashboard:**
   - Go to Assistants > Riley > Model
   - Check "Tools" section
   - Ensure `hael_route` is listed and enabled

3. **Check system prompt:**
   - Ensure prompt instructs Riley to use the tool
   - Look for: "For any operational action... call the hael_route tool"

---

### Issue 5: Transfer Not Working

**Symptoms:**
- Riley says "let me transfer you" but nothing happens
- Transfer destination request fails

**Diagnosis:**
```bash
fly logs --app haes-hvac | grep "transfer-destination-request"
```

**Solutions:**

1. **Verify server messages are enabled:**
   ```bash
   python scripts/configure_vapi_assistant.py
   ```

2. **Check transfer number format:**
   - Should be: `+19723724458` (E.164 format)
   - Check in logs or code: `src/api/vapi_server.py`

3. **Verify business hours logic:**
   ```bash
   # Test the health endpoint to see current business hours status
   curl https://haes-hvac.fly.dev/vapi/server/health | jq '.business_hours'
   ```

---

### Issue 6: Odoo Integration Failures

**Symptoms:**
- Tool executes but returns error
- "Failed to create record in Odoo"

**Diagnosis:**
```bash
fly logs --app haes-hvac | grep -E "Odoo|odoo_client"
```

**Solutions:**

1. **Verify Odoo credentials:**
   ```bash
   fly ssh console --app haes-hvac -C "python scripts/verify_odoo_connection.py"
   ```

2. **Check Odoo models are accessible:**
   ```bash
   fly ssh console --app haes-hvac -C "python scripts/discover_odoo_capabilities.py"
   ```

3. **Review Odoo discovery file:**
   ```bash
   cat .cursor/odoo_discovery.json | jq '.models | keys'
   ```

---

## Configuration Checklist

### ✅ Vapi Dashboard Configuration

- [ ] Assistant "Riley" exists
- [ ] **Server URL** set to: `https://haes-hvac.fly.dev/vapi/server`
- [ ] **Server URL Secret** matches `VAPI_WEBHOOK_SECRET` from Fly.io
- [ ] **Server Messages** enabled:
  - `tool-calls`
  - `transfer-destination-request`
  - `end-of-call-report`
  - `status-update`
- [ ] Tool `hael_route` is created and attached
- [ ] System prompt is updated (from `doc/vapi/system_prompt.md`)
- [ ] Phone number is routed to assistant Riley

### ✅ Fly.io Configuration

- [ ] App deployed: `fly status --app haes-hvac`
- [ ] Secrets set:
  ```bash
  fly secrets list --app haes-hvac
  ```
  - `VAPI_API_KEY`
  - `VAPI_WEBHOOK_SECRET`
  - `VAPI_PUBLIC_KEY`
  - `VAPI_ASSISTANT_ID`
  - `VAPI_TWILIO_PHONE_ID`
  - `ODOO_BASE_URL`
  - `ODOO_DB`
  - `ODOO_USERNAME`
  - `ODOO_PASSWORD`
- [ ] Health check passing: `curl https://haes-hvac.fly.dev/health`
- [ ] Database migrations applied: `fly ssh console -C "python -m alembic current"`

### ✅ Local Environment

- [ ] `.env` file has all required variables
- [ ] Can run configuration script:
  ```bash
  python scripts/configure_vapi_assistant.py
  ```
- [ ] Can run verification script:
  ```bash
  python scripts/verify_vapi_server_url.py --prod
  ```

---

## Testing Procedures

### 1. Test Backend Directly

```bash
# Test health endpoint
curl https://haes-hvac.fly.dev/vapi/server/health

# Expected: {"status": "ok", "business_hours": true/false, ...}
```

### 2. Test with Signed Request

```bash
# Run verification script
python scripts/verify_vapi_server_url.py --prod

# Expected: All tests should pass (health, tool-calls, transfer, etc.)
```

### 3. Test End-to-End Call

1. Call your Vapi phone number
2. Say: "My heater isn't working"
3. Provide: Name, phone, address when asked
4. Expected: Riley creates service request and confirms

Monitor logs during call:
```bash
fly logs --app haes-hvac --region dfw
```

Look for:
- `POST /vapi/server | status=200`
- `Vapi server message: type=tool-calls`
- `Vapi tool call: call_id=...`

### 4. Test Transfer (During Business Hours)

1. Call during business hours (8 AM - 5 PM CST)
2. Say: "I want to talk to a person"
3. Expected: Riley transfers to 972-372-4458

### 5. Test After-Hours Behavior

1. Call after hours (outside 8 AM - 5 PM CST)
2. Say: "I want to talk to a person"
3. Expected: Riley collects callback info instead of transferring

---

## Log Analysis

### Successful Request Pattern

```
INFO | POST /vapi/server | status=200 | duration_ms=150
INFO | Vapi server message: type=tool-calls, call_id=call_123
INFO | Vapi tool call: call_id=call_123, tool_call_id=tc_001
```

### Failed Request Patterns

#### Pattern 1: Signature Issue
```
ERROR | Missing webhook signature in production
INFO | GET /vapi/server | status=401 | duration_ms=0.70
```
**Fix:** Configure Server URL Secret in Vapi Dashboard

#### Pattern 2: Wrong Endpoint
```
INFO | POST /vapi/tools/hael_route | status=422 | duration_ms=7.64
```
**Fix:** Update assistant to use Server URL

#### Pattern 3: Backend Error
```
ERROR | Exception in hael_route: ...
INFO | POST /vapi/server | status=500 | duration_ms=...
```
**Fix:** Check exception details and fix code issue

---

## Emergency Rollback

If the new Server URL integration isn't working and you need to rollback:

### Option 1: Revert to Legacy Tool Endpoint (Temporary)

In Vapi Dashboard:
1. Go to Assistants > Riley > Model > Tools
2. Change tool server URL to: `https://haes-hvac.fly.dev/vapi/tools/hael_route`
3. Remove Server URL configuration (leave blank)

This uses the old endpoint which doesn't require signature verification.

### Option 2: Deploy Previous Version

```bash
# Check deployment history
fly releases list --app haes-hvac

# Rollback to previous version
fly deploy --image registry.fly.io/haes-hvac:deployment-<PREVIOUS_ID>
```

---

## Getting Help

### Check Documentation
- Project Flow: `doc/PROJECT_FLOW.md`
- Deployment Guide: `doc/DEPLOYMENT.md`
- Vapi Plan: `.cursor/plans/vapi_full_setup_82ef3522.plan.md`

### Collect Debug Info

```bash
# Create debug bundle
mkdir -p debug_info
fly logs --app haes-hvac -n 500 > debug_info/fly_logs.txt
fly status --app haes-hvac > debug_info/fly_status.txt
fly secrets list --app haes-hvac > debug_info/fly_secrets.txt
curl https://haes-hvac.fly.dev/health > debug_info/health.json
curl https://haes-hvac.fly.dev/vapi/server/health > debug_info/vapi_health.json

# Share debug_info/ folder for troubleshooting
```

### Common Support Questions

**Q: How do I know if Vapi is calling the right endpoint?**  
A: Check logs for `POST /vapi/server` (correct) vs `POST /vapi/tools/hael_route` (old)

**Q: Why am I getting 401 errors?**  
A: Signature verification is enforced. Set Server URL Secret in Vapi Dashboard.

**Q: How do I test without making a real phone call?**  
A: Use the verification script: `python scripts/verify_vapi_server_url.py --prod`

**Q: Can I see what Vapi is sending?**  
A: Yes, check Fly.io logs during a call: `fly logs --app haes-hvac`

---

## Advanced Debugging

### Enable Debug Logging

```bash
# Temporarily enable debug logging
fly secrets set LOG_LEVEL=DEBUG --app haes-hvac

# Make test call, then revert
fly secrets set LOG_LEVEL=INFO --app haes-hvac
```

### Test Signature Verification Locally

```python
import hashlib
import hmac
import time

secret = "your_webhook_secret"
body = b'{"message": {"type": "status-update"}}'
timestamp = str(int(time.time()))

payload = f"{timestamp}.".encode() + body
signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

print(f"X-Vapi-Signature: {signature}")
print(f"X-Vapi-Timestamp: {timestamp}")
```

### Inspect Vapi Assistant Config

```bash
curl -X GET "https://api.vapi.ai/assistant/$VAPI_ASSISTANT_ID" \
  -H "Authorization: Bearer $VAPI_API_KEY" | jq '.'
```

---

**Last Updated:** 2026-01-09  
**Version:** 1.0
