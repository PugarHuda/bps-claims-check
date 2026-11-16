# Synthetic perturbation benchmark

105 claims built from official figures; every claim has a known verdict. Cells = share of claims where the system's verdict equals the expected one (n in brackets). `last_digit_plus1`, `truncated_1dp`, `off_by_0.5`, `wrong_period` must be MISMATCH; `exact`, `rounded_1dp` must be MATCH; `absent_period` must be UNVERIFIABLE.

| system | covered | absent_period | exact | last_digit_plus1 | off_by_0.5 | rounded_1dp | truncated_1dp | wrong_period | overall | false accusations | missed errors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| oracle (gold tuple → deterministic verdict) | 105/105 | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (9) | 100% (16) | **100%** | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free | 105/105 | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (9) | 100% (16) | **100%** | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free__e2e | 105/105 | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (9) | 100% (16) | **100%** | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 105/105 | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (9) | 100% (16) | **100%** | 0 | 0 |
| rules | 105/105 | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (16) | 100% (9) | 100% (16) | **100%** | 0 | 0 |
