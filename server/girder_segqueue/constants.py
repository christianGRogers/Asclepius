"""Names that must stay stable: groups, settings keys, and the folder layout.

Collected in one module because every one of them is written into the database
on first run and read back forever after. Renaming a constant here without a
migration orphans data rather than breaking a test, which is the worst kind of
change to make casually.
"""

from girder.constants import AccessType  # noqa: F401  (re-exported for convenience)

#: Girder group whose members may be assigned cases.
ANNOTATOR_GROUP = "segqueue-annotators"
#: Girder group whose members may review submissions. Reviewers are usually also
#: annotators; membership of both is fine and common in a small lab.
REVIEWER_GROUP = "segqueue-reviewers"

#: Site admins are admins here too -- there is no separate SegQueue admin role.
#: One fewer thing to get out of sync, and a lab this size has one or two people
#: who need it.

# ------------------------------------------------------------ storage layout

#: Everything the plugin owns lives under one Girder collection, so a backup or
#: an audit has a single obvious root.
COLLECTION_NAME = "SegQueue"
#: Source volumes. One item per case, one file per item.
CASES_FOLDER = "cases"
#: Expert reference segmentations for gold cases, keyed by case.
GOLD_FOLDER = "gold"
#: Uploaded ``.seg.nrrd`` files, one per submission (including superseded ones --
#: nothing is ever overwritten, so a rework history stays inspectable).
SUBMISSIONS_FOLDER = "submissions"
#: Scratch space the client uploads into before calling /submit. Files are moved
#: out on acceptance and swept if they are never claimed.
INCOMING_FOLDER = "incoming"

# ------------------------------------------------------------ settings keys

#: JSON blob holding a ``segqueue.policy.SamplingPolicy``.
SETTING_POLICY = "segqueue.policy"
#: JSON blob holding the project's ``ProjectConfig`` (instructions + segments).
SETTING_PROJECT = "segqueue.project"

# ------------------------------------------------------------ token scopes

#: Scope for an annotator's long-lived API key, if one is issued. Deliberately
#: narrow: it cannot be used to read other people's work or to review.
SCOPE_ANNOTATE = "segqueue.annotate"

# ------------------------------------------------------------ tuning

#: How many candidate cases ``/next`` will try to claim before giving up and
#: telling the client the queue is empty. Each failed attempt means another
#: annotator won the same case in the same instant; with 30 users, more than a
#: couple of collisions in a row is essentially impossible.
MAX_ASSIGN_ATTEMPTS = 8

#: Cap on a single ``/next`` candidate scan. Bounds the query cost on a 5,000
#: case project.
CANDIDATE_BATCH = 32
