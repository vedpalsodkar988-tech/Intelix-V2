# Runbook: checkout-service Incident Response

**On-call:** whoever's holding the pager
**Escalation:** if unresolved after 15 minutes, escalate to the platform channel.

## If checkout-service is throwing 5xx errors

1. Check recent deploys:
   ```
   kubectl rollout history deployment/checkout-service
   ```

2. If a bad deploy is suspected, roll it back:
   ```
   kubectl rollout undo deployment/checkout-service
   ```

3. Confirm the service picked up its required config. It needs these env vars set:
   - `STRIPE_API_KEY`
   - `PAYMENT_WEBHOOK_SECRET`
   - `CHECKOUT_LEGACY_FLAG`

4. If pods are stuck crash-looping, check the old payments sidecar:
   ```
   kubectl describe pod checkout-payments-sidecar
   ```

5. If nothing else works, restart the deployment:
   ```
   kubectl rollout restart deployment/checkout-service-v2
   ```

## Post-incident

Update this runbook if any of the above steps turned out to be wrong —
stale runbooks cost the next on-call engineer time they don't have.
