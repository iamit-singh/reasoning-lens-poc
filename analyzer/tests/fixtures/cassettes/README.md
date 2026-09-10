# Cassettes — recorded provider responses for `MOCK_LLM=1`

`MOCK_LLM=1` is the default in every PR job, so these are what CI actually runs against.
Recorded from a real run of the pinned model with
`python -m rlens.runner --record-cassettes`.

**Scope: `probe-01` only, arms 1–2.** M1-6 needs exactly enough replay for
`test_span_contract.py` to exercise the real emission path — a DoD of "spans pass the
span contract" cannot be met by a test that needs a GPU. **The full bank × arms recording
job is M1-14 (W4)**, and it is also the frontend's W5 unblock (E11).

**Re-record on any pin change.** A cassette recorded against different weights, a
different quantization or different sampling settings is a recording of a different
experiment. The pin the current set was recorded against is asserted in
`test_span_contract.py::TEST_PIN`, so a mismatch fails rather than passing quietly.
