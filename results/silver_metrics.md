# Metrics — reference labels: silver (blind Claude Opus annotator, not human-verified)

> **Provisional.** These labels come from a blind LLM annotator (Claude Opus), not a person. Use them for coverage only; the human-gold report is `results/metrics.md`.

Labels: 164 checked sentences (2 duplicate sentences dropped), 75 with ≥1 in-scope claim, 94 claim tuples. Reference table: 104 rows; variant table: 83 rows. CIs: 95% bootstrap over sentences (2,000 resamples).

## Headline (silver (blind Claude Opus annotator, not human-verified))

- Bindable rate (claim resolves to a BPS figure): **87/94 = 92.6%** [86.9%, 97.6%]
- Mismatch rate among bindable: **1/87 = 1.1%** [0.0%, 3.8%]
- Unverifiable: 7
- Of 1 MISMATCHes, **right number, wrong frame** (claim equals another published variant of the same release): none; wrong number: 1

| indicator | MATCH | MISMATCH | UNVERIFIABLE |
|---|---|---|---|
| inflation_yoy | 24 | 0 | 0 |
| unemployment_rate | 15 | 0 | 5 |
| poverty_rate | 18 | 1 | 2 |
| gdp_growth_yoy | 29 | 0 | 0 |

### By speaker_type

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| bps_official | 51 | 32 | 30/32 = 94% | 0/30 = 0% |
| dpr_or_politician | 1 | 1 | 1/1 = 100% | 0/1 = 0% |
| government_official | 70 | 42 | 39/42 = 93% | 0/39 = 0% |
| journalist_or_other | 42 | 19 | 17/19 = 89% | 1/17 = 6% |

### By source

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| government (.go.id) | 25 | 11 | 11/11 = 100% | 0/11 = 0% |
| news media | 139 | 83 | 76/83 = 92% | 1/76 = 1% |

### By attributes BPS in sentence

| group | sentences | tuples | bindable | mismatch among bindable |
|---|---|---|---|---|
| no | 131 | 64 | 59/64 = 92% | 0/59 = 0% |
| yes | 33 | 30 | 28/30 = 93% | 1/28 = 4% |

## Systems vs gold

`__e2e` = the LLM gave the verdict itself with the BPS table in its prompt (ablation); every other row: LLM/rules extract, deterministic lookup decides. Systems that did not process every gold sentence are scored on the ones they did (see 'scored').

| system | scored | extract P | extract R | extract F1 | verdict acc | verdict macro-F1 [95% CI] | false MISMATCH | missed MISMATCH | values not in sentence |
|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 164/164 | 1.00 | 0.99 | 0.99 | 0.96 | 0.60 [0.53, 0.67] | 0 | 1 | 0 |
| anthropic__claude-sonnet-5.5__agent | 164/164 | 1.00 | 0.99 | 0.99 | 0.99 | 0.67 [0.67, 0.67] | 0 | 1 | 0 |
| baidu__ernie-5.5-flash-preview_free | 164/164 | 0.96 | 0.97 | 0.96 | 0.84 | 0.83 [0.42, 0.91] | 0 | 0 | 2 |
| baidu__ernie-5.5-flash-preview_free__e2e | 124/164 | 0.97 | 0.99 | 0.98 | 0.90 | 0.84 [0.40, 0.96] | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free__persentence | 10/164 | 1.00 | 1.00 | 1.00 | 1.00 | 0.33 [0.00, 0.33] | 0 | 0 | 0 |
| liquid__lfm-3-1.7b_free | 38/164 | 0.92 | 0.85 | 0.88 | 0.79 | 0.29 [0.24, 0.33] | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 164/164 | 0.92 | 1.00 | 0.96 | 0.83 | 0.58 [0.43, 0.82] | 7 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 164/164 | 0.99 | 0.98 | 0.98 | 0.89 | 0.83 [0.41, 0.91] | 0 | 0 | 0 |
| regex | 164/164 | 0.43 | 0.73 | 0.54 | 0.29 | 0.30 [0.24, 0.36] | 31 | 0 | 0 |
| rules | 164/164 | 0.46 | 0.98 | 0.63 | 0.31 | 0.32 [0.27, 0.37] | 54 | 0 | 0 |

## Error taxonomy (one cause per disagreement with gold)

| system | wrong period | other out-of-scope figure | target / projection | missed claim | core / component inflation | mtm read as y-on-y | wrong value | regional figure | q-to-q / c-to-c read as y-on-y | ytd read as y-on-y |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 12 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| anthropic__claude-sonnet-5.5__agent | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free | 16 | 2 | 1 | 3 | 0 | 0 | 0 | 0 | 1 | 0 |
| baidu__ernie-5.5-flash-preview_free__e2e | 8 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| baidu__ernie-5.5-flash-preview_free__persentence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| liquid__lfm-3-1.7b_free | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 14 | 3 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 10 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| regex | 19 | 43 | 15 | 19 | 15 | 4 | 4 | 6 | 3 | 3 |
| rules | 33 | 58 | 18 | 2 | 6 | 9 | 13 | 2 | 1 | 0 |

## Model–model agreement (verdict-level Cohen's κ on claims both processed; no gold needed)

| | anthropic__claude-haiku-5.5__agent | anthropic__claude-sonnet-5.5__agent | baidu__ernie-5.5-flash-preview_free | baidu__ernie-5.5-flash-preview_free__e2e | baidu__ernie-5.5-flash-preview_free__persentence | liquid__lfm-3-1.7b_free | nvidia__nemotron-3-ultra-550b-a55b_free | nvidia__nemotron-3-ultra-550b-a55b_free__e2e | regex | rules |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic__claude-haiku-5.5__agent | 1.00 | 0.81 | 0.55 | 0.56 | 1.00 | -0.11 | 0.60 | 0.58 | 0.10 | 0.21 |
| anthropic__claude-sonnet-5.5__agent | 0.81 | 1.00 | 0.42 | 0.48 | 1.00 | -0.11 | 0.50 | 0.49 | 0.10 | 0.20 |
| baidu__ernie-5.5-flash-preview_free | 0.55 | 0.42 | 1.00 | 0.90 | 1.00 | 0.16 | 0.68 | 0.65 | 0.10 | 0.21 |
| baidu__ernie-5.5-flash-preview_free__e2e | 0.56 | 0.48 | 0.90 | 1.00 | 1.00 | -0.15 | 0.67 | 0.75 | 0.09 | 0.22 |
| baidu__ernie-5.5-flash-preview_free__persentence | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.18 | 1.00 | 0.17 | 0.12 |
| liquid__lfm-3-1.7b_free | -0.11 | -0.11 | 0.16 | -0.15 | 1.00 | 1.00 | 0.27 | 0.00 | 0.11 | 0.09 |
| nvidia__nemotron-3-ultra-550b-a55b_free | 0.60 | 0.50 | 0.68 | 0.67 | 0.18 | 0.27 | 1.00 | 0.68 | 0.14 | 0.28 |
| nvidia__nemotron-3-ultra-550b-a55b_free__e2e | 0.58 | 0.49 | 0.65 | 0.75 | 1.00 | 0.00 | 0.68 | 1.00 | 0.11 | 0.22 |
| regex | 0.10 | 0.10 | 0.10 | 0.09 | 0.17 | 0.11 | 0.14 | 0.11 | 1.00 | 0.27 |
| rules | 0.21 | 0.20 | 0.21 | 0.22 | 0.12 | 0.09 | 0.28 | 0.22 | 0.27 | 1.00 |

## Confusion matrices

### anthropic__claude-haiku-5.5__agent (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 83 | 0 | 3 | 0 |
| **MISMATCH** | 0 | 0 | 0 | 1 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

### anthropic__claude-sonnet-5.5__agent (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 86 | 0 | 0 | 0 |
| **MISMATCH** | 0 | 0 | 0 | 1 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

### baidu__ernie-5.5-flash-preview_free (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 74 | 0 | 9 | 3 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 3 | 0 | 1 | 0 |

### baidu__ernie-5.5-flash-preview_free__e2e (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 64 | 0 | 5 | 1 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 4 | 0 |
| **NONE** | 1 | 0 | 1 | 0 |

### baidu__ernie-5.5-flash-preview_free__persentence (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 2 | 0 | 0 | 0 |
| **MISMATCH** | 0 | 0 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 0 | 0 |
| **NONE** | 0 | 0 | 0 | 0 |

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
| **MATCH** | 77 | 0 | 9 | 0 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 0 | 7 | 1 | 0 |

### nvidia__nemotron-3-ultra-550b-a55b_free__e2e (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 79 | 0 | 7 | 0 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 5 | 2 |
| **NONE** | 1 | 0 | 0 | 0 |

### regex (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 46 | 2 | 13 | 25 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 3 | 29 | 61 | 0 |

### rules (rows = gold, cols = system)

| | MATCH | MISMATCH | UNVERIFIABLE | NONE |
|---|---|---|---|---|
| **MATCH** | 55 | 13 | 16 | 2 |
| **MISMATCH** | 0 | 1 | 0 | 0 |
| **UNVERIFIABLE** | 0 | 0 | 7 | 0 |
| **NONE** | 1 | 41 | 65 | 0 |
