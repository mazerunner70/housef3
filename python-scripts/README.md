# Python Scripts Directory

This directory contains all Python-based tooling and utilities for the project, with a single shared virtual environment.

## Structure

```
python-scripts/
├── venv/                      # Shared Python virtual environment
├── requirements.txt           # All Python dependencies
├── workflow-diagnostics/      # Workflow diagnostic tools
│   ├── workflow_diagnostics.py
│   ├── workflow_diagnostics.sh
│   ├── workflow_config.env
│   └── README.md
└── README.md                  # This file
```

## Virtual Environment

All Python scripts in this directory share a single virtual environment located at `python-scripts/venv/`.

### Setup
```bash
cd python-scripts
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage
The virtual environment is automatically activated by shell wrapper scripts, but you can also activate it manually:
```bash
cd python-scripts
source venv/bin/activate
python workflow-diagnostics/workflow_diagnostics.py --help
```

## Adding New Python Tools

1. Create a new subdirectory for your tool
2. Add any new dependencies to `requirements.txt`
3. Create a shell wrapper in the main `scripts/` directory if needed
4. Update this README

## Current Tools

### Workflow Diagnostics
- **Location**: `workflow-diagnostics/`
- **Purpose**: Monitor and diagnose workflow operations (file deletion, etc.)
- **Shell Access**: `../scripts/workflow-diag`
- **Direct Access**: `python workflow-diagnostics/workflow_diagnostics.py`

## Dependencies

See `requirements.txt` for the complete list of Python dependencies shared across all tools.

## Integration with Scripts Directory

The main `scripts/` directory contains shell scripts that can invoke Python tools from this directory:
- Shell scripts handle orchestration, environment setup, and simple operations
- Python scripts handle complex logic, AWS API calls, and data processing
- Shell wrappers automatically activate the Python virtual environment

This separation keeps the codebase organized and makes it easy to maintain both shell and Python tooling.
