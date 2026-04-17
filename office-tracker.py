#!/usr/bin/env python3
"""
Calculates the office attendance status for the current month.
Reads events from iCloud CalDAV and counts Office / Holiday / Vacation days.

Requirements:
    pip install caldav

Environment variables:
    CALDAV_USER   — your Apple ID (email)
    CALDAV_PASS   — app-specific password from iCloud
"""

import os
import sys
from datetime import date, datetime, timedelta
from math import ceil

import caldav


CALDAV_URL    = "https://caldav.icloud.com"
CALDAV_USER   = os.environ["CALDAV_USER"]
CALDAV_PASS   = os.environ["CALDAV_PASS"]
CALENDAR_NAME = "trabajo"

TITLE_OFFICE   = "Oficina"
TITLE_HOLIDAY  = "Festivo"
TITLE_VACATION = "Vacación"
OFFICE_RATIO   = 0.40


def get_month_range(today: date) -> tuple[date, date]:
    """Returns the first and last day of the month for the given date."""
    start = today.replace(day=1)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return start, end


def count_weekdays(start: date, end: date) -> int:
    """Counts weekdays (Monday–Friday) between start and end, inclusive."""
    total = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # 0=Monday, 4=Friday
            total += 1
        current += timedelta(days=1)
    return total


def get_calendar(client: caldav.DAVClient) -> caldav.Calendar:
    """Finds and returns the calendar matching CALENDAR_NAME."""
    principal = client.principal()
    for cal in principal.calendars():
        if cal.get_display_name().lower() == CALENDAR_NAME.lower():
            return cal
    names = [c.get_display_name() for c in principal.calendars()]
    print(f"Error: calendar '{CALENDAR_NAME}' not found.")
    print(f"Available calendars: {names}")
    sys.exit(1)


def count_days_by_title(calendar: caldav.Calendar, title: str, start: date, end: date) -> int:
    """
    Counts the number of weekdays covered by events matching the given title
    within the specified date range. Handles multi-day events correctly.
    """
    start_dt = datetime(start.year, start.month, start.day)
    end_dt   = datetime(end.year,   end.month,   end.day, 23, 59, 59)
    events = calendar.search(start=start_dt, end=end_dt, event=True, expand=True)

    count = 0
    for event in events:
        summary = str(event.icalendar_component.get("SUMMARY", ""))
        if summary.strip().lower() != title.strip().lower():
            continue

        comp = event.icalendar_component
        ev_start = comp.get("DTSTART").dt
        ev_end   = comp.get("DTEND").dt

        # Normalize to date (all-day events already are date objects)
        if hasattr(ev_start, "date"):
            ev_start = ev_start.date()
        if hasattr(ev_end, "date"):
            ev_end = ev_end.date()

        # DTEND for all-day events is exclusive (points to next day), subtract 1
        ev_end = ev_end - timedelta(days=1)

        # Clamp to the current month range
        effective_start = max(ev_start, start)
        effective_end   = min(ev_end, end)

        # Count weekdays within the effective range
        current = effective_start
        while current <= effective_end:
            if current.weekday() < 5:  # Monday–Friday
                count += 1
            current += timedelta(days=1)

    return count


def main():
    today = date.today()
    start, end = get_month_range(today)

    print("Connecting to iCloud CalDAV...")
    with caldav.DAVClient(url=CALDAV_URL, username=CALDAV_USER, password=CALDAV_PASS) as client:
        cal = get_calendar(client)
        print(f"Calendar found: {cal.get_display_name()}\n")

        office_days   = count_days_by_title(cal, TITLE_OFFICE,   start, end)
        holiday_days  = count_days_by_title(cal, TITLE_HOLIDAY,  start, end)
        vacation_days = count_days_by_title(cal, TITLE_VACATION, start, end)

    total_weekdays  = count_weekdays(start, end)
    net_workdays    = total_weekdays - holiday_days - vacation_days
    required        = ceil(net_workdays * OFFICE_RATIO)
    remaining       = max(0, required - office_days)
    already_met     = office_days >= required

    month = today.strftime("%B %Y")
    print(f"📊 Office tracker — {month}")
    print(f"{'─' * 30}")
    print(f"Days in office:   {office_days} / {required} required")
    print(f"Remaining:        {remaining} day(s)")
    print()
    print(f"Total weekdays:   {total_weekdays}")
    print(f"Holidays:         {holiday_days}")
    print(f"Vacation:         {vacation_days}")
    print(f"Net workdays:     {net_workdays}")
    print()
    if already_met:
        surplus = office_days - required
        print(f"✅ 40% requirement met — you have {surplus} extra day(s).")
    else:
        print(f"⚠️  Still need {remaining} more day(s) to reach 40%.")


if __name__ == "__main__":
    main()
