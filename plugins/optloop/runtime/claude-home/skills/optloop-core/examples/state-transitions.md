# State transition examples

Normal path:
- `uninitialized` -> `discovering`
- `discovering` -> `building-benchmark`
- `building-benchmark` -> `baselining`
- `baselining` -> `selecting-candidate`
- `selecting-candidate` -> `implementing-candidate`
- `implementing-candidate` -> `running-correctness`
- `running-correctness` -> `running-benchmark`
- `running-benchmark` -> `judging`
- `judging` -> `accepting` or `rejecting`
- `accepting` -> `baselining`
- `rejecting` -> `selecting-candidate`

Recovery path:
- any interrupted phase -> `recovering`
- `recovering` -> last safe phase, usually `selecting-candidate` or `baselining`
