# hosts_manager.py — Windows Hosts File Manager
# Handles adding/removing adult domain blocks from the Windows hosts file.
# REQUIRES ADMINISTRATOR PRIVILEGES.

import os
import subprocess
import ctypes
import sys
import stat
import shutil
from blocklist import get_all_domains
from config import get_whitelist

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
BLOCK_MARKER_START = "# === ADULT CONTENT BLOCKER START ==="
BLOCK_MARKER_END = "# === ADULT CONTENT BLOCKER END ==="
REDIRECT_IP = "0.0.0.0"


def is_admin() -> bool:
    """Check if the process has Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin() -> None:
    """Re-launch the script with administrator privileges if needed."""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()


def read_hosts() -> str:
    """Read the current contents of the hosts file."""
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except PermissionError:
        return ""
    except Exception:
        return ""


def write_hosts(content: str) -> bool:
    """Write content to the hosts file, handling ReadOnly attribute and backup."""
    try:
        if os.path.exists(HOSTS_PATH):
            # Create backup if not already present
            bak_path = HOSTS_PATH + ".bak"
            if not os.path.exists(bak_path):
                try:
                    shutil.copy2(HOSTS_PATH, bak_path)
                except Exception:
                    pass
            # Clear ReadOnly attribute if present
            try:
                os.chmod(HOSTS_PATH, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass

        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except PermissionError:
        return False
    except Exception:
        return False


def flush_dns() -> None:
    """Flush Windows DNS cache."""
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        pass


def remove_existing_blocks(content: str) -> str:
    """Remove any existing adult blocker entries from hosts content."""
    lines = content.splitlines(keepends=True)
    result = []
    inside_block = False
    for line in lines:
        if BLOCK_MARKER_START in line:
            inside_block = True
            continue
        if BLOCK_MARKER_END in line:
            inside_block = False
            continue
        if not inside_block:
            result.append(line)
    return "".join(result)


def apply_blocks() -> tuple[bool, int]:
    """
    Apply adult domain blocks to the hosts file.
    Returns (success: bool, domains_blocked: int).
    """
    if not is_admin():
        return False, 0

    domains = get_all_domains()
    whitelist = [d.lower() for d in get_whitelist()]

    # Filter out whitelisted domains
    domains_to_block = [
        d for d in domains
        if d.lower() not in whitelist and d.strip()
    ]

    # Read and clean existing hosts file
    current_content = read_hosts()
    clean_content = remove_existing_blocks(current_content)

    # Build new block section
    block_lines = [
        f"\n{BLOCK_MARKER_START}\n",
        f"# Adult Content Blocker — {len(domains_to_block)} domains blocked\n",
        f"# DO NOT EDIT MANUALLY — Managed by Adult Content Blocker\n",
    ]
    for domain in sorted(set(domains_to_block)):
        block_lines.append(f"{REDIRECT_IP} {domain}\n")
    block_lines.append(f"{BLOCK_MARKER_END}\n")

    new_content = clean_content.rstrip() + "\n" + "".join(block_lines)

    success = write_hosts(new_content)
    if success:
        flush_dns()
        return True, len(domains_to_block)
    return False, 0


def remove_blocks() -> bool:
    """
    Remove all adult content blocker entries from the hosts file.
    Returns True if successful.
    """
    if not is_admin():
        return False

    current_content = read_hosts()
    clean_content = remove_existing_blocks(current_content)
    success = write_hosts(clean_content)
    if success:
        flush_dns()
    return success


def is_domain_blocked(domain: str) -> bool:
    """Check if a specific domain is currently in the hosts block list."""
    content = read_hosts()
    domain_lower = domain.lower().strip()
    return f"{REDIRECT_IP} {domain_lower}" in content.lower()


def get_block_status() -> dict:
    """
    Returns info about current blocking status.
    """
    content = read_hosts()
    is_active = BLOCK_MARKER_START in content
    count = content.count(REDIRECT_IP) if is_active else 0
    return {
        "active": is_active,
        "domains_blocked": count,
        "has_admin": is_admin(),
    }
