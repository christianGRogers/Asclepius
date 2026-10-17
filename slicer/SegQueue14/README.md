# SegQueue14

The 3D Slicer module for the **14-class prelabel-correction** project. It installs
**beside** the SegQueue module and changes nothing about it: same server, its own
routes (`/api/v1/segqueue14`), its own settings, its own cache (`~/.segqueue14`).

## What you do

1. **Segmentation → SegQueue14**, log in with your usual account (you must be in the
   `segqueue14-annotators` group).
2. **Get next case.** The CT arrives with the 14-class model's prediction already
   loaded into the project's 14 segments:

   | | | | |
   |---|---|---|---|
   | 1 LM | 2 LAD\* | 3 LCx\* | 4 D1 |
   | 5 D2 | 6 OM1 | 7 OM2 | 8 IM |
   | 9 RCA\* | 10 R-PDA | 11 R-PLA | 12 L-PDA |
   | 13 L-PLA | 14 Other (D3/D4, OM3/OM4) | | |

   \* required: the case cannot be submitted while LAD, LCx or RCA is empty.
3. **Correct it** in the Segment Editor (the panel shows the instructions and a
   one-line hint per class): fix wrong names, add vessel the model missed, delete
   anything that is not a coronary artery, and trim or extend the outline to the
   contrast-filled lumen.
4. **Submit case.** What is in the 14 segments is what is submitted. The heart
   mask (`~ heart region (not submitted)`) is a helper and never leaves your
   machine.

## Install

From a build: `python slicer/build-extension14.py` writes
`dist/SegQueue14-<version>-Slicer-5.8.zip`; **Extensions Manager → Install from
file** → restart. From a checkout: add `slicer/SegQueue14` to *Additional module
paths* (the module finds `src/segqueue14` and `src/segqueue` itself).

There is no self-updater (the SegQueue one installs SegQueue releases). If the
server's SegQueue14 protocol has moved on, login is refused with
*"Update the SegQueue14 module"*: install the newer zip from the project lead.

## For developers

`SegQueue14Lib/` (client, cache) has no Slicer imports and is tested by
`tests/test_segqueue14_client.py`; the module itself is checked statically by
`tests/test_segqueue14_module.py`. `tests/segqueue14_e2e.py` runs the module's
network path against a live server.
