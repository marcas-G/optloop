# Example: Python import failure

Symptom:
- `ModuleNotFoundError` when running the benchmark command.

Preferred fix order:
1. use the documented project launcher such as `python -m package.module`;
2. run from the repository root if imports assume package-relative execution;
3. add the missing dependency only if the project already declares it;
4. patch the repository's broken import only when the project code is plainly wrong.
