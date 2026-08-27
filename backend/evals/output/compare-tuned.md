# Eval comparison

- Before: `baseline-rescored` prompts {'outline_system': 'f781327362eb', 'lesson_system': 'd1a215d4d567', 'outline_system_chars': 432, 'lesson_system_chars': 634}
- After: `tuned` prompts {'outline_system': '51268cb63391', 'lesson_system': 'f575bed1be67', 'outline_system_chars': 850, 'lesson_system_chars': 1433}

## prose-text

| Metric | Before | After | Delta |
|---|---|---|---|
| Lessons | 12 | 10 | -2 |
| Quiz items | 72 | 60 | -12 |
| Structure problems | 0 | 6 | 6 |
| Strict JSON first try | 1 | 0.9167 | -0.0833 |
| Hard parse failures | 0 | 1 | 1 |
| Grounded, all items (old metric) | 0.3889 | 0.1833 | -0.2056 |
| Grounded, extractive items only | 0.4828 | 0.22 | -0.2628 |
| Ungrounded items, all | 25 | 23 | -2 |
| Ungrounded extractive items | 13 | 17 | 4 |
| Hallucination candidates | 5 | 5 | 0 |
| Mean grounding recall | 0.6275 | 0.5315 | -0.096 |
| Answerable from lesson | 0.4306 | 0.3 | -0.1306 |
| Unanswerable items | 8 | 13 | 5 |
| Giveaway MCQs | 7 | 1 | -6 |
| Source chunks covered | 1 | 1 | 0 |
| Largest single-chunk share (old metric) | 0.9167 | 0.7917 | -0.125 |
| Concentration vs chunk length | 1.2499 | 1.0795 | -0.1704 |
| Source recall, mean chunk | 0.9666 | 0.9487 | -0.0179 |
| Source recall, worst chunk | 0.9643 | 0.9286 | -0.0357 |
| Cost USD | 1.4182 | 1.4154 | -0.0029 |
| Wall clock s | 615.85 | 666.49 | 50.64 |
