"""Fixed CT window [-300, 1300] HU (Atlas v3 §2.2): overwrite the clipping percentiles nnU-Net's CTNormalization
reads from the dataset fingerprint, before planning. usage: python patch_fp.py FINGERPRINT.json"""
import json
import sys

p = sys.argv[1]
fp = json.load(open(p))
props = fp['foreground_intensity_properties_per_channel']['0']
props['percentile_00_5'] = -300.0
props['percentile_99_5'] = 1300.0
json.dump(fp, open(p, 'w'), indent=1)
print('fingerprint window set to [-300, 1300] HU; mean/std kept:', props.get('mean'), props.get('std'))
