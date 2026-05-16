# Star Dodger

A Python/pygame remake of **STAR DODGER v2**, an Amstrad CPC BASIC type-in game by **G. French (14-2-92)**.

The original BASIC listing is preserved in [`star-dodger.bas`](star-dodger.bas). The Python versions keep the original attribution and gameplay idea: hold `SPACE` to climb, release it to descend, dodge the killer asterisks, and reach the Nextscreen Gap.

## Versions

- `star_dodger.py` - faithful pygame port of the BASIC version.
- `star_dodger_plus.py` - same classic gameplay with practical modern conveniences:
  - resizable scaled window
  - fullscreen toggle
  - restart/title shortcuts
  - persistent top-six high scores
- `cmd/stardodgerplus` - Go/Ebiten version of Plus with the same classic gameplay.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

`pygame` is declared in `pyproject.toml` and installed automatically by `uv`.

The Go version requires Go 1.24+ and downloads Ebiten through Go modules.

## Run

Faithful classic port:

```bash
uv run ./star_dodger.py
```

Classic gameplay plus scaling and persistent scores:

```bash
uv run ./star_dodger_plus.py
```

Useful Plus options:

```bash
uv run ./star_dodger_plus.py --fullscreen
uv run ./star_dodger_plus.py --scale 3
```

Go Plus version:

```bash
go run ./cmd/stardodgerplus
```

Or build a native binary:

```bash
go build ./cmd/stardodgerplus
./stardodgerplus
```

## Controls

- `SPACE` - climb
- release `SPACE` - descend
- `Q` - quit

Plus-only controls:

- `F` - toggle fullscreen
- `R` - restart
- `ESC` - return to title

## Attribution

Original game: **STAR DODGER v2** by **G. French (14-2-92)**.

This repository is a Python remake/port and includes the original BASIC listing for reference and preservation.
