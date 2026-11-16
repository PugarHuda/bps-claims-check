# Hard synthetic benchmark (relative periods, stale figures, unlabelled m-to-m)

39 claims built from official figures; every claim has a known verdict (`A|B` = either accepted). Cells = share of claims judged as expected (n in brackets).

| system | covered | mtm_unlabelled | relative_last_month | relative_wrong_month | stale_latest | overall | false accusations | missed errors |
|---|---|---|---|---|---|---|---|---|
| oracle (gold tuple → deterministic verdict) | 39/39 | 100% (10) | 100% (10) | 100% (9) | 100% (10) | **100%** | 0 | 0 |
| anthropic__claude-haiku-5.5__agent | 39/39 | 100% (10) | 100% (10) | 100% (9) | 90% (10) | **97%** | 0 | 1 |
| anthropic__claude-sonnet-5.5__agent | 39/39 | 100% (10) | 100% (10) | 100% (9) | 90% (10) | **97%** | 0 | 1 |
| gemini__gemini-3.5-flash | 39/39 | 100% (10) | 100% (10) | 100% (9) | 90% (10) | **97%** | 0 | 1 |
| gemini__gemini-3.5-flash__e2e | 39/39 | 100% (10) | 100% (10) | 100% (9) | 80% (10) | **95%** | 0 | 1 |
| rules | 39/39 | 100% (10) | 100% (10) | 100% (9) | 0% (10) | **74%** | 0 | 0 |
