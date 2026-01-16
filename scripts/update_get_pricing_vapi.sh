#!/bin/bash
# Update get_pricing tool in Vapi with corrected schema

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
SCHEMA_FILE="$PROJECT_ROOT/doc/vapi/tools/static/get_pricing.json"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
fi

if [ -z "$VAPI_API_KEY" ]; then
    echo "Error: VAPI_API_KEY not set"
    exit 1
fi

if [ -z "$VAPI_WEBHOOK_SECRET" ]; then
    echo "Error: VAPI_WEBHOOK_SECRET not set"
    exit 1
fi

echo "Updating get_pricing tool in Vapi..."
echo ""

# Find the tool ID
echo "Finding tool ID..."
TOOL_ID=$(curl -s -X GET "https://api.vapi.ai/tool" \
    -H "Authorization: Bearer $VAPI_API_KEY" \
    -H "Content-Type: application/json" | \
    python3 -c "
import sys, json
tools = json.load(sys.stdin)
for tool in tools:
    func = tool.get('function', {})
    if func.get('name') == 'get_pricing':
        print(tool.get('id'))
        sys.exit(0)
")

if [ -z "$TOOL_ID" ]; then
    echo "Error: Tool 'get_pricing' not found in Vapi"
    exit 1
fi

echo "Found tool ID: $TOOL_ID"
echo ""

# Extract tool payload from schema
echo "Loading schema..."
PAYLOAD=$(python3 -c "
import json
import sys

with open('$SCHEMA_FILE') as f:
    schema = json.load(f)

tool_def = schema.get('tool_definition', {})
function = tool_def.get('function', {})

payload = {
    'async': tool_def.get('async', False),
    'messages': tool_def.get('messages', [
        {'type': 'request-start', 'content': 'Let me check that for you.'},
        {'type': 'request-complete', 'content': ''},
        {'type': 'request-failed', 'content': \"I'm having trouble processing that request. Let me try again.\"},
        {'type': 'request-response-delayed', 'content': 'This is taking a moment. Please hold.', 'timingMilliseconds': 3000}
    ]),
    'function': function,
    'server': {
        'url': tool_def.get('server', {}).get('url', 'https://haes-hvac.fly.dev/vapi/server'),
        'timeoutSeconds': 30,
        'secret': '$VAPI_WEBHOOK_SECRET'
    }
}

print(json.dumps(payload))
")

# Update the tool
echo "Updating tool..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PATCH "https://api.vapi.ai/tool/$TOOL_ID" \
    -H "Authorization: Bearer $VAPI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
    echo "✅ Successfully updated get_pricing tool!"
    echo "Tool ID: $TOOL_ID"
    echo ""
    echo "Verify at: https://dashboard.vapi.ai/tools/$TOOL_ID"
else
    echo "❌ Error updating tool: HTTP $HTTP_STATUS"
    echo "Response: $BODY"
    exit 1
fi
