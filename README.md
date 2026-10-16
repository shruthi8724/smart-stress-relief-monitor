# Smart Stress Relief Monitor

Python prototype that plays calming music when BPM rises above a threshold. It includes a scripted demo and an optional HTTP endpoint for BPM readings sent by an external app or bridge. It does not connect directly to a smartwatch or Google Fit.

## Run a demo

Python 3.10 or newer is recommended.

```powershell
python -m pip install -r requirements.txt
python stress_monitor.py
```

Demo mode is the default and needs no watch. It plays a scripted sequence of baseline, elevated, and recovery readings. Music starts above 100 BPM and stops when the reading falls below the threshold. After 15 seconds of elevated demo readings, it prints a demo alert without sending email, followed by an optional breathing cue. The included track is loaded from `musicplay/`.

This uses simulated readings to demonstrate behavior; it is not a stress diagnosis or medical advice.

## Optional external BPM input

Watch mode starts an HTTP receiver. An external app or bridge must provide the BPM readings; this repository does not include a watch app or a direct wearable integration. Start the receiver with:

```powershell
python stress_monitor.py --source watch
```

The receiver listens at `http://127.0.0.1:8765/bpm` and accepts JSON in this format:

```json
{"bpm": 82}
```

Readings older than 30 seconds are ignored until the app sends another update.

For example, test the receiver from another PowerShell window:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/bpm -ContentType 'application/json' -Body '{"bpm": 108}'
```

To receive readings from another device on the same trusted Wi-Fi, bind with `--host 0.0.0.0` and configure the app or bridge to POST to this computer's LAN IP on port `8765`. The receiver has no authentication; only use it on a trusted network and do not expose it to the public internet.

## Optional email alerts

In watch mode, an email alert is attempted if BPM stays above 100 for 120 seconds. Configure `STRESS_MONITOR_SENDER`, `STRESS_MONITOR_APP_PASSWORD`, and `STRESS_MONITOR_RECEIVER` as environment variables to enable SMTP. The demo mode never sends email. Use an email-provider app password, not your account password, and never commit credentials to GitHub.