"""Strict input validation and preflight for the news sentiment pipeline."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException
from datetime import datetime, tzinfo, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


_NEWS_SOURCE = "news"
_CONSTITUENTS_SOURCE = "constituents"
_TIMEZONE_KEY = "America/New_York"
_REQUIRED_CSV_HEADERS = (
    "symbol",
    "security",
    "gics_sector",
    "headquarters",
    "date_added",
)
_ARTICLE_FIELDS = frozenset({"id", "date", "headline", "body"})
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", re.ASCII)
_SECONDARY_TO_PREFERRED = {
    "GOOG": "GOOGL",
    "FOX": "FOXA",
    "NWS": "NWSA",
    "BRK.A": "BRK.B",
}


@dataclass(frozen=True)
class InputDiagnostic:
    """A safe diagnostic containing no input values or parser messages."""

    source: str
    record: int | None
    field: str | None
    code: str
    severity: str


class InputPreflightError(ValueError):
    """All detectable blocking input issues, with a source-safe message."""

    def __init__(self, issues: tuple[InputDiagnostic, ...]):
        self.issues = issues
        codes = ", ".join(sorted({issue.code for issue in issues}))
        super().__init__(f"Input preflight failed with {len(issues)} blocking issue(s): {codes}")


@dataclass(frozen=True, repr=False)
class EligibleArticle:
    """Article fields eligible for later processing; its complete source is private."""

    id: int | str = field(repr=False)
    published_at: datetime = field(repr=False)
    headline: str = field(repr=False)
    body: str = field(repr=False)
    _source_record: Mapping[str, object] = field(repr=False, compare=False)

    def __repr__(self) -> str:
        return "EligibleArticle(<redacted>)"


@dataclass(frozen=True, repr=False)
class Constituent:
    """One allowed CSV constituent and its unmodified public display fields."""

    ticker: str
    security: str = field(repr=False)
    gics_sector: str = field(repr=False)
    headquarters: str = field(repr=False)
    date_added: str = field(repr=False)
    _source_record: Mapping[str, object] = field(repr=False, compare=False)

    def __repr__(self) -> str:
        return "Constituent(<redacted>)"


@dataclass(frozen=True)
class PreflightCounts:
    article_records: int
    eligible_articles: int
    omitted_articles: int
    deduplicated_articles: int
    constituent_records: int
    constituents: int
    deduplicated_constituents: int


@dataclass(frozen=True)
class SnapshotProvenance:
    """Digests of the exact source byte snapshots read during preflight."""

    news_sha256: str
    constituents_sha256: str


@dataclass(frozen=True)
class PreflightResult:
    articles: tuple[EligibleArticle, ...]
    constituents: tuple[Constituent, ...]
    canonical_tickers: tuple[str, ...]
    diagnostics: tuple[InputDiagnostic, ...]
    counts: PreflightCounts
    snapshots: SnapshotProvenance

    @property
    def warnings(self) -> tuple[InputDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "warning")

    @property
    def omissions(self) -> tuple[InputDiagnostic, ...]:
        return tuple(
            item for item in self.diagnostics if item.code == "blank_body_omitted"
        )


class _PairsObject:
    """Temporary JSON object representation that preserves duplicate keys."""

    def __init__(self, pairs: list[tuple[str, object]]):
        self.pairs = pairs


class _FrozenObject(Mapping[str, object]):
    """Small immutable mapping used to retain complete records without repr leaks."""

    __slots__ = ("_items",)

    def __init__(self, items: Iterator[tuple[str, object]]):
        self._items = tuple(items)

    def __getitem__(self, key: str) -> object:
        for item_key, value in self._items:
            if item_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)


@dataclass(frozen=True, repr=False)
class _NewsCandidate:
    position: int
    record: dict[str, object]
    id_value: int | str | None
    id_valid: bool
    naive_date: datetime | None
    headline: str | None
    headline_valid: bool
    body: str | None
    body_valid: bool


@dataclass(frozen=True, repr=False)
class _ConstituentCandidate:
    position: int
    ticker: str | None
    row: dict[str, str]
    normalized_values: tuple[str, ...]


def _error(
    issues: list[InputDiagnostic],
    source: str,
    code: str,
    *,
    record: int | None = None,
    field_name: str | None = None,
) -> None:
    issues.append(InputDiagnostic(source, record, field_name, code, "error"))


def _notice(
    diagnostics: list[InputDiagnostic],
    source: str,
    code: str,
    *,
    record: int | None = None,
    field_name: str | None = None,
    severity: str = "warning",
) -> None:
    diagnostics.append(InputDiagnostic(source, record, field_name, code, severity))


def _read_snapshot(
    path: str | Path, source: str, issues: list[InputDiagnostic]
) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except (OSError, TypeError, ValueError):
        _error(issues, source, "read_failed")
        return None


def _decode_snapshot(
    snapshot: bytes | None, source: str, issues: list[InputDiagnostic]
) -> str | None:
    if snapshot is None:
        return None
    try:
        return snapshot.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _error(issues, source, "invalid_utf8")
        return None


def _materialize_json(
    value: object,
    issues: list[InputDiagnostic],
    record: int | None,
) -> object:
    if isinstance(value, _PairsObject):
        result: dict[str, object] = {}
        for key, raw_value in value.pairs:
            child = _materialize_json(raw_value, issues, record)
            if key in result:
                _error(
                    issues,
                    _NEWS_SOURCE,
                    "duplicate_json_key",
                    record=record,
                    field_name=key if key in _ARTICLE_FIELDS else None,
                )
            else:
                result[key] = child
        return result
    if isinstance(value, list):
        return [_materialize_json(item, issues, record) for item in value]
    return value


def _reject_nonstandard_constant(_value: str) -> object:
    raise ValueError("Non-standard JSON constant")


def _parse_json_decimal(value: str) -> Decimal:
    """Retain JSON fractional and exponent values without binary-float rounding."""
    try:
        number = Decimal(value)
    except (DecimalException, ValueError):
        raise ValueError("JSON number is outside the exact decimal range") from None
    if not number.is_finite():
        raise ValueError("JSON number is outside the exact decimal range")
    return number


def _same_json_value(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return False
        return all(_same_json_value(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_json_value(a, b) for a, b in zip(left, right)
        )
    return left == right


def _valid_id(value: object) -> bool:
    if type(value) is int:
        return True
    if type(value) is str:
        return bool(value.strip()) and value == value.strip()
    return False


def _typed_id(value: int | str) -> tuple[type, int | str]:
    return (type(value), value)


def _validate_id(
    record: dict[str, object], position: int, issues: list[InputDiagnostic]
) -> tuple[int | str | None, bool]:
    if "id" not in record:
        _error(issues, _NEWS_SOURCE, "required_field_missing", record=position, field_name="id")
        return None, False
    value = record["id"]
    if not _valid_id(value):
        if type(value) is str:
            code = "invalid_id_whitespace"
        else:
            code = "invalid_id_type"
        _error(issues, _NEWS_SOURCE, code, record=position, field_name="id")
        return None, False
    return value, True


def _deduplicate_news(
    records: list[tuple[int, dict[str, object]]],
    issues: list[InputDiagnostic],
    diagnostics: list[InputDiagnostic],
) -> tuple[list[tuple[int, dict[str, object], int | str | None, bool]], int]:
    by_typed_id: dict[tuple[type, int | str], tuple[int, dict[str, object]]] = {}
    by_csv_id: dict[str, tuple[tuple[type, int | str], int]] = {}
    accepted: list[tuple[int, dict[str, object], int | str | None, bool]] = []
    deduplicated = 0

    for position, record in records:
        value, is_valid = _validate_id(record, position, issues)
        if not is_valid or value is None:
            accepted.append((position, record, None, False))
            continue

        typed_key = _typed_id(value)
        prior = by_typed_id.get(typed_key)
        if prior is not None:
            first_position, first_record = prior
            if _same_json_value(first_record, record):
                deduplicated += 1
                _notice(
                    diagnostics,
                    _NEWS_SOURCE,
                    "duplicate_article_deduplicated",
                    record=position,
                    field_name="id",
                    severity="info",
                )
                continue
            _error(
                issues,
                _NEWS_SOURCE,
                "duplicate_article_conflict",
                record=position,
                field_name="id",
            )
            accepted.append((position, record, value, True))
            continue

        csv_value = str(value)
        prior_csv_id = by_csv_id.get(csv_value)
        if prior_csv_id is not None and prior_csv_id[0] != typed_key:
            _error(
                issues,
                _NEWS_SOURCE,
                "csv_id_collision",
                record=position,
                field_name="id",
            )
        by_typed_id[typed_key] = (position, record)
        by_csv_id.setdefault(csv_value, (typed_key, position))
        accepted.append((position, record, value, True))

    return accepted, deduplicated


def _parse_date(
    record: dict[str, object], position: int, issues: list[InputDiagnostic]
) -> datetime | None:
    if "date" not in record:
        _error(issues, _NEWS_SOURCE, "required_field_missing", record=position, field_name="date")
        return None
    value = record["date"]
    if type(value) is not str:
        _error(issues, _NEWS_SOURCE, "invalid_date_type", record=position, field_name="date")
        return None
    if _DATE_PATTERN.fullmatch(value) is None:
        _error(issues, _NEWS_SOURCE, "invalid_date_format", record=position, field_name="date")
        return None
    try:
        return datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            int(value[11:13]),
            int(value[14:16]),
        )
    except ValueError:
        _error(issues, _NEWS_SOURCE, "invalid_calendar_date", record=position, field_name="date")
        return None


def _validate_text_field(
    record: dict[str, object],
    position: int,
    field_name: str,
    issues: list[InputDiagnostic],
) -> tuple[str | None, bool]:
    if field_name not in record:
        _error(
            issues,
            _NEWS_SOURCE,
            "required_field_missing",
            record=position,
            field_name=field_name,
        )
        return None, False
    value = record[field_name]
    if type(value) is not str:
        _error(
            issues,
            _NEWS_SOURCE,
            "invalid_text_type",
            record=position,
            field_name=field_name,
        )
        return None, False
    return value, True


def _parse_news(
    text: str | None,
    issues: list[InputDiagnostic],
    diagnostics: list[InputDiagnostic],
) -> tuple[list[_NewsCandidate], int, int]:
    if text is None:
        return [], 0, 0
    try:
        raw_root = json.loads(
            text,
            object_pairs_hook=_PairsObject,
            parse_float=_parse_json_decimal,
            parse_constant=_reject_nonstandard_constant,
        )
    except (json.JSONDecodeError, ValueError):
        _error(issues, _NEWS_SOURCE, "invalid_json")
        return [], 0, 0

    if not isinstance(raw_root, list):
        _materialize_json(raw_root, issues, None)
        _error(issues, _NEWS_SOURCE, "news_root_not_list")
        return [], 0, 0

    article_count = len(raw_root)
    records: list[tuple[int, dict[str, object]]] = []
    for position, raw_record in enumerate(raw_root, start=1):
        record = _materialize_json(raw_record, issues, position)
        if not isinstance(record, dict):
            _error(issues, _NEWS_SOURCE, "article_not_object", record=position)
            continue
        records.append((position, record))

    unique_records, deduplicated = _deduplicate_news(records, issues, diagnostics)
    candidates: list[_NewsCandidate] = []
    for position, record, id_value, id_valid in unique_records:
        naive_date = _parse_date(record, position, issues)
        headline, headline_valid = _validate_text_field(
            record, position, "headline", issues
        )
        body, body_valid = _validate_text_field(record, position, "body", issues)
        candidates.append(
            _NewsCandidate(
                position,
                record,
                id_value,
                id_valid,
                naive_date,
                headline,
                headline_valid,
                body,
                body_valid,
            )
        )
    return candidates, article_count, deduplicated


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return _FrozenObject((key, _freeze(child)) for key, child in value.items())
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _freeze_record(record: Mapping[str, object]) -> Mapping[str, object]:
    return _freeze(dict(record))  # type: ignore[return-value]


def _resolve_timezone(
    resolver: Callable[[str], tzinfo] | None, issues: list[InputDiagnostic]
) -> tzinfo | None:
    try:
        zone = ZoneInfo(_TIMEZONE_KEY) if resolver is None else resolver(_TIMEZONE_KEY)
        if not isinstance(zone, tzinfo):
            raise TypeError
        return zone
    except Exception:
        _error(
            issues,
            _NEWS_SOURCE,
            "timezone_unavailable",
            field_name="date",
        )
        return None


def _localize_timestamp(
    naive: datetime, zone: tzinfo
) -> tuple[datetime | None, str | None]:
    valid: list[tuple[datetime, datetime]] = []
    try:
        for fold in (0, 1):
            candidate = naive.replace(tzinfo=zone, fold=fold)
            instant = candidate.astimezone(timezone.utc)
            round_trip = instant.astimezone(zone)
            if round_trip.replace(tzinfo=None) == naive:
                valid.append((candidate, instant))
    except Exception:
        return None, "timezone_conversion_failed"

    if not valid:
        return None, "nonexistent_local_time"
    distinct_instants = {instant for _, instant in valid}
    if len(distinct_instants) > 1:
        return None, "ambiguous_local_time"
    return valid[0][0], None


def _resolve_article_dates(
    candidates: list[_NewsCandidate],
    resolver: Callable[[str], tzinfo] | None,
    issues: list[InputDiagnostic],
) -> dict[int, datetime]:
    dated = [candidate for candidate in candidates if candidate.naive_date is not None]
    if not dated:
        return {}
    zone = _resolve_timezone(resolver, issues)
    if zone is None:
        return {}

    resolved: dict[int, datetime] = {}
    for candidate in dated:
        localized, error_code = _localize_timestamp(candidate.naive_date, zone)
        if error_code is not None:
            _error(
                issues,
                _NEWS_SOURCE,
                error_code,
                record=candidate.position,
                field_name="date",
            )
        elif localized is not None:
            resolved[candidate.position] = localized
    return resolved


def _parse_constituents(
    text: str | None,
    issues: list[InputDiagnostic],
    diagnostics: list[InputDiagnostic],
) -> tuple[list[_ConstituentCandidate], int, int]:
    if text is None:
        return [], 0, 0
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        header = []
    except csv.Error:
        _error(issues, _CONSTITUENTS_SOURCE, "invalid_csv", record=1)
        return [], 0, 0

    if not header:
        _error(issues, _CONSTITUENTS_SOURCE, "missing_header", record=1)
    if len(set(header)) != len(header):
        _error(issues, _CONSTITUENTS_SOURCE, "duplicate_header", record=1)
    header_indexes: dict[str, int] = {}
    for index, name in enumerate(header):
        header_indexes.setdefault(name, index)
    for required in _REQUIRED_CSV_HEADERS:
        if required not in header_indexes:
            _error(
                issues,
                _CONSTITUENTS_SOURCE,
                "required_header_missing",
                record=1,
                field_name=required,
            )

    candidates: list[_ConstituentCandidate] = []
    ticker_rows: dict[str, tuple[int, tuple[str, ...]]] = {}
    record_position = 2
    row_count = 0
    deduplicated = 0
    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error:
            _error(
                issues,
                _CONSTITUENTS_SOURCE,
                "invalid_csv",
                record=record_position,
            )
            break
        row_count += 1
        if len(row) != len(header):
            _error(
                issues,
                _CONSTITUENTS_SOURCE,
                "row_length_mismatch",
                record=record_position,
            )
            record_position += 1
            continue

        row_values = {name: row[index] for index, name in enumerate(header)}
        normalized_row = list(row)
        ticker: str | None = None
        if "symbol" in header_indexes:
            raw_ticker = row[header_indexes["symbol"]]
            ticker = raw_ticker.strip()
            normalized_row[header_indexes["symbol"]] = ticker
            if not ticker:
                _error(
                    issues,
                    _CONSTITUENTS_SOURCE,
                    "empty_ticker",
                    record=record_position,
                    field_name="symbol",
                )
                ticker = None
            elif raw_ticker != ticker:
                _notice(
                    diagnostics,
                    _CONSTITUENTS_SOURCE,
                    "ticker_whitespace_normalized",
                    record=record_position,
                    field_name="symbol",
                )

        if "security" in row_values and not row_values["security"].strip():
            _error(
                issues,
                _CONSTITUENTS_SOURCE,
                "empty_security",
                record=record_position,
                field_name="security",
            )
        for auxiliary in ("gics_sector", "headquarters", "date_added"):
            if auxiliary in row_values and not row_values[auxiliary].strip():
                _notice(
                    diagnostics,
                    _CONSTITUENTS_SOURCE,
                    "empty_auxiliary_field",
                    record=record_position,
                    field_name=auxiliary,
                )

        comparable_row = tuple(normalized_row)
        if ticker is not None:
            prior = ticker_rows.get(ticker)
            if prior is not None:
                if prior[1] == comparable_row:
                    deduplicated += 1
                    _notice(
                        diagnostics,
                        _CONSTITUENTS_SOURCE,
                        "duplicate_constituent_deduplicated",
                        record=record_position,
                        field_name="symbol",
                        severity="info",
                    )
                    record_position += 1
                    continue
                _error(
                    issues,
                    _CONSTITUENTS_SOURCE,
                    "duplicate_constituent_conflict",
                    record=record_position,
                    field_name="symbol",
                )
                record_position += 1
                continue
            ticker_rows[ticker] = (record_position, comparable_row)

        candidates.append(
            _ConstituentCandidate(record_position, ticker, row_values, comparable_row)
        )
        record_position += 1

    return candidates, row_count, deduplicated


def _select_constituents(
    candidates: list[_ConstituentCandidate],
    issues: list[InputDiagnostic],
    diagnostics: list[InputDiagnostic],
) -> tuple[Constituent, ...]:
    available = {candidate.ticker for candidate in candidates if candidate.ticker is not None}
    selected: list[Constituent] = []
    for candidate in candidates:
        ticker = candidate.ticker
        if ticker is None:
            continue
        preferred = _SECONDARY_TO_PREFERRED.get(ticker)
        if preferred is not None:
            if preferred not in available:
                _error(
                    issues,
                    _CONSTITUENTS_SOURCE,
                    "preferred_class_missing",
                    record=candidate.position,
                    field_name="symbol",
                )
            else:
                _notice(
                    diagnostics,
                    _CONSTITUENTS_SOURCE,
                    "nonpreferred_class_omitted",
                    record=candidate.position,
                    field_name="symbol",
                    severity="info",
                )
            continue

        row = candidate.row
        selected.append(
            Constituent(
                ticker=ticker,
                security=row.get("security", ""),
                gics_sector=row.get("gics_sector", ""),
                headquarters=row.get("headquarters", ""),
                date_added=row.get("date_added", ""),
                _source_record=_freeze_record(row),
            )
        )
    return tuple(selected)


def preflight_inputs(
    news_path: str | Path,
    constituents_path: str | Path,
    *,
    timezone_resolver: Callable[[str], tzinfo] | None = None,
) -> PreflightResult:
    """Read both inputs once and validate them before returning any valid result.

    The production path always requests the IANA ``America/New_York`` zone.
    The optional resolver is a deterministic test seam; it receives that exact
    key and must return a real ``tzinfo`` implementation.
    """
    issues: list[InputDiagnostic] = []
    diagnostics: list[InputDiagnostic] = []

    news_snapshot = _read_snapshot(news_path, _NEWS_SOURCE, issues)
    constituents_snapshot = _read_snapshot(
        constituents_path, _CONSTITUENTS_SOURCE, issues
    )
    news_text = _decode_snapshot(news_snapshot, _NEWS_SOURCE, issues)
    constituents_text = _decode_snapshot(
        constituents_snapshot, _CONSTITUENTS_SOURCE, issues
    )

    article_candidates, article_count, deduplicated_articles = _parse_news(
        news_text, issues, diagnostics
    )
    constituent_candidates, constituent_record_count, deduplicated_constituents = (
        _parse_constituents(constituents_text, issues, diagnostics)
    )
    localized_dates = _resolve_article_dates(article_candidates, timezone_resolver, issues)
    constituents = _select_constituents(constituent_candidates, issues, diagnostics)

    articles: list[EligibleArticle] = []
    omitted_articles = 0
    for candidate in article_candidates:
        if (
            not candidate.id_valid
            or candidate.id_value is None
            or candidate.naive_date is None
            or candidate.position not in localized_dates
            or not candidate.headline_valid
            or not candidate.body_valid
            or candidate.headline is None
            or candidate.body is None
        ):
            continue
        if not candidate.body.strip():
            omitted_articles += 1
            _notice(
                diagnostics,
                _NEWS_SOURCE,
                "blank_body_omitted",
                record=candidate.position,
                field_name="body",
                severity="info",
            )
            continue
        if not candidate.headline.strip():
            _notice(
                diagnostics,
                _NEWS_SOURCE,
                "empty_headline_eligible",
                record=candidate.position,
                field_name="headline",
            )
        articles.append(
            EligibleArticle(
                id=candidate.id_value,
                published_at=localized_dates[candidate.position],
                headline=candidate.headline,
                body=candidate.body,
                _source_record=_freeze_record(candidate.record),
            )
        )

    if issues:
        raise InputPreflightError(tuple(issues)) from None

    canonical_tickers = tuple(constituent.ticker for constituent in constituents)
    counts = PreflightCounts(
        article_records=article_count,
        eligible_articles=len(articles),
        omitted_articles=omitted_articles,
        deduplicated_articles=deduplicated_articles,
        constituent_records=constituent_record_count,
        constituents=len(constituents),
        deduplicated_constituents=deduplicated_constituents,
    )
    snapshots = SnapshotProvenance(
        news_sha256=hashlib.sha256(news_snapshot).hexdigest(),
        constituents_sha256=hashlib.sha256(constituents_snapshot).hexdigest(),
    )
    return PreflightResult(
        articles=tuple(articles),
        constituents=constituents,
        canonical_tickers=canonical_tickers,
        diagnostics=tuple(diagnostics),
        counts=counts,
        snapshots=snapshots,
    )
