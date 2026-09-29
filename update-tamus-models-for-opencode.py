#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://tamucc.tamus.ai"
MODELS_URL = f"{BASE_URL}/api/models"
AUTH_STATE_FILE = Path(__file__).parent / "auth_state.json"
LOCAL_CONFIG_FILE = Path(__file__).parent / "opencode.json"
GLOBAL_CONFIG_FILE = Path.home() / ".config" / "opencode" / "opencode.json"


def _get_token(context):
    page = context.new_page()
    page.goto(BASE_URL, wait_until="networkidle")
    token = page.evaluate("window.localStorage.getItem('token')")
    page.close()
    return token


def _fetch_with_token(context, token):
    response = context.request.get(
        MODELS_URL, headers={"Authorization": f"Bearer {token}"}
    )
    if not response.ok:
        return None
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        return None
    return response.text()


def fetch_models():
    with sync_playwright() as p:
        if AUTH_STATE_FILE.exists():
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(AUTH_STATE_FILE))
            token = _get_token(context)
            text = _fetch_with_token(context, token) if token else None
            context.close()
            browser.close()
            if text is not None:
                Path("response.txt").write_text(text)
                print("Fetched latest models and saved to response.txt")
                return
            print("Saved session is no longer valid, need to log in again.")

        print(
            "Opening browser. Complete SSO login AND make sure you are signed "
            "into the app itself (tamucc.tamus.ai), then return here."
        )
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)
        input("Press Enter once you are fully logged in... ")
        page.close()

        token = _get_token(context)
        if not token:
            print(
                "Error: Could not find an auth token in localStorage after "
                "login. Make sure you are signed into the app (not just the "
                "Cloudflare Access SSO screen).",
                file=sys.stderr,
            )
            context.close()
            browser.close()
            sys.exit(1)

        text = _fetch_with_token(context, token)
        if text is None:
            print(
                "Error: Still did not get a JSON response after login.",
                file=sys.stderr,
            )
            context.close()
            browser.close()
            sys.exit(1)

        context.storage_state(path=str(AUTH_STATE_FILE))
        AUTH_STATE_FILE.chmod(0o600)
        context.close()
        browser.close()

        Path("response.txt").write_text(text)
        print("Fetched latest models and saved to response.txt")
        print(f"Saved session for future runs to {AUTH_STATE_FILE}")


def ensure_local_config():
    if LOCAL_CONFIG_FILE.exists():
        return
    if not GLOBAL_CONFIG_FILE.exists():
        return
    shutil.copy(GLOBAL_CONFIG_FILE, LOCAL_CONFIG_FILE)
    print(f"Copied {GLOBAL_CONFIG_FILE} to {LOCAL_CONFIG_FILE}")


def shred_auth_state():
    if not AUTH_STATE_FILE.exists():
        return
    size = AUTH_STATE_FILE.stat().st_size
    with open(AUTH_STATE_FILE, "wb") as f:
        f.write(os.urandom(size))
        f.flush()
        os.fsync(f.fileno())
    AUTH_STATE_FILE.unlink()
    print(f"Shredded {AUTH_STATE_FILE}")


def update_models():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-fetch", action="store_true",
        help="Skip fetching from the API and just reprocess the existing response.txt",
    )
    parser.add_argument(
        "-k", "--keep-auth", action="store_true",
        help="Keep auth_state.json after a successful update instead of shredding it",
    )
    args = parser.parse_args()

    try:
        if not args.no_fetch:
            fetch_models()

        ensure_local_config()

        with open('response.txt', 'r') as f:
            models_data = json.load(f)
        
        print(f"Retrieved {len(models_data.get('data', []))} models from response.txt")
        
        with open('opencode.json', 'r') as f:
            config = json.load(f)
        
        models_dict = {}
        for model in models_data.get('data', []):
            model_id = model.get('id')
            if model_id:
                models_dict[model_id] = {"name": model_id}
        
        config['provider']['tamucc']['models'] = models_dict
        
        with open('opencode.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Updated opencode.json with {len(models_dict)} models")

        if not args.keep_auth:
            shred_auth_state()
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    update_models()
