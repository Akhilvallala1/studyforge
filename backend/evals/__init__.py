"""StudyForge course-generation evaluation harness.

Plain Python, no eval framework, no dependencies beyond what the backend already
uses. The metric functions are pure and unit-tested from the normal pytest suite
(`tests/test_evals.py`); only `run_eval.py` ever touches a real LLM, and it is
run explicitly by a human, never from pytest.
"""
