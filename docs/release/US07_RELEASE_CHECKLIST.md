# US-07 Release Readiness Checklist

**Verified application baseline:** `754d03c6d86927e490438ff7286c76f8258a2a12`

**Status:** Verification completed and team agreement confirmed by Ronit on 17 November 2026. Application scope is frozen. This final documentation PR remains subject to normal review, merge and main CI.

## Acceptance Criteria

- [x] Documentation reflects the agreed project scope and implemented functionality.
- [x] Setup and execution instructions are documented in the project README.
- [x] Database schema and application architecture are documented.
- [x] Known limitations and unresolved release items are documented.
- [x] Sprint 2 video evidence is present at [`docs/demo/sprint2-demo.mp4`](../demo/sprint2-demo.mp4).
- [x] Final integrated verification is complete.
- [x] Team approval of the release baseline is complete.
- [x] Final release freeze is complete.
- [x] Final team sign-off is complete.

## Current Verification

The historical CI evidence from the earlier tested commit `8ed347410b784dd9c3328ee5151d0bb4dadc2e58` was **409 passed, 1 skipped**. It is not verification of the current PR head.

- Sprint 1 demo evidence: [`docs/demo/sprint1-demo.mp4`](../demo/sprint1-demo.mp4)
- Sprint 2 demo evidence: [`docs/demo/sprint2-demo.mp4`](../demo/sprint2-demo.mp4), 270.90 seconds (4 minutes 31 seconds)
- Final integrated verification: completed; see [verification record](FINAL_VERIFICATION_2026-11-17.md)
- Application scope freeze: 17 November 2026, at the verified baseline
- Team approval of the release baseline: confirmed by Ronit on 17 November 2026
- Team sign-off: confirmed by Ronit; acceptance limitations remain documented

## Release Scope

The submission documentation covers the implemented bank-management functionality and the documented security, schema, architecture, setup, testing and known limitations.

After this final documentation PR merges and main CI passes, close issue #36
as Completed with links to PR #84 and this verification update. Remaining SRS
verification limitations are retained in the deviations log; team agreement
does not establish an assessor waiver or passing results for those criteria.
