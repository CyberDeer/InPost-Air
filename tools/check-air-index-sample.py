"""Compare point air-index levels with the air-sensors endpoint."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import random
import secrets
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

POINTS_URL = "https://api-pl-points.easypack24.net/v1/points"
TIMEOUT = 30


def request_json(url):
    """Return an HTTP status and parsed JSON; a 404 may have an empty body."""
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return response.status, json.load(response)
    except HTTPError as err:
        if err.code == 404:
            return 404, None
        raise


def get_points():
    """Fetch all pages, including pages beyond the requested 50,000 items."""
    points = []
    page = 1
    while True:
        query = urlencode(
            {
                "type": "parcel_locker_only",
                "fields": "name,location_description,location,air_index_level",
                "per_page": 50000,
                "page": page,
            }
        )
        status, payload = request_json(f"{POINTS_URL}?{query}")
        if status != 200:
            raise ValueError(f"Points list returned HTTP {status}")
        points.extend(payload["items"])
        if page >= payload["total_pages"]:
            return points
        page += 1


def check_point(point):
    """Compare the list level with the availability of sensor readings."""
    code = point["name"]
    url = f"{POINTS_URL}/{quote(code, safe='')}"
    sensor_status, sensor = request_json(f"{url}/air-sensors")

    list_level = point.get("air_index_level")
    if sensor_status == 404:
        has_readings = False
    elif sensor_status == 200:
        current = (sensor or {}).get("current") or {}
        has_readings = bool(current.get("values"))
    else:
        return "error", f"sensors HTTP {sensor_status}"

    mismatches = []
    if (list_level is not None) != has_readings:
        mismatches.append("sensor readings do not match list level")

    result = "mismatch" if mismatches else "match"
    sensor_description = (
        "readings" if has_readings else f"HTTP {sensor_status}, no readings"
    )
    detail_description = f"list={list_level!r}, sensors={sensor_description}"
    if mismatches:
        detail_description += f" ({'; '.join(mismatches)})"
    return result, detail_description


def check_point_safely(point):
    """Keep individual request failures from stopping the sample."""
    try:
        return check_point(point)
    except (OSError, URLError, ValueError, KeyError, TypeError) as err:
        return "error", str(err)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="The sample size applies separately to null and non-null groups.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="number of lockers to sample from each group (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="random seed for reproducibility (generated and printed if omitted)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="maximum concurrent locker checks (default: 10)",
    )
    args = parser.parse_args()
    if args.sample_size < 1:
        parser.error("--sample-size must be at least 1")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    seed = args.seed if args.seed is not None else secrets.randbits(64)
    print(f"Seed: {seed}", flush=True)
    try:
        points = get_points()
    except (OSError, URLError, ValueError, KeyError) as err:
        print(f"Failed to fetch points: {err}", file=sys.stderr)
        return 1

    rng = random.Random(seed)
    missing_level = [p for p in points if "air_index_level" not in p]
    if missing_level:
        print(
            f"Warning: {len(missing_level)} points have no air_index_level field",
            file=sys.stderr,
        )
    groups = {
        "null": sorted(
            (
                p
                for p in points
                if "air_index_level" in p and p["air_index_level"] is None
            ),
            key=lambda p: p["name"],
        ),
        "non-null": sorted(
            (p for p in points if p.get("air_index_level") is not None),
            key=lambda p: p["name"],
        ),
    }
    counts = Counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for group, candidates in groups.items():
            count = min(args.sample_size, len(candidates))
            print(
                f"\n{group}: sampling {count} of {len(candidates)} lockers", flush=True
            )
            if count < args.sample_size:
                print("  Warning: fewer candidates than requested", flush=True)
            selected = rng.sample(candidates, count)
            for point, (result, detail) in zip(
                selected, executor.map(check_point_safely, selected)
            ):
                counts[(group, result)] += 1
                print(f"  {point['name']}: {result.upper()} — {detail}", flush=True)

    print("\nSummary:")
    for group in groups:
        print(
            f"  {group}: {counts[group, 'match']} matches, "
            f"{counts[group, 'mismatch']} mismatches, {counts[group, 'error']} errors"
        )
    return (
        1
        if missing_level
        or any(
            counts[group, result]
            for group in groups
            for result in ("mismatch", "error")
        )
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
