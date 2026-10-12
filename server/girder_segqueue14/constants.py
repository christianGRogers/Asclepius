"""Names SegQueue14 writes into the database. All of them differ from the live
SegQueue's (``girder_segqueue.constants``), which is what lets both plugins load
in one Girder at once without either touching the other's data.

Renaming any of these without a migration orphans data, as in the live plugin.
"""

#: Girder groups. Separate from ``segqueue-annotators`` / ``segqueue-reviewers``:
#: being on the live project does not put anybody on this one.
ANNOTATOR_GROUP = "segqueue14-annotators"
REVIEWER_GROUP = "segqueue14-reviewers"

# ------------------------------------------------------------ storage layout

#: Everything SegQueue14 *writes* lives under this collection. The CT volumes it
#: serves are NOT here: cases reference the live SegQueue collection's files by
#: id and never copy, move or modify them.
COLLECTION_NAME = "SegQueue14"
#: ``SegQueue14/prelabels/<model_version>/<case>.prelabel.nii.gz``.
PRELABELS_FOLDER = "prelabels"
SUBMISSIONS_FOLDER = "submissions"
INCOMING_FOLDER = "incoming"

#: Where the population tool looks for the live project's ImageCAS-X material:
#: ``SegQueue/imagecas-x/segmentations/<id>.coronary.nii.gz``. Read only.
LIVE_COLLECTION_NAME = "SegQueue"
ICX_FOLDER = "imagecas-x"
ICX_SEGMENTATIONS_FOLDER = "segmentations"

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
