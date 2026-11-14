#!/bin/sh
# Keeps parallel Blender jobs from exhausting RAM: pauses the newest job when memory is
# low and resumes the oldest paused job when it recovers. Always leaves one job running.
# A job is a batch Blender (blender -b) and its worker processes, which are signalled
# together. An open Blender window is never touched and never counts.
LOW_KB=${1:-3000000}
HIGH_KB=${2:-5000000}

table() {
    ps -eo pid=,ppid=,stat=,etimes=,args= | awk '$5 == "./blender" && $6 == "-b" {print $1, $2, $3, $4}'
}

jobs_in() {
    # Prints "age pid" for top-level jobs whose stopped state matches $1 (T or R).
    printf '%s\n' "$2" | awk -v want="$1" '
        NF { line[NR] = $0; blender[$1] = 1 }
        END {
            for (i in line) {
                split(line[i], f, " ")
                if (f[2] in blender) continue
                stopped = (f[3] ~ /^T/)
                if ((want == "T") == stopped) print f[4], f[1]
            }
        }'
}

send() {
    kill "-$1" "$2" $(pgrep -P "$2" 2>/dev/null) 2>/dev/null
}

while :; do
    all=$(table)
    # A worker left stopped under a running parent would stall its job forever.
    printf '%s\n' "$all" | awk '
        NF { state[$1] = $3; parent[$1] = $2 }
        END { for (p in state) if (state[p] ~ /^T/ && parent[p] in state && state[parent[p]] !~ /^T/) print p }' |
        while read -r worker; do kill -CONT "$worker"; done
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    running=$(jobs_in R "$all" | sort -n)
    paused=$(jobs_in T "$all" | sort -nr)
    count=$(printf '%s\n' "$running" | grep -c .)
    if [ "$avail" -lt "$LOW_KB" ] && [ "$count" -gt 1 ]; then
        send STOP "$(printf '%s\n' "$running" | head -1 | cut -d' ' -f2)"
    elif [ -n "$paused" ] && { [ "$avail" -gt "$HIGH_KB" ] || [ "$count" -eq 0 ]; }; then
        send CONT "$(printf '%s\n' "$paused" | head -1 | cut -d' ' -f2)"
    fi
    sleep 4
done
