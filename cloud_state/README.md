# cloud_state

What the GitHub Actions watcher has learned, committed back after every run so
it is not starting from zero each time.

`check_memory.json` is the calibration memory. `learning_report.md` is the
readable version -- open that one.

Locally the same files live in `forward_test/`, which is gitignored. The
`CHECK_STATE_DIR` environment variable is what points the cloud run here
instead.
