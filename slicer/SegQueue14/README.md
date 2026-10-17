# SegQueue14

The 3D Slicer module for the **14-class prelabel-correction** project. From
**0.14.0 it replaces the 4-class SegQueue module** and continues its version
numbers (D24): same server, its own routes (`/api/v1/segqueue14`), its own
settings, its own cache (`~/.segqueue14`).

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

**Running SegQueue 0.13 or older:** open SegQueue and press *Check for updates* →
**Update and restart**. It installs SegQueue14 over it; afterwards open
**Segmentation → SegQueue14** (opening "SegQueue" takes you there). Your server
address carries over. If you installed the separate SegQueue14 0.1.0 extension,
uninstall it first.

**First install:** download `SegQueue-<version>-Slicer-5.8.zip` from the newest
`segqueue-v…` release (or build it: `python slicer/build-extension14.py`), then
**Extensions Manager → Install from file** → restart. From a checkout: add
`slicer/SegQueue14` to *Additional module paths*.

**Updating:** the module checks for a newer release when opened and offers
**Update and restart** (`SegQueue14Lib/updater.py`, which only installs archives
that carry SegQueue14). If the server's protocol has moved on, login is refused
with *"Update the SegQueue14 module"*.

## For developers

`SegQueue14Lib/` (client, cache) has no Slicer imports and is tested by
`tests/test_segqueue14_client.py`; the module itself is checked statically by
`tests/test_segqueue14_module.py`. `tests/segqueue14_e2e.py` runs the module's
network path against a live server.
