"""Names SegQueue14 writes into the database. The Mongo collections, settings and
groups differ from the retired 4-class SegQueue's (``girder_segqueue.constants``);
since D36 the Girder *collection* is shared: SegQueue14 writes into ``SegQueue``,
beside the CT volumes it serves, and the old queue's folders sit archived in
``SegQueue/_archive-4class/``.

Renaming any of these without a migration orphans data, as in the old plugin.
"""

#: Girder groups. Separate from ``segqueue-annotators`` / ``segqueue-reviewers``:
#: being on the live project does not put anybody on this one.
ANNOTATOR_GROUP = "segqueue14-annotators"
REVIEWER_GROUP = "segqueue14-reviewers"

# ------------------------------------------------------------ storage layout

#: Everything SegQueue14 *writes* lives under this collection (D36: one collection).
#: It is the same collection as the CT volumes it serves (``SegQueue/cases``), but
#: in its own top-level folders; cases reference those CTs by id and never copy,
#: move or modify them. Before D36 this was a separate ``SegQueue14`` collection.
COLLECTION_NAME = "SegQueue"
#: ``SegQueue/prelabels/<model_version>/<case>.prelabel.nii.gz``.
PRELABELS_FOLDER = "prelabels"
SUBMISSIONS_FOLDER = "submissions"
INCOMING_FOLDER = "incoming"

#: Where the CT volumes and seeds are read from -- the same collection as
#: ``COLLECTION_NAME`` since D36; kept as its own name for the readers.
#: The population tool's ImageCAS-X material:
#: ``SegQueue/imagecas-x/segmentations/<id>.coronary.nii.gz``. Read only.
LIVE_COLLECTION_NAME = "SegQueue"
ICX_FOLDER = "imagecas-x"
ICX_SEGMENTATIONS_FOLDER = "segmentations"
#: The pooled new datasets (D22, D23): ``SegQueue/cases`` holds one CT item per
#: volume (``<Source>__<Case>.nii.gz``), ``SegQueue/seeds-totalseg`` one binary
#: vessel seed per CT (``<Source>__<Case>__totalseg-coronary.nii.gz``). Read only.
POOL_FOLDER = "cases"
SEEDS_FOLDER = "seeds-totalseg"

#: The live plugin's Mongo collection of cases. Read, never written, by
#: ``segqueue14-populate``.
LIVE_CASE_COLLECTION = "segqueue_case"

# ------------------------------------------------------------ settings keys

SETTING_POLICY = "segqueue14.policy"
SETTING_PROJECT = "segqueue14.project"
#: Thresholds for the automatic ImageCAS-X reference score and the two-read
#: agreement score.
SETTING_REFERENCE = "segqueue14.reference"

#: Per-user case cap, on the Girder user document. Not ``segqueueQuota``: a cap
#: on the live project must not cap this one.
QUOTA_FIELD = "segqueue14Quota"

# ------------------------------------------------------------ tuning

MAX_ASSIGN_ATTEMPTS = 8
CANDIDATE_BATCH = 32
