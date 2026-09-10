# ForensicGuard

**Lightweight Digital Evidence Analyzer**

Open-source forensic triage tool for inspecting files, images and emails for
suspicious indicators, metadata anomalies and potential security threats.

> **Status:** work in progress — Stage 1 (project structure and health check).
> No forensic analysis is implemented yet.

---

## Privacy first

- No database
- No account required
- No permanent evidence storage
- Files are removed after processing
- Designed to run locally

---

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | Python 3.12+, FastAPI, Pydantic, Uvicorn |
| Tests | pytest |
| Persistence | none |

---

## 1. Prerequisites

Three tools are needed. Everything else is installed by the project itself.

| Tool | Minimum version | Check with |
| --- | --- | --- |
| Git | any | `git --version` |
| Python | 3.12 | `python --version` |
| Node.js | 20 | `node --version` |

If all three commands already print a version, skip to step 2.

### Windows

Using [winget](https://learn.microsoft.com/windows/package-manager/winget/),
which ships with Windows 10 and 11:

```powershell
winget install Git.Git
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
```

Close and reopen the terminal afterwards so the new commands are found.

> **If `python` opens the Microsoft Store instead of running Python**, that is
> a Windows placeholder, not a real installation. Use `py` instead — it is the
> official Python launcher and points at your actual installation. Every
> `python` command in this README can be replaced by `py`.

Alternatively, download the installers from [git-scm.com](https://git-scm.com/download/win),
[python.org](https://www.python.org/downloads/windows/) and
[nodejs.org](https://nodejs.org/). In the Python installer, tick
**"Add python.exe to PATH"** on the first screen.

### Linux — Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 python3-venv curl
```

`python3-venv` is a separate package on Debian and Ubuntu. Without it, virtual
environment creation fails.

The Node.js version in the default repositories is often too old. Install a
current one from [NodeSource](https://github.com/nodesource/distributions):

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Linux — Fedora / RHEL

```bash
sudo dnf install -y git python3 nodejs npm
```

### macOS

Using [Homebrew](https://brew.sh/):

```bash
brew install git python@3.12 node
```

---

## 2. Clone the repository

```bash
git clone https://github.com/Vinicius-Rampazzo/forensic-guard.git
cd forensic-guard
```

---

## 3. Install and run the backend

**No manual installation step is required.** The first run creates the virtual
environment, installs every Python dependency and then starts the server.

**Windows**

```powershell
python backend\dev.py
```

**Linux / macOS**

```bash
python3 backend/dev.py
```

Expected output on the first run:

```text
> Creating virtual environment at backend\.venv
  done

> Installing dependencies
  done

> Starting development server
  API      http://127.0.0.1:8000
  Docs     http://127.0.0.1:8000/docs
  Stop     Ctrl+C
```

Later runs skip straight to the server. If `requirements.txt` changes, the next
run reinstalls automatically.

Leave this terminal open — the server runs until you press `Ctrl+C`.

---

## 4. Install and run the frontend

Open a **second terminal**, in the same project folder. Both servers must run
at the same time.

**Windows**

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

**Linux / macOS**

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

`npm install` is only needed the first time, and again whenever
`package.json` changes.

Expected output:

```text
▲ Next.js 16.3.4 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://192.168.1.10:3000
- Environments: .env.local
✓ Ready in 1547ms
```

If port 3000 is already taken, Next picks the next free port and says so —
read the `Local:` line for the address actually in use.

---

## 5. Verify the installation

Open http://localhost:3000 in a browser.

The page must show the **API online** badge in green. If it shows **API
offline**, the frontend is running but cannot reach the backend — check that
step 3 is still running in the other terminal.

Two more addresses worth opening:

| Address | What it is |
| --- | --- |
| http://127.0.0.1:8000/health | The API endpoint itself, as raw JSON |
| http://127.0.0.1:8000/docs | Interactive API documentation, generated automatically |

To run the test suite:

```bash
python backend/dev.py test
```

---

## Backend commands

`backend/dev.py` is the backend task runner — the equivalent of `npm run` on
the frontend side. It always uses the project virtual environment, so there is
no need to activate anything.

| Command | What it does |
| --- | --- |
| `python backend/dev.py` | Start the development server with auto-reload |
| `python backend/dev.py test` | Run the test suite |
| `python backend/dev.py lint` | Check the code with ruff |
| `python backend/dev.py format` | Format the code with ruff |
| `python backend/dev.py check` | Lint and test — run this before committing |
| `python backend/dev.py install` | Prepare the environment without running anything |
| `python backend/dev.py --help` | Show all available tasks |

Extra arguments are forwarded to the underlying tool:

```bash
python backend/dev.py dev --port 9000
python backend/dev.py test -k health
```

The commands also work from inside the `backend/` directory, as `python dev.py`.

### Working without the task runner

If you prefer the conventional workflow, activate the virtual environment and
call the tools directly.

**Windows**

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
cd backend
uvicorn app.main:app --reload
```

> If PowerShell blocks the activation script, run
> `Set-ExecutionPolicy -Scope Process RemoteSigned` first. It applies only to
> that terminal window.

**Linux / macOS**

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
uvicorn app.main:app --reload
```

Leave the environment with `deactivate`.

---

## Frontend commands

| Command | What it does |
| --- | --- |
| `npm --prefix frontend install` | Install dependencies |
| `npm --prefix frontend run dev` | Start the development server |
| `npm --prefix frontend run build` | Production build — also type-checks the project |
| `npm --prefix frontend run start` | Serve a previous production build |
| `npm --prefix frontend run lint` | Check the code with ESLint |

---

## Configuration

Both sides read their configuration from environment files. **This step is
optional** — every value has a working default, so the project runs correctly
right after cloning.

The `.example` files are versioned and document which variables exist; the real
files are ignored by git and never leave your machine.

| File | Copy from | Purpose |
| --- | --- | --- |
| `backend/.env` | `backend/.env.example` | API name, version, CORS origins, upload limit, temp directory |
| `frontend/.env.local` | `frontend/.env.local.example` | Backend URL used by the browser |

**Windows**

```powershell
copy backend\.env.example backend\.env
copy frontend\.env.local.example frontend\.env.local
```

**Linux / macOS**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Only variables prefixed with `NEXT_PUBLIC_` reach the browser, and everything
that reaches the browser is public. Never give that prefix to a secret.

---

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `python` opens the Microsoft Store | Windows placeholder. Use `py` instead, or install Python from python.org with "Add to PATH" ticked. |
| `Error: Command '...venv' returned non-zero exit status 1` on Debian/Ubuntu | `python3-venv` is missing. Run `sudo apt install python3-venv`. |
| `Python 3.12+ is required, but this is 3.11` | Older interpreter. Use `py -3.12 dev.py` on Windows or `python3.12 backend/dev.py` on Linux. |
| PowerShell refuses `Activate.ps1` | Execution policy. Run `Set-ExecutionPolicy -Scope Process RemoteSigned`, or just use `python backend\dev.py`, which needs no activation. |
| Page shows **API offline** | The backend is not running, or it is on a different port. Confirm http://127.0.0.1:8000/health responds. |
| `EADDRINUSE` / port already in use | Another process holds the port. Use `python backend/dev.py dev --port 9000`, or stop the other process. |

---

## Project layout

```text
forensic-guard/
├── backend/            FastAPI application
│   ├── app/
│   │   ├── api/routes/     HTTP layer
│   │   ├── services/       orchestration
│   │   ├── analyzers/      one analyzer per evidence type
│   │   ├── utils/          pure helpers: hashing, entropy, signatures
│   │   ├── schemas/        Pydantic contracts
│   │   └── constants/      signature table and risk rules
│   ├── tests/
│   └── dev.py              backend task runner
├── frontend/           Next.js application
│   ├── app/                pages and layout
│   ├── services/           API access layer
│   └── types/              TypeScript mirrors of the backend schemas
└── docs/
    └── project-context.md  full technical specification
```

---

## Documentation

The full technical specification lives in [`docs/project-context.md`](docs/project-context.md).

---

## Disclaimer

The ForensicGuard risk score is based on static indicators and heuristics.
It does not provide a definitive malware or phishing verdict.
