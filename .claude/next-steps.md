# Next Steps

## Current Status
- **Phase 1:** Documentation and analysis ✓ COMPLETE
- **Phase 2:** Import tooling ✓ COMPLETE
- **Phase 3:** Full import ✓ COMPLETE — all 38 UBL 2.x releases on `main`, tags pushed
- **Ongoing:** Keep the repository up to date with new OASIS releases

---

## Adding New Releases

Check https://docs.oasis-open.org/ubl/ for new `<stage>-UBL-<version>/` directories,
then follow `tools/README.md` → "Adding a New Release":

1. Add the release to `tools/release_data.py` (tooling commit)
2. `python3 -m tools.import_release <num>` (release commit + tags)
3. Push the branch and the new tags
4. Update the docs (separate commit)

---

## Open Items (not blockers)

### Test infrastructure issues
- `negative_test.sh`: 6 of 21 tests fail (patch tests use wrong release numbering;
  validators import the real `release_data.py`, not the test releases)
- `test_granular_import.py`: 1 of 10 tests fails
  (`validate_repo_matches_release()` called without its `release` argument)

### Root README.md
- `import_release.update_readme()` only updates a README with "Latest Release" /
  "Release History" sections; the current root README has neither, so it is
  never changed by imports

### History with rename tracking
- `tools/granular_import.py` / `replay_history_with_renames.py` can rebuild the history
  on a separate branch with `git mv` renames (see `replay-history-guide.md`); not run yet

See `.claude/deferred-items.md` for future enhancements.
