---
name: slurm-epilog-wipes-tmp
description: On TT SLURM nodes, the Epilog deletes all top-level /tmp entries owned by the job's UID at job completion, killing tmux sockets.
metadata:
  type: project
---

On the TT exabox SLURM compute nodes (e.g. bh-glx-110-a10u08), `slurm.conf` sets
`Epilog=/usr/local/bin/tt_slurm_tmp_epilog.sh`, whose operative line is:

    find /tmp -mindepth 1 -maxdepth 1 -uid "$SLURM_JOB_UID" -exec rm -rf -- {} +

So **every time any of kmabee's SLURM jobs on the node completes**, root deletes
`/tmp/tmux-4140`, `/tmp/ssh-XXXXXX`, `/tmp/claude-4140`, and `/tmp/ttnn`. Orphaned tmux
servers keep running but are unreachable — tmux has no reattach-by-PID, and the socket path
is fixed at server start, so recovery is impossible. **Confirmed empirically 2026-08-20**: kmabee ran `scancel` on the allocation and the /tmp
entries were deleted and the tmux session became unreattachable on demand. Full writeup in
`~/tmux_socket_incident_2026-08-19.md`. Trigger is *job completion* — a deliberate `scancel` or
any short `srun` finishing does it, not just a timeout.

**Why:** the script's own SAFETY comment falsely claims `tmux-*` and ssh-agent sockets are
excluded — they are only safe when owned by *another* user, and there is no `-name` filter.

**How to apply:** always start long-lived tmux off `/tmp` — `tmux -S ~/.tmux-kmabee.sock`.
Do NOT diagnose this class of loss as a `/tmp` cleaner: `/usr/lib/tmpfiles.d/tmp.conf` has
`D /tmp 1777 root root -` (age `-` = aging disabled), no tmpreaper/tmpwatch, no cron on /tmp;
Aug-4 files survive 16+ days. Also not the NOPASSWD `tt_*` scripts — none reference `/tmp`.
`journalctl -t tt_slurm_tmp_epilog` holds the audit trail but needs `adm`/`systemd-journal`,
which kmabee lacks.
