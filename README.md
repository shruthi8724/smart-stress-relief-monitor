# Smart Stress Relief Monitor

Monitors heart rate, plays a calming track above the BPM threshold, and can send an email alert if the high reading continues.

## Run a demo

Python 3.10 or newer is recommended.

```powershell
python -m pip install -r requirements.txt
python stress_monitor.py
```

Demo mode is the default and runs without a paired watch. It plays a repeatable scenario: baseline readings, a sustained elevated episode, then recovery. After 15 seconds above the demo threshold, it prints a console-only demo alert; it does not send email. The recovery step prints an optional breathing cue. The included track is loaded from `musicplay/`.

This simulated scenario demonstrates program behavior; it is not a stress diagnosis or medical advice.

## Connect a watch app

The watch app (or a companion bridge that can access its heart-rate data) must be able to send HTTP `POST` requests. Start the monitor in receiver mode:

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

For a phone or watch app on the same Wi-Fi, bind to the computer's LAN address with `--host 0.0.0.0`, then configure the app/bridge to POST to the computer's LAN IP on port `8765`. Allow the port through the firewall only on a trusted network. The app's vendor and model determine whether it can send readings directly; many require a companion bridge or their own API. Do not expose this receiver to the public internet.

## Optional email alerts

Set `STRESS_MONITOR_SENDER`, `STRESS_MONITOR_APP_PASSWORD`, and `STRESS_MONITOR_RECEIVER` as environment variables to enable SMTP alerts. Use an email-provider app password, not your account password. Never commit credentials to GitHub.