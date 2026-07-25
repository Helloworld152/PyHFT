import argparse

import pyarrow.parquet as pq


def main() -> int:
    parser = argparse.ArgumentParser(description="Read parquet ticks for verification")
    parser.add_argument("path", help="parquet file path")
    parser.add_argument("--tail", type=int, default=5, help="number of rows to print from tail")
    args = parser.parse_args()

    table = pq.read_table(args.path)
    rows = table.to_pylist()

    print(f"rows={len(rows)}")
    for item in rows[-args.tail:]:
        print(
            item["symbol"],
            item["update_time"],
            item["last_price"],
            item["volume"],
            item["bid_price"][0],
            item["bid_volume"][0],
            item["ask_price"][0],
            item["ask_volume"][0],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
