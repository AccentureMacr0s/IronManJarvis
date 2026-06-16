# IronManJarvis
A voice assistant interface that controls the entire environment, interacts with programs like a person, and can execute commands through Node.js, Python, and the system API.

## Split projects

- `/home/runner/work/IronManJarvis/IronManJarvis/projects/voice_agent`
  - isolated voice-agent launcher (default entrypoint: `dima_6_stark_mode_chat/main.py`)
- `/home/runner/work/IronManJarvis/IronManJarvis/projects/analyther`
  - CLI for log analysis, repo search, and Jira story template generation

Backward-compatible CLI entrypoint:

`/home/runner/work/IronManJarvis/IronManJarvis/devai.py`

## devai CLI

### Commands

- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py logs file.log`
- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py find "terraform" --root /home/runner/work/IronManJarvis/IronManJarvis`
- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py jira-from-log file.log --jira-md /tmp/devai/jira.md --json-out /tmp/devai/event.json`
- `python /home/runner/work/IronManJarvis/IronManJarvis/devai.py jira-story --context "paste text" --attachment /path/to/file.log --attachment /path/to/file.tf --jira-md /tmp/devai/jira.md`

`devai` flow for logs:

`pipeline.log -> read file -> extract errors -> classify failure -> detect component -> build structured event -> render jira template -> stdout/jira.md`

Structured result fields:

- `type`
- `component`
- `severity`
- `matches`
- `evidence`

## Rules

Rule files are stored in:

`/home/runner/work/IronManJarvis/IronManJarvis/rules/`

```
rules/
├── chef.yml
├── terraform.yml
├── gitlab_runner.yml
├── aws_ssm.yml
├── windows_patch.yml
└── powershell.yml
```
