# AGENTS.md

## Project overview

Python 3.9+ picture frame for Turing Smart Screen USB displays. The application is the single
module `turing_smart_picture_frame.py` (launcher: `turing-smart-picture-frame.py`). `library/`
holds display communication code from the upstream turing-smart-screen-python project; `res/fonts/`
holds bundled fonts. Runtime threads: the main loop (the only thread that talks to the display),
the background rotation thread and, with `--auto-refresh`, the source refresh thread.

## Code Review Rules

Review adversarially: assume the change is wrong until the code shows otherwise. For every finding,
give a concrete failure scenario (input or state -> wrong behavior). Do not report style, naming or
formatting preferences.

### Correctness and concurrency (P1)
- ImageManager rotation state (discovered images, sample, queues, default background) has a single
  owner: the main thread until the rotation thread starts, then only the rotation thread. Other
  threads must not modify it; data crosses threads only through offer_scan()/pending_scan (single
  slot under pending_lock, refresh -> rotation), the image_list tuple (replaced, never modified;
  read by scan()), pending_transition under transition_lock (rotation -> main loop), current_background (main loop only) and wake_event, stop_event and the
  thread-safe OrientationCache. Flag any other cross-thread access, races, lost updates and
  check-then-act sequences across threads.
- Slow work (image decoding, resizing, directory scans, file I/O) must not run while holding a lock
  (OrientationCache's lock and pending_lock guard only their own data).
- Only the main loop may call display (lcd_comm) methods.
- Shutdown: every loop must exit promptly when stop_event is set; flag blocking calls without timeout.
- Timing: transitions must stay aligned to multiples of --interval from local midnight; flag drift,
  double transitions, skipped transitions, DST or wall clock change issues.
- Filesystem edge cases: missing, unreadable or partially written files, directories that disappear
  or fail during traversal, files replaced at the same path, empty directories.
- Exceptions must not be silently swallowed where the caller then acts on an empty or default result.

### Security (P1)
- Images are untrusted input: flag decoding without Pillow's decompression bomb protection, unbounded
  memory use, or trusting file names, sizes or metadata.
- Writes must stay inside the cache directory ($XDG_CACHE_HOME/tspf); flag path traversal, symlink
  following on writes, or writes to the current or images directory.
- No shell execution, eval/exec, pickle or network access added without clear need.
- No credentials, tokens or keys in code, docs, tests or commit content.

### Confidentiality (P1)
- Documentation, comments, docstrings, changelogs and examples must be generic product content.
  Flag real host names, IP addresses, internal domains, user names, personal e-mail addresses, home
  directory paths, mount points, deployment procedures or descriptions of specific installations.
  Placeholders (<host>, /path/to/images) and public URLs are fine.

### Consistency (P2)
- README.md, the module docstring, argparse help, the header changelog and __version__ must match
  the implemented behavior and defaults.
- Every new command line option appears in the README options table, the usage line and the
  startup configuration log.

### Out of scope
- `library/` and `res/fonts/` are upstream/vendored: review only lines changed in the pull request.
