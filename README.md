Using the [uv](https://github.com/astral-sh/uv) package manager and pyright via pylance on vscode for type checking.

Create a virtual environment:

```bash
uv venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
uv sync
```

Run the program:

```bash
uv run src/main.py
```

### Current Strategies:

- `Noisy`: Randomly places bids/asks to simulate retail/noisy behavior.
