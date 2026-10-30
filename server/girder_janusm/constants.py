"""Every name the Janus-M read queue writes. None is shared with SegQueue14
(``girder_segqueue14.constants``): another collection, other groups, other Mongo
collections, other settings. Renaming any of these without a migration orphans data.
"""

#: Girder groups. Being a SegQueue14 annotator does not make anybody a Janus-M reader.
READER_GROUP = "janusm-readers"
ADMIN_GROUP = "janusm-admins"

#: Everything the queue writes lives in this collection. Private.
COLLECTION_NAME = "JanusM"
SEEDS_FOLDER = "seeds"
INCOMING_FOLDER = "incoming"
READS_FOLDER = "reads"

#: Mongo collections.
CASE_COLLECTION = "janusm_case"
READ_COLLECTION = "janusm_read"

#: Settings.
SETTING_SEAL_OPEN = "janusm.sealOpen"
SETTING_MAX_OPEN = "janusm.maxOpen"
DEFAULT_MAX_OPEN = 1

#: Where the CTs are read from (read only): the ImageCAS-X collection's cases (D22).
CT_COLLECTION_NAME = "ImageCAS-X"
CT_FOLDER = "cases"

#: Lost-race retries in /next.
MAX_CLAIM_ATTEMPTS = 8
