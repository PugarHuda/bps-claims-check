# No-gold report (system outputs only — NOT accuracy)

Reference table 104 rows; variant table 83 rows. Duplicates dropped: 2.

| system | sentences | tuples | MATCH | MISMATCH | of which = another published variant | UNVERIFIABLE | values not in sentence |
|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 164 | 93 | 83 | 0 | 0 (–) | 10 | 0 |
| anthropic__claude-sonnet-5.5__agent | 164 | 93 | 86 | 0 | 0 (–) | 7 | 0 |
| baidu__ernie-5.5-flash-preview_free | 164 | 95 | 77 | 1 | 0 (–) | 17 | 2 |
| baidu__ernie-5.5-flash-preview_free__e2e | 124 | 76 | 65 | 1 | 0 (–) | 10 | 0 |
| baidu__ernie-5.5-flash-preview_free__persentence | 10 | 2 | 2 | 0 | 0 (–) | 0 | 0 |
| liquid__lfm-3-1.7b_free | 38 | 12 | 12 | 0 | 0 (–) | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 164 | 102 | 77 | 8 | 5 (inflation_mtm 5) | 17 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 164 | 93 | 80 | 1 | 0 (–) | 12 | 0 |
| regex | 164 | 162 | 49 | 32 | 8 (inflation_ytd 2, inflation_mtm 4, gdp_growth_ctc 2) | 81 | 0 |
| rules | 164 | 204 | 60 | 55 | 7 (inflation_mtm 5, gdp_growth_ctc 2) | 89 | 0 |

## Verdict agreement (Cohen's κ; n = sentences both systems processed)

| | anthropic__claude-haiku-5.5__agent | anthropic__claude-sonnet-5.5__agent | baidu__ernie-5.5-flash-preview_free | baidu__ernie-5.5-flash-preview_free__e2e | baidu__ernie-5.5-flash-preview_free__persentence | liquid__lfm-3-1.7b_free | nvidia__nemotron-3-ultra-550b-a55b_free | nvidia__nemotron-3-ultra-550b-a55b_free__e2e | regex | rules |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 1.00 (n=164) | 0.81 (n=164) | 0.55 (n=164) | 0.56 (n=124) | 1.00 (n=10) | -0.11 (n=38) | 0.60 (n=164) | 0.58 (n=164) | 0.10 (n=164) | 0.21 (n=164) |
| anthropic__claude-sonnet-5.5__agent | 0.81 (n=164) | 1.00 (n=164) | 0.42 (n=164) | 0.48 (n=124) | 1.00 (n=10) | -0.11 (n=38) | 0.50 (n=164) | 0.49 (n=164) | 0.10 (n=164) | 0.20 (n=164) |
| baidu__ernie-5.5-flash-preview_free | 0.55 (n=164) | 0.42 (n=164) | 1.00 (n=164) | 0.90 (n=124) | 1.00 (n=10) | 0.16 (n=38) | 0.68 (n=164) | 0.65 (n=164) | 0.10 (n=164) | 0.21 (n=164) |
| baidu__ernie-5.5-flash-preview_free__e2e | 0.56 (n=124) | 0.48 (n=124) | 0.90 (n=124) | 1.00 (n=124) | 1.00 (n=10) | -0.15 (n=22) | 0.67 (n=124) | 0.75 (n=124) | 0.09 (n=124) | 0.22 (n=124) |
| baidu__ernie-5.5-flash-preview_free__persentence | 1.00 (n=10) | 1.00 (n=10) | 1.00 (n=10) | 1.00 (n=10) | 1.00 (n=10) | 1.00 (n=10) | 0.18 (n=10) | 1.00 (n=10) | 0.17 (n=10) | 0.12 (n=10) |
| liquid__lfm-3-1.7b_free | -0.11 (n=38) | -0.11 (n=38) | 0.16 (n=38) | -0.15 (n=22) | 1.00 (n=10) | 1.00 (n=38) | 0.27 (n=38) | 0.00 (n=38) | 0.11 (n=38) | 0.09 (n=38) |
| nvidia__nemotron-3-ultra-550b-a55b_free | 0.60 (n=164) | 0.50 (n=164) | 0.68 (n=164) | 0.67 (n=124) | 0.18 (n=10) | 0.27 (n=38) | 1.00 (n=164) | 0.68 (n=164) | 0.14 (n=164) | 0.28 (n=164) |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 0.58 (n=164) | 0.49 (n=164) | 0.65 (n=164) | 0.75 (n=124) | 1.00 (n=10) | 0.00 (n=38) | 0.68 (n=164) | 1.00 (n=164) | 0.11 (n=164) | 0.22 (n=164) |
| regex | 0.10 (n=164) | 0.10 (n=164) | 0.10 (n=164) | 0.09 (n=124) | 0.17 (n=10) | 0.11 (n=38) | 0.14 (n=164) | 0.11 (n=164) | 1.00 (n=164) | 0.27 (n=164) |
| rules | 0.21 (n=164) | 0.20 (n=164) | 0.21 (n=164) | 0.22 (n=124) | 0.12 (n=10) | 0.09 (n=38) | 0.28 (n=164) | 0.22 (n=164) | 0.27 (n=164) | 1.00 (n=164) |
