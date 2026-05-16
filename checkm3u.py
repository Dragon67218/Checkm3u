#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import sqlite3
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

DB = "iptv.db"
MAX_CONCURRENT = 40

# ==========================================
# 🇵🇾 BANNER PRY
# ==========================================
def banner():
    RED = "\033[91m"
    WHITE = "\033[97m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    print(f"""
{RED}██████╗ ██████╗ ██╗   ██╗{RESET}
{WHITE}██╔══██╗██╔══██╗╚██╗ ██╔╝{RESET}
{BLUE}██████╔╝██████╔╝ ╚████╔╝ {RESET}
{RED}██╔═══╝ ██╔══██╗  ╚██╔╝  {RESET}
{WHITE}██║     ██║  ██║   ██║   {RESET}
{BLUE}╚═╝     ╚═╝  ╚═╝   ╚═╝   {RESET}

{RED}🇵🇾 IPTV PLATFORM PRY 🇵🇾{RESET}
{WHITE}⚡ CHECK M3U PRO ⚡{RESET}
{BLUE}👨‍💻 Desarrollador: IMHOTEP{RESET}
{RED}⚡ Ultra Fast Scanner | Mobile Edition{RESET}
""")

# ==========================================
# 🧠 DETECTAR ENTORNO
# ==========================================
def is_termux():
    return "com.termux" in os.environ.get("PREFIX", "")

# ==========================================
# 🗄 DB
# ==========================================
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=OFF;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS streams (
        url TEXT PRIMARY KEY,
        name TEXT,
        score REAL,
        latency REAL,
        speed REAL
    )
    """)

    conn.commit()
    conn.close()

# ==========================================
# 📄 PARSER
# ==========================================
def parse_m3u(text):
    lines = text.splitlines()
    return [
        {"name": lines[i-1].split(",", 1)[-1] if i > 0 else "Canal", "url": l}
        for i, l in enumerate(lines)
        if l.startswith("http")
    ]

# ==========================================
# 📊 BARRA DE PROGRESO
# ==========================================
def progress_bar(current, total):
    bar_length = 20
    percent = current / total
    filled = int(bar_length * percent)

    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r[{bar}] {int(percent*100)}% ({current}/{total})", end="")

# ==========================================
# ⚡ CHECK
# ==========================================
async def check(session, sem, ch):
    async with sem:
        try:
            start = time.perf_counter()

            async with session.get(
                ch["url"],
                timeout=aiohttp.ClientTimeout(total=4)
            ) as r:

                if r.status != 200:
                    return None

                chunk = await r.content.read(8192)
                if not chunk:
                    return None

                latency = time.perf_counter() - start
                speed = (len(chunk) / latency) / 1024

                score = max(0, 100 - latency * 10) + min(speed / 50, 20)

                return {
                    "name": ch["name"],
                    "url": ch["url"],
                    "latency": latency,
                    "speed": speed,
                    "score": round(score, 2)
                }

        except:
            return None

# ==========================================
# 🚀 SCAN
# ==========================================
async def scan(url):
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)

    async with aiohttp.ClientSession(connector=connector) as session:
        print("📥 Descargando lista...")

        async with session.get(url) as r:
            text = await r.text()

        channels = parse_m3u(text)
        print(f"📺 {len(channels)} canales")

        tasks = [check(session, sem, c) for c in channels]

        results = []
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            res = await t
            if res:
                results.append(res)

            progress_bar(i, len(channels))

    print(f"\n✔ Activos: {len(results)}")
    return results

# ==========================================
# 💾 SAVE DB
# ==========================================
def save(results):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executemany("""
    INSERT OR REPLACE INTO streams
    VALUES (?, ?, ?, ?, ?)
    """, [
        (r["url"], r["name"], r["score"],
         r["latency"], r["speed"])
        for r in results
    ])

    conn.commit()
    conn.close()

# ==========================================
# 📁 GUARDAR TXT
# ==========================================
def save_txt(results):
    folder = "Resultadocheck"

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = time.strftime("resultado_%Y%m%d_%H%M%S.txt")
    path = os.path.join(folder, filename)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"{r['name']} | {r['score']} | {r['url']}\n")

    print(f"\n💾 Guardado en: {path}")

# ==========================================
# 🌐 API SIMPLE (QPython)
# ==========================================
def start_simple_api():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            conn = sqlite3.connect(DB)
            cur = conn.cursor()

            cur.execute("SELECT name, url, score FROM streams ORDER BY score DESC LIMIT 20")
            data = cur.fetchall()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            import json
            self.wfile.write(json.dumps(data).encode())

    print("🌐 API en http://0.0.0.0:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

# ==========================================
# 🚀 API PRO (TERMUX)
# ==========================================
def start_fastapi():
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()

    @app.get("/top")
    def top():
        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute("SELECT name, url, score FROM streams ORDER BY score DESC LIMIT 50")
        return cur.fetchall()

    print("🌐 API PRO en http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ==========================================
# 🎯 MAIN
# ==========================================
def main():
    banner()
    init_db()

    print("\033[91m1) Escanear lista\033[0m")
    print("\033[97m2) Ver top\033[0m")
    print("\033[94m3) Iniciar API\033[0m")

    op = input("> ")

    if op == "1":
        url = input("🌐 URL M3U: ")
        results = asyncio.run(scan(url))
        save(results)
        save_txt(results)

    elif op == "2":
        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute("SELECT name, score FROM streams ORDER BY score DESC LIMIT 20")

        print("\n🏆 TOP STREAMS:\n")
        for r in cur.fetchall():
            print(r)

    elif op == "3":
        if is_termux():
            start_fastapi()
        else:
            start_simple_api()

# ==========================================
if __name__ == "__main__":
    main()