"""Stress monitor with a no-watch demo mode and an HTTP BPM input mode."""

import argparse
import itertools
import json
import logging
import os
import smtplib
import sys
import threading
import time
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# ---------------- SETTINGS ----------------
THRESHOLD_BPM = 100
HIGH_DURATION = 120  # seconds
CHECK_INTERVAL = 5   # seconds

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = os.getenv("STRESS_MONITOR_SENDER", "")
APP_PASSWORD = os.getenv("STRESS_MONITOR_APP_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("STRESS_MONITOR_RECEIVER", "")

MUSIC_FILE = Path(__file__).resolve().parent / "musicplay" / "mixkit-yoga-song-444.mp3"
DEMO_BPM_VALUES = itertools.cycle((88, 108, 112, 96))
latest_bpm = None
latest_bpm_at = None
bpm_lock = threading.Lock()

logging.basicConfig(
    filename="stress_monitor.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --------------- EMAIL --------------------

def send_email(bpm):
    if not all((SENDER_EMAIL, APP_PASSWORD, RECEIVER_EMAIL)):
        raise RuntimeError(
            "Email is not configured. Set STRESS_MONITOR_SENDER, "
            "STRESS_MONITOR_APP_PASSWORD, and STRESS_MONITOR_RECEIVER."
        )

    msg = MIMEText(
        f"High heart rate detected.\n\nCurrent BPM: {bpm}\n"
        "Please check on the user immediately."
    )
    msg["Subject"] = "High Heart Rate Alert"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)

    print("Email alert sent.")
    logging.info("Email sent.")


# --------------- MUSIC --------------------

music_started = False

def play_music():
    global music_started
    if music_started:
        return
    if not HAS_PYGAME:
        print(f"Music unavailable: pygame is not installed for {sys.executable}.")
        print(f'Install it with: "{sys.executable}" -m pip install -r requirements.txt')
        return
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(str(MUSIC_FILE))
        pygame.mixer.music.play(-1)
        music_started = True
        print("Playing calming music...")
    except Exception as e:
        print("Unable to play music:", e)


def stop_music():
    global music_started
    if HAS_PYGAME and music_started:
        pygame.mixer.music.stop()
        music_started = False
        print("Music stopped.")


# -------- HEART RATE (SIMULATION) ---------

def get_heart_rate():
    """Return a repeatable BPM value for demos without a paired watch."""
    return next(DEMO_BPM_VALUES)


class BPMRequestHandler(BaseHTTPRequestHandler):
    """Accept app/bridge readings as JSON: {"bpm": 82}."""

    def do_POST(self):
        global latest_bpm, latest_bpm_at
        if self.path != "/bpm":
            self.send_error(404, "POST readings to /bpm")
            return

        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            value = payload["bpm"]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("bpm must be a number")
            if not 30 <= value <= 240:
                raise ValueError("bpm must be between 30 and 240")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_error(400, str(error))
            return

        with bpm_lock:
            latest_bpm = round(value)
            latest_bpm_at = time.time()
        self.send_response(202)
        self.end_headers()
        self.wfile.write(b"BPM received")

    def log_message(self, format, *args):
        logging.info("BPM app: " + format, *args)


def parse_args():
    parser = argparse.ArgumentParser(description="Smart Stress Relief heart-rate monitor")
    parser.add_argument(
        "--source",
        choices=("demo", "watch"),
        default="demo",
        help="Use repeatable demo readings or receive BPM from a watch app/bridge (default: demo).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Watch receiver bind address")
    parser.add_argument("--port", type=int, default=8765, help="Watch receiver port")
    return parser.parse_args()


# ---------------- MAIN --------------------

def main(args):
    print("Smart Stress Relief Monitor Started")
    print("Press Ctrl+C to stop.\n")

    server = None
    if args.source == "watch":
        server = ThreadingHTTPServer((args.host, args.port), BPMRequestHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Waiting for watch-app readings at http://{args.host}:{args.port}/bpm")

    high_start = None
    email_sent = False

    try:
        while True:
            if args.source == "demo":
                bpm = get_heart_rate()
            else:
                with bpm_lock:
                    bpm = latest_bpm
                    reading_age = time.time() - latest_bpm_at if latest_bpm_at else None
                if bpm is None or reading_age > 30:
                    high_start = None
                    email_sent = False
                    stop_music()
                    print("Waiting for a fresh BPM reading...")
                    time.sleep(CHECK_INTERVAL)
                    continue

            print(f"Current BPM: {bpm}")
            logging.info("BPM=%s", bpm)

            if bpm > THRESHOLD_BPM:
                play_music()

                if high_start is None:
                    high_start = time.time()
                    email_sent = False

                elapsed = time.time() - high_start

                if elapsed >= HIGH_DURATION and not email_sent:
                    try:
                        send_email(bpm)
                        email_sent = True
                    except Exception as error:
                        print("Email failed:", error)
                        logging.exception(error)
            else:
                high_start = None
                email_sent = False
                stop_music()

            time.sleep(CHECK_INTERVAL)
    finally:
        stop_music()
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    try:
        main(parse_args())
    except KeyboardInterrupt:
        print("\nStopped.")
