"""Synthetic tests for strict input preflight."""

import csv
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

from news_sentiment import InputPreflightError, preflight_inputs
from news_sentiment import input as input_module


CSV_HEADERS = ["symbol", "security", "gics_sector", "headquarters", "date_added"]
TIMEZONE_KEY = "America/New_York"


def _fixed_synthetic_zone(key):
    if key != TIMEZONE_KEY:
        raise AssertionError("Unexpected timezone key")
    return timezone(timedelta(hours=-5))


def _article(**changes):
    record = {
        "id": "article-1",
        "date": "2026-09-28T09:30",
        "headline": "Synthetic earnings update",
        "body": "Synthetic company reports results.",
    }
    record.update(changes)
    return record


def _constituent_row(ticker="ABC", security="Example Security", **changes):
    values = {
        "symbol": ticker,
        "security": security,
        "gics_sector": "Technology",
        "headquarters": "Synthetic City",
        "date_added": "2020-01-01",
    }
    values.update(changes)
    return [values.get(header, "") for header in CSV_HEADERS]


def _csv_text(rows, headers=None):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS if headers is None else headers)
    writer.writerows(rows)
    return output.getvalue()


def _nth_sunday(year, month, occurrence):
    first = datetime(year, month, 1)
    first_sunday = 1 + ((6 - first.weekday()) % 7)
    return first_sunday + (occurrence - 1) * 7


class _SyntheticEasternZone(tzinfo):
    """A small test-only DST zone with a spring gap and a fall fold."""

    _standard = timedelta(hours=-5)
    _daylight = timedelta(hours=1)

    def _transitions(self, year):
        start = datetime(year, 3, _nth_sunday(year, 3, 2), 2)
        end = datetime(year, 11, _nth_sunday(year, 11, 1), 2)
        return start, end

    def utcoffset(self, dt):
        if dt is None:
            return self._standard
        return self._standard + self.dst(dt)

    def dst(self, dt):
        if dt is None:
            return timedelta(0)
        local = dt.replace(tzinfo=None)
        start, end = self._transitions(local.year)
        if local.month < 3 or local.month > 11:
            return timedelta(0)
        if 3 < local.month < 11:
            return self._daylight
        if local.month == 3:
            if local.day < start.day:
                return timedelta(0)
            if local.day > start.day:
                return self._daylight
            if local.hour < 2:
                return timedelta(0)
            if local.hour >= 3:
                return self._daylight
            return self._daylight if dt.fold else timedelta(0)
        if local.day < end.day:
            return self._daylight
        if local.day > end.day:
            return timedelta(0)
        if local.hour < 1:
            return self._daylight
        if local.hour >= 2:
            return timedelta(0)
        return timedelta(0) if dt.fold else self._daylight

    def tzname(self, dt):
        return "Synthetic EDT" if dt is not None and self.dst(dt) else "Synthetic EST"

    def fromutc(self, dt):
        if dt.tzinfo is not self:
            raise ValueError("fromutc requires this synthetic zone")
        utc_value = dt.replace(tzinfo=None)
        start_local, end_local = self._transitions(utc_value.year)
        start_utc = start_local - self._standard
        end_utc = end_local - self._standard - self._daylight
        if start_utc <= utc_value < end_utc:
            local = utc_value + self._standard + self._daylight
            fold = 0
        elif end_utc <= utc_value < end_utc + timedelta(hours=1):
            local = utc_value + self._standard
            fold = 1
        else:
            local = utc_value + self._standard
            fold = 0
        return local.replace(tzinfo=self, fold=fold)


class PreflightInputTests(unittest.TestCase):
    def _run(self, news_text, constituents_text=None, *, resolver=_fixed_synthetic_zone):
        if constituents_text is None:
            constituents_text = _csv_text([_constituent_row()])
        with tempfile.TemporaryDirectory() as temporary_directory:
            news_path = Path(temporary_directory) / "news.json"
            constituents_path = Path(temporary_directory) / "constituents.csv"
            news_path.write_bytes(news_text.encode("utf-8"))
            constituents_path.write_bytes(constituents_text.encode("utf-8"))
            return preflight_inputs(
                str(news_path), str(constituents_path), timezone_resolver=resolver
            )

    def _issues(self, news_text, constituents_text=None, *, resolver=_fixed_synthetic_zone):
        with self.assertRaises(InputPreflightError) as captured:
            self._run(news_text, constituents_text, resolver=resolver)
        return captured.exception

    def test_valid_inputs_return_an_article_and_only_the_supplied_constituent(self):
        result = self._run(json.dumps([_article()]))

        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.articles[0].id, "article-1")
        self.assertEqual(result.articles[0].headline, "Synthetic earnings update")
        self.assertEqual(result.articles[0].body, "Synthetic company reports results.")
        self.assertEqual(result.canonical_tickers, ("ABC",))
        self.assertEqual(result.articles[0].published_at.utcoffset(), timedelta(hours=-5))
        self.assertEqual(result.counts.eligible_articles, 1)
        self.assertEqual(len(result.snapshots.news_sha256), 64)

    def test_requests_the_exact_new_york_key_from_the_injected_resolver(self):
        requested = []

        def resolver(key):
            requested.append(key)
            return timezone.utc

        self._run(json.dumps([_article()]), resolver=resolver)

        self.assertEqual(requested, [TIMEZONE_KEY])

    def test_reads_each_input_into_one_snapshot(self):
        original_read_bytes = Path.read_bytes
        with tempfile.TemporaryDirectory() as temporary_directory:
            news_path = Path(temporary_directory) / "news.json"
            constituents_path = Path(temporary_directory) / "constituents.csv"
            news_path.write_bytes(json.dumps([_article()]).encode("utf-8"))
            constituents_path.write_bytes(
                _csv_text([_constituent_row()]).encode("utf-8")
            )

            with patch.object(
                Path,
                "read_bytes",
                autospec=True,
                side_effect=lambda path: original_read_bytes(path),
            ) as read_bytes:
                result = preflight_inputs(
                    str(news_path),
                    str(constituents_path),
                    timezone_resolver=_fixed_synthetic_zone,
                )

        self.assertEqual(read_bytes.call_count, 2)
        self.assertEqual(len(result.articles), 1)

    def test_accepts_more_than_one_hundred_records_and_future_timestamps(self):
        records = [
            _article(id=f"article-{index}", date="2027-01-01T00:00")
            for index in range(101)
        ]

        result = self._run(json.dumps(records))

        self.assertEqual(result.counts.article_records, 101)
        self.assertEqual(result.counts.eligible_articles, 101)
        self.assertFalse(result.warnings)

    def test_rejects_non_list_roots_non_object_items_malformed_json_and_nan(self):
        cases = [
            ('{"article": 1}', "news_root_not_list"),
            ('["not an object"]', "article_not_object"),
            ('[{broken]', "invalid_json"),
            ('[{"value": NaN}]', "invalid_json"),
        ]
        for raw, code in cases:
            with self.subTest(code=code):
                error = self._issues(raw)
                self.assertIn(code, {issue.code for issue in error.issues})

    def test_rejects_duplicate_json_keys_without_echoing_source_text(self):
        marker = "SYNTHETIC-PRIVATE-ARTICLE-MARKER"
        raw = (
            '[{"id":"article-1","id":"article-2",'
            '"date":"2026-09-28T09:30","headline":"' + marker + '",'
            '"body":"Synthetic body"}]'
        )

        error = self._issues(raw)

        self.assertIn("duplicate_json_key", {issue.code for issue in error.issues})
        self.assertNotIn(marker, str(error))
        self.assertNotIn(marker, repr(error.issues))

    def test_duplicate_keys_inside_extra_objects_are_also_blocking(self):
        raw = (
            '[{"id":"article-1","date":"2026-09-28T09:30",'
            '"headline":"Synthetic","body":"Synthetic body",'
            '"extra":{"tag":"first","tag":"second"}}]'
        )

        error = self._issues(raw)

        self.assertEqual(
            [issue.code for issue in error.issues].count("duplicate_json_key"), 1
        )

    def test_requires_valid_ids_and_text_fields(self):
        cases = [
            ({"id": True}, "invalid_id_type", "id"),
            ({"id": 1.0}, "invalid_id_type", "id"),
            ({"id": " article-1"}, "invalid_id_whitespace", "id"),
            ({"id": "   "}, "invalid_id_whitespace", "id"),
            ({"headline": None}, "invalid_text_type", "headline"),
            ({"body": 3}, "invalid_text_type", "body"),
            ({"headline": ""}, None, None),
            ({"body": None}, "invalid_text_type", "body"),
        ]
        for changes, code, field_name in cases:
            if code is None:
                continue
            with self.subTest(changes=changes):
                error = self._issues(json.dumps([_article(**changes)]))
                self.assertIn(
                    (code, field_name),
                    {(issue.code, issue.field) for issue in error.issues},
                )

        missing_id = _article()
        del missing_id["id"]
        missing_date = _article()
        del missing_date["date"]
        for record, field_name in ((missing_id, "id"), (missing_date, "date")):
            with self.subTest(missing=field_name):
                error = self._issues(json.dumps([record]))
                self.assertIn(
                    ("required_field_missing", field_name),
                    {(issue.code, issue.field) for issue in error.issues},
                )

        error = self._issues(json.dumps([_article(date=20260928)]))
        self.assertIn("invalid_date_type", {issue.code for issue in error.issues})

        missing_headline = _article()
        del missing_headline["headline"]
        missing_body = _article()
        del missing_body["body"]
        for record, field_name in (
            (missing_headline, "headline"),
            (missing_body, "body"),
        ):
            with self.subTest(missing=field_name):
                error = self._issues(json.dumps([record]))
                self.assertIn(
                    ("required_field_missing", field_name),
                    {(issue.code, issue.field) for issue in error.issues},
                )

    def test_preserves_integer_article_ids_without_string_conversion(self):
        result = self._run(json.dumps([_article(id=73)]))

        self.assertEqual(result.articles[0].id, 73)
        self.assertIs(type(result.articles[0].id), int)

    def test_requires_exact_ascii_local_timestamp_format_and_calendar_date(self):
        invalid_dates = (
            "2026-9-28T09:30",
            "2026-09-28T09:30:00",
            "2026-09-28T09:30Z",
            " 2026-09-28T09:30",
            "２０２６-09-28T09:30",
            "2026-02-30T09:30",
            "0000-01-01T00:00",
        )
        for value in invalid_dates:
            with self.subTest(value=value):
                error = self._issues(json.dumps([_article(date=value)]))
                codes = {issue.code for issue in error.issues}
                self.assertTrue(
                    {"invalid_date_format", "invalid_calendar_date"} & codes
                )

    def test_deduplicates_identical_full_article_records(self):
        article = _article(extra={"source": "synthetic"})

        result = self._run(json.dumps([article, article]))

        self.assertEqual(result.counts.article_records, 2)
        self.assertEqual(result.counts.deduplicated_articles, 1)
        self.assertEqual(result.counts.eligible_articles, 1)
        self.assertIn("duplicate_article_deduplicated", {item.code for item in result.diagnostics})
        self.assertEqual(result.articles[0]._source_record["extra"]["source"], "synthetic")

    def test_conflicting_same_id_and_type_sensitive_extra_values_block(self):
        first = _article(extra={"value": True})
        second = _article(extra={"value": 1})

        error = self._issues(json.dumps([first, second]))

        self.assertIn(
            "duplicate_article_conflict", {issue.code for issue in error.issues}
        )

    def test_overflowing_json_numbers_remain_distinct_in_duplicate_records(self):
        base = json.dumps(_article())[:-1]
        first = base + ',"extra":{"value":1e400}}'
        second = base + ',"extra":{"value":2e400}}'

        error = self._issues(f"[{first},{second}]")

        self.assertIn(
            "duplicate_article_conflict", {issue.code for issue in error.issues}
        )

    def test_underflowing_and_finite_rounded_json_numbers_remain_distinct(self):
        base = json.dumps(_article())[:-1]
        cases = (
            ("1e-400", "2e-400"),
            ("9007199254740992.0", "9007199254740993.0"),
        )
        for first_value, second_value in cases:
            with self.subTest(first=first_value, second=second_value):
                first = base + ',"extra":{"value":' + first_value + "}}"
                second = base + ',"extra":{"value":' + second_value + "}}"

                error = self._issues(f"[{first},{second}]")

                self.assertIn(
                    "duplicate_article_conflict",
                    {issue.code for issue in error.issues},
                )
                self.assertNotIn(first_value, str(error))

    def test_equivalent_json_decimal_spellings_deduplicate_exactly(self):
        base = json.dumps(_article())[:-1]
        pairs = (("1.00", "1.0"), ("1e400", "10e399"))
        for first_value, second_value in pairs:
            with self.subTest(first=first_value, second=second_value):
                first = base + ',"extra":{"value":' + first_value + "}}"
                second = base + ',"extra":{"value":' + second_value + "}}"

                result = self._run(f"[{first},{second}]")

                self.assertEqual(result.counts.deduplicated_articles, 1)
                self.assertIsInstance(
                    result.articles[0]._source_record["extra"]["value"], Decimal
                )

    def test_json_decimal_outside_stdlib_exponent_range_fails_closed(self):
        base = json.dumps(_article())[:-1]
        raw_number = "1e999999999999999999999999999999999999999999"
        record = base + ',"extra":{"value":' + raw_number + "}}"

        error = self._issues(f"[{record}]")

        self.assertIn("invalid_json", {issue.code for issue in error.issues})
        self.assertNotIn(raw_number, str(error))

    def test_distinct_typed_ids_with_the_same_csv_spelling_block(self):
        error = self._issues(json.dumps([_article(id=1), _article(id="1")]))

        self.assertIn("csv_id_collision", {issue.code for issue in error.issues})

    def test_duplicate_conflict_is_detected_before_blank_body_omission(self):
        first = _article(body=" ")
        second = _article(body="Changed synthetic body")

        error = self._issues(json.dumps([first, second]))

        self.assertIn(
            "duplicate_article_conflict", {issue.code for issue in error.issues}
        )

    def test_blank_body_is_omitted_but_blank_headline_with_body_is_eligible(self):
        omitted = _article(id="article-omitted", headline="", body=" \t\n")
        blank_headline = _article(id="article-no-headline", headline=" \t", body=" Usable body ")

        result = self._run(json.dumps([omitted, blank_headline]))

        self.assertEqual([article.id for article in result.articles], ["article-no-headline"])
        self.assertEqual(result.articles[0].headline, " \t")
        self.assertEqual(result.articles[0].body, " Usable body ")
        self.assertEqual(result.counts.omitted_articles, 1)
        self.assertEqual([item.code for item in result.omissions], ["blank_body_omitted"])
        self.assertEqual([item.code for item in result.warnings], ["empty_headline_eligible"])

    def test_full_csv_rows_include_extras_and_preserve_security_and_metadata(self):
        headers = CSV_HEADERS + ["synthetic_extra"]
        row = [" ABC ", " Example Security ", "", "Synthetic City", "2020", "extra-value"]
        result = self._run(
            json.dumps([_article()]),
            _csv_text([row], headers=headers),
        )

        self.assertEqual(result.canonical_tickers, ("ABC",))
        self.assertEqual(result.constituents[0].security, " Example Security ")
        self.assertEqual(result.constituents[0]._source_record["symbol"], " ABC ")
        self.assertEqual(result.constituents[0]._source_record["synthetic_extra"], "extra-value")
        self.assertEqual(
            {item.code for item in result.diagnostics},
            {"ticker_whitespace_normalized", "empty_auxiliary_field"},
        )

    def test_identical_normalized_ticker_rows_deduplicate_but_differences_block(self):
        duplicate_rows = [
            ["ABC", "Example Security", "Technology", "Synthetic City", "2020", "same"],
            [" ABC ", "Example Security", "Technology", "Synthetic City", "2020", "same"],
        ]
        headers = CSV_HEADERS + ["extra"]
        result = self._run(
            json.dumps([_article()]), _csv_text(duplicate_rows, headers=headers)
        )
        self.assertEqual(result.counts.deduplicated_constituents, 1)
        self.assertEqual(result.canonical_tickers, ("ABC",))

        conflicting_rows = [duplicate_rows[0], duplicate_rows[1][:-1] + ["different"]]
        error = self._issues(
            json.dumps([_article()]), _csv_text(conflicting_rows, headers=headers)
        )
        self.assertIn(
            "duplicate_constituent_conflict", {issue.code for issue in error.issues}
        )

    def test_rejects_missing_or_repeated_headers_and_mismatched_rows(self):
        missing_header_text = _csv_text(
            [["ABC", "Example", "Technology", "City"]],
            headers=["symbol", "security", "gics_sector", "headquarters"],
        )
        error = self._issues(json.dumps([_article()]), missing_header_text)
        self.assertIn("required_header_missing", {issue.code for issue in error.issues})

        repeated_header_text = _csv_text(
            [["ABC", "Example", "Technology", "City", "2020", "other"]],
            headers=CSV_HEADERS + ["symbol"],
        )
        error = self._issues(json.dumps([_article()]), repeated_header_text)
        self.assertIn("duplicate_header", {issue.code for issue in error.issues})

        mismatched_text = ",".join(CSV_HEADERS) + "\nABC,Example\n"
        error = self._issues(json.dumps([_article()]), mismatched_text)
        self.assertIn("row_length_mismatch", {issue.code for issue in error.issues})

    def test_rejects_invalid_csv_syntax_empty_ticker_and_blank_security(self):
        malformed_csv = ",".join(CSV_HEADERS) + '\nABC,"unfinished\n'
        error = self._issues(json.dumps([_article()]), malformed_csv)
        self.assertIn("invalid_csv", {issue.code for issue in error.issues})

        rows = [
            _constituent_row(ticker=" \t", security="Example"),
            _constituent_row(ticker="XYZ", security=" \t "),
        ]
        error = self._issues(json.dumps([_article()]), _csv_text(rows))
        self.assertIn("empty_ticker", {issue.code for issue in error.issues})
        self.assertIn("empty_security", {issue.code for issue in error.issues})

    def test_does_not_normalize_ticker_case_or_auxiliary_values(self):
        row = ["abc", "  Company Name  ", "  sector  ", "  place  ", " date "]
        result = self._run(json.dumps([_article()]), _csv_text([row]))

        self.assertEqual(result.canonical_tickers, ("abc",))
        constituent = result.constituents[0]
        self.assertEqual(constituent.security, "  Company Name  ")
        self.assertEqual(constituent.gics_sector, "  sector  ")
        self.assertEqual(constituent.headquarters, "  place  ")
        self.assertEqual(constituent.date_added, " date ")

    def test_selects_only_the_preferred_classes_in_input_order(self):
        rows = [
            _constituent_row("GOOG", "Alphabet Class C"),
            _constituent_row("ABC", "Example Company"),
            _constituent_row("GOOGL", "Alphabet Class A"),
            _constituent_row("FOX", "Fox Class B"),
            _constituent_row("FOXA", "Fox Class A"),
            _constituent_row("NWS", "News Class B"),
            _constituent_row("NWSA", "News Class A"),
            _constituent_row("BRK.A", "Berkshire Class A"),
            _constituent_row("BRK.B", "Berkshire Class B"),
        ]

        result = self._run(json.dumps([_article()]), _csv_text(rows))

        self.assertEqual(result.canonical_tickers, ("ABC", "GOOGL", "FOXA", "NWSA", "BRK.B"))
        self.assertEqual(result.constituents[1].security, "Alphabet Class A")
        self.assertEqual(
            [item.code for item in result.diagnostics].count("nonpreferred_class_omitted"),
            4,
        )

    def test_secondary_class_without_its_preferred_row_blocks(self):
        error = self._issues(
            json.dumps([_article()]), _csv_text([_constituent_row("GOOG")])
        )

        self.assertIn("preferred_class_missing", {issue.code for issue in error.issues})

    def test_collects_news_csv_and_timezone_errors_before_blocking(self):
        private_marker = "SYNTHETIC-PRIVATE-ERROR-TEXT"
        bad_article = _article(body=None, headline=private_marker)
        error = self._issues(
            json.dumps([bad_article]),
            "symbol,security\nABC,Example\n",
            resolver=lambda _key: (_ for _ in ()).throw(RuntimeError(private_marker)),
        )

        codes = {issue.code for issue in error.issues}
        self.assertIn("invalid_text_type", codes)
        self.assertIn("required_header_missing", codes)
        self.assertIn("timezone_unavailable", codes)
        self.assertNotIn(private_marker, str(error))
        self.assertNotIn(private_marker, repr(error.issues))

    def test_timezone_is_not_resolved_when_no_calendar_valid_date_needs_it(self):
        calls = []

        def resolver(key):
            calls.append(key)
            raise RuntimeError("synthetic resolver should not run")

        error = self._issues(json.dumps([_article(date="not-a-date")]), resolver=resolver)

        self.assertIn("invalid_date_format", {issue.code for issue in error.issues})
        self.assertEqual(calls, [])
        self.assertNotIn("timezone_unavailable", {issue.code for issue in error.issues})

    def test_synthetic_timezone_gap_and_fold_are_blocked(self):
        zone = _SyntheticEasternZone()
        resolver = lambda key: zone if key == TIMEZONE_KEY else None
        cases = (
            ("2026-03-08T02:30", "nonexistent_local_time"),
            ("2026-11-01T01:30", "ambiguous_local_time"),
        )
        for value, expected_code in cases:
            with self.subTest(date=value):
                error = self._issues(
                    json.dumps([_article(date=value)]), resolver=resolver
                )
                self.assertIn(expected_code, {issue.code for issue in error.issues})

    def test_production_zoneinfo_failure_fails_closed_without_fallback(self):
        marker = "SYNTHETIC-TZDB-DETAIL"
        with patch.object(
            input_module,
            "ZoneInfo",
            side_effect=ZoneInfoNotFoundError(marker),
        ):
            error = self._issues(json.dumps([_article()]), resolver=None)

        self.assertIn("timezone_unavailable", {issue.code for issue in error.issues})
        self.assertNotIn(marker, str(error))

    def test_invalid_inputs_return_no_partial_preflight_result(self):
        error = self._issues(json.dumps([_article(body=None)]))

        self.assertIsInstance(error, InputPreflightError)
        self.assertEqual(len(error.issues), 1)


if __name__ == "__main__":
    unittest.main()
