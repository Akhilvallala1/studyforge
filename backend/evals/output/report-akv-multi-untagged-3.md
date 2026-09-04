# StudyForge generation eval

## Headline metrics

| Metric | multi-darwin-pep8 |
|---|---|
| Lessons | 0 |
| Quiz items | 0 |
| Structure problems | 0 |
| Strict JSON first try | 0.5 |
| Hard parse failures | 1 |
| Grounded, all items (old metric) | 0 |
| Grounded, extractive items only | 0 |
| Ungrounded items, all | 0 |
| Ungrounded extractive items | 0 |
| Hallucination candidates | 0 |
| Mean grounding recall | 0 |
| Answerable from lesson | 0 |
| Unanswerable items | 0 |
| Giveaway MCQs | 0 |
| Source chunks covered | 0 |
| Largest single-chunk share (old metric) | 0 |
| Concentration vs chunk length | 0 |
| Source recall, mean chunk | 0 |
| Source recall, worst chunk | 0 |
| Cost USD | 0.0663 |
| Wall clock s | 26.14 |

## multi-darwin-pep8

**Generation failed:** `APIStatusError: {'type': 'error', 'error': {'details': None, 'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011CegasQtDthcaheLbshpDs'}`

Source: text `darwin-origin + pep8-style-guide`, 13,639 chars, 3 chunks

### Parse reliability

| Stage | Calls | Strict JSON | Fence strip | Prose trim | Parsed | Schema ok | Failures |
|---|---|---|---|---|---|---|---|
| lesson | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| outline | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

### Cost and latency by stage

| Stage | Calls | In tokens | Out tokens | Cost | Mean s | Max s |
|---|---|---|---|---|---|---|
| lesson | 1 | 0 | 0 | $0.0000 | 3.4 | 3.4 |
| outline | 1 | 4,934 | 1,664 | $0.0663 | 22.7 | 22.7 |
