# Windows setup and validation

## Install Python

Install CPython 3.14, 64-bit, from python.org.

Include the Python launcher during installation. These instructions do
not require administrator execution of the application.

Verify:

```powershell
py -3.14 --version
py -3.14 -c "import struct; print(struct.calcsize('P') * 8)"
```

The second command should print 64.

## Open the project

Open PowerShell in the symbiote-ghost directory containing requirements.txt.

Confirm the source files have been copied into the paths shown in the
project tree.

## Scripted installation

```powershell
.\setup.ps1
```

If your execution policy prevents running PowerShell scripts, use the
manual commands below. There is no need to change machine-wide execution
policy.

## Manual installation

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Internet access is needed to obtain dependencies unless you already have
a suitable local package cache. The application itself has no Phase 1
network integration.

## Automated checks

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The test suite checks configuration validation and creation, structured
logging, suppression of exception messages, UI status, unavailable
feature controls, settings visibility, and window show/close behavior.

Compilation is a syntax check, not linting or static type checking.

## Launch

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Or:

```powershell
.\run.ps1
```

With an explicitly selected configuration:

```powershell
.\run.ps1 -ConfigPath .\config\default.yaml
```

The equivalent Python command is:

```powershell
.\.venv\Scripts\python.exe -m src.main --config .\config\default.yaml
```

For the shorter command, activate the environment first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.main
```

Activation is optional. Calling the virtual environment's Python directly
works even when PowerShell blocks activation scripts.

## Manual acceptance checks

| Check | Expected outcome |
|---|---|
| Launch | Main window appears without a traceback |
| Branding | SYMBIOTE heading is visible |
| Ghost status | OFF |
| AI status | OFFLINE |
| Screen status | READY, with a capture-not-implemented explanation |
| Analyze Screen | Explains unavailability without capturing anything |
| Ghost Mode | Explains unavailability and remains OFF |
| Settings | Shows actual loaded YAML and configuration path |
| Close window | Python process exits |
| Log file | Contains JSON Lines lifecycle events |
| Restart | Existing configuration is loaded |

## Configuration errors

If startup reports invalid configuration, correct the selected YAML
file and restart.

For a clean default configuration, close the application and manually
rename the per-user config.yaml file before launching again.

Do not delete unrelated files from the application-data directory.

## Troubleshooting

| Symptom | Action |
|---|---|
| No module named PySide6 | Use the virtual environment's Python and rerun installation |
| No module named src | Run from the project root |
| Python launcher missing | Install Python 3.14 with its launcher, or use your Python executable for manual setup |
| Existing virtual environment has another Python version | Rename that environment and recreate it with Python 3.14 |
| Unable to create configuration or logs | Check write access to your per-user local application-data directory |
| Qt platform plugin failure | Record the exact terminal output and verify the environment uses the pinned packages |
| Window does not appear normally | Ensure QT_QPA_PLATFORM is not set to offscreen in your launch environment |

The test process sets its own offscreen environment variable. It does
not change the parent PowerShell environment.

## Reporting results

Provide the command you ran, Python version, full test or terminal error,
and whether the main window appeared.

If startup displays a dialog, include its exact message. Avoid including
private configuration values.

Windows GUI behavior has not been validated by the source author in this
delivery. Local checks must pass before continuing to Phase 2.
