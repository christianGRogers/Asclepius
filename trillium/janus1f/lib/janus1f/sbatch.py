"""The Fir SBATCH headers (F-A34): the one place they are written. `python -m janus1f.sbatch <kind> <name> <log>`.

  GPU (train links, predict): --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G,
                              --time=23:50:00 per train link, 6:00:00 for predict (icx4's Fir values)
  CPU (prep, collect):        --account=def-aso22 --cpus-per-task=16 --mem=64G
"""
import sys

GPU = ('#SBATCH --account=def-aso22_gpu', '#SBATCH --gpus-per-node=h100:1', '#SBATCH --cpus-per-task=12',
       '#SBATCH --mem=280G')
CPU = ('#SBATCH --account=def-aso22', '#SBATCH --cpus-per-task=16', '#SBATCH --mem=64G')
TIME = {'train': '23:50:00', 'predict': '6:00:00', 'prep': '3:00:00', 'collect': '4:00:00'}
KIND = {'train': GPU, 'predict': GPU, 'prep': CPU, 'collect': CPU}
TRAIN_MAX_SECONDS = 84000          # 23:50:00 - 30 min (F-A34)


def header(kind, name, log):
    if kind not in KIND:
        raise ValueError(f'unknown job kind {kind!r}')
    return '\n'.join(('#!/bin/bash', f'#SBATCH --job-name={name}', '#SBATCH --nodes=1') + KIND[kind]
                     + (f'#SBATCH --time={TIME[kind]}', f'#SBATCH --output={log}')) + '\n'


if __name__ == '__main__':
    sys.stdout.write(header(*sys.argv[1:4]))
