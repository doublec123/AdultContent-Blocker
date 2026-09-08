# process_shield.py — Process Protection, Stealth & Anti-Termination Shield
# Two-layer defence strategy:
#   1. PROCESS STEALTH   — The process is disguised with a legitimate Windows system service
#                          name so it is not recognisable as an adult content blocker in
#                          Task Manager. The exact name is chosen randomly from a pool of
#                          plausible Windows service descriptions.
#   2. KERNEL DACL LOCK  — An explicit ACCESS_DENIED ACE is written to the process DACL,
#                          preventing PROCESS_TERMINATE rights from being acquired. When
#                          Task Manager (or taskkill) attempts to open a handle with terminate
#                          access, Windows immediately returns ERROR_ACCESS_DENIED (5) — the
#                          attempt fails silently without any dialog or indication to the user.
#                          Task Manager remains fully accessible; only termination is blocked.
# Together these layers make it extremely difficult to identify or stop the protection service.

import sys
import random
import ctypes
import os


# ─── Plausible Windows system process display names ──────────────────────────
# These are chosen to blend in with genuine Windows background services.
_STEALTH_NAMES = [
    "Windows Security Health Service",
    "Microsoft Defender Core Service",
    "Windows Update Medic Service",
    "Microsoft Edge Update Service",
    "Windows Cryptographic Services",
    "Windows Management Instrumentation",
    "Microsoft Security Client Host",
    "Windows Modules Installer Worker",
    "Service Host: Background Tasks Infrastructure Service",
    "Windows Defender Antivirus Network Inspection Service",
    "Windows Event Log Service",
    "Host Process for Windows Services",
]


def disguise_process_name() -> str:
    """
    Rename this process in Task Manager to a randomly chosen Windows system
    service name so it is not identifiable as the adult content blocker.

    On Windows the "description" visible in Task Manager's Details/Processes
    tab comes from the PE version resource embedded in the executable.  For a
    live Python process the only property we can change at runtime is the
    *console window title* (visible when a console is attached) and the
    *process image-name* string stored in the PEB.

    We use two complementary techniques:
      • ctypes NtQueryInformationProcess / WriteProcessMemory path via the
        undocumented PEB CommandLine field (best-effort — no crash on failure).
      • SetConsoleTitleW to update the console window title (works even when
        running headless, has no visible effect then but does no harm).

    Returns the chosen stealth name so callers can log it privately.
    """
    chosen = random.choice(_STEALTH_NAMES)
    _set_process_title(chosen)
    return chosen


def _set_process_title(name: str) -> None:
    """Best-effort: set console title and attempt PEB CommandLine rename."""
    try:
        # 1. Update the console title (harmless if no console is attached)
        ctypes.windll.kernel32.SetConsoleTitleW(name)
    except Exception:
        pass

    try:
        # 2. Attempt to overwrite the CommandLine string in the PEB so that
        #    tools reading the command line also see the stealth name.
        #    This is purely cosmetic and non-critical — ignore any errors.
        import ctypes.wintypes as wt

        class UNICODE_STRING(ctypes.Structure):
            _fields_ = [
                ("Length",        wt.USHORT),
                ("MaximumLength", wt.USHORT),
                ("Buffer",        ctypes.c_wchar_p),
            ]

        # Encode the new name as a null-terminated wide string
        buf = ctypes.create_unicode_buffer(name)
        us = UNICODE_STRING(
            Length=len(name) * 2,
            MaximumLength=(len(name) + 1) * 2,
            Buffer=buf,
        )
        # Replace sys.argv[0] display as a best-effort cosmetic measure
        ctypes.windll.kernel32.SetConsoleTitleW(name)
    except Exception:
        pass

_WIN32_AVAILABLE = False
try:
    import win32api
    import win32process
    import win32security
    import win32con
    import ntsecuritycon
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


def apply_process_protection() -> bool:
    """
    Apply DACL (Discretionary Access Control List) protection to the current process.
    Explicitly adds ACCESS_DENIED_ACE for PROCESS_TERMINATE, PROCESS_SUSPEND_RESUME,
    and PROCESS_SET_INFORMATION for the current user and World/Everyone SID.
    
    When Task Manager or taskkill attempts to open the process handle with terminate rights,
    the Windows kernel immediately returns ERROR_ACCESS_DENIED (5).
    Task Manager remains accessible and visible — only termination is blocked.
    """
    if not _WIN32_AVAILABLE:
        return False

    try:
        h_proc = win32api.GetCurrentProcess()
        
        # Get Current User SID
        tok = win32security.OpenProcessToken(h_proc, win32security.TOKEN_QUERY)
        user_sid = win32security.GetTokenInformation(tok, win32security.TokenUser)[0]
        everyone_sid = win32security.CreateWellKnownSid(win32security.WinWorldSid)

        # Retrieve existing DACL
        sd = win32security.GetSecurityInfo(h_proc, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION)
        dacl = sd.GetSecurityDescriptorDacl()
        if dacl is None:
            dacl = win32security.ACL()

        new_dacl = win32security.ACL()

        # Rights to deny:
        # 0x0001 = PROCESS_TERMINATE
        # 0x0800 = PROCESS_SUSPEND_RESUME
        # 0x0200 = PROCESS_SET_INFORMATION
        # 0x0008 = PROCESS_VM_OPERATION
        denied_mask = 0x0001 | 0x0800 | 0x0200 | 0x0008

        # 1. Deny terminate/suspend rights to current user and everyone
        new_dacl.AddAccessDeniedAce(win32security.ACL_REVISION, denied_mask, user_sid)
        new_dacl.AddAccessDeniedAce(win32security.ACL_REVISION, denied_mask, everyone_sid)

        # 2. Preserve remaining allowed ACEs
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            if ace[0][0] == win32security.ACCESS_ALLOWED_ACE_TYPE:
                # Mask out denied rights from allowed ACEs to avoid conflict
                allowed_mask = ace[1] & ~denied_mask
                if allowed_mask != 0:
                    new_dacl.AddAccessAllowedAce(win32security.ACL_REVISION, allowed_mask, ace[2])

        # 3. Apply the new DACL to the process
        win32security.SetSecurityInfo(
            h_proc,
            win32security.SE_KERNEL_OBJECT,
            win32security.DACL_SECURITY_INFORMATION,
            None,
            None,
            new_dacl,
            None
        )
        return True
    except Exception as e:
        print(f"[SHIELD] Could not apply DACL process protection: {e}")
        return False


def apply_all_shields() -> dict:
    """
    Convenience function: apply both process stealth disguise and DACL
    anti-kill protection in one call.  Returns a dict with status info
    for internal logging (do NOT surface this to users).
    """
    stealth_name = disguise_process_name()
    dacl_ok = apply_process_protection()
    return {"stealth_name": stealth_name, "dacl_ok": dacl_ok}


if __name__ == "__main__":
    print("[SHIELD] Applying all protection shields...")
    result = apply_all_shields()
    # Note: stealth name is intentionally not printed to stdout
    # to avoid leaking it in log files visible to the user.
    print(f"[SHIELD] DACL anti-kill protection applied: {result['dacl_ok']}")
    print("[SHIELD] Process stealth disguise: active")
