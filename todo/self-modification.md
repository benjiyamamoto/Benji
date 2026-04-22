# Self-Modification

## Goal
Allow Benji to improve its own non-core source code autonomously, while keeping a human in the loop for restarts and protecting the files whose failure would prevent recovery.

## Protected core (read-only for Benji)
If any of these break on startup, Benji goes silent and cannot self-heal:
- `benji/main.py`
- `benji/scheduler.py`
- `benji/imessage.py`
- `benji/claude.py` — if this breaks, Benji can't call Claude to fix itself
- `benji/config.py`
- `benji/logger.py`

When Benji wants to change a core file, it creates a `todo/` file describing the change and notifies via iMessage instead.

## Writable (Benji can self-modify)
- `benji/ollama.py`
- `benji/run_log.py`
- `benji/tasks/`
- `benji/skills/`
- Any new module it creates

These fail gracefully — a broken task shows `FAILURE` in the run log, the scheduler keeps running.

## Flow
1. Benji identifies an improvement to make
2. Checks if any target file is in the protected core
   - If yes → create a `todo/` file, notify via iMessage, stop
   - If no → proceed
3. `git commit` current state with a message describing what's about to change (rollback point)
4. Make the change
5. Run `mypy benji/` and `ast.parse()` on any modified files — abort and `git revert` if either fails
6. Send an iMessage: "I've updated [what] — can you restart me when you're ready? Here's what changed: [summary]"
7. Wait. Do not restart itself.
8. On next startup, the change is live. If something goes wrong, `git revert` + restart restores the previous state.

## Why notify-and-wait instead of auto-restart
A bad self-modification could crash Benji on startup. If it restarted itself immediately, there'd be nobody around to notice or recover it. By asking first, the user can choose a moment when they're available to bring it back up if needed.

## Open questions
- Should the iMessage include a diff, or just a plain-language summary from Gemma4?
- If Benji queues multiple self-modifications, should it batch them into one restart request or notify per change?
- Should there be a cooldown (e.g., no more than one self-modification per day) to prevent runaway changes?
