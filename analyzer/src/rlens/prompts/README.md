# Prompt bundle

Every `*.md` in this directory is part of `PROMPT_BUNDLE_VERSION`, which is a content
hash over the bundle (`rlens.versions`). Editing any prompt changes the version, which
invalidates the cache (C2.3) and triggers the `calibrate --dev` CI job (C7.2).

Skeletons for the classifier, triage and escalation prompts are in
[Appendix A](../../../../docs/decisions/) of the implementation plan; they land with
M1-9 and M2-5. This README is intentionally *not* named `*.md`-excluded: it is part of
the bundle hash, so the bundle version is stable and non-empty from Week 1.
