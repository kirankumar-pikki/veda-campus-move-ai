# CampusMove AI

Hackathon-ready campus transportation AI agent built with Python, Flask, HTML and CSS.

## What makes it an agent?

The LLM can decide which transport tools to call, inspect their results, call additional tools when necessary, and then produce a final operational recommendation.

## Demo data

This project includes a deterministic simulated live-data layer for:
- bus GPS/progress
- ETA
- occupancy/seats
- delays
- traffic/roadblocks
- maintenance/safety incidents
- stop demand

It does NOT pretend to connect to a real campus feed. For a production deployment, replace the functions in `agent/tools.py` with real GTFS-Realtime/AVL/GPS, occupancy, dispatch and traffic APIs.

## Run

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

If using the included `.env` directly, edit `OPENAI_API_KEY`.

Open (https://veda-campus-move-ai-1.onrender.com/)
