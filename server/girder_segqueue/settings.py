"""Project configuration, stored as Girder settings and validated on write.

Two settings hold everything an admin can tune: the sampling policy (rates,
leases, quotas) and the project definition (instructions and the segment list).
Both are plain JSON documents so that an admin can edit them in Girder's stock
settings UI without this plugin needing a settings page of its own.

Validation happens on write, not on read. A rejected save is a message in the
admin's browser; a policy that only fails when the fiftieth annotator asks for a
case is a support call on a Sunday.
"""

import json

from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.utility import setting_utilities
from segqueue.policy import SamplingPolicy
from segqueue.protocol import ProjectConfig, SegmentSpec

from .constants import SETTING_POLICY, SETTING_PROJECT

#: Shipped as the default so a fresh install is immediately usable against this
#: repository's phase 1 task. The label values match configs/labels/coronary.yaml
#: -- if they drift, `segtrain convert` will happily build a training set with
#: the wrong structures under the right names, which is the worst possible
#: outcome and the reason they are written down together.
DEFAULT_SEGMENTS = [
    {'name': 'left_main', 'label': 1, 'color': [0.95, 0.25, 0.20], 'required': True,
     'hint': 'Ostium to the LAD/LCx bifurcation.'},
    {'name': 'left_anterior_descending', 'label': 2, 'color': [0.20, 0.70, 0.30],
     'required': True, 'hint': 'Follow the anterior interventricular groove.'},
    {'name': 'left_circumflex', 'label': 3, 'color': [0.25, 0.45, 0.90],
     'required': True, 'hint': 'Left atrioventricular groove.'},
    {'name': 'right_coronary_artery', 'label': 4, 'color': [0.95, 0.75, 0.15],
     'required': False, 'hint': 'May be small or absent in a left-dominant system.'},
]

DEFAULT_INSTRUCTIONS = (
    'Segment the coronary lumen only -- not the vessel wall, not calcified '
    'plaque. Work on the native grid; do not resample. Stop each branch where '
    'the lumen is no longer confidently distinguishable from surrounding '
    'tissue, and say so in the note rather than guessing.'
)


@setting_utilities.default(SETTING_POLICY)
def _defaultPolicy():
    return _policyToDict(SamplingPolicy())


@setting_utilities.default(SETTING_PROJECT)
def _defaultProject():
    return {
        'name': 'Coronary segmentation',
        'instructions': DEFAULT_INSTRUCTIONS,
        'segments': DEFAULT_SEGMENTS,
    }


@setting_utilities.validator(SETTING_POLICY)
def _validatePolicy(doc):
    value = _asDict(doc['value'], SETTING_POLICY)
    unknown = set(value) - set(_policyToDict(SamplingPolicy()))
    if unknown:
        raise ValidationException(
            f"Unknown policy keys: {', '.join(sorted(unknown))}.", 'value')
    try:
        policy = SamplingPolicy(**value)
        policy.validate()
    except (TypeError, ValueError) as exc:
        raise ValidationException(str(exc), 'value') from exc
    doc['value'] = value


@setting_utilities.validator(SETTING_PROJECT)
def _validateProject(doc):
    value = _asDict(doc['value'], SETTING_PROJECT)
    segments = value.get('segments') or []
    if not segments:
        raise ValidationException(
            'A project needs at least one segment; annotators have nothing to '
            'draw otherwise.', 'value')

    seenNames, seenLabels = set(), set()
    for entry in segments:
        try:
            spec = SegmentSpec.from_dict(entry)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationException(f'Malformed segment: {exc}', 'value') from exc
        if spec.label < 1:
            raise ValidationException(
                f'{spec.name!r} has label {spec.label}; label 0 is background.', 'value')
        if spec.name in seenNames:
            raise ValidationException(f'Duplicate segment name {spec.name!r}.', 'value')
        if spec.label in seenLabels:
            # Two structures sharing a label value silently merge in the
            # labelmap, and the result looks like a plausible segmentation.
            raise ValidationException(
                f'Two segments both use label {spec.label}.', 'value')
        seenNames.add(spec.name)
        seenLabels.add(spec.label)

    doc['value'] = value


def _asDict(value, key):
    """Accept either a dict or a JSON string, so the stock settings UI works."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise ValidationException(f'{key} must be valid JSON: {exc}', 'value') from exc
    if not isinstance(value, dict):
        raise ValidationException(f'{key} must be a JSON object.', 'value')
    return value


def _policyToDict(policy):
    return {
        'training_gate_cases': policy.training_gate_cases,
        'base_review_rate': policy.base_review_rate,
        'trusted_review_rate': policy.trusted_review_rate,
        'trusted_after_clean': policy.trusted_after_clean,
        'probation_cases': policy.probation_cases,
        'gold_rate': policy.gold_rate,
        'duplicate_rate': policy.duplicate_rate,
        'gold_first_case': policy.gold_first_case,
        'lease_days': policy.lease_days,
        'stale_heartbeat_hours': policy.stale_heartbeat_hours,
        'max_concurrent': policy.max_concurrent,
        'gold_dice_flag': policy.gold_dice_flag,
        'duplicate_dice_flag': policy.duplicate_dice_flag,
    }


def getPolicy():
    """The current ``SamplingPolicy``.

    Falls back to defaults for any key the stored document is missing, so that
    adding a knob to ``SamplingPolicy`` does not require touching a running
    deployment's settings.
    """
    stored = Setting().get(SETTING_POLICY) or {}
    merged = _policyToDict(SamplingPolicy())
    merged.update({k: v for k, v in stored.items() if k in merged})
    return SamplingPolicy(**merged)


def getProject(maxConcurrent=None, quotaRemaining=None, uploadFolderId=''):
    """The current ``ProjectConfig``, optionally resolved for one user."""
    stored = Setting().get(SETTING_PROJECT) or {}
    policy = getPolicy()
    return ProjectConfig(
        name=stored.get('name', ''),
        instructions=stored.get('instructions', ''),
        segments=[SegmentSpec.from_dict(s) for s in stored.get('segments', [])],
        max_concurrent=(policy.max_concurrent if maxConcurrent is None else maxConcurrent),
        quota_remaining=quotaRemaining,
        upload_folder_id=uploadFolderId,
    )
