## Permission-Wall Fuse (condensed load)

**Symptom identification**: messages silently vanish / cannot speak / no error logs → **access-control allowlist silent interception** (not idle_timeout, not a permission-wall crash). First diagnostic step: compare the actually effective access-control configuration (does allow_from / group_allow_from include the requester?).

**Fuse rules**:
- **≥{{fuse_threshold}} workers with consecutive permission errors → re-route to a DM private channel within ≤{{fuse_window_seconds}}s**; stop grinding into the wall
- single-worker permission error → report to leader (leader checks that worker's configuration)
- still failing after re-route → escalate to human (attach the configuration comparison evidence)

**Companion rule**: after a configuration change (allow_from/roster), verify it took effect (a test message that actually arrives counts); never assume.
