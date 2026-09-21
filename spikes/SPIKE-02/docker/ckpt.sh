#!/usr/bin/env bash
# Inside a privileged container: start a warm `import Mathlib` Lean process under runsc, checkpoint
# it, restore it, and time each step. usage: ckpt.sh <overlay2 flag value>
set -uo pipefail
OV=${1:-none}
R="runsc --platform=${PLATFORM:-systrap} --network=none --ignore-cgroups --host-uds=none --overlay2=$OV --root /tmp/runsc-root"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
B=/tmp/bundle; I=/tmp/ckpt; rm -rf $B $I; mkdir -p $B $I; rm -f /mnt/hb
cd $B && runsc spec --cwd /work/project -- bash -c 'exec lake env lean --run /work/fixtures/warm.lean' 
jq '.root.path="/" | .root.readonly=false | .process.terminal=false
    | .process.env += ["PATH=/opt/elan/bin:/usr/local/bin:/usr/bin:/bin","ELAN_HOME=/opt/elan","HOME=/root","GIT_CONFIG_COUNT=1","GIT_CONFIG_KEY_0=safe.directory","GIT_CONFIG_VALUE_0=*"]
    | .mounts += [{"destination":"/work/project","type":"bind","source":"/work/project","options":["rbind","rw"]},
                  {"destination":"/work/fixtures","type":"bind","source":"/work/fixtures","options":["rbind","ro"]}]' config.json > c2 && mv c2 config.json
now() { date +%s.%N; }
t0=$(now)
$R run -detach --bundle $B warm1 > /tmp/run1.log 2>&1 < /dev/null
for i in $(seq 600); do [ -s /mnt/hb ] && break; sleep 0.1; done
[ -s /mnt/hb ] || { echo "NO HEARTBEAT after 60 s"; cat /tmp/run1.log | head; $R list; $R state warm1 | head -6; exit 1; }
t1=$(now); echo "cold start to first heartbeat (import Mathlib loaded): $(python3 -c "print(round($t1-$t0,2))") s"
sleep 2; echo "heartbeats before checkpoint: $(wc -l < /mnt/hb)"
t2=$(now); $R checkpoint --image-path=$I warm1 2>&1 | tail -3; rc=$?; t3=$(now)
echo "checkpoint wall: $(python3 -c "print(round($t3-$t2,2))") s; image: $(du -sm $I | cut -f1) MB; files: $(ls $I | tr '\n' ' ')"
$R delete -f warm1 >/dev/null 2>&1
n0=$(wc -l < /mnt/hb); t4=$(now)
$R restore -detach --image-path=$I --bundle $B warm2 > /tmp/restore.log 2>&1 < /dev/null
for i in $(seq 3000); do [ "$(wc -l < /mnt/hb)" -gt "$n0" ] && break; sleep 0.02; done
[ "$(wc -l < /mnt/hb)" -gt "$n0" ] || { echo "NO HEARTBEAT after restore"; head /tmp/restore.log; exit 1; }
t5=$(now); echo "restore to next heartbeat: $(python3 -c "print(round($t5-$t4,2))") s"
tail -3 /mnt/hb | tr '\n' ' '; echo "(counter continues from $n0 => process state preserved)"
head -5 /tmp/restore.log
$R delete -f warm2 >/dev/null 2>&1
