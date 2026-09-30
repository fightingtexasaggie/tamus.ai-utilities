# tamus.ai-utilities
handy-dandy utilities for working with the TAMUS AI models

## Install

Requires Python 3.10+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

The `playwright install chromium` step is separate from `pip install` — the
Python package does not include browser binaries, and the utility launches
Chromium to complete the SSO login.

## Usage

```sh
./update-tamus-models-for-opencode.py
```
This is institution specific, but easy enough to change as you need.

The first run opens a browser window so you can log in. Complete the SSO
login, make sure you are signed into the app itself at
[tamucc.tamus.ai](https://tamucc.tamus.ai) (not just the Cloudflare Access
screen), then return to the terminal and press Enter. The session is optionally
saved to `auth_state.json` and shredded again once the update completes, so a
subsequent run will be fully headless, but this probably isn't a great idea
so is not default.

`opencode.json` is created by copying your global config from
`~/.config/opencode/opencode.json` on the first run if you don't already
have one in your pwd, and this copy is the one that will be updated with the current
model list from the API, not the live one.

### Options

| Flag | Effect |
| --- | --- |
| `--no-fetch` | Skip the API fetch and reprocess the existing `response.txt` |
| `-k`, `--keep-auth` | Keep `auth_state.json` after a successful update instead of shredding it |
