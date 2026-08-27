# Eval comparison

- Before: `baseline-rescored` prompts {'outline_system': 'f781327362eb', 'lesson_system': 'd1a215d4d567', 'outline_system_chars': 432, 'lesson_system_chars': 634}
- After: `fixed` prompts {'outline_system': '1f4a89050a37', 'lesson_system': 'f575bed1be67', 'outline_system_chars': 856, 'lesson_system_chars': 1433}

## pep8-url

| Metric | Before | After | Delta |
|---|---|---|---|
| Lessons | 0 | 13 | 13 |
| Quiz items | 0 | 78 | 78 |
| Structure problems | 0 | 10 | 10 |
| Strict JSON first try | 1 | 1 | 0 |
| Hard parse failures | 1 | 0 | -1 |
| Grounded, all items (old metric) | 0 | 0.2692 | 0.2692 |
| Grounded, extractive items only | 0 | 0.2857 | 0.2857 |
| Ungrounded items, all | 0 | 17 | 17 |
| Ungrounded extractive items | 0 | 14 | 14 |
| Hallucination candidates | 0 | 0 | 0 |
| Mean grounding recall | 0 | 0.6524 | 0.6524 |
| Answerable from lesson | 0 | 0.4487 | 0.4487 |
| Unanswerable items | 0 | 6 | 6 |
| Giveaway MCQs | 0 | 6 | 6 |
| Source chunks covered | 0 | 1 | 1 |
| Largest single-chunk share (old metric) | 0 | 0.2157 | 0.2157 |
| Concentration vs chunk length | 0 | 1.6511 | 1.6511 |
| Source recall, mean chunk | 0 | 0.7908 | 0.7908 |
| Source recall, worst chunk | 0 | 0.7045 | 0.7045 |
| Cost USD | 0.3282 | 1.587 | 1.2588 |
| Wall clock s | 68.09 | 583.58 | 515.49 |

## prose-text

| Metric | Before | After | Delta |
|---|---|---|---|
| Lessons | 12 | 6 | -6 |
| Quiz items | 72 | 34 | -38 |
| Structure problems | 0 | 0 | 0 |
| Strict JSON first try | 1 | 0.8571 | -0.1429 |
| Hard parse failures | 0 | 0 | 0 |
| Grounded, all items (old metric) | 0.3889 | 0.0882 | -0.3007 |
| Grounded, extractive items only | 0.4828 | 0.1034 | -0.3793 |
| Ungrounded items, all | 25 | 19 | -6 |
| Ungrounded extractive items | 13 | 15 | 2 |
| Hallucination candidates | 5 | 1 | -4 |
| Mean grounding recall | 0.6275 | 0.4885 | -0.139 |
| Answerable from lesson | 0.4306 | 0.1176 | -0.3129 |
| Unanswerable items | 8 | 13 | 5 |
| Giveaway MCQs | 7 | 1 | -6 |
| Source chunks covered | 1 | 1 | 0 |
| Largest single-chunk share (old metric) | 0.9167 | 0.7143 | -0.2024 |
| Concentration vs chunk length | 1.2499 | 1.0716 | -0.1783 |
| Source recall, mean chunk | 0.9666 | 0.9453 | -0.0213 |
| Source recall, worst chunk | 0.9643 | 0.8906 | -0.0737 |
| Cost USD | 1.4182 | 0.7972 | -0.621 |
| Wall clock s | 615.85 | 372.52 | -243.33 |
