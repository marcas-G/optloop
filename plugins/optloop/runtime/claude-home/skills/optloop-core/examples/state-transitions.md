# State transition examples

Every Claude Code session may perform one or several transitions, then persist
`next_action` and exit.

Normal path:

- `uninitialized` -> `discovering`
- `discovering` -> `designing-benchmark`
- `designing-benchmark` -> `baselining`
- `baselining` -> `selecting-candidate`
- `selecting-candidate` -> `implementing-candidate`
- `implementing-candidate` -> `reviewing-candidate`
- `reviewing-candidate` -> `running-benchmark`
- `running-benchmark` -> `judging`
- `judging` -> `accepting` or `rejecting`
- `accepting` -> `committing`
- `committing` -> `baselining`
- `rejecting` -> `rolling-back`
- `rolling-back` -> `selecting-candidate`

Recovery path:

- any interrupted phase -> `recovering`
- `recovering` -> last useful phase
- unrepaired blocker -> `blocked`
- future work reads the blocker and resumes recovery

There is no terminal `done` phase.
