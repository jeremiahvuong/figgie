## An algorithmic sandbox for Jane Street's Figgie

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
