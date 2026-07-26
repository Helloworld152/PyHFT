import argparse
from pathlib import Path
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from _shmringbuffer import ShmRingBufferReader


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll shm ticks and write them to a parquet file")
    parser.add_argument("name", help="shared memory ring name")
    parser.add_argument("output", help="output parquet path")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reader = ShmRingBufferReader(args.name)
    writer = None

    try:
        while True:
            batch = reader.poll()
            if not batch:
                time.sleep(0.01)
                continue

            table = pa.Table.from_pylist(batch)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
            writer.write_table(table)
    except KeyboardInterrupt:
        return 0
    finally:
        reader.close()
        if writer is not None:
            writer.close()


if __name__ == "__main__":
    raise SystemExit(main())
