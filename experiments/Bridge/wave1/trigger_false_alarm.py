"""How often does A31.1's pre-registered trigger (f or k > 1.2 in any class) fire when the truth is f = k = 1?
f = SD(model, pool, n patients) / SD(val, 80 cases); k = SD(inter, pool) / SD(model, pool). Normal per-case scores,
independent classes (conservative for 'any'), 20000 simulations. Usage: trigger_false_alarm.py"""
import json

import numpy as np

rng = np.random.default_rng(20261019)
SIMS, NVAL = 20000, 80
out = {}
for true in (1.0, 0.8):
    for n in (20, 30, 50, 75, 100, 150):
        any_ = np.zeros(SIMS, bool)
        for _ in range(4):
            val = rng.normal(0, 1, (SIMS, NVAL)).std(1, ddof=1)
            mod = rng.normal(0, true, (SIMS, n)).std(1, ddof=1)
            inter = rng.normal(0, true, (SIMS, n)).std(1, ddof=1)
            # true f = true, true k = 1 (inter and model share the same SD): the k trigger is pure noise
            any_ |= (mod / val > 1.2) | (inter / mod > 1.2)
        out[f'true_f{true}_n{n}'] = round(float(any_.mean()), 3)
print(json.dumps(out, indent=1))
