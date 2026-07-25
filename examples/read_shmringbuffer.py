import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from _shmringbuffer import ShmRingBufferReader


def main() -> int:
    parser = argparse.ArgumentParser(description="Read messages from shm ring buffer")
    parser.add_argument("name", help="shared memory ring name")
    args = parser.parse_args()

    reader = ShmRingBufferReader(args.name)
    try:
        while True:
            batch = reader.poll()
            if not batch:
                time.sleep(0.01)
                continue
            for item in batch:
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
    finally:
        reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
