# API Cost Management — Gemini 2.0 Flash

## Pricing Model

Gemini 2.0 Flash pricing (Google AI Studio / Vertex AI, as of 2025):

| Metric | Price |
|--------|-------|
| Input tokens | $0.10 per 1M tokens |
| Output tokens | $0.40 per 1M tokens |
| Free tier | 15 RPM, 1M TPM, 1,500 RPD |

> **Note:** Pricing may vary. Check [Google AI pricing](https://ai.google.dev/pricing) for current rates.

## Cost Estimation

### Per Conversation

| Parameter | Estimate |
|-----------|----------|
| Average input tokens (prompt + context) | ~500 tokens |
| Average output tokens (response) | ~200 tokens |
| Input cost per conversation | $0.00005 |
| Output cost per conversation | $0.00008 |
| **Total cost per conversation** | **$0.00013** |

### Monthly Projection

| Usage Level | Conversations/Day | Monthly Cost |
|-------------|-------------------|--------------|
| Light | 20 | $0.08 |
| Moderate | 50 | $0.20 |
| Heavy | 100 | $0.39 |
| Intensive | 200 | $0.78 |

### Free Tier Analysis

With 1,500 requests per day free:
- At **50 conversations/day** → **well within free tier**
- At **200 conversations/day** → still within free tier
- Free tier is sufficient for typical home assistant usage

## Cost Monitoring Strategy

### 1. Home Assistant Sensors

Template sensors in [sensors.yaml](../home-assistant/includes/sensors.yaml) track:

- `sensor.gemini_api_daily_cost` — Estimated cost based on daily conversation count
- `sensor.gemini_api_monthly_projection` — 30-day cost projection

### 2. Conversation Counter

Create a helper counter in HA (Settings → Helpers → Counter):
- Name: `daily_voice_conversations`
- Minimum: 0
- Step: 1
- Reset daily via automation

### 3. Daily Reset Automation

```yaml
# Add to automations.yaml
- alias: "Reset daily voice conversation counter"
  trigger:
    - platform: time
      at: "00:00:00"
  action:
    - service: counter.reset
      target:
        entity_id: counter.daily_voice_conversations
```

### 4. Cost Alert Automation

```yaml
# Alert if daily cost exceeds threshold
- alias: "Gemini API cost alert"
  trigger:
    - platform: numeric_state
      entity_id: sensor.gemini_api_daily_cost
      above: 0.10
  action:
    - service: notify.notify
      data:
        title: "API Cost Alert"
        message: >-
          Gemini API daily cost estimate: ${{ states('sensor.gemini_api_daily_cost') }}.
          Monthly projection: ${{ states('sensor.gemini_api_monthly_projection') }}.
```

## Token Optimization Tips

1. **System prompt caching** — Keep the system prompt concise; Gemini caches repeated prefixes
2. **Context window management** — Limit conversation history sent to API (last 3-5 turns)
3. **Short responses** — Configure the conversation agent to prefer brief answers
4. **Local fallback** — Use HA's built-in intent matching for simple commands (lights, switches) without calling the API
5. **Rate limiting** — Set a max conversations/minute in the conversation agent config

## Google Cloud Budget Alerts

If using Vertex AI (instead of AI Studio), set up billing alerts:

1. Go to Google Cloud Console → Billing → Budgets & Alerts
2. Create a budget for the project
3. Set alert thresholds at $1, $5, $10/month
4. Enable email notifications

For Google AI Studio (free API key), the free tier limits serve as a natural cost cap.
