# Example: Path resolution failure

Symptom:
- benchmark or correctness commands fail because relative paths are resolved from the wrong directory.

Preferred fix:
- change the command wrapper so it runs from the intended repository root,
- or make the repository-local script resolve paths from `__file__` instead of the current shell directory.
