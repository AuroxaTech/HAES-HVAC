#!/usr/bin/env python3
"""
HAES HVAC - Run Report Once Script

Generate a report on-demand for testing.

Usage:
    uv run python scripts/run_report_once.py --type daily --date 2026-01-08
"""

import argparse
import json
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, ".")

from src.reporting.schema import ReportType
from src.reporting.generate import generate_report, generate_summary, get_period_for_report_type


def main() -> int:
    """Generate a report."""
    parser = argparse.ArgumentParser(description="Generate a HAES report")
    parser.add_argument(
        "--type",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Report type",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Reference date (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HAES HVAC - Report Generation")
    print("=" * 60)

    # Parse report type
    report_type = ReportType(args.type)

    # Parse reference date
    if args.date:
        reference_date = datetime.fromisoformat(args.date)
    else:
        reference_date = datetime.utcnow()

    print(f"\nReport Type: {report_type.value}")
    print(f"Reference Date: {reference_date.date()}")

    # Get period
    period_start, period_end = get_period_for_report_type(report_type, reference_date)
    print(f"Period: {period_start} to {period_end}")

    # Generate report
    print("\nGenerating report...")
    report = generate_report(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
    )

    # Generate summary
    summary = generate_summary(report)

    # Print results
    print("\n" + "-" * 60)
    print("Report Generated")
    print("-" * 60)

    print(f"\nKPIs ({len(report.kpis)}):")
    for kpi in report.kpis:
        if kpi.value is not None:
            print(f"  {kpi.name}: {kpi.value} {kpi.unit}")
        else:
            print(f"  {kpi.name}: N/A ({kpi.missing_reason})")

    if report.notes:
        print(f"\nNotes:")
        for note in report.notes:
            print(f"  - {note}")

    if report.alerts:
        print(f"\nAlerts:")
        for alert in report.alerts:
            print(f"  ⚠ {alert}")

    print("\n" + "-" * 60)
    print("Summary (SMS-safe)")
    print("-" * 60)
    print(f"{summary.report_type.value} ({summary.period})")
    print(summary.key_metrics)

    print("\n" + "=" * 60)
    print("PASS - Report generated successfully")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

