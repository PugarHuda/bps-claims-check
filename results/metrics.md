# Metrics — reference labels: adjudicated silver: blind Claude Opus labels, with all 7 sentences where the systems' majority disagreed with them decided by a human

> Reference labels are LLM labels except 7 human-adjudicated sentences. Sentences where every system agreed with the annotator were not human-checked: correlated errors there are invisible to these metrics.

Labels: 164 checked sentences (2 duplicate sentences dropped), 75 with ≥1 in-scope claim, 94 claim tuples. Reference table: 104 rows; variant table: 83 rows. CIs: 95% bootstrap over sentences (2,000 resamples).

## Headline (adjudicated silver: blind Claude Opus labels, with all 7 sentences where the systems' majority disagreed with them decided by a human)

- Bindable rate (claim resolves to a BPS figure): **90/94 = 95.7%** [91.1%, 99.1%]
- Mismatch rate among bindable: **2/90 = 2.2%** [0.0%, 5.7%]
- Unverifiable: 4
- Of 2 MISMATCHes, **right number, wrong frame** (claim equals another published variant of the same release): none; wrong number: 2

| indicator | MATCH | MISMATCH | UNVERIFIABLE |
|---|---|---|---|
| inflation_yoy | 24 | 0 | 0 |
| unemployment_rate | 17 | 1 | 2 |
| poverty_rate | 18 | 1 | 2 |
| gdp_growth_yoy | 29 | 0 | 0 |

### By speaker_type

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| bps_official | 51 | 32 | 32/32 = 100% | 0/32 = 0% |
| dpr_or_politician | 1 | 1 | 1/1 = 100% | 0/1 = 0% |
| government_official | 70 | 42 | 39/42 = 93% | 0/39 = 0% |
| journalist_or_other | 42 | 19 | 18/19 = 95% | 2/18 = 11% |

### By source

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| government (.go.id) | 25 | 11 | 10/11 = 91% | 0/10 = 0% |
| news media | 139 | 83 | 80/83 = 96% | 2/80 = 2% |

### By attributes BPS in sentence

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| no | 131 | 64 | 60/64 = 94% | 1/60 = 2% |
| yes | 33 | 30 | 30/30 = 100% | 1/30 = 3% |

## Systems vs gold

`__e2e` = the LLM gave the verdict itself with the BPS table in its prompt (ablation); every other row: LLM/rules extract, deterministic lookup decides. Systems that did not process every gold sentence are scored on the ones they did (see 'scored').

| system | scored | extract P | extract R | extract F1 | verdict acc | verdict macro-F1 [95% CI] | false MISMATCH | missed MISMATCH | values not in sentence |
|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 164/164 | 1.00 | 0.99 | 0.99 | 0.93 | 0.51 [0.38, 0.60] | 0 | 2 | 0 |
| anthropic__claude-sonnet-5.5__agent | 164/164 | 1.00 | 0.99 | 0.99 | 0.94 | 0.51 [0.33, 0.62] | 0 | 2 | 0 |
| baidu__ernie-5.5-flash-preview_free | 164/164 | 0.96 | 0.97 | 0.96 | 0.81 | 0.65 [0.35, 0.82] | 0 | 1 | 2 |
| baidu__ernie-5.5-flash-preview_free__e2e | 124/164 | 0.97 | 0.99 | 0.98 | 0.87 | 0.76 [0.31, 0.88] | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free__persentence | 10/164 | 1.00 | 1.00 | 1.00 | 1.00 | 0.33 [0.00, 0.33] | 0 | 0 | 0 |
| gemini__gemini-3.8-flash | 164/164 | 0.99 | 0.99 | 0.99 | 0.87 | 0.68 [0.37, 0.86] | 0 | 1 | 0 |
| gemini__gemini-3.8-flash__e2e | 144/164 | 0.99 | 0.96 | 0.98 | 0.88 | 0.65 [0.32, 0.85] | 0 | 1 | 0 |
| liquid__lfm-3-1.7b_free | 38/164 | 0.92 | 0.85 | 0.88 | 0.79 | 0.29 [0.24, 0.33] | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 164/164 | 0.92 | 1.00 | 0.96 | 0.80 | 0.50 [0.36, 0.70] | 7 | 1 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 164/164 | 0.99 | 0.98 | 0.98 | 0.85 | 0.62 [0.31, 0.80] | 0 | 1 | 0 |
| regex | 164/164 | 0.43 | 0.73 | 0.54 | 0.27 | 0.27 [0.23, 0.33] | 31 | 1 | 0 |
| rules | 164/164 | 0.46 | 0.98 | 0.63 | 0.30 | 0.30 [0.25, 0.34] | 54 | 1 | 0 |

## Error taxonomy (one cause per disagreement with gold)

| system | wrong period | other out-of-scope figure | target / projection | missed claim | core / component inflation | mtm read as y-on-y | wrong value | regional figure | q-to-q / c-to-c read as y-on-y | ytd read as y-on-y |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 12 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| anthropic__claude-sonnet-5.5__agent | 6 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free | 15 | 2 | 1 | 3 | 0 | 0 | 0 | 0 | 1 | 0 |
| baidu__ernie-5.5-flash-preview_free__e2e | 7 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free__persentence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemini__gemini-3.8-flash | 12 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemini__gemini-3.8-flash__e2e | 7 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| liquid__lfm-3-1.7b_free | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 14 | 3 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 12 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| regex | 22 | 43 | 15 | 19 | 15 | 4 | 4 | 6 | 3 | 3 |
| rules | 36 | 58 | 18 | 2 | 6 | 9 | 13 | 2 | 1 | 0 |

## Model–model agreement (verdict-level Cohen's κ on claims both processed; no gold needed)

| | anthropic__claude-haiku-5.5__agent | anthropic__claude-sonnet-5.5__agent | baidu__ernie-5.5-flash-preview_free | baidu__ernie-5.5-flash-preview_free__e2e | baidu__ernie-5.5-flash-preview_free__persentence | gemini__gemini-3.8-flash | gemini__gemini-3.8-flash__e2e | liquid__lfm-3-1.7b_free | nvidia__nemotron-3-ultra-550b-a55b_free | nvidia__nemotron-3-ultra-550b-a55b_free__e2e | regex | rules |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 1.00 | 0.81 | 0.55 | 0.56 | 1.00 | 0.72 | 0.53 | -0.11 | 0.60 | 0.58 | 0.10 | 0.21 |
| anthropic__claude-sonnet-5.5__agent | 0.81 | 1.00 | 0.42 | 0.48 | 1.00 | 0.57 | 0.35 | -0.11 | 0.50 | 0.49 | 0.10 | 0.20 |
| baidu__ernie-5.5-flash-preview_free | 0.55 | 0.42 | 1.00 | 0.90 | 1.00 | 0.76 | 0.65 | 0.16 | 0.68 | 0.65 | 0.10 | 0.21 |
| baidu__ernie-5.5-flash-preview_free__e2e | 0.56 | 0.48 | 0.90 | 1.00 | 1.00 | 0.90 | 0.86 | -0.15 | 0.67 | 0.75 | 0.09 | 0.22 |
| baidu__ernie-5.5-flash-preview_free__persentence | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.18 | 1.00 | 0.17 | 0.12 |
| gemini__gemini-3.8-flash | 0.72 | 0.57 | 0.76 | 0.90 | 1.00 | 1.00 | 0.91 | -0.11 | 0.74 | 0.79 | 0.12 | 0.23 |
| gemini__gemini-3.8-flash__e2e | 0.53 | 0.35 | 0.65 | 0.86 | 1.00 | 0.91 | 1.00 | -0.11 | 0.66 | 0.70 | 0.08 | 0.21 |
| liquid__lfm-3-1.7b_free | -0.11 | -0.11 | 0.16 | -0.15 | 1.00 | -0.11 | -0.11 | 1.00 | 0.27 | 0.00 | 0.11 | 0.09 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 0.60 | 0.50 | 0.68 | 0.67 | 0.18 | 0.74 | 0.66 | 0.27 | 1.00 | 0.68 | 0.14 | 0.28 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 0.58 | 0.49 | 0.65 | 0.75 | 1.00 | 0.79 | 0.70 | 0.00 | 0.68 | 1.00 | 0.11 | 0.22 |
| regex | 0.10 | 0.10 | 0.10 | 0.09 | 0.17 | 0.12 | 0.08 | 0.11 | 0.14 | 0.11 | 1.00 | 0.27 |
| rules | 0.21 | 0.20 | 0.21 | 0.22 | 0.12 | 0.23 | 0.21 | 0.09 | 0.28 | 0.22 | 0.27 | 1.00 |

## Human adjudication (7 hardest sentences: the annotator vs the systems' majority)

Exact-tuple agreement with the human decision (indicator, period, value).

| labeller | sentences matching the human decision |
|---|---|
| LLM annotator (Claude Opus, silver) | 2/7 |
| anthropic__claude-haiku-5.5__agent | 0/7 |
| anthropic__claude-sonnet-5.5__agent | 2/7 |
| baidu__ernie-5.5-flash-preview_free | 1/7 |
| baidu__ernie-5.5-flash-preview_free__e2e | 1/4 |
| gemini__gemini-3.8-flash | 1/7 |
| gemini__gemini-3.8-flash__e2e | 1/4 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 1/7 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 0/7 |
| regex | 1/7 |
| rules | 1/7 |

## Confusion matrices

### anthropic__claude-haiku-5.5__agent (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 83 | 0 | 5 | 0 |
| **MISMATCH** | 0 | 0 | 1 | 1 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

### anthropic__claude-sonnet-5.5__agent (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 85 | 0 | 3 | 0 |
| **MISMATCH** | 0 | 0 | 1 | 1 |
| **UNVERIFIABLE** | 1 | 0 | 3 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

### baidu__ernie-5.5-flash-preview_free (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 74 | 0 | 11 | 3 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 3 | 0 | 1 | 0 |

### baidu__ernie-5.5-flash-preview_free__e2e (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 64 | 0 | 7 | 1 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 2 | 0 |
| **NONE** | 1 | 0 | 1 | 0 |

### baidu__ernie-5.5-flash-preview_free__persentence (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 2 | 0 | 0 | 0 |
| **MISMATCH** | 0 | 0 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 0 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

### gemini__gemini-3.8-flash (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 78 | 0 | 9 | 1 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 0 | 0 | 1 | 0 |

### gemini__gemini-3.8-flash__e2e (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 71 | 0 | 5 | 2 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 2 | 1 |
| **NONE** | 0 | 0 | 1 | 0 |

### liquid__lfm-3-1.7b_free (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 11 | 0 | 0 | 2 |
| **MISMATCH** | 0 | 0 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 0 | 0 |
| **NONE** | 1 | 0 | 0 | 0 |

### nvidia__nemotron-3-ultra-550b-a55b_free (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 77 | 0 | 11 | 0 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 0 | 7 | 1 | 0 |

### nvidia__nemotron-3-ultra-550b-a55b_free__e2e (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 78 | 0 | 9 | 1 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 1 | 0 | 2 | 1 |
| **NONE** | 1 | 0 | 0 | 0 |

### regex (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 46 | 2 | 15 | 25 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 3 | 29 | 61 | 0 |

### rules (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 55 | 13 | 18 | 2 |
| **MISMATCH** | 0 | 1 | 1 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 1 | 41 | 65 | 0 |
