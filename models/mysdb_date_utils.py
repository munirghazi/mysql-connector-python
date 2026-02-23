# -*- coding: utf-8 -*-
"""
Shared date/datetime normalization helpers.

All three data-source models (connector, API, sheet) need to coerce messy
incoming strings into clean Odoo date/datetime values.  This module
provides a single implementation so fixes and format additions are applied
everywhere at once.
"""
import re
from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

try:
    import dateutil.parser as _dateutil_parser
except ImportError:
    _dateutil_parser = None


def normalize_datetime(value):
    """Normalise *value* to an Odoo datetime string (``YYYY-MM-DD HH:MM:SS``).

    Handles:
    * ``None`` / ``False`` / empty string  → passthrough
    * ``datetime`` objects                 → formatted directly
    * ISO-8601 with ``T``, ``Z``, ``+HH:MM`` offset
    * Arabic AM/PM markers (``م`` / ``ص``)
    * ``DD/MM/YYYY HH:MM[:SS]``
    * ``YYYY-MM-DD HH:MM[:SS]``
    * Falls back to ``dateutil.parser.parse`` with *dayfirst=True*
    """
    if not value:
        return value
    if isinstance(value, datetime):
        return value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    cleaned = str(value).strip()

    # Arabic AM/PM
    cleaned = cleaned.replace('م', 'PM').replace('ص', 'AM').replace('|', '')

    # ISO-8601 cleanup: Z → +00:00, strip offset, remove T
    cleaned = cleaned.replace('Z', '+00:00')
    cleaned = re.sub(r'([+-]\d{2}:?\d{2})$', '', cleaned)
    cleaned = cleaned.replace('T', ' ').strip()

    # Remove sub-second precision (.123456)
    cleaned = re.sub(r'\.\d+', '', cleaned)

    # Try well-known formats first (fast path)
    for fmt in (DEFAULT_SERVER_DATETIME_FORMAT, '%Y-%m-%d %H:%M',
                '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        except ValueError:
            continue

    # Fallback: dateutil
    if _dateutil_parser:
        try:
            dt = _dateutil_parser.parse(cleaned, dayfirst=True)
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        except (ValueError, OverflowError):
            pass

    raise ValidationError(f"Invalid datetime value: {value}")


def normalize_date(value):
    """Normalise *value* to an Odoo date string (``YYYY-MM-DD``).

    Same logic as :func:`normalize_datetime` but returns date-only.
    """
    if not value:
        return value
    if isinstance(value, datetime):
        return value.strftime(DEFAULT_SERVER_DATE_FORMAT)

    cleaned = str(value).strip()
    cleaned = cleaned.replace('م', 'PM').replace('ص', 'AM').replace('|', '')

    for fmt in (DEFAULT_SERVER_DATE_FORMAT, '%d/%m/%Y'):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
        except ValueError:
            continue

    # Try ISO-8601 (may include time part — discard it)
    try:
        return datetime.fromisoformat(cleaned).strftime(DEFAULT_SERVER_DATE_FORMAT)
    except (ValueError, TypeError):
        pass

    # Fallback: dateutil
    if _dateutil_parser:
        try:
            dt = _dateutil_parser.parse(cleaned, dayfirst=True)
            return dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
        except (ValueError, OverflowError):
            pass

    raise ValidationError(f"Invalid date value: {value}")


def normalize_date_field(value, field_type):
    """Dispatch to :func:`normalize_datetime` or :func:`normalize_date`
    based on the Odoo *field_type* (``'datetime'`` or ``'date'``)."""
    if field_type == 'datetime':
        return normalize_datetime(value)
    return normalize_date(value)
