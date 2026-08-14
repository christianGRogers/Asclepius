#!/usr/bin/env python
"""Fetch the TotalSegmentator v2.0.1 dataset from Zenodo into a dataset root.

The deploy-time bootstrap: run this on whatever machine is about to train, before
`segtrain convert`. It downloads the 22 GB archive, checks it, and extracts the
1228 subject directories that `zenodo_root` is expected to contain.

Four properties matter more than anything clever, and they are why this is longer
than a `curl | unzip`:

**Resumable.** 22 GB is hours on a home connection and minutes in a datacenter,
but either way a dropped connection must not cost the whole transfer. The
download continues with an HTTP Range request, and extraction skips members
already on disk at the right size. Interrupt it and run it again.

**Verified.** A truncated download, or an HTML error page saved as `.zip`, is not
detected until extraction fails -- or worse, extracts partially and silently
trains on 900 cases. The archive's published MD5 is checked before anything is
unpacked.

**Idempotent.** Deployment scripts get run twice. A dataset root that already
looks complete is left alone and the script exits 0.

**Stdlib only.** This runs on a bare box before `pip install -e .`, and inside a
container whose image does not necessarily have the package installed.

    python scripts/init_dataset.py --dest /data/Totalsegmentator_dataset_v201

With no `--dest` it reads `zenodo_root` from the pipeline config, so on a
configured machine `python scripts/init_dataset.py` is the whole command.

It also fetches labelled CT from the NCI Imaging Data Commons:

    python scripts/init_dataset.py --list-idc          # what is there
    python scripts/init_dataset.py --idc expert        # every human-drawn set
    python scripts/init_dataset.py --idc pediatric_ct_seg --limit-cases 25

Be clear about what that second source is. IDC's largest CT segmentation
holding by far is TotalSegmentator's *own output* over 26k NLST chest scans:
126k series, ~22 TB, and pseudo-labels. Training on it distils the model this
pipeline is reproducing rather than improving on it. The human-drawn sets are
two orders of magnitude smaller and worth far more per case -- `pediatric_ct_seg`
in particular covers a population the TotalSegmentator training set does not.

And IDC ships DICOM. The pipeline reads NIfTI plus one mask per structure, so
what comes down still needs converting and its structure names mapping onto the
117. That converter does not exist in this repo yet; `--idc` gets you the data
and the provenance, not a drop-in dataset.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]

# Zenodo record 10047292, "Dataset with segmentations of 117 important anatomical
# structures in 1228 CT images", version 2.0.1. Size and MD5 are the record's own
# published values -- if Zenodo ever reissues the file these stop matching, which
# is the point.
ZENODO_URL = (
    "https://zenodo.org/records/10047292/files/"
    "Totalsegmentator_dataset_v201.zip?download=1"
)
ZIP_BYTES = 23_581_218_285
ZIP_MD5 = "fe250e5718e0a3b5df4c4ea9d58a62fe"

EXPECTED_CASES = 1228
EXPECTED_STRUCTURES = 117

# Extracted images (21 GB) plus masks (9.1 GB), and the archive alongside them
# until it is deleted. Checked up front because running out of disk 19 GB into an
# extraction leaves a mess that looks like a corrupt download.
EXTRACTED_BYTES = 32 * 2**30

USER_AGENT = "segtrain-init-dataset/1.0"


# -- small helpers -----------------------------------------------------------


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


class Progress:
    """Byte progress that behaves in a terminal and in a log file.

    Modal, nohup and CI capture stdout to a file, where a carriage-returning
    progress bar becomes tens of thousands of useless lines. When stdout is not
    a tty this prints one line every `log_every` seconds instead.
    """

    def __init__(self, total: int, label: str, done: int = 0, log_every: float = 60.0):
        self.total = total
        self.label = label
        self.done = done
        self.start = time.monotonic()
        self.start_done = done
        self.last = 0.0
        self.tty = sys.stdout.isatty()
        self.interval = 0.5 if self.tty else log_every

    def advance(self, n: int) -> None:
        self.done += n
        now = time.monotonic()
        if now - self.last >= self.interval:
            self.last = now
            self._render(now)

    def _render(self, now: float, final: bool = False) -> None:
        elapsed = max(1e-6, now - self.start)
        rate = (self.done - self.start_done) / elapsed
        pct = 100.0 * self.done / self.total if self.total else 0.0
        eta = (self.total - self.done) / rate if rate > 0 and self.total else 0
        line = (f"  {self.label}  {human(self.done)} / {human(self.total)}"
                f"  {pct:5.1f}%  {human(rate)}/s  eta {duration(eta)}")
        if self.tty and not final:
            sys.stdout.write("\r" + line + " " * 6)
            sys.stdout.flush()
        else:
            print(line, flush=True)

    def close(self) -> None:
        now = time.monotonic()
        if self.tty:
            sys.stdout.write("\r")
        self._render(now, final=True)


def default_dest() -> Path | None:
    """`zenodo_root` from the pipeline config, if this checkout is configured.

    Imported lazily and defensively: the whole point of a stdlib-only script is
    that it still runs when the package is not installed.
    """
    try:
        sys.path.insert(0, str(REPO / "src"))
        from segtrain.config import load_config

        return Path(load_config().zenodo_root)
    except Exception:
        return None


# -- completeness ------------------------------------------------------------


def case_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir()
                  if p.is_dir() and p.name.startswith("s") and p.name[1:].isdigit())


def looks_complete(root: Path, expect_cases: int = EXPECTED_CASES) -> bool:
    """Cheap "is it already there?" check, run before any network access."""
    return (root / "meta.csv").is_file() and len(case_dirs(root)) >= expect_cases


def validate(root: Path, expect_cases: int, expect_structures: int) -> list[str]:
    """Structural check of an extracted dataset. Returns a list of problems."""
    problems = []
    if not (root / "meta.csv").is_file():
        problems.append(f"meta.csv missing from {root}")

    cases = case_dirs(root)
    if len(cases) < expect_cases:
        problems.append(f"found {len(cases)} subject directories, expected {expect_cases}")
    if not cases:
        return problems

    # Spot-check rather than walk 145k files: a truncated extraction shows up in
    # the case count, and a corrupt one in the MD5 that has already passed.
    sampled = dict.fromkeys((cases[0], cases[len(cases) // 2], cases[-1]))
    for case in sampled:
        if not (case / "ct.nii.gz").is_file():
            problems.append(f"{case.name}: ct.nii.gz missing")
        masks = list((case / "segmentations").glob("*.nii.gz"))
        if len(masks) < expect_structures:
            problems.append(
                f"{case.name}: {len(masks)} masks, expected {expect_structures}")
    return problems


# -- download ----------------------------------------------------------------


def _stream(url: str, path: Path, offset: int, total: int) -> None:
    """One download attempt, resuming from `offset` bytes."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    if offset:
        req.add_header("Range", f"bytes={offset}-")

    with urlopen(req, timeout=120) as resp:
        # A server that ignores Range replies 200 with the whole file. Appending
        # then would corrupt it, so start over rather than produce a file that
        # is the right size and wrong bytes.
        resumed = offset > 0 and resp.getcode() == 206
        if offset and not resumed:
            print("  server ignored Range; restarting the download", flush=True)
            offset = 0

        length = resp.headers.get("Content-Length")
        if length and not total:
            total = int(length) + offset

        progress = Progress(total, "download", done=offset)
        with open(path, "ab" if resumed else "wb") as fh:
            if not resumed:
                fh.truncate(0)
            while True:
                chunk = resp.read(8 * 2**20)
                if not chunk:
                    break
                fh.write(chunk)
                progress.advance(len(chunk))
        progress.close()


def download(url: str, path: Path, expected_size: int, retries: int = 10) -> None:
    """Download `url` to `path`, resuming and retrying."""
    path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(retries + 1):
        have = path.stat().st_size if path.exists() else 0
        if expected_size and have == expected_size:
            print(f"  archive already downloaded ({human(have)})")
            return
        if expected_size and have > expected_size:
            # Longer than the published size means a previous run appended to a
            # complete file, or the record changed. Neither is recoverable by
            # resuming.
            print(f"  {path.name} is larger than expected; discarding and refetching")
            path.unlink()
            have = 0
        if have:
            print(f"  resuming at {human(have)} of {human(expected_size)}")

        try:
            _stream(url, path, have, expected_size)
            return
        except HTTPError as exc:
            # 416 with bytes on disk means the server considers the range past
            # the end -- i.e. we already have the whole file.
            if exc.code == 416 and have:
                print("  server reports the file is already complete")
                return
            failure = f"HTTP {exc.code} {exc.reason}"
        except (URLError, OSError) as exc:
            failure = str(exc)
        except HTTPException as exc:
            # IncompleteRead and friends are not OSErrors, and a multi-hour
            # stream hits them often enough that missing this would turn a
            # resumable hiccup into a crash.
            failure = f"{type(exc).__name__}: {exc}"

        if attempt == retries:
            raise RuntimeError(f"download failed after {retries + 1} attempts: {failure}")
        wait = min(60, 2 ** attempt)
        print(f"  {failure} -- retrying in {wait}s "
              f"(attempt {attempt + 2}/{retries + 1})", flush=True)
        time.sleep(wait)


def md5sum(path: Path) -> str:
    # MD5 because that is what Zenodo publishes. It is an integrity check against
    # truncation and corruption, not a security control.
    digest = hashlib.md5()
    total = path.stat().st_size
    progress = Progress(total, "checksum")
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(16 * 2**20)
            if not chunk:
                break
            digest.update(chunk)
            progress.advance(len(chunk))
    progress.close()
    return digest.hexdigest()


# -- extraction --------------------------------------------------------------


def archive_root(names: list[str]) -> str:
    """The directory inside the archive that is the dataset root, or "".

    Zenodo archives are inconsistent about this: some wrap everything in a
    directory named after the dataset, some are flat. Getting it wrong nests the
    data one level too deep, which surfaces much later as "no subject
    directories" -- so decide it from the archive rather than assuming.

    `meta.csv` sits at the dataset root and nowhere else, which makes it the
    reliable signal. Only when it is absent (a hand-made subset, say) does this
    fall back to stripping a lone wrapping directory.
    """
    for name in names:
        if name == "meta.csv":
            return ""
        if name.count("/") == 1 and name.endswith("/meta.csv"):
            return name.split("/", 1)[0]

    tops = {n.split("/", 1)[0] for n in names if n}
    if len(tops) != 1:
        return ""
    top = tops.pop()
    if not all(n == top or n.startswith(top + "/") for n in names):
        return ""
    # A subject directory is content, not a wrapper. Without this, an archive of
    # a single case would have that case stripped away.
    return "" if re.fullmatch(r"s\d+", top) else top


def _safe_target(dest: Path, name: str) -> Path | None:
    """Resolve an archive member against `dest`, rejecting escapes.

    An archive is untrusted input; a member named `../../etc/x` would otherwise
    be written outside the dataset root.
    """
    target = (dest / name).resolve()
    root = dest.resolve()
    return target if target == root or target.is_relative_to(root) else None


def extract(zip_path: Path, dest: Path) -> int:
    """Extract into `dest`, skipping members already present at the right size.

    Not `extractall`: per-member handling is what makes an interrupted extraction
    resumable, and what lets a 145k-file archive report progress.
    """
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        root = archive_root(zf.namelist())
        if root:
            print(f"  archive wraps everything in {root}/ -- stripping it")

        total = sum(i.file_size for i in infos)
        print(f"  {len(infos)} files, {human(total)} extracted")
        progress = Progress(total, "extract")
        written = 0

        for info in infos:
            name = info.filename
            if root:
                name = name[len(root) + 1:]
            if not name:
                continue

            target = _safe_target(dest, name)
            if target is None:
                raise RuntimeError(f"archive member escapes the destination: {info.filename}")

            if target.exists() and target.stat().st_size == info.file_size:
                progress.advance(info.file_size)  # already extracted
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            # Write beside the target and rename, so an interruption leaves a
            # partial file that the size check above will redo rather than a
            # short file it would accept.
            tmp = target.with_name(target.name + ".part")
            with zf.open(info) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 2**20)
            tmp.replace(target)
            written += 1
            progress.advance(info.file_size)

        progress.close()
    return written


# -- NCI Imaging Data Commons ------------------------------------------------
#
# IDC (imaging.datacommons.cancer.gov) publishes public cancer imaging with its
# metadata queryable as SQL over a REST endpoint, and its pixel data in
# anonymously readable S3/GCS buckets. Both are reachable with urllib, so this
# stays dependency-free: no idc-index, no boto3, no credentials.
#
# What IDC adds to a TotalSegmentator-style model is *not* more of the same.
# Read the `truth` field on each entry below before training on any of it:
#
#   expert -- humans drew these. Real ground truth, small, and worth the most
#             per case. `pediatric_ct_seg` is the standout: paediatric anatomy
#             is exactly what the adult-heavy TotalSegmentator dataset lacks.
#   model  -- a model drew these. `totalsegmentator_ct_segmentations` is
#             TotalSegmentator's own output over 26k NLST chest CTs. Training on
#             it distils the model this pipeline is trying to reproduce; it
#             cannot exceed it. Useful for pretraining or semi-supervised work,
#             misleading as "labelled data".
#   mixed  -- model output with a fraction human-reviewed.

IDC_API = "https://api.imaging.datacommons.cancer.gov/v3/sql"
IDC_BUCKET_URL = "https://idc-open-data.s3.amazonaws.com"
IDC_PAGE = 5000
IDC_VERSION_URL = "https://api.imaging.datacommons.cancer.gov/v3/version"


@dataclass(frozen=True)
class IDCDataset:
    """One downloadable slice of IDC, with what it actually contains."""

    id: str
    labels: str
    truth: str  # expert | model | mixed
    cases: int
    ct_gb: float
    label_gb: float
    license: str
    label_modality: str  # SEG or RTSTRUCT
    collection: str = ""
    analysis_result: str = ""
    note: str = ""
    # IDC attaches licences to series, not collections, so images and labels can
    # differ -- pancreas_ct's CT is CC BY 3.0 while its segmentations are 4.0.
    # Empty means "same as the images".
    label_license: str = ""

    @property
    def total_gb(self) -> float:
        return self.ct_gb + self.label_gb

    @property
    def licenses(self) -> str:
        if self.label_license and self.label_license != self.license:
            return f"{self.license} + {self.label_license}"
        return self.license

    @property
    def commercial_ok(self) -> bool:
        """Using the data means honouring both licences, so both must allow it."""
        return "NC" not in self.license and "NC" not in (self.label_license or "")


# Counts, sizes and licences below were read from the IDC index (v24) rather than
# from documentation, and are checked by tests against the live API when it is
# reachable. Sizes are the DICOM on the wire.
IDC_CATALOGUE = (
    IDCDataset(
        id="pediatric_ct_seg",
        labels=("29 organs incl. liver, spleen, kidneys, pancreas, duodenum, adrenals, "
                "gallbladder, stomach, bowel, lungs, heart, oesophagus, bladder, femoral heads"),
        truth="expert",
        cases=359,
        ct_gb=56.6,
        label_gb=7.5,
        license="CC BY 4.0",
        label_modality="RTSTRUCT",
        collection="pediatric_ct_seg",
        note="Paediatric CT. The single most valuable entry here: a population the "
             "TotalSegmentator training set barely covers, contoured by humans.",
    ),
    IDCDataset(
        id="mediastinal_lymph_node_seg",
        labels="mediastinal lymph nodes",
        truth="expert",
        cases=513,
        ct_gb=34.1,
        label_gb=0.3,
        license="CC BY 4.0",
        label_modality="SEG",
        collection="mediastinal_lymph_node_seg",
        note="Not one of the 117 classes -- useful only if you extend the label set.",
    ),
    IDCDataset(
        id="c4kc_kits",
        labels="kidney and kidney tumour",
        truth="expert",
        cases=210,
        ct_gb=36.8,
        label_gb=3.0,
        license="CC BY 3.0",
        label_modality="SEG",
        collection="c4kc_kits",
        note="KiTS19. Contrast-enhanced abdominal CT; kidney labels include tumour, "
             "which the TotalSegmentator kidney class does not.",
    ),
    IDCDataset(
        id="prostate_anatomical_edge_cases",
        labels="prostate, bladder, rectum, left and right femoral head",
        truth="expert",
        cases=131,
        ct_gb=16.6,
        label_gb=0.1,
        license="CC BY 4.0",
        label_modality="RTSTRUCT",
        collection="prostate_anatomical_edge_cases",
        note="Chosen for anatomy that is hard to contour -- exactly the cases a model "
             "trained on routine scans gets wrong.",
    ),
    IDCDataset(
        id="pancreas_ct",
        labels="pancreas",
        truth="expert",
        cases=80,
        ct_gb=9.7,
        label_gb=0.2,
        license="CC BY 3.0",
        label_modality="SEG",
        collection="pancreas_ct",
        note="The NIH Clinical Center pancreas set. Small, and the reference standard "
             "for a structure models routinely do badly on.",
        label_license="CC BY 4.0",
    ),
    IDCDataset(
        id="lctsc",
        labels="oesophagus, heart, left lung, right lung, spinal cord",
        truth="expert",
        cases=60,
        ct_gb=4.9,
        label_gb=0.1,
        license="CC BY 3.0",
        label_modality="RTSTRUCT",
        collection="lctsc",
        note="Lung CT Segmentation Challenge -- radiotherapy organs at risk, so the "
             "contours are clinical-grade.",
    ),
    IDCDataset(
        id="spine_mets_ct_seg",
        labels="vertebrae and spinal metastases",
        truth="expert",
        cases=55,
        ct_gb=18.3,
        label_gb=1.6,
        license="CC BY 4.0",
        label_modality="SEG",
        collection="spine_mets_ct_seg",
        note="Diseased vertebrae. Vertebra labelling degrades on pathological spines.",
    ),
    IDCDataset(
        id="adrenal_acc_ki67_seg",
        labels="adrenal gland (adrenocortical carcinoma)",
        truth="expert",
        cases=53,
        ct_gb=9.4,
        label_gb=0.3,
        license="CC BY 4.0",
        label_modality="SEG",
        collection="adrenal_acc_ki67_seg",
    ),
    IDCDataset(
        id="nsclc_radiomics",
        labels="left lung, right lung, oesophagus, heart, spinal cord, GTV",
        truth="expert",
        cases=422,
        ct_gb=26.3,
        label_gb=0.6,
        license="CC BY-NC 3.0",
        label_modality="RTSTRUCT",
        collection="nsclc_radiomics",
        note="NON-COMMERCIAL licence. A model trained on it inherits that restriction, "
             "so it is excluded unless you pass --allow-noncommercial.",
    ),
    IDCDataset(
        id="totalsegmentator_ct_segmentations",
        labels="~77 structures per series, TotalSegmentator's own label vocabulary",
        truth="model",
        cases=26194,
        ct_gb=8666.8,
        label_gb=13854.6,
        license="CC BY 4.0",
        label_modality="SEG",
        analysis_result="totalsegmentator_ct_segmentations",
        note="126,051 series over 26,194 NLST patients -- ~22 TB whole, so use "
             "--limit-cases. Low-dose non-contrast CHEST screening CT only: no "
             "abdominal or pelvic coverage, and the labels are model output.",
    ),
    IDCDataset(
        id="bamf_aimi_annotations",
        labels="kidney, liver, lung, prostate, breast and associated tumours",
        truth="mixed",
        cases=4226,
        ct_gb=0.0,
        label_gb=0.0,
        license="CC BY 4.0",
        label_modality="SEG",
        analysis_result="bamf_aimi_annotations",
        note="nnU-Net output with ~10% reviewed and corrected by a radiologist. Spans "
             "22 collections and several modalities; sizes vary with what you select.",
    ),
)

IDC_BY_ID = {d.id: d for d in IDC_CATALOGUE}


def idc_sql(sql: str, timeout: int = 300) -> list[dict]:
    """Run one SQL query against the IDC REST API."""
    body = json.dumps({"sql": sql}).encode()
    req = Request(IDC_API, data=body,
                  headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    if "rows" not in payload:
        raise RuntimeError(f"unexpected IDC response: {str(payload)[:300]}")
    return payload["rows"]


def idc_query_all(base_sql: str) -> list[dict]:
    """Page through a query. The API caps a single response at 5000 rows."""
    rows: list[dict] = []
    while True:
        page = idc_sql(f"SELECT * FROM ({base_sql}) ORDER BY patient, modality, uuid "
                       f"LIMIT {IDC_PAGE} OFFSET {len(rows)}")
        rows.extend(page)
        if len(page) < IDC_PAGE:
            return rows


def idc_selection_sql(ds: IDCDataset, limit_cases: int = 0) -> str:
    """SQL selecting every series to download for `ds`, images and labels.

    Two shapes, because IDC models the two differently: a *collection* is an
    original submission and holds its own CT, while an *analysis result* is
    derived and only references CT that lives elsewhere.
    """
    if ds.collection:
        cases = ""
        if limit_cases:
            cases = (f" AND PatientID IN (SELECT PatientID FROM index "
                     f"WHERE collection_id = '{ds.collection}' "
                     f"AND Modality = '{ds.label_modality}' "
                     f"GROUP BY 1 ORDER BY 1 LIMIT {limit_cases})")
        return (f"SELECT crdc_series_uuid AS uuid, Modality AS modality, "
                f"PatientID AS patient, series_size_MB AS mb FROM index "
                f"WHERE collection_id = '{ds.collection}' "
                f"AND Modality IN ('CT', '{ds.label_modality}'){cases}")

    cases = ""
    if limit_cases:
        cases = (f" AND PatientID IN (SELECT PatientID FROM index "
                 f"WHERE analysis_result_id = '{ds.analysis_result}' "
                 f"AND Modality = '{ds.label_modality}' "
                 f"GROUP BY 1 ORDER BY 1 LIMIT {limit_cases})")
    return (
        f"WITH labels AS (SELECT SeriesInstanceUID, crdc_series_uuid, PatientID, "
        f"series_size_MB FROM index WHERE analysis_result_id = '{ds.analysis_result}' "
        f"AND Modality = '{ds.label_modality}'{cases}) "
        f"SELECT crdc_series_uuid AS uuid, '{ds.label_modality}' AS modality, "
        f"PatientID AS patient, series_size_MB AS mb FROM labels "
        f"UNION ALL "
        f"SELECT src.crdc_series_uuid, 'CT', src.PatientID, src.series_size_MB "
        f"FROM seg_index s JOIN labels ON labels.SeriesInstanceUID = s.SeriesInstanceUID "
        f"JOIN index src ON src.SeriesInstanceUID = s.segmented_SeriesInstanceUID"
    )


S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def parse_s3_listing(xml_text: str) -> tuple[list[tuple[str, int]], str]:
    """(key, size) pairs and the continuation token from an S3 ListObjectsV2 body."""
    root = ET.fromstring(xml_text)
    objects = []
    for contents in root.findall(f"{S3_NS}Contents"):
        key = contents.findtext(f"{S3_NS}Key") or ""
        size = int(contents.findtext(f"{S3_NS}Size") or 0)
        if key and not key.endswith("/"):
            objects.append((key, size))
    truncated = (root.findtext(f"{S3_NS}IsTruncated") or "false").lower() == "true"
    token = root.findtext(f"{S3_NS}NextContinuationToken") or ""
    return objects, (token if truncated else "")


def idc_series_objects(series_uuid: str) -> list[tuple[str, int]]:
    """Every object making up one DICOM series. Anonymous; the bucket is public."""
    objects: list[tuple[str, int]] = []
    token = ""
    while True:
        url = (f"{IDC_BUCKET_URL}/?list-type=2&prefix={quote(series_uuid)}/"
               + (f"&continuation-token={quote(token, safe='')}" if token else ""))
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=120) as resp:
            page, token = parse_s3_listing(resp.read().decode())
        objects.extend(page)
        if not token:
            return objects


def _fetch_object(key: str, target: Path, size: int,
                  retries: int = 3) -> tuple[int, bool]:
    """Download one object unless it is already there at the right size.

    Returns (bytes, whether it was actually fetched) so a resumed run still
    reports progress across files it skipped.
    """
    if target.exists() and target.stat().st_size == size:
        return size, False
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    for attempt in range(retries + 1):
        try:
            req = Request(f"{IDC_BUCKET_URL}/{quote(key)}",
                          headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=300) as resp, open(tmp, "wb") as fh:
                shutil.copyfileobj(resp, fh, 2**20)
            tmp.replace(target)
            return size, True
        except (URLError, OSError, HTTPException):
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return size, True


def idc_download(ds: IDCDataset, root: Path, limit_cases: int = 0,
                 workers: int = 8, dry_run: bool = False) -> int:
    """Fetch one catalogue entry into `root/<id>/<patient>/<modality>/<series>/`.

    Laid out by patient so an image series and the labels drawn on it sit
    together -- IDC's own file names are opaque UUIDs, and the association is the
    only thing that makes the download usable later.
    """
    print(f"\n=== {ds.id} ===")
    print(f"  labels   {ds.labels}")
    print(f"  truth    {ds.truth}")
    print(f"  licence  {ds.licenses}")
    if ds.note:
        print(f"  note     {ds.note}")

    print("  querying the IDC index ...", flush=True)
    rows = idc_query_all(idc_selection_sql(ds, limit_cases))
    if not rows:
        print("  nothing matched -- has the collection been renamed?", file=sys.stderr)
        return 0

    patients = {r["patient"] for r in rows}
    approx = sum(float(r["mb"] or 0) for r in rows) / 1024
    n_lab = sum(1 for r in rows if r["modality"] != "CT")
    print(f"  {len(rows)} series ({len(rows) - n_lab} CT, {n_lab} {ds.label_modality}) "
          f"over {len(patients)} patients, about {approx:.1f} GB")

    dest = root / ds.id
    if dry_run:
        print(f"  [dry-run] would download into {dest}")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "ATTRIBUTION.txt").write_text(
        f"{ds.id}\nSource: NCI Imaging Data Commons (https://imaging.datacommons.cancer.gov/)\n"
        f"Licence: {ds.license}\nLabels: {ds.labels}\nProvenance: {ds.truth}\n"
        f"Retrieved: {time.strftime('%Y-%m-%d')}\n\n"
        "IDC requires attribution. Cite the collection's own DOI as well as IDC.\n",
        encoding="utf-8")
    with open(dest / "series.tsv", "w", encoding="utf-8") as fh:
        fh.write("patient\tmodality\tseries_uuid\n")
        for r in sorted(rows, key=lambda r: (r["patient"], r["modality"])):
            fh.write(f"{r['patient']}\t{r['modality']}\t{r['uuid']}\n")

    # Listing is one request per series and downloads are many small files, so
    # both are threaded. The bottleneck is round trips, not bandwidth.
    print("  listing objects ...", flush=True)
    jobs: list[tuple[str, Path, int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        listings = pool.map(idc_series_objects, [r["uuid"] for r in rows])
        for row, objects in zip(rows, listings):
            series_dir = dest / str(row["patient"]) / str(row["modality"]) / str(row["uuid"])
            for key, size in objects:
                jobs.append((key, series_dir / key.rsplit("/", 1)[-1], size))

    total = sum(size for _, _, size in jobs)
    print(f"  {len(jobs)} files, {human(total)}")
    progress = Progress(total, "idc")
    fetched = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_object, key, target, size)
                   for key, target, size in jobs]
        for future in concurrent.futures.as_completed(futures):
            size, was_fetched = future.result()
            progress.advance(size)
            fetched += int(was_fetched)
    progress.close()
    skipped = len(jobs) - fetched
    print(f"  {fetched} file(s) downloaded"
          + (f", {skipped} already present" if skipped else ""))
    print(f"  -> {dest}")
    return fetched


def print_idc_catalogue() -> None:
    print("Labelled CT available from the NCI Imaging Data Commons (IDC v24).\n")
    print(f"{'id':<34} {'truth':<7} {'cases':>6} {'GB':>8}  licence")
    print("-" * 78)
    for ds in IDC_CATALOGUE:
        size = f"{ds.total_gb:.1f}" if ds.total_gb else "varies"
        print(f"{ds.id:<34} {ds.truth:<7} {ds.cases:>6} {size:>8}  {ds.licenses}")
    print("\nGroups: 'expert' (human-drawn, commercial-safe), 'all'.")
    print("\nDetail:")
    for ds in IDC_CATALOGUE:
        print(f"\n  {ds.id}")
        print(f"    labels: {ds.labels}")
        if ds.note:
            print(f"    note:   {ds.note}")
    print("\nEverything here is DICOM. See the notes in this script's docstring for "
          "what still has to happen before it is training data.")


def idc_group(name: str) -> list[IDCDataset]:
    if name == "expert":
        return [d for d in IDC_CATALOGUE if d.truth == "expert" and d.commercial_ok]
    if name == "all":
        return list(IDC_CATALOGUE)
    if name in IDC_BY_ID:
        return [IDC_BY_ID[name]]
    raise KeyError(name)


def run_idc(args) -> int:
    root = (args.idc_dest or Path("idc")).expanduser()

    selected: list[IDCDataset] = []
    for name in args.idc:
        try:
            for ds in idc_group(name):
                if ds not in selected:
                    selected.append(ds)
        except KeyError:
            print(f"error: unknown IDC dataset {name!r}. --list-idc shows the options.",
                  file=sys.stderr)
            return 2

    blocked = [d for d in selected if not d.commercial_ok and not args.allow_noncommercial]
    for ds in blocked:
        print(f"skipping {ds.id}: {ds.licenses} forbids commercial use, and a model "
              f"trained on it inherits that. --allow-noncommercial to include it.")
    selected = [d for d in selected if d not in blocked]
    if not selected:
        print("nothing selected")
        return 1

    try:
        with urlopen(Request(IDC_VERSION_URL, headers={"User-Agent": USER_AGENT}),
                     timeout=60) as resp:
            version = json.loads(resp.read().decode()).get("idc_version", "?")
        print(f"IDC data version {version}")
    except Exception as exc:
        print(f"warning: could not reach the IDC API ({exc})", file=sys.stderr)
        return 1

    planned = sum(d.total_gb for d in selected)
    print(f"selected {len(selected)} dataset(s), roughly {planned:.0f} GB before limits")

    for ds in selected:
        idc_download(ds, root, limit_cases=args.limit_cases,
                     workers=args.workers, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nDICOM is in {root}. It is not yet training data: the pipeline reads "
              "NIfTI\nimages with one mask per structure, so these series still need "
              "converting\n(DICOM -> NIfTI, SEG/RTSTRUCT -> per-structure masks) and "
              "their structure names\nmapped onto the 117. No converter ships with this "
              "repo yet.")
    return 0


# -- main --------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download and extract the TotalSegmentator v2.0.1 dataset.")
    ap.add_argument("--dest", type=Path, default=None,
                    help="dataset root to populate (default: zenodo_root from the config)")
    ap.add_argument("--url", default=ZENODO_URL, help="archive URL")
    ap.add_argument("--zip", dest="zip_path", type=Path, default=None,
                    help="where to keep the archive (default: <dest>/../<name>.zip)")
    ap.add_argument("--keep-zip", action="store_true",
                    help="keep the 22 GB archive after extracting (default: delete it)")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the MD5 check (saves a few minutes, risks a silent bad extract)")
    ap.add_argument("--md5", default=ZIP_MD5, help="expected MD5 of the archive")
    ap.add_argument("--size", type=int, default=ZIP_BYTES, help="expected archive size in bytes")
    ap.add_argument("--retries", type=int, default=10, help="download retry attempts")
    ap.add_argument("--expect-cases", type=int, default=EXPECTED_CASES,
                    help="subject directories expected after extraction")
    ap.add_argument("--force", action="store_true",
                    help="re-download and re-extract even if the dataset looks complete")
    ap.add_argument("--no-space-check", action="store_true",
                    help="proceed even if the filesystem looks too small")

    idc = ap.add_argument_group(
        "NCI Imaging Data Commons",
        "Additional labelled CT, on top of the TotalSegmentator dataset.")
    idc.add_argument("--list-idc", action="store_true",
                     help="show what labelled CT is available from IDC and exit")
    idc.add_argument("--idc", nargs="+", metavar="ID",
                     help="fetch these IDC datasets ('expert' for all human-drawn ones)")
    idc.add_argument("--idc-dest", type=Path,
                     help="where IDC data goes (default: <dest>/../idc)")
    idc.add_argument("--limit-cases", type=int, default=0,
                     help="download only the first N patients of each dataset")
    idc.add_argument("--workers", type=int, default=8,
                     help="parallel downloads (default 8)")
    idc.add_argument("--allow-noncommercial", action="store_true",
                     help="include CC BY-NC datasets; the trained weights inherit that")
    idc.add_argument("--dry-run", action="store_true",
                     help="report what would be fetched from IDC, download nothing")
    args = ap.parse_args()

    dest: Path | None = args.dest or default_dest()

    if args.list_idc:
        print_idc_catalogue()
        return 0
    if args.idc:
        if args.idc_dest is None:
            args.idc_dest = (dest.parent / "idc") if dest else Path("idc")
        return run_idc(args)

    if dest is None:
        print("error: no --dest given and zenodo_root could not be read from the config.\n"
              "       Pass --dest /path/to/Totalsegmentator_dataset_v201", file=sys.stderr)
        return 2
    dest = dest.expanduser()

    print(f"dataset root  {dest}")

    if looks_complete(dest, args.expect_cases) and not args.force:
        print(f"already present: {len(case_dirs(dest))} subjects and meta.csv. Nothing to do.")
        print("  (--force to re-download)")
        return 0

    zip_path = args.zip_path or dest.parent / "Totalsegmentator_dataset_v201.zip"
    zip_path = zip_path.expanduser()
    print(f"archive       {zip_path}")

    # Space check against the parent that will actually hold the data. The zip
    # and the extracted tree coexist until the zip is deleted.
    if not args.no_space_check:
        probe = next((p for p in (dest, dest.parent, zip_path.parent) if p.exists()), None)
        if probe is not None:
            free = shutil.disk_usage(probe).free
            needed = EXTRACTED_BYTES + (args.size if not zip_path.exists() else 0)
            print(f"free space    {human(free)} (need roughly {human(needed)})")
            if free < needed:
                print("error: not enough free space. Free some, point --dest and --zip at a "
                      "bigger disk, or pass --no-space-check to override.", file=sys.stderr)
                return 1

    print("\n[1/4] downloading")
    download(args.url, zip_path, args.size, retries=args.retries)

    actual = zip_path.stat().st_size
    if args.size and actual != args.size:
        print(f"error: archive is {actual} bytes, expected {args.size}", file=sys.stderr)
        return 1

    print("\n[2/4] verifying")
    if args.no_verify:
        print("  skipped (--no-verify)")
    else:
        got = md5sum(zip_path)
        if got != args.md5:
            print(f"error: MD5 mismatch\n  expected {args.md5}\n  got      {got}\n"
                  f"Delete {zip_path} and run again.", file=sys.stderr)
            return 1
        print(f"  md5 ok  {got}")

    print("\n[3/4] extracting")
    written = extract(zip_path, dest)
    print(f"  {written} file(s) written")

    print("\n[4/4] checking")
    problems = validate(dest, args.expect_cases, EXPECTED_STRUCTURES)
    if problems:
        print("error: the extracted dataset does not look right:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(f"Re-run to continue extracting; delete {dest} to start over.", file=sys.stderr)
        return 1
    print(f"  {len(case_dirs(dest))} subjects, meta.csv present, structures per case ok")

    if not args.keep_zip:
        zip_path.unlink(missing_ok=True)
        print(f"  removed {zip_path.name} ({human(args.size)} reclaimed)")

    print(f"\nready: {dest}")
    print("next: segtrain convert --task 701")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
