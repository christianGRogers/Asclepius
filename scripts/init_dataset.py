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
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import time
import zipfile
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
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
    args = ap.parse_args()

    dest: Path | None = args.dest or default_dest()
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
