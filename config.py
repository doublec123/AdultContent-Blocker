# config.py — Application Configuration & Settings Manager
import json
import os
import sys
import hashlib
import threading
import time

# Directory where config is stored
def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
TEMP_CONFIG_FILE = os.path.join(BASE_DIR, "config.json.tmp")

_CONFIG_LOCK = threading.Lock()

# Default password: "admin123"
DEFAULT_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# These settings are LOCKED and cannot be disabled by anyone.
# Any attempt to set them False (e.g. by editing config.json manually) is overridden.
_LOCKED_TRUE = {"enabled", "monitor_titles", "block_hosts", "randomize_password"}

DEFAULT_CONFIG = {
    "enabled": True,
    "password_hash": DEFAULT_PASSWORD_HASH,
    "custom_password_hash": None,
    "whitelist": [],           # Domains the admin has whitelisted
    "auto_start": True,        # Add to Windows startup
    "monitor_titles": True,    # Monitor browser window titles (LOCKED ON)
    "block_hosts": True,       # Modify hosts file (LOCKED ON)
    "show_blocked_url": True,  # Show the blocked URL on the block screen
    "first_run": True,         # Whether to show first-run setup
    "randomize_password": True, # Randomize password every 5 seconds (LOCKED ON)
}


def load_config() -> dict:
    """Load config from file with thread locking and retry logic."""
    with _CONFIG_LOCK:
        if not os.path.exists(CONFIG_FILE):
            _save_config_unlocked(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)

        # Retry loop to handle Windows file lock race conditions
        for attempt in range(5):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Merge with defaults to handle missing keys
                for key, val in DEFAULT_CONFIG.items():
                    if key not in data:
                        data[key] = val

                # Enforce locked settings — cannot be disabled
                for key in _LOCKED_TRUE:
                    data[key] = True

                return data
            except (PermissionError, json.JSONDecodeError, OSError):
                time.sleep(0.05)
            except Exception:
                break

        # Fallback to defaults only if file is permanently unreadable/corrupt
        _save_config_unlocked(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def _save_config_unlocked(config: dict) -> None:
    """Internal helper to write config atomically without acquiring lock again."""
    try:
        with open(TEMP_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(TEMP_CONFIG_FILE, CONFIG_FILE)
    except Exception:
        # Emergency direct write if atomic replace fails
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass


def save_config(config: dict) -> None:
    """Save config to file atomically with thread lock."""
    with _CONFIG_LOCK:
        _save_config_unlocked(config)


def get_setting(key: str):
    """Get a single config setting."""
    cfg = load_config()
    return cfg.get(key, DEFAULT_CONFIG.get(key))


def set_setting(key: str, value) -> None:
    """Update a single config setting."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def check_password(plain_password: str) -> bool:
    """
    Verify a plain text password against stored hash.
    Always accepts 'admin123', custom set password, or randomized password hash.
    """
    cfg = load_config()
    hashed = hashlib.sha256(plain_password.encode()).hexdigest()

    # Always allow default password "admin123" as master admin fallback
    if hashed == DEFAULT_PASSWORD_HASH:
        return True

    # Allow explicitly set custom password if user changed it
    custom_hash = cfg.get("custom_password_hash")
    if custom_hash and hashed == custom_hash:
        return True

    # Allow current randomized password
    return hashed == cfg.get("password_hash", DEFAULT_PASSWORD_HASH)


def set_password(new_password: str) -> None:
    """Update the stored password hash."""
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    cfg = load_config()
    cfg["password_hash"] = hashed
    cfg["custom_password_hash"] = hashed
    save_config(cfg)


def add_to_whitelist(domain: str) -> None:
    """Add a domain to the whitelist."""
    cfg = load_config()
    domain = domain.lower().strip()
    if domain and domain not in cfg["whitelist"]:
        cfg["whitelist"].append(domain)
        save_config(cfg)


def remove_from_whitelist(domain: str) -> None:
    """Remove a domain from the whitelist."""
    cfg = load_config()
    domain = domain.lower().strip()
    if domain in cfg["whitelist"]:
        cfg["whitelist"].remove(domain)
        save_config(cfg)


def is_whitelisted(domain: str) -> bool:
    """Check if a domain is in the whitelist."""
    cfg = load_config()
    domain = domain.lower().strip()
    return domain in cfg.get("whitelist", [])


def get_whitelist() -> list:
    """Get the full whitelist."""
    return load_config().get("whitelist", [])
