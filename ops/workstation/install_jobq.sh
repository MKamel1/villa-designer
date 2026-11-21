#!/usr/bin/env bash
# Install or update the jobq runner on the workstation (idempotent). Run ON the workstation from a checkout:
#   bash ops/workstation/install_jobq.sh
# or from the laptop:  python scripts/workstation.py install-runner
# Needs `loginctl enable-linger omar` (already on) so the user service starts at boot without a login.
set -eu
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p ~/archpipe/bin ~/archpipe/queue/jobs ~/archpipe/locks ~/.config/systemd/user
install -m 755 "$HERE/jobq.py" ~/archpipe/bin/jobq.new && mv -f ~/archpipe/bin/jobq.new ~/archpipe/bin/jobq
install -m 644 "$HERE/systemd/jobq.service" ~/.config/systemd/user/jobq.service
systemctl --user daemon-reload
systemctl --user enable jobq.service
systemctl --user restart jobq.service
sleep 1
systemctl --user is-active jobq.service
