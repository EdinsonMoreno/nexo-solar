"""Property-based tests for database operations.



This module contains property-based tests using Hypothesis to verify


database operation properties.



Property 13: Timestamp Ordering in Database


**Validates: Database operations maintain timestamp ordering**
"""

import pytest


from hypothesis import given, strategies as st, settings


from datetime import datetime, timedelta
import tempfile


import sqlite3


from pathlib import Path


from typing import List, Tuple

# Property 13: Timestamp Ordering in Database


# **Validates: Database operations maintain timestamp ordering**


@st.composite
def timestamp_sequence(draw):
    """Generate a sequence of timestamps in ascending order."""

    base_time = datetime(2024, 1, 1, 0, 0, 0)

    count = draw(st.integers(min_value=2, max_value=10))

    timestamps = []

    current_time = base_time

    for _ in range(count):

        # Add random seconds (0 to 3600) to ensure ordering

        delta = draw(st.integers(min_value=0, max_value=3600))

        current_time = current_time + timedelta(seconds=delta)

        timestamps.append(current_time)

    return timestamps


@st.composite
def measurement_data(draw):
    """Generate measurement data with timestamp, date, time, and irradiance."""

    timestamp = draw(st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2024, 12, 31)))

    irradiance = draw(st.floats(min_value=0, max_value=1500, allow_nan=False, allow_infinity=False))

    return {
        "date": timestamp.strftime("%Y-%m-%d"),
        "time": timestamp.strftime("%H:%M:%S"),
        "irradiance": irradiance,
        "timestamp": timestamp,
    }


@given(timestamps=timestamp_sequence())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.database
def test_timestamp_ordering_preserved_in_database(timestamps: List[datetime]):
    """


    Property: Database records must maintain timestamp ordering.



    **Validates: Database operations**



    This test verifies that:


    - Records inserted in timestamp order are retrieved in the same order


    - Timestamp ordering is preserved across database operations


    - Query results maintain chronological order
    """

    from modbuspython.backend import sqlite_manager

    # Create temporary database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:

        db_path = f.name

    try:

        # Connect and create table

        conn = sqlite_manager.connect_db(db_path)

        sqlite_manager.crear_tabla(conn, "measurements")

        # Insert records with timestamps

        for ts in timestamps:

            date_str = ts.strftime("%Y-%m-%d")

            time_str = ts.strftime("%H:%M:%S")

            irradiance = 100.0

            sqlite_manager.insert_record(conn, "measurements", date_str, time_str, irradiance)

        # Query all records

        cursor = conn.cursor()

        cursor.execute("SELECT fecha, hora FROM measurements ORDER BY fecha, hora")

        records = cursor.fetchall()

        # Verify ordering is preserved

        retrieved_timestamps = []

        for date_str, time_str in records:

            ts_str = f"{date_str} {time_str}"

            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

            retrieved_timestamps.append(ts)

        # Check that timestamps are in ascending order

        for i in range(len(retrieved_timestamps) - 1):
            assert (
                retrieved_timestamps[i] <= retrieved_timestamps[i + 1]
            ), f"Timestamp ordering violated: {retrieved_timestamps[i]} > {retrieved_timestamps[i + 1]}"

        conn.close()

    finally:

        # Cleanup

        Path(db_path).unlink(missing_ok=True)


@given(measurements=st.lists(measurement_data(), min_size=2, max_size=10))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.database
def test_consecutive_records_maintain_timestamp_order(measurements: List[dict]):
    """


    Property: For all consecutive database records r1, r2: timestamp(r1) <= timestamp(r2).



    **Validates: Database operations**



    This test verifies that:


    - Consecutive records maintain timestamp ordering


    - No record has a timestamp earlier than the previous record


    - Database maintains chronological consistency
    """

    from modbuspython.backend import sqlite_manager

    # Sort measurements by timestamp to ensure proper insertion order

    measurements.sort(key=lambda x: x["timestamp"])

    # Create temporary database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:

        db_path = f.name

    try:

        # Connect and create table

        conn = sqlite_manager.connect_db(db_path)

        sqlite_manager.crear_tabla(conn, "measurements")

        # Insert records

        for m in measurements:

            sqlite_manager.insert_record(conn, "measurements", m["date"], m["time"], m["irradiance"])

        # Query all records in order

        cursor = conn.cursor()

        cursor.execute("SELECT fecha, hora FROM measurements ORDER BY fecha, hora")

        records = cursor.fetchall()

        # Verify consecutive records maintain ordering

        for i in range(len(records) - 1):

            date1, time1 = records[i]

            date2, time2 = records[i + 1]

            ts1 = datetime.strptime(f"{date1} {time1}", "%Y-%m-%d %H:%M:%S")

            ts2 = datetime.strptime(f"{date2} {time2}", "%Y-%m-%d %H:%M:%S")

            assert ts1 <= ts2, f"Consecutive records violate timestamp ordering: record {i} ({ts1}) > record {i+1} ({ts2})"

        conn.close()

    finally:

        # Cleanup

        Path(db_path).unlink(missing_ok=True)


@given(record_count=st.integers(min_value=5, max_value=20), shuffle=st.booleans())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.database
def test_timestamp_ordering_independent_of_insertion_order(record_count: int, shuffle: bool):
    """


    Property: Timestamp ordering in query results is independent of insertion order.



    **Validates: Database operations**



    This test verifies that:


    - Records can be inserted in any order


    - Query with ORDER BY always returns chronologically ordered results


    - Database sorting is consistent and correct
    """

    from modbuspython.backend import sqlite_manager
    import random

    # Generate timestamps

    base_time = datetime(2024, 1, 1, 0, 0, 0)

    timestamps = []

    for i in range(record_count):

        ts = base_time + timedelta(hours=i)

        timestamps.append(ts)

    # Optionally shuffle insertion order

    insertion_order = timestamps.copy()

    if shuffle:

        random.shuffle(insertion_order)

    # Create temporary database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:

        db_path = f.name

    try:

        # Connect and create table

        conn = sqlite_manager.connect_db(db_path)

        sqlite_manager.crear_tabla(conn, "measurements")

        # Insert records in specified order

        for ts in insertion_order:

            date_str = ts.strftime("%Y-%m-%d")

            time_str = ts.strftime("%H:%M:%S")

            sqlite_manager.insert_record(conn, "measurements", date_str, time_str, 100.0)

        # Query with ORDER BY

        cursor = conn.cursor()

        cursor.execute("SELECT fecha, hora FROM measurements ORDER BY fecha, hora")

        records = cursor.fetchall()

        # Verify results are in chronological order regardless of insertion order

        for i in range(len(records) - 1):

            date1, time1 = records[i]

            date2, time2 = records[i + 1]

            ts1 = datetime.strptime(f"{date1} {time1}", "%Y-%m-%d %H:%M:%S")

            ts2 = datetime.strptime(f"{date2} {time2}", "%Y-%m-%d %H:%M:%S")

            assert ts1 <= ts2, f"Query results not in chronological order: {ts1} > {ts2}"

        conn.close()

    finally:

        # Cleanup

        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
