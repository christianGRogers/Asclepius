"""SegQueue14's settings: ``segqueue14.policy``, ``segqueue14.project`` and
``segqueue14.reference``. Same shape and validation as the live plugin's, under
keys of its own, so an admin can tune either project without touching the other.
"""

import json

from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.utility import setting_utilities
from segqueue.policy import SamplingPolicy
from segqueue.protocol import ProjectConfig, SegmentSpec
from segqueue14 import labels

from .constants import SETTING_POLICY, SETTING_PROJECT, SETTING_REFERENCE

#: Where SegQueue14's defaults differ from ``SamplingPolicy``'s:
#:
#: * no gold cases and no *random* duplicates. The ImageCAS-X reference replaces
#:   gold seeding, and the blind duplicates are data -- chosen once by
#:   ``segqueue14-populate`` (D11) -- so a roll at serve time would double them.
POLICY_OVERRIDES = {
    'gold_rate': 0.0,
    'duplicate_rate': 0.0,
    'gold_first_case': False,
}

#: Automatic-score thresholds. A submission scoring below any of them goes to a
#: reviewer regardless of the sampling roll.
#:
#: * ``mean_dice_flag`` -- mean per-class Dice against ImageCAS-X, over the classes
#:   present in either volume.
#: * ``required_dice_flag`` -- the lowest Dice among LAD, LCx and RCA. The trunks
#:   are large and should agree closely; a low one usually means a wrong name.
#: * ``class_dice_flags`` -- optional ``{class: threshold}`` overrides.
#: * ``duplicate_mean_dice_flag`` -- mean Dice between the two reads of a two-read
#:   case (or a blind duplicate).
#:
#: These defaults are a starting point for the project lead to confirm on the
#: validation account (VALIDATION.md), not a measured operating point.
DEFAULT_REFERENCE = {
    'mean_dice_flag': 0.60,
    'required_dice_flag': 0.70,
    'class_dice_flags': {},
    'duplicate_mean_dice_flag': 0.60,
}


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


def defaultPolicyDict():
    value = _policyToDict(SamplingPolicy())
    value.update(POLICY_OVERRIDES)
    return value


def defaultProjectDict():
    return {
        'name': labels.PROJECT_NAME,
        'instructions': labels.INSTRUCTIONS,
        'segments': labels.segment_dicts(),
    }


@setting_utilities.default(SETTING_POLICY)
def _defaultPolicy():
    return defaultPolicyDict()


@setting_utilities.default(SETTING_PROJECT)
def _defaultProject():
    return defaultProjectDict()


@setting_utilities.default(SETTING_REFERENCE)
def _defaultReference():
    return dict(DEFAULT_REFERENCE)


@setting_utilities.validator(SETTING_POLICY)
def _validatePolicy(doc):
    value = _asDict(doc['value'], SETTING_POLICY)
    unknown = set(value) - set(defaultPolicyDict())
    if unknown:
        raise ValidationException(
            f"Unknown policy keys: {', '.join(sorted(unknown))}.", 'value')
    merged = defaultPolicyDict()
    merged.update(value)
    try:
        SamplingPolicy(**merged).validate()
    except (TypeError, ValueError) as exc:
        raise ValidationException(str(exc), 'value') from exc
    doc['value'] = value


@setting_utilities.validator(SETTING_PROJECT)
def _validateProject(doc):
    value = _asDict(doc['value'], SETTING_PROJECT)
    segments = value.get('segments') or []
    if not segments:
        raise ValidationException('A project needs at least one segment.', 'value')
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
            raise ValidationException(f'Two segments both use label {spec.label}.', 'value')
        seenNames.add(spec.name)
        seenLabels.add(spec.label)
    # The prelabels, the ImageCAS-X references and the scorer all speak
    # ImageCAS-X's label values. A project whose values drifted from them would
    # load every prelabel into the wrong segments and score every read against
    # the wrong vessels -- while looking entirely plausible.
    for spec in (SegmentSpec.from_dict(e) for e in segments):
        expected = labels.LABEL_VALUES.get(spec.name)
        if expected is not None and expected != spec.label:
            raise ValidationException(
                f'{spec.name} must keep ImageCAS-X label {expected}, not {spec.label}.',
                'value')
    doc['value'] = value


@setting_utilities.validator(SETTING_REFERENCE)
def _validateReference(doc):
    value = _asDict(doc['value'], SETTING_REFERENCE)
    unknown = set(value) - set(DEFAULT_REFERENCE)
    if unknown:
        raise ValidationException(
            f"Unknown reference keys: {', '.join(sorted(unknown))}.", 'value')
    for key in ('mean_dice_flag', 'required_dice_flag', 'duplicate_mean_dice_flag'):
        if key in value:
            _unitInterval(value[key], key)
    flags = value.get('class_dice_flags', {})
    if not isinstance(flags, dict):
        raise ValidationException('class_dice_flags must be an object.', 'value')
    for name, threshold in flags.items():
        if name not in labels.LABEL_VALUES:
            raise ValidationException(f'class_dice_flags: unknown class {name!r}.', 'value')
        _unitInterval(threshold, f'class_dice_flags.{name}')
    doc['value'] = value


def _unitInterval(value, key):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationException(f'{key} must be a number.', 'value') from None
    if not 0.0 <= number <= 1.0:
        raise ValidationException(f'{key} must be in [0, 1].', 'value')


def _asDict(value, key):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise ValidationException(f'{key} must be valid JSON: {exc}', 'value') from exc
    if not isinstance(value, dict):
        raise ValidationException(f'{key} must be a JSON object.', 'value')
    return value


def getPolicy():
    stored = Setting().get(SETTING_POLICY) or {}
    merged = defaultPolicyDict()
    merged.update({k: v for k, v in stored.items() if k in merged})
    return SamplingPolicy(**merged)


def getReference():
    stored = Setting().get(SETTING_REFERENCE) or {}
    merged = dict(DEFAULT_REFERENCE)
    merged.update({k: v for k, v in stored.items() if k in merged})
    return merged


def getProject(maxConcurrent=None, quotaRemaining=None, uploadFolderId=''):
    stored = Setting().get(SETTING_PROJECT) or {}
    policy = getPolicy()
    from segqueue14 import PROTOCOL_VERSION

    return ProjectConfig(
        name=stored.get('name', ''),
        instructions=stored.get('instructions', ''),
        segments=[SegmentSpec.from_dict(s) for s in stored.get('segments', [])],
        max_concurrent=(policy.max_concurrent if maxConcurrent is None else maxConcurrent),
        quota_remaining=quotaRemaining,
        upload_folder_id=uploadFolderId,
        protocol_version=PROTOCOL_VERSION,
    )
