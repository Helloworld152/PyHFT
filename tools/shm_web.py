import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from _shmringbuffer import ShmRingBufferReader


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SHM Tick Monitor</title>
  <style>
    :root {
      --bg: #f5f1e8;
      --panel: #fffdf8;
      --ink: #1f1a14;
      --muted: #7a6d5d;
      --line: #ded4c5;
      --accent: #b65a2a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at top, #fff8ee 0%, var(--bg) 55%);
      color: var(--ink);
      font-family: "Iosevka Aile", "JetBrains Mono", monospace;
    }
    .wrap {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .hero {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 20px;
    }
    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1;
      letter-spacing: -0.04em;
    }
    .meta {
      color: var(--muted);
      font-size: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(31, 26, 20, 0.06);
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }
    th {
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: #faf4ea;
    }
    tr:last-child td { border-bottom: 0; }
    .price { color: var(--accent); font-weight: 700; }
    .empty {
      padding: 28px 16px;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>SHM Tick Monitor</h1>
        <div class="meta" id="meta">loading...</div>
      </div>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Update</th>
            <th>Last</th>
            <th>Volume</th>
            <th>Bid1</th>
            <th>BidQty</th>
            <th>Ask1</th>
            <th>AskQty</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="8">waiting for ticks...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <script>
    async function refresh() {
      const res = await fetch('/api/latest', { cache: 'no-store' });
      const data = await res.json();
      document.getElementById('meta').textContent =
        `${data.name} | cached ${data.count} rows | refreshed ${new Date().toLocaleTimeString()}`;

      const rows = document.getElementById('rows');
      if (!data.items.length) {
        rows.innerHTML = '<tr><td class="empty" colspan="8">waiting for ticks...</td></tr>';
        return;
      }

      rows.innerHTML = data.items.map(item => `
        <tr>
          <td>${item.symbol}</td>
          <td>${item.update_time}</td>
          <td class="price">${item.last_price}</td>
          <td>${item.volume}</td>
          <td>${item.bid1_price}</td>
          <td>${item.bid1_volume}</td>
          <td>${item.ask1_price}</td>
          <td>${item.ask1_volume}</td>
        </tr>
      `).join('');
    }

    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


class TickCache:
    def __init__(self, name: str):
        self.name = name
        self.reader = ShmRingBufferReader(name)
        self.lock = threading.Lock()
        self.items_by_symbol = {}
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            batch = self.reader.poll()
            if not batch:
                time.sleep(0.01)
                continue
            mapped = [
                {
                    "symbol": item["symbol"],
                    "update_time": item["update_time"],
                    "last_price": item["last_price"],
                    "volume": item["volume"],
                    "bid1_price": item["bid_price"][0],
                    "bid1_volume": item["bid_volume"][0],
                    "ask1_price": item["ask_price"][0],
                    "ask1_volume": item["ask_volume"][0],
                }
                for item in batch
            ]
            with self.lock:
                for item in mapped:
                    self.items_by_symbol[item["symbol"]] = item

    def snapshot(self):
        with self.lock:
            return sorted(
                self.items_by_symbol.values(),
                key=lambda item: item["symbol"],
            )

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        self.reader.close()


def make_handler(cache: TickCache):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/api/latest":
                payload = {
                    "name": cache.name,
                    "count": len(cache.snapshot()),
                    "items": cache.snapshot()[:20],
                }
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve shm ticks on a minimal web page")
    parser.add_argument("name", help="shared memory ring name")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    cache = TickCache(args.name)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(cache))

    print(f"http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
        cache.close()


if __name__ == "__main__":
    raise SystemExit(main())
