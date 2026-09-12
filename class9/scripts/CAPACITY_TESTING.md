# Capacity experiments (run on your Mac)

Run all commands from ~/dev/class-code/class9 with the existing .venv and .env.
Lambda is already serving: no cluster setup, sync, SSH login or rollout is needed.
These commands run the repository's Gateway/Router in a separate process on your
Mac and send actual inference requests to the Lambda workers through SSH tunnels.
They do not exercise the Kubernetes orch-serve HTTP endpoint or change that pod.

## 1. Keep the existing worker tunnels running

Terminal 1:

    make port-forward

If your tunnels are already running, keep them; do not start a duplicate.
PREFILL_URLS in the Mac .env must point to the working forwarded text worker
(normally http://127.0.0.1:8000). The runner discovers /v1/models and uses the served model automatically when
only one is available; with multiple models, TEXT_MODEL must select one.
The runner checks worker health and the KV metric before sending load.

## 2. Check deterministic policy paths (no API spend)

Terminal 2:

    make test-429
    make test-503

429 sends a request exceeding a 10,000-token tenant allowance. Expected: 429,
via=local. 503 uses an empty worker pool with fallback disabled. Expected: 503,
via=local. These are repeatable policy checks, NOT evidence of GPU saturation.

## 3. Find the real saturation point, with fallback disabled

    make test-saturation

Defaults: 128 requests, 32 concurrent, 1,024 generated tokens per request.
If TARGET NOT OBSERVED and there are no worker errors, increase gradually:

    make test-saturation LAB_REQUESTS=256 LAB_CONCURRENCY=64
    make test-saturation LAB_REQUESTS=512 LAB_CONCURRENCY=128

Expected at saturation: a local 503 with reason=kv_free, meaning the real worker
KV-cache metric crossed the router's 80% threshold. A network failure is not
counted as saturation. No particular concurrency guarantees this threshold.
The load-only worker adapter uses ignore_eos=true to keep generation running and
allows the requested token budget instead of the normal adapter's 128-token cap.
Keep prompt plus output within the deployed model context limit (last observed:
2,048 tokens); defaults leave prompt headroom. Do not use 5,000 output tokens.
Each load request has its own tenant to avoid tenant 429s masking fleet limits.

## 4. Repeat with real Superlinked fallback

Ensure the Mac .env contains OVERFLOW_BASE_URL, OVERFLOW_MODEL and
OVERFLOW_API_KEY. Credentials are loaded without printing them.

    make test-overflow LAB_REQUESTS=256 LAB_CONCURRENCY=64
    make superlinked-usage

Use the concurrency that reached saturation in step 3. Fallback is limited to
3 requests per run and 32 output tokens per fallback request. To change the cap:

    make test-overflow LAB_REQUESTS=256 LAB_CONCURRENCY=64 LAB_OVERFLOW_LIMIT=5

Success requires status=200, via=overflow, local_status=503 and reason=kv_free.
Other final 503s can remain after the fallback cap is consumed. Backend failures
are not counted as successful overflow. A run that does not reach its target
returns a nonzero exit code, so make reports an error rather than a false pass.

## Results

Every run prints outcome counts and actual elapsed wall time, and writes a new
traces/capacity-<mode>-<run>.jsonl with each request's routing decision and reason.
These are direct Gateway/Router calls, so via is read from the response object;
the equivalent HTTP signal is X-Via. The old test-traffic targets still send to
the worker directly and should not be used as evidence of gateway fallback.

    make capacity-help
