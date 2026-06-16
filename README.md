# IronManJarvis
A voice assistant interface that controls the entire environment, interacts with programs like a person, and can execute commands through Node.js, Python, and the system API.

## DevAI CLI MVP

A practical local CLI prototype is available at:

`/home/runner/work/IronManJarvis/IronManJarvis/devai.py`

### Commands

- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py logs <log_file>`
  - reads a log file
  - finds critical lines (`error|fail|exception|denied|timeout`)
  - groups failures by type and prints a short summary

- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py find "<query>" --root /home/runner/work/IronManJarvis/IronManJarvis`
  - searches repository files (`.gitlab-ci.yml`, `terraform/**/*.tf`, `*.sh`, `*.py`, `*.yml`, `*.yaml`)
  - ranks results with simple relevance scoring

- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py jira-from-log <log_file>`
  - extracts failure signals from logs
  - generates a Jira-ready draft with fields: Title, Type, Component, Error, Impact, Steps, Proposed Fix
