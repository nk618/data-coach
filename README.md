# Data Coach

A local Windows desktop coach for a **21-day data analyst sprint**. It combines a study plan,
a skill diagnostic, daily tasks, progress tracking, and a Gemini-powered mentor that knows
where you are and what you're weak at.

Your data stays on this PC. Only chat text is sent to Google Gemini.

---

## Quick start

1. **Set up once:** double-click `Setup Data Coach.bat` and wait for it to finish.
2. **Launch:** double-click `Start Data Coach.bat` (or the `Data Coach` desktop shortcut).
3. **Connect the AI:** create a free key at <https://aistudio.google.com/apikey>, then paste it
   into **Settings → AI connection** and click **Test connection**.
4. **Start Day 1:** finish onboarding (profile → self-ratings → 12-question diagnostic) and the
   plan is created automatically.

If Python is missing, install Python 3.10+ from python.org and tick
**"Add python.exe to PATH"** during installation.

### Standalone desktop build (no Python needed)

The packaged app is one folder with `DataCoach.exe` inside. Python, Git, and the
command line are not required to run it.

1. Unzip `DataCoach-win64.zip` to a permanent folder, for example `C:\Apps\DataCoach`.
2. Double-click `DataCoach.exe`.
3. Profile, progress, and chat history are stored in `%LOCALAPPDATA%\DataCoach`.

Build it yourself with:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1 -Zip
```

That produces `dist\DataCoach\DataCoach.exe` and, with `-Zip`, `dist\DataCoach-win64.zip`.
The build bundles the Python runtime, Streamlit, and the WebView2 shell. If WebView2 is
missing, the app opens in your default browser instead.

### Desktop shortcut

For the source checkout, run once in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\create_shortcut.ps1
```

---

## What's in this build (Phase 1)

- **Onboarding** — profile, six skill self-ratings, a 12-question diagnostic with explanations,
  and a calibrated 21-day plan.
- **Today** — the day's Learn / Build / Prove / Log tasks, checkboxes, focus minutes, and the
  deliverable for the day.
- **Coach** — streaming chat grounded in your current day, skill levels, weak areas, and sprint
  progress. Direct feedback, one quiz question at a time, exact SQL/pandas/DAX examples.
- **Progress** — completion stats, study streak, a skill radar, weak areas, and the full roadmap
  with the ability to open any day.
- **Settings** — secure API key storage (Windows Credential Locker), model selection,
  connection test, editable profile, local data folder, and reset.
- **Native window** — opens in its own desktop window via WebView2; falls back to the browser if
  WebView2 is unavailable.
- **Standalone build** — `DataCoach.exe` bundles the runtime, Streamlit, and the window shell, so
  it runs on a clean Windows PC without Python installed.
- **Data Lab** — upload CSV/Excel, auto-profile, cleaning checklist with pandas code, sandboxed
  SQL queries via DuckDB, and export of cleaned data.
- **Interview Room** — configurable timed mock interviews (focus, difficulty, length) with
  one-question-at-a-time flow and a scored report card.
- **Dashboard Coach** — turn business questions into KPIs, charts, and DAX; upload a screenshot
  for a scored critique.
- **Job tracker** — log applications, track pipeline status, follow-up reminders, and ask the
  coach to review your pipeline.

---

## The 21-day sprint

| Week | Theme | Outcome |
|---|---|---|
| 1 | Foundations & Project 1 — e-commerce | SQL fundamentals, data understanding, cleaning, EDA, first Power BI dashboard, published project |
| 2 | Depth & Project 2 — HR analytics | Advanced SQL, statistics, DAX, second dashboard, harder mocks |
| 3 | Interview & job readiness | Finance case, resume/LinkedIn, STAR stories, daily mocks, 10–15 applications |

Each day has four task types:

- **Learn** — the concept, with a resource.
- **Build** — apply it to the project.
- **Prove** — explain, validate, or take a drill.
- **Log** — write the artifact (README, cleaning log, insight bullets).

Planning for 3–4 focused hours per day. If a day slips, open the day from **Progress** and
continue — don't skip the deliverable.

---

## Project structure

```
DataCoach/
├─ app.py                  Streamlit entry point
├─ desktop.py              Frozen-app entry: server + native window
├─ launcher.pyw            Source-checkout launcher (same behaviour)
├─ datacoach.spec          PyInstaller build definition
├─ build_desktop.ps1       Builds dist\DataCoach\DataCoach.exe
├─ version_info.txt        Windows file properties for the exe
├─ Start Data Coach.bat    Normal launch from source
├─ Setup Data Coach.bat    One-time install
├─ create_shortcut.ps1     Desktop shortcut helper
├─ assets/
│  ├─ diagnostic.json      12 diagnostic questions with explanations
│  ├─ sprint_21day.json    The full 21-day plan
│  └─ icon.ico             App and window icon
├─ core/
│  ├─ config.py            Paths, constants, keyring access
│  ├─ db.py                SQLite schema and queries
│  ├─ diagnostic.py        Scoring and skill blending
│  ├─ llm.py               Gemini wrapper and friendly errors
│  ├─ prompts.py           Coach system prompt
│  └─ roadmap.py           Sprint template and current-day logic
├─ ui/
│  ├─ onboarding.py        Four-step setup wizard
│  ├─ styles.py            Shared CSS and cards
│  └─ pages/               Today, Coach, Data Lab, Interview Room, Dashboard Coach, Job Tracker, Progress, Settings
├─ data/                   Runtime database and logs — not in git
├─ dist/                   Build output — not in git
└─ tests/                  Core logic and UI smoke tests
```

The frozen build writes to `%LOCALAPPDATA%\DataCoach\` instead of `data/`, so updates never
overwrite your progress. The Gemini key stays in Windows Credential Locker across both builds.

---

## Troubleshooting

**Nothing opens when I double-click Start.**
Run `Setup Data Coach.bat` again. Check `data/launcher.log` and `data/streamlit.log`.

**The window opens but the coach says it needs a key.**
Go to Settings, paste the key from <https://aistudio.google.com/apikey>, click **Save key**,
then **Test connection**.

**"Free-tier limit reached."**
Wait a minute, or choose `gemini-2.0-flash-lite` in Settings. The daily limit resets.

**The dashboard asks for a key every time.**
The key is stored in Windows Credential Locker. If that service is unavailable, use a `.env`
file with `GEMINI_API_KEY=...` (copy `.env.example`).

**I want to start over.**
Settings → Data and privacy → type `RESET` → **Reset all data**. Your API key is kept.

---

## Privacy

- Profile, roadmap, progress, and chat history: local SQLite at `data/coach.db`.
- API key: Windows Credential Locker (or `.env` if you choose).
- Data sent to Google: the chat text and the coach prompt (your name, day, skills, tasks).
  Datasets and files are never uploaded by this app.
- The local server listens on `127.0.0.1` only.

---

## Development

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Model choices are in `core/config.py`. The prompt lives in `core/prompts.py`. The plan content
is plain JSON in `assets/`, so it can be edited without touching code.
