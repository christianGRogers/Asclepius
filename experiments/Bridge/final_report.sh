#!/bin/sh
# Final numbers for the notes: frozen v3 labeller on every cached case; split into dev (seen while developing) and held-out.
W=/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Bridge
E=/home/user/Asclepius/experiments/Bridge
python3 $E/evaluate.py $W/ex $W/ev_final.jsonl rerank_learned --ostw $W/ostium_w_dev2.json
python3 - <<PY
import json
dev=set(open('$W/devset3.txt').read().replace('\n','').split(','))
R=[json.loads(l) for l in open('$W/ev_final.jsonl')]
open('$W/ev_final_dev.jsonl','w').write(''.join(json.dumps(r)+'\n' for r in R if r['case'] in dev))
open('$W/ev_final_held.jsonl','w').write(''.join(json.dumps(r)+'\n' for r in R if r['case'] not in dev))
PY
python3 $E/summ2.py $W/ev_final_dev.jsonl $W/ev_final_held.jsonl $W/ev_final.jsonl
python3 $E/cohort.py $W/ex $W/ev_final.jsonl
