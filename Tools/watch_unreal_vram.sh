#!/bin/sh
# Stop the Unreal editor before a GPU-memory stall can lock up the computer.
#
# Run on the host from the project folder, just before Tools/rebuild_physis.py:
#     sh Tools/watch_unreal_vram.sh
# Stop it with Ctrl-C when the rebuild has finished.
#
# Trips on any of:
#   - MAX_ERRORS new Vulkan allocation failures. A good build logged about 3,200;
#     the build that froze the laptop logged about 4,900 within a minute.
#   - MAX_SECONDS elapsed. A good build takes under two minutes.
#   - VRAM within FREE_MIB of full for FULL_CHECKS checks in a row.
# A kill can leave /Game/MetaHumans half written, but that folder is rebuilt from
# MH_Physis and the outfit, which are saved before assembly starts.
LOG=Saved/Logs/Physis.log
REPORT=Saved/Logs/vram-watchdog.log
EDITOR=UnrealEditor
MAX_ERRORS=4000
MAX_SECONDS=600
FREE_MIB=120
FULL_CHECKS=15
INTERVAL=2

errors() { grep -c 'Failed to allocate Device Memory' "$LOG"; }
say() { echo "$(date +%H:%M:%S) $*" | tee -a "$REPORT"; }

if ! pgrep -x "$EDITOR" >/dev/null; then
    echo 'The Physis editor is not running.'
    exit 1
fi
base=$(errors)
start=$(date +%s)
full=0
say "watching from $base logged errors"
while pgrep -x "$EDITOR" >/dev/null; do
    sleep "$INTERVAL"
    new=$(($(errors) - base))
    elapsed=$(($(date +%s) - start))
    free=$(flatpak-spawn --host nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1)
    if [ -n "$free" ] && [ "$free" -lt "$FREE_MIB" ]; then full=$((full + 1)); else full=0; fi
    reason=
    [ "$new" -ge "$MAX_ERRORS" ] && reason="$new GPU allocation errors"
    [ "$elapsed" -ge "$MAX_SECONDS" ] && reason="time limit of $MAX_SECONDS s"
    [ "$full" -ge "$FULL_CHECKS" ] && reason="VRAM full for $full checks"
    if [ -n "$reason" ]; then
        say "TRIPPED: $reason. Stopping the editor."
        pkill -TERM -x "$EDITOR"
        sleep 5
        pkill -KILL -x "$EDITOR"
        exit 2
    fi
    [ $((elapsed % 30)) -lt "$INTERVAL" ] && say "ok: ${elapsed}s, $new errors, ${free:-unknown} MiB free"
done
say 'editor exited'
