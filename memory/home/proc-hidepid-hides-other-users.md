---
name: proc-hidepid-hides-other-users
description: Since 2026-09-15 TT boxes mount /proc with hidepid=2, so ps/fuser only show your own processes — "device looks free" is no longer trustworthy
metadata:
  type: project
---

On 2026-09-15 ~20:16 UTC a `dev-sec` hardening baseline was applied to the shared TT
boxes and added `hidepid=2` to the `proc` line in `/etc/fstab` (mounts as
`hidepid=invisible`). The kernel now hides other users' `/proc/<pid>` entirely, so
`ps`, `top`, `fuser` and `pkill` see **only kmabee's own processes**. Fixing it needs
root; kmabee's sudo is limited to the five `tt_*` NOPASSWD scripts.

**Why:** this silently invalidates the "who holds the TT device" step in the global
CLAUDE.md working notes. `fuser -v /dev/tenstorrent/*` returning empty used to mean
"device is free"; it now only means "*I* am not holding it". Another user's
`VLLM::EngineCore` on that chip is invisible until the run fails to acquire it.

**How to apply:** when a TT device can't be acquired but `fuser` shows nothing, do NOT
conclude the chip is free — suspect an invisible other-user holder and say so rather
than chasing the failure in tt-xla/tt-metal. Same caveat for any cross-user process
hunt. The ask for whoever owns the hardening playbook is `hidepid=2,gid=slurmusers`
(the dev-sec role's supported escape hatch) or `hidepid=1`. Other files from the same
batch: `/etc/sysctl.d/90-dev-sec.conf`, `/etc/modprobe.d/dev-sec.conf`,
`/etc/security/limits.d/10.hardcore.conf`, `/etc/profile.d/tmout.sh`, `pam.d/common-*`.
It is config management, so a manual remount will be reverted.
