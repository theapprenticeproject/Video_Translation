# Contributing to Video Translator

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Code Style](#code-style)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Project Structure](#project-structure)

---

## Prerequisites

- Python **3.10+**
- [Frappe Bench](https://frappeframework.com/docs/user/en/installation) installed and configured
- A running Frappe site (v15+)
- RabbitMQ (for background queue processing)

---

## Local Setup

```bash
# 1. Get the app into your bench
cd $PATH_TO_YOUR_BENCH
bench get-app git@github.com:theapprenticeproject/Video_Translation.git --branch main
bench install-app my_app

# 2. Create the required folders under your site's public directory
mkdir -p sites/<your_site_name>/public/files/original
mkdir -p sites/<your_site_name>/public/files/processed

# 3. Install Python dev dependencies (uses uv)
pip install uv
uv sync

# 4. Start bench
bench start
```

> **Note:** The `original/` and `processed/` folders must be created manually before
> first use. Uploads will fail with a `FileNotFoundError` if they don't exist.

---

## Code Style

### Python
This project uses **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting.

```bash
# Check for lint issues
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format code
ruff format .
```

Key style rules (from `pyproject.toml`):
- Line length: **110 characters**
- Target: **Python 3.10**
- Indentation: **tabs** (not spaces)
- Quote style: **double quotes**

### Commit Messages
This project follows **[Conventional Commits](https://www.conventionalcommits.org/)**.

Format: `<type>(<scope>): <short description>`

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, dependency updates, etc. |
| `perf` | Performance improvement |

Examples:
```
feat(api): add batch video upload endpoint
fix(file-naming): sync Frappe File record after physical move
docs(readme): clarify folder setup requirement
```

---

## Pre-commit Hooks

Install pre-commit to catch issues before they reach CI:

```bash
pip install pre-commit
pre-commit install
```

The hooks run Ruff on every commit. If Ruff fails, the commit is blocked until you fix the issues.

To run hooks manually on all files:
```bash
pre-commit run --all-files
```

---

## Submitting a Pull Request

1. **Fork** the repository and create a branch:
   ```bash
   git checkout -b fix/your-fix-name
   # or
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes.** Keep PRs focused — one logical change per PR.

3. **Run the linter** before committing:
   ```bash
   ruff check . && ruff format --check .
   ```

4. **Commit** using conventional commit format:
   ```bash
   git commit -m "fix(scope): short description of what changed"
   ```

5. **Push** and open a Pull Request against the `main` branch.

6. **Reference the issue** in your PR description:
   ```
   Fixes #<issue-number>
   ```

### PR Description Template
```markdown
## What
One sentence: what this PR does.

## Why
What problem it solves. Link to the issue: Fixes #X

## Changes
- `file_naming.py`: description of change
- `video_info.py`: description of change

## Testing
Steps to verify the fix or feature works as expected.
```

---

## Reporting Bugs

Open an issue on GitHub with:
1. A clear title describing the problem
2. Steps to reproduce
3. Expected behaviour vs actual behaviour
4. Relevant logs (from `bench logs` or the Frappe error log)
5. Environment: Frappe version, Python version, OS

---

## Project Structure

```
Video_Translation/
├── my_app/
│   ├── api/
│   │   ├── v1/                 ← V1 API endpoints (Bhashini, audio extraction, subtitles)
│   │   └── v2/                 ← V2 API endpoints (segment tasks, ElevenLabs, onscreen text)
│   ├── helper/
│   │   ├── file_naming.py      ← File move + rename logic after upload
│   │   ├── videolink_download.py ← HTTP video URL download helper
│   │   └── options.py          ← Language/config constants
│   ├── media-queues/
│   │   └── tasks_pipe.py       ← RabbitMQ consumer — processes translation jobs
│   └── self_app/
│       └── doctype/
│           └── video_info/     ← Core Frappe DocType (upload, move, track video)
├── pyproject.toml              ← Project config + Ruff settings
└── README.md
```

### Key Concepts

- **VideoInfo DocType**: the central record for each uploaded video. `on_update` moves the file
  into `files/original/` and triggers downstream processing via RabbitMQ.
- **file_retitling()**: renames and moves uploaded files. Always updates the Frappe `File` record
  after moving to prevent orphaned references (see issue #4).
- **V1 vs V2 APIs**: V1 uses Bhashini for translation; V2 uses ElevenLabs + segment-based processing.
  Both pipelines write results to `files/processed/`.
