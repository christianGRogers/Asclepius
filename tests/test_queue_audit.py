"""The #126 queue audit reproduces its numbers from the committed snapshot (names, no images)."""

import importlib.util
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, 'experiments', 'QueueAudit', 'audit_queue.py')


def test_queue_audit_numbers(capsys):
    spec = importlib.util.spec_from_file_location('audit_queue', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out['problems'] == []
    keys = ('1_queue_vs_pool_list', '2_ct_and_seed', '3_left_out', '4_patients')
    c1, c2, c3, c4 = (out[k] for k in keys)
    assert c1['queue_rows'] == c1['pool_list_entries'] == 675
    assert not c1['in_queue_not_in_list'] and not c1['in_list_not_in_queue']
    assert not c2['queued_without_ct'] and not c2['queued_without_seed']
    assert c3['left_out'] == 229 and not c3['unexplained']
    assert c3['left_out_by_reason']['QC not annotatable'] == 212
    assert c4['patients'] == 468 and not c4['sealed_volumes_missing_from_queue']
    a33 = c4['accounting_A33_Delta_with_A34_reserve']
    assert a33['sealed (primary, A10)'] == {'patients': 150, 'volumes': 305, 'reads': 610}
    assert a33['D35 decision set']['patients'] == 35 and a33['reserve']['patients'] == 78
    assert out['5_reads']['total'] == 1350 == sum(out['5_reads']['A33_Delta'].values())
