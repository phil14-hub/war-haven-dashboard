#!/usr/bin/env python3
"""
Clash Recruitment 4.5 — WAR HAVEN RECRUITER

What this version adds over 3.x
--------------------------------
1. Better freshness tracking
   - Records the last successful roster time and the detection time per clan.
   - Shows the true observation window ("left within <= X"), never an invented
     exact leave time.
   - Tracks first/last live verification that a candidate is clanless.

2. Persistent candidate lifecycle
   NEW -> STILL_CLANLESS -> JOINED_MY_CLAN / JOINED_OTHER_CLAN / BELOW_FILTERS / ARCHIVED
   plus COOLDOWN_CLANLESS and VERIFY_ERROR safety states.

3. Your-clan conversion tracking
   - Watches your clan roster directly every run.
   - Marks known recruiting candidates who join your clan, even if they were
     previously in another lifecycle state.
   - Preserves the first detected join time for recruiting conversion history.

4. Smart duplicate cooldown
   - A player can remain visible while continuously clanless.
   - If they later rejoin a clan and leave again, they can become NEW again only
     after the configurable duplicate cooldown has elapsed.

5. Core + rotating clan pool
   - High-value / high-turnover clans are promoted into the core pool.
   - Low-value rotating clans are periodically replaced with newly discovered
     U.S.-located clans.
   - Newly added clans are baseline-only on their first successful scan, so an
     old/stale roster can never create fake departures.

6. Clan turnover metrics
   - Tracks comparable scans, observed member slots, departures, qualifying
     clanless departures, turnover rate, and a transparent High/Medium/Low
     recruiting-value label.

7. Easy filters
   - Town Hall, war stars, best trophies, current trophies, XP level, active
     candidate age, duplicate cooldown, and max results.

8. Better HTML dashboard
   - NEW THIS SCAN, STILL AVAILABLE, JOINED YOUR CLAN, and NO LONGER AVAILABLE sections.
   - In-page filters/sorting and tappable "Open in Clash" links.
   - Clan turnover table.

9. Reliability
   - Retries/backoff.
   - A failed clan request NEVER means all of its members left.
   - Atomic state writes.
   - Incremental scan checkpoint and crash resume.
   - Error log and last-run statistics.
   - Optional second scan of the hottest clans to tighten observation windows.

10. Unlimited API-key failover
   - coc_token.txt can contain any number of API keys, one per line.
   - The script automatically tries the configured keys until Supercell accepts
     one for the public IP/network currently in use.
   - Once a key works, it is preferred for the rest of that run.
   - Existing one-key coc_token.txt files continue to work unchanged.

11. Parallel player verification
   - New departures and active candidates are profile-checked concurrently.
   - State/lifecycle updates remain serialized on the main thread for safety.

12. Minimum Ranked League filter
   - Optionally require candidates to be in a Ranked League tier or higher.
   - Supports current 2026 Ranked tiers from Skeleton 1 through Legend I.
   - Human-friendly values such as Titan, Titan 25, Electro 33, or Legend III.

Data source
-----------
Supercell's official Clash of Clans API only. The script does NOT automate the
Clash of Clans app and does NOT send invitations.

The player's former clan being configured as United States is only a proxy for
U.S. association. The API does not expose the player's residence or language.
"""

import argparse
import atexit
import csv
import hashlib
import html
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

VERSION = "4.6"
API_ROOT = "https://api.clashofclans.com/v1"

# ---------------------------------------------------------------------------
# EASY SETTINGS — change these if you want different defaults.
# Command-line options can still override them.
# ---------------------------------------------------------------------------
DEFAULT_MY_CLAN_TAG = "#2PQQJ0GR0"
DEFAULT_MIN_TH = 11
DEFAULT_MIN_WAR_STARS = 0
DEFAULT_MIN_BEST_TROPHIES = 0
DEFAULT_MIN_CURRENT_TROPHIES = 0
DEFAULT_MIN_EXP_LEVEL = 0
DEFAULT_MIN_LEAGUE = "ANY"
DEFAULT_TARGET = 50
DEFAULT_MAX_CLANS = 1000
DEFAULT_MIN_CLAN_MEMBERS = 20
DEFAULT_WORKERS = 10
DEFAULT_PROFILE_WORKERS = 10
DEFAULT_ACTIVE_DAYS = 7
DEFAULT_DUPLICATE_COOLDOWN_DAYS = 30
DEFAULT_ROTATION_DAYS = 7
DEFAULT_ROTATION_COUNT = 100
DEFAULT_CORE_FRACTION = 0.70
DEFAULT_HOT_RESCAN_COUNT = 50
DEFAULT_CHECKPOINT_MAX_AGE_HOURS = 12
DEFAULT_HISTORY_DISPLAY_DAYS = 7
CHECKPOINT_SAVE_EVERY = 25

HOME = Path.home()
BASE_DIR = HOME / "Documents" / "Clash_Recruitment"
STATE_DIR = BASE_DIR / "state"

TOKEN_FILE = BASE_DIR / "coc_token.txt"
TRACKED_CLANS_FILE = STATE_DIR / "tracked_us_clans.json"
ROSTERS_FILE = STATE_DIR / "us_clan_rosters.json"
LEAVERS_FILE = STATE_DIR / "detected_leavers.json"
CLAN_METRICS_FILE = STATE_DIR / "clan_metrics.json"
CHECKPOINT_FILE = STATE_DIR / "scan_checkpoint.json"
RUN_STATS_FILE = STATE_DIR / "last_run_stats.json"
ERROR_LOG_FILE = BASE_DIR / "recruitment_errors.log"

DEFAULT_CSV = BASE_DIR / "recruiting_candidates.csv"
DEFAULT_HISTORY_CSV = BASE_DIR / "recruiting_history.csv"
DEFAULT_TURNOVER_CSV = BASE_DIR / "clan_turnover.csv"
DEFAULT_HTML = BASE_DIR / "recruiting_candidates.html"

_thread_local = threading.local()


RECRUITER_CSS = ':root{color-scheme:dark;--bg:#0d1524;--surface:#162337;--ink:#f3f5fa;--muted:#a3b3c9;--line:#2a3e56;--gold:#efc46a;--green:#81d5a2;--red:#ffa3a3;--radius:18px}\n*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% 0%,#21364b 0,transparent 45%),var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased;overflow-wrap:anywhere}.wrap{max-width:1150px;margin:auto;padding:22px 18px 50px}h1,h2,h3,p{margin:0}h1{font-size:28px;letter-spacing:-.8px;line-height:1.2}h2{font-size:20px;font-weight:680;letter-spacing:-.3px}h3{font-size:17px;line-height:1.3;font-weight:650}.eyebrow{color:#d9c595;font-size:10px;letter-spacing:2.3px;text-transform:uppercase;font-weight:650;margin-bottom:8px}.hero{padding:24px;border:1px solid #705c3a;border-radius:20px;background:radial-gradient(ellipse at top right,#b48a322b,transparent 65%),linear-gradient(130deg,#1b2d42,#132135)}.hero-top{display:flex;align-items:center;justify-content:space-between;gap:16px}.hero-mark{width:48px;height:48px;border-radius:15px;background:#efc46a18;color:var(--gold);border:1px solid #af79304d;display:grid;place-items:center;flex:none}.hero-mark svg{width:28px;height:28px}.sub{font-size:12px;color:var(--muted);line-height:1.7;margin-top:12px;max-width:730px}.snapshot{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.snapshot>span{color:#cfdceb;border:1px solid var(--line);border-radius:99px;padding:5px 10px;font-size:10px;background:#0d1c2d88}.baseline{padding:14px 16px;border:1px solid #577763;border-radius:14px;color:#bce6cb;background:#203b3429;font-size:12px;margin:16px 0}\n.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:18px 0}.summary .box,.card,.empty,.table-wrap,.filter-panel{background:linear-gradient(130deg,#1b2d42,#132135);border:1px solid var(--line);border-radius:var(--radius)}.summary .box{padding:15px 14px}.summary strong{display:block;font-size:25px;font-weight:720;line-height:1.2;letter-spacing:-.6px;color:var(--gold);font-variant-numeric:tabular-nums}.summary span{display:block;font-size:11px;color:var(--muted);margin-top:6px}.filter-panel{padding:16px;margin-bottom:24px}.filter-title{font-size:13px;font-weight:650;margin-bottom:12px}.controls{display:grid;grid-template-columns:2fr repeat(3,minmax(0,1fr));gap:10px}.controls label{font-size:10px;color:var(--muted);font-weight:600;display:flex;flex-direction:column;gap:5px;min-width:0}.controls .wide{grid-column:span 2}.controls input,.controls select{width:100%;min-width:0;min-height:43px;padding:10px 11px;border:1px solid var(--line);border-radius:11px;background:#0e1b2d;color:var(--ink);font:inherit;font-size:12px}input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:3px}.section-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:25px 0 13px}.count{color:var(--muted);font-size:11px;text-align:right}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{padding:18px;min-width:0;box-shadow:0 3px 12px #0001}.row{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.identity{min-width:0}.tag{color:var(--muted);font-size:10px;font-family:ui-monospace,monospace;margin-top:5px}.th{font-size:12px;font-weight:700;white-space:nowrap;padding:5px 9px;border-radius:9px;background:#efc46a12;color:var(--gold);border:1px solid #af79304d}.badges{display:flex;flex-wrap:wrap;gap:6px;margin:13px 0}.badge{display:inline-block;background:#32523c33;border:1px solid #55795a75;color:#abdfbb;padding:4px 8px;border-radius:99px;font-size:9px;font-weight:600}.badge.secondary{color:#c7d4e4;background:#22364b;border-color:#3b506a}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:15px 0;padding:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.stats strong{display:block;font-size:18px;font-weight:700;font-variant-numeric:tabular-nums}.stats span{display:block;color:var(--muted);font-size:9px;margin-top:4px}.timing{font-size:10px;line-height:1.8;color:var(--muted);margin-top:12px}.timing summary{font-size:11px;color:var(--gold);cursor:pointer;min-height:34px;padding:6px 0}.timing strong{color:#c6d5e6;font-weight:500}.source,.gone,.joined-note{color:var(--muted);font-size:11px;margin-top:10px}.joined-note{color:var(--green)}.gone{color:#d3b993}.open{display:block;text-align:center;min-height:44px;padding:11px;margin-top:17px;border:1px solid #dfb75e;border-radius:12px;background:linear-gradient(120deg,#f6d47b,#dfaa49);color:#172035;text-decoration:none;font-size:12px;font-weight:650;box-shadow:0 3px 14px #0002}.open:hover{filter:brightness(1.07)}.empty{grid-column:1/-1;padding:22px 18px;color:var(--muted);font-size:12px;border-style:dashed}.table-wrap{overflow:auto;margin-top:14px}table{width:100%;border-collapse:collapse;min-width:600px}th,td{padding:13px 12px;border-bottom:1px solid #2a3c5170;text-align:left;font-size:11px}th{color:var(--muted);font-size:9px;letter-spacing:.5px;text-transform:uppercase;background:#142337}tr:last-child td{border-bottom:0}.mini{color:var(--muted);font-family:ui-monospace,monospace;font-size:9px;margin-top:3px}.note{margin:23px 0 6px;color:var(--muted);font-size:10px;line-height:1.8}.hidden{display:none!important}.turnover-heading{margin-top:28px}\n@media(max-width:760px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.cards{grid-template-columns:1fr}.wrap{padding:14px 10px 35px}.hero{padding:20px 17px}.hero-mark{width:43px;height:43px}.filter-panel{padding:14px}.card{padding:16px}.section-head h2{font-size:17px}.count{font-size:10px}.summary strong{font-size:23px}}\n@media(prefers-reduced-motion:no-preference){.open{transition:filter .15s ease}}\n'

def configure_paths(directory):
    """Keep cloud scan files in an isolated temporary directory."""
    global BASE_DIR, STATE_DIR, TOKEN_FILE, TRACKED_CLANS_FILE, ROSTERS_FILE
    global LEAVERS_FILE, CLAN_METRICS_FILE, CHECKPOINT_FILE, RUN_STATS_FILE, ERROR_LOG_FILE
    global DEFAULT_CSV, DEFAULT_HISTORY_CSV, DEFAULT_TURNOVER_CSV, DEFAULT_HTML
    BASE_DIR = Path(directory)
    STATE_DIR = BASE_DIR / 'state'
    TOKEN_FILE = BASE_DIR / 'coc_token.txt'
    TRACKED_CLANS_FILE = STATE_DIR / 'tracked_us_clans.json'
    ROSTERS_FILE = STATE_DIR / 'us_clan_rosters.json'
    LEAVERS_FILE = STATE_DIR / 'detected_leavers.json'
    CLAN_METRICS_FILE = STATE_DIR / 'clan_metrics.json'
    CHECKPOINT_FILE = STATE_DIR / 'scan_checkpoint.json'
    RUN_STATS_FILE = STATE_DIR / 'last_run_stats.json'
    ERROR_LOG_FILE = BASE_DIR / 'recruitment_errors.log'
    DEFAULT_CSV = BASE_DIR / 'recruiting_candidates.csv'
    DEFAULT_HISTORY_CSV = BASE_DIR / 'recruiting_history.csv'
    DEFAULT_TURNOVER_CSV = BASE_DIR / 'clan_turnover.csv'
    DEFAULT_HTML = BASE_DIR / 'recruiting_candidates.html'


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().isoformat()


def normalize_tag(tag):
    tag = str(tag or "").strip().upper()
    if tag and not tag.startswith("#"):
        tag = "#" + tag
    return tag


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Current Ranked League ladder (2026). Regular tiers are numbered globally
# 1-33 by Supercell, followed by Legend III, II, I. The official API exposes
# the player's current ranked tier in `leagueTier` (for example,
# "Valkyrie League 14" with id 105000014).
LEAGUE_FAMILY_RANGES = [
    ("Skeleton", 1, 3),
    ("Barbarian", 4, 6),
    ("Archer", 7, 9),
    ("Wizard", 10, 12),
    ("Valkyrie", 13, 15),
    ("Witch", 16, 18),
    ("Golem", 19, 21),
    ("P.E.K.K.A", 22, 24),
    ("Titan", 25, 27),
    ("Dragon", 28, 30),
    ("Electro", 31, 33),
]
LEAGUE_FAMILY_MIN = {name.upper().replace(".", ""): lo for name, lo, _ in LEAGUE_FAMILY_RANGES}
LEAGUE_FAMILY_MIN.update({"PEKKA": 22, "LEGEND": 34})
LEGEND_SCORE_BY_ROMAN = {"III": 34, "II": 35, "I": 36}


def league_tier_label(score):
    score = safe_int(score)
    if score <= 0:
        return "Any / Unranked"
    for family, lo, hi in LEAGUE_FAMILY_RANGES:
        if lo <= score <= hi:
            return f"{family} League {score}"
    if score == 34:
        return "Legend League III"
    if score == 35:
        return "Legend League II"
    if score == 36:
        return "Legend League I"
    return f"Ranked tier {score}"


def parse_league_requirement(value):
    """Return (minimum_score, normalized_label) for a user league setting.

    Accepted examples: ANY, Titan, Titan 25, Titan League 25, 25,
    Electro 33, Legend III, Legend II, Legend I. A family name by itself
    means the lowest tier in that family (e.g. Titan == tier 25+).
    """
    raw = str(value or "ANY").strip()
    if not raw:
        raw = "ANY"
    compact = re.sub(r"\s+", " ", raw.upper().replace("P.E.K.K.A", "PEKKA").replace("P.E.K.K.A.", "PEKKA")).strip()
    compact = compact.replace(" LEAGUE", "")
    if compact in {"ANY", "NONE", "OFF", "UNRANKED", "0"}:
        return 0, "Any / Unranked"

    if compact.startswith("LEGEND"):
        rest = compact[len("LEGEND"):].strip()
        if not rest:
            return 34, league_tier_label(34)
        if rest in LEGEND_SCORE_BY_ROMAN:
            score = LEGEND_SCORE_BY_ROMAN[rest]
            return score, league_tier_label(score)
        if rest.isdigit() and int(rest) in (34, 35, 36):
            score = int(rest)
            return score, league_tier_label(score)
        raise ValueError("Legend must be Legend III, Legend II, Legend I, or tier 34-36.")

    m = re.search(r"(?:^|\s)(\d{1,2})$", compact)
    if m:
        score = int(m.group(1))
        if not 1 <= score <= 36:
            raise ValueError("Ranked league tier must be between 1 and 36.")
        return score, league_tier_label(score)

    family_key = compact.replace(".", "")
    if family_key in LEAGUE_FAMILY_MIN:
        score = LEAGUE_FAMILY_MIN[family_key]
        return score, league_tier_label(score)

    valid = ", ".join([x[0] for x in LEAGUE_FAMILY_RANGES] + ["Legend III", "Legend II", "Legend I"] )
    raise ValueError(f"Unknown Ranked League '{raw}'. Try ANY, a tier number 1-36, or: {valid}.")


def league_score_from_name(name):
    name = str(name or "").strip()
    if not name or name.casefold() == "unranked":
        return 0
    try:
        return parse_league_requirement(name)[0]
    except ValueError:
        return 0


def league_score_from_player(player):
    tier = (player or {}).get("leagueTier") or {}
    tier_id = safe_int(tier.get("id"))
    if 105000000 <= tier_id <= 105000999:
        score = tier_id - 105000000
        if 0 <= score <= 36:
            return score
    return league_score_from_name(tier.get("name"))


def league_score_from_record(rec):
    score = safe_int((rec or {}).get("leagueTierScore"), -1)
    if score >= 0:
        return score
    tier_id = safe_int((rec or {}).get("leagueTierId"))
    if 105000000 <= tier_id <= 105000999:
        score = tier_id - 105000000
        if 0 <= score <= 36:
            return score
    return league_score_from_name((rec or {}).get("leagueTierName"))


def profile_link(tag):
    clean = normalize_tag(tag).lstrip("#")
    return f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={clean}"


def parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def seconds_between(a, b):
    da = parse_iso(a)
    db = parse_iso(b)
    if not da or not db:
        return None
    return max(0, int((db - da).total_seconds()))


def human_duration(seconds):
    if seconds is None:
        return "unknown"
    try:
        seconds = max(0, int(seconds))
    except Exception:
        return "unknown"

    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    rem_m = minutes % 60
    if hours < 24:
        return f"{hours}h {rem_m}m" if rem_m else f"{hours}h"
    days = hours // 24
    rem_h = hours % 24
    return f"{days}d {rem_h}h" if rem_h else f"{days}d"


def age_text(iso_value, now=None):
    dt = parse_iso(iso_value)
    if not dt:
        return "unknown"
    now = now or utc_now()
    seconds = max(0, int((now - dt).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        mins = max(1, seconds // 60)
        return f"{mins} min ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr{'s' if hours != 1 else ''} ago"
    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


def freshness_label(detected_at, now=None):
    dt = parse_iso(detected_at)
    if not dt:
        return "RECENTLY DETECTED"
    now = now or utc_now()
    hours = max(0, (now - dt).total_seconds() / 3600)
    if hours <= 1:
        return "JUST DETECTED — <1h"
    if hours <= 24:
        return "NEW — <24h"
    if hours <= 72:
        return "VERY RECENT — <3d"
    if hours <= 168:
        return "RECENT — <7d"
    return "OLDER DETECTION"


def json_load(path, default):
    try:
        manifest = STATE_DIR / 'generation.json'
        if manifest.exists() and Path(path).parent == STATE_DIR and Path(path).name not in ('generation.json', 'scan_checkpoint.json'):
            generation = json.loads(manifest.read_text(encoding='utf-8'))
            if Path(path).name in generation['files']:
                directory = Path(generation['directory'])
                candidate = directory if directory.is_absolute() else STATE_DIR / directory
                if not candidate.resolve().is_relative_to((STATE_DIR/'generations').resolve()):
                    raise ValueError('Invalid recruiter generation path')
                path = candidate / Path(path).name
                if not path.is_file():
                    raise ValueError('The completed recruiter generation is incomplete; restore its previous generation')
        if Path(path).exists():
            with Path(path).open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        log_error(f"Could not read {Path(path).name}: {exc}")
        raise ValueError(f"Saved recruiter file {Path(path).name} is unreadable. Restore the prior generation; existing files were not overwritten.") from exc
    return default


def json_save_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if path.exists():
        import shutil
        shutil.copy2(path, path.with_suffix(path.suffix + '.previous'))
    tmp.replace(path)


def save_generation(values):
    # One manifest is the commit point. A crash before it leaves the previous generation valid.
    import uuid
    folder = STATE_DIR / 'generations' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    for path, value in values:
        json_save_atomic(folder / Path(path).name, value)
    json_save_atomic(STATE_DIR / 'generation.json', {'version': 1, 'directory': folder.relative_to(STATE_DIR).as_posix(), 'files': [Path(p).name for p, _ in values]})
    # Legacy mirrors remain available to older Pyto copies and cloud packaging.
    for path, value in values:
        json_save_atomic(path, value)


def log_error(message, context=None):
    try:
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "at": iso_now(),
            "message": str(message),
        }
        if context is not None:
            payload["context"] = context
        with ERROR_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Error logging must never crash the recruiter.
        pass


def fingerprint_tags(clans):
    tags = sorted(normalize_tag(c.get("tag")) for c in clans if c.get("tag"))
    raw = "\n".join(tags).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def clamp_fraction(value, default=DEFAULT_CORE_FRACTION):
    try:
        v = float(value)
    except Exception:
        return default
    return max(0.05, min(0.95, v))


def normalize_token(raw):
    token = str(raw or "").strip()
    # Accept users pasting quoted values from a note/app.
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        token = token[1:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _split_env_tokens(raw):
    """Split optional multi-token environment input without exposing values."""
    text = str(raw or "").strip()
    if not text:
        return []
    # Clash API JWTs do not contain whitespace, commas, or semicolons, so these
    # are safe convenience separators for COC_API_TOKENS.
    for sep in (",", ";"):
        text = text.replace(sep, "\n")
    return [part.strip() for part in text.splitlines() if part.strip()]


def get_tokens():
    """Return all configured API tokens, de-duplicated and in stable order.

    Backward compatible with the original one-token coc_token.txt file.
    Additional keys are simply placed on additional nonblank lines. Lines that
    start with # are comments and are ignored.
    """
    raw_values = []

    # Optional environment configuration. The plural form may contain tokens
    # separated by newlines, commas, or semicolons. The singular form remains
    # supported for backward compatibility.
    raw_values.extend(_split_env_tokens(os.getenv("COC_API_TOKENS", "")))
    single_env = os.getenv("COC_API_TOKEN", "")
    if single_env:
        raw_values.append(single_env)

    if TOKEN_FILE.exists():
        try:
            for line in TOKEN_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                raw_values.append(line)
        except Exception as exc:
            log_error(f"Could not read token file: {exc}")
    else:
        try:
            TOKEN_FILE.write_text("", encoding="utf-8")
        except Exception as exc:
            log_error(f"Could not create token file: {exc}")

    tokens = []
    seen = set()
    for raw in raw_values:
        token = normalize_token(raw)
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)

    if tokens:
        return tokens

    raise SystemExit(
        "\nNo Clash API token was found.\n\n"
        f"Open this file and add your API key:\n{TOKEN_FILE}\n\n"
        "For multiple locations, put ONE API key on EACH LINE. You can add as "
        "many keys as you want. The script will automatically try them until "
        "it finds the key authorized for your current public IP.\n\n"
        "Raw tokens, quoted tokens, and values that start with 'Bearer ' are accepted."
    )


def get_token():
    """Backward-compatible helper for code that expects a single token."""
    return get_tokens()[0]


# ---------------------------------------------------------------------------
# Supercell API
# ---------------------------------------------------------------------------

class OfficialAPI:
    def __init__(self, tokens):
        if isinstance(tokens, str):
            tokens = [tokens]

        cleaned = []
        seen = set()
        for raw in tokens or []:
            token = normalize_token(raw)
            if token and token not in seen:
                seen.add(token)
                cleaned.append(token)

        if not cleaned:
            raise ValueError("At least one Clash API token is required.")

        self.tokens = cleaned
        self._preferred_index = 0
        self._preference_lock = threading.Lock()
        self._main_sessions = {}
        atexit.register(self.close)

    @property
    def key_count(self):
        return len(self.tokens)

    @property
    def active_key_number(self):
        with self._preference_lock:
            return self._preferred_index + 1

    def _new_session(self, token_index):
        s = requests.Session()
        s.headers.update({
            "Authorization": f"Bearer {self.tokens[token_index]}",
            "Accept": "application/json",
            "User-Agent": f"Clash-Recruitment/{VERSION}",
        })
        return s

    def _session(self, token_index):
        # requests.Session should not be shared by worker threads. Keep a
        # separate session for each token in each thread.
        if threading.current_thread() is threading.main_thread():
            session = self._main_sessions.get(token_index)
            if session is None:
                session = self._new_session(token_index)
                self._main_sessions[token_index] = session
            return session

        stores = getattr(_thread_local, "coc_sessions", None)
        if stores is None:
            stores = {}
            _thread_local.coc_sessions = stores
        key = (id(self), token_index)
        session = stores.get(key)
        if session is None:
            session = self._new_session(token_index)
            stores[key] = session
        return session

    def _ordered_token_indices(self):
        with self._preference_lock:
            preferred = self._preferred_index
        return [preferred] + [i for i in range(len(self.tokens)) if i != preferred]

    def _mark_working(self, token_index):
        # The first successful authenticated request establishes the preferred
        # key. If the network changes during a run, a later successful key can
        # safely become preferred.
        with self._preference_lock:
            self._preferred_index = token_index

    def get(self, endpoint, params=None, retries=5, allow_404=False):
        url = API_ROOT + endpoint
        rejected_indices = []

        # A 401/403 is authentication/IP-specific, so try the next configured
        # key immediately. Network errors, rate limits, and server errors are
        # retried on the same key instead of using extra keys to evade limits.
        for token_index in self._ordered_token_indices():
            last_error = None
            auth_rejected = False

            for attempt in range(1, retries + 1):
                try:
                    r = self._session(token_index).get(url, params=params, timeout=30)
                except requests.RequestException as exc:
                    last_error = exc
                    time.sleep(min(8, attempt * 1.5))
                    continue

                if r.status_code in (401, 403):
                    rejected_indices.append(token_index)
                    auth_rejected = True
                    # Never log the token itself.
                    log_error(
                        f"Supercell rejected API key {token_index + 1} of "
                        f"{len(self.tokens)} with HTTP {r.status_code}; trying next key."
                    )
                    break

                # A 404 proves authentication succeeded, so remember this key
                # even when the caller wants None for a missing player/clan.
                if r.status_code == 404 and allow_404:
                    self._mark_working(token_index)
                    return None

                if r.status_code == 429:
                    retry_after = safe_int(r.headers.get("Retry-After"), 0)
                    time.sleep(retry_after if retry_after > 0 else min(20, attempt * 3))
                    continue

                if r.status_code in (500, 502, 503, 504):
                    time.sleep(min(15, attempt * 2.5))
                    continue

                try:
                    r.raise_for_status()
                except requests.HTTPError as exc:
                    last_error = exc
                    break

                try:
                    data = r.json()
                except ValueError as exc:
                    last_error = exc
                    break

                self._mark_working(token_index)
                return data

            if auth_rejected:
                continue

            # Authentication was not the problem. Preserve the old safety
            # behavior: do not hide network/server/format errors by cycling keys.
            if last_error:
                raise RuntimeError(str(last_error))
            raise RuntimeError(f"Supercell request failed: {endpoint}")

        count = len(self.tokens)
        noun = "key" if count == 1 else "keys"
        raise RuntimeError(
            f"Supercell rejected all {count} configured API {noun} for this network. "
            f"Each key must be created/authorized for the public IP of a location "
            f"where you want to run the script. Add another key on a new line in "
            f"{TOKEN_FILE}."
        )

    def get_locations(self):
        return (self.get("/locations", {"limit": 500}) or {}).get("items", [])

    def search_clans(self, location_id, min_members, limit=50, after=None):
        params = {
            "locationId": location_id,
            "minMembers": min_members,
            "limit": limit,
        }
        if after:
            params["after"] = after
        return self.get("/clans", params) or {}

    def get_members(self, clan_tag):
        endpoint = "/clans/" + quote(normalize_tag(clan_tag), safe="") + "/members"
        data = self.get(endpoint, {"limit": 50}, allow_404=True)
        if data is None:
            return None
        return data.get("items", [])

    def get_clan(self, clan_tag):
        endpoint = "/clans/" + quote(normalize_tag(clan_tag), safe="")
        return self.get(endpoint, allow_404=True)

    def get_player(self, player_tag):
        endpoint = "/players/" + quote(normalize_tag(player_tag), safe="")
        return self.get(endpoint, allow_404=True)

    def close(self):
        for session in list(self._main_sessions.values()):
            try:
                session.close()
            except Exception:
                pass
        self._main_sessions.clear()


def get_us_location(api):
    for loc in api.get_locations():
        if bool(loc.get("isCountry")) and str(loc.get("name", "")).casefold() == "united states":
            return loc
    raise RuntimeError("United States location could not be found.")


# ---------------------------------------------------------------------------
# Clan discovery, core/rotating pool, and turnover metrics
# ---------------------------------------------------------------------------

def discover_us_clans(api, location_id, max_clans, min_members):
    print("\nDiscovering U.S.-located clans...")
    clans = []
    seen = set()
    after = None

    while len(clans) < max_clans:
        page = api.search_clans(
            location_id=location_id,
            min_members=min_members,
            limit=50,
            after=after,
        )
        items = page.get("items", []) if isinstance(page, dict) else []
        if not items:
            break

        for item in items:
            tag = normalize_tag(item.get("tag"))
            if not tag or tag in seen:
                continue
            seen.add(tag)
            clans.append({
                "tag": tag,
                "name": item.get("name", "Unknown clan"),
                "members": safe_int(item.get("members")),
            })
            if len(clans) >= max_clans:
                break

        print(f"  Discovered {len(clans):,}/{max_clans:,} clans")

        paging = page.get("paging", {}) if isinstance(page, dict) else {}
        cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
        next_after = cursors.get("after") if isinstance(cursors, dict) else None
        if not next_after or next_after == after:
            break
        after = next_after

    return clans


def get_metrics_store():
    data = json_load(CLAN_METRICS_FILE, {"version": 1, "clans": {}})
    if not isinstance(data, dict):
        data = {"version": 1, "clans": {}}
    if not isinstance(data.get("clans"), dict):
        data["clans"] = {}
    return data


def metric_for(metrics_store, tag):
    tag = normalize_tag(tag)
    rec = metrics_store.get("clans", {}).get(tag, {})
    return rec if isinstance(rec, dict) else {}


def turnover_rate(metric):
    observed = safe_int(metric.get("observedMemberSlots"))
    departures = safe_int(metric.get("departuresDetected"))
    if observed <= 0:
        return 0.0
    return departures * 100.0 / observed


def recruiting_value(metric):
    """Transparent rule, not a candidate quality score."""
    qualifying = safe_int(metric.get("qualifyingClanlessDepartures"))
    rate = turnover_rate(metric)
    if qualifying >= 3 or rate >= 3.0:
        return "High"
    if qualifying >= 1 or rate >= 1.0:
        return "Medium"
    return "Low"


def clan_priority_tuple(clan, metrics_store):
    m = metric_for(metrics_store, clan.get("tag"))
    last_departure = parse_iso(m.get("lastDepartureAt"))
    last_departure_ts = last_departure.timestamp() if last_departure else 0
    return (
        safe_int(m.get("qualifyingClanlessDepartures")),
        safe_int(m.get("departuresDetected")),
        turnover_rate(m),
        last_departure_ts,
        safe_int(m.get("successfulScans")),
    )


def normalize_tracked_state(stored, us, max_clans, min_members, core_fraction):
    now = iso_now()
    if not isinstance(stored, dict):
        stored = {}
    raw_clans = stored.get("clans")
    if not isinstance(raw_clans, list):
        raw_clans = []

    normalized = []
    seen = set()
    core_target = max(1, int(round(max(1, len(raw_clans)) * core_fraction))) if raw_clans else 0

    for idx, c in enumerate(raw_clans):
        if not isinstance(c, dict):
            continue
        tag = normalize_tag(c.get("tag"))
        if not tag or tag in seen:
            continue
        seen.add(tag)
        bucket = c.get("bucket")
        if bucket not in ("core", "rotating"):
            bucket = "core" if idx < core_target else "rotating"
        normalized.append({
            "tag": tag,
            "name": c.get("name", "Unknown clan"),
            "members": safe_int(c.get("members")),
            "bucket": bucket,
            "addedAt": c.get("addedAt") or stored.get("createdAt") or now,
            "lastSeenAt": c.get("lastSeenAt"),
            "needsBaseline": bool(c.get("needsBaseline", False)),
        })

    return {
        "version": 2,
        "createdAt": stored.get("createdAt") or now,
        "updatedAt": now,
        "lastRotationAt": stored.get("lastRotationAt") or now,
        "locationId": stored.get("locationId") or us.get("id"),
        "locationName": stored.get("locationName") or us.get("name"),
        "minMembers": safe_int(stored.get("minMembers"), min_members),
        "maxClans": safe_int(stored.get("maxClans"), max_clans),
        "coreFraction": safe_float(stored.get("coreFraction"), core_fraction),
        "clans": normalized,
    }


def reclassify_clan_buckets(tracked_state, metrics_store, core_fraction):
    clans = tracked_state.get("clans", [])
    if not clans:
        return
    core_count = max(1, min(len(clans), int(round(len(clans) * core_fraction))))
    ranked = sorted(
        clans,
        key=lambda c: clan_priority_tuple(c, metrics_store),
        reverse=True,
    )
    core_tags = {c["tag"] for c in ranked[:core_count]}
    for c in clans:
        c["bucket"] = "core" if c["tag"] in core_tags else "rotating"


def rotation_due(tracked_state, rotation_days):
    if rotation_days <= 0:
        return False
    last = parse_iso(tracked_state.get("lastRotationAt"))
    if not last:
        return False
    return utc_now() - last >= timedelta(days=rotation_days)


def maybe_rotate_clans(
    api,
    tracked_state,
    metrics_store,
    location_id,
    max_clans,
    min_members,
    core_fraction,
    rotation_days,
    rotation_count,
    force_refresh=False,
):
    now = iso_now()

    if force_refresh or not tracked_state.get("clans"):
        discovered = discover_us_clans(api, location_id, max_clans, min_members)
        if not discovered:
            raise RuntimeError("No U.S.-located clans were discovered.")
        clans = []
        core_count = max(1, int(round(len(discovered) * core_fraction)))
        for i, c in enumerate(discovered):
            clans.append({
                **c,
                "bucket": "core" if i < core_count else "rotating",
                "addedAt": now,
                "lastSeenAt": None,
                "needsBaseline": True,
            })
        tracked_state.update({
            "version": 2,
            "createdAt": tracked_state.get("createdAt") or now,
            "updatedAt": now,
            "lastRotationAt": now,
            "locationId": location_id,
            "minMembers": min_members,
            "maxClans": max_clans,
            "coreFraction": core_fraction,
            "clans": clans,
        })
        return {"rotated": True, "added": [c["tag"] for c in clans], "removed": []}

    # Keep the highest-value clans in the core group before choosing removals.
    reclassify_clan_buckets(tracked_state, metrics_store, core_fraction)

    if not rotation_due(tracked_state, rotation_days) or rotation_count <= 0:
        tracked_state["updatedAt"] = now
        return {"rotated": False, "added": [], "removed": []}

    existing = tracked_state["clans"]
    existing_tags = {c["tag"] for c in existing}
    rotating = [c for c in existing if c.get("bucket") == "rotating"]
    if not rotating:
        tracked_state["lastRotationAt"] = now
        return {"rotated": False, "added": [], "removed": []}

    remove_n = min(rotation_count, len(rotating))
    removal_rank = sorted(
        rotating,
        key=lambda c: clan_priority_tuple(c, metrics_store),
    )
    proposed_remove = removal_rank[:remove_n]
    proposed_remove_tags = {c["tag"] for c in proposed_remove}

    # Ask for a wider discovery pool so we have a real chance of finding tags
    # that are not already being tracked.
    discovery_target = min(max(200, max_clans + remove_n * 5), max_clans * 3)
    discovered = discover_us_clans(api, location_id, discovery_target, min_members)
    replacements = []
    for c in discovered:
        tag = normalize_tag(c.get("tag"))
        if not tag or tag in existing_tags or any(x["tag"] == tag for x in replacements):
            continue
        replacements.append({
            **c,
            "tag": tag,
            "bucket": "rotating",
            "addedAt": now,
            "lastSeenAt": None,
            "needsBaseline": True,
        })
        if len(replacements) >= remove_n:
            break

    actual_remove_n = min(len(replacements), remove_n)
    actual_remove_tags = {c["tag"] for c in proposed_remove[:actual_remove_n]}
    kept = [c for c in existing if c["tag"] not in actual_remove_tags]
    kept.extend(replacements[:actual_remove_n])

    # Do not exceed the requested pool size; normally this is already exact.
    tracked_state["clans"] = kept[:max_clans]
    tracked_state["lastRotationAt"] = now
    tracked_state["updatedAt"] = now
    reclassify_clan_buckets(tracked_state, metrics_store, core_fraction)

    return {
        "rotated": actual_remove_n > 0,
        "added": [c["tag"] for c in replacements[:actual_remove_n]],
        "removed": sorted(actual_remove_tags),
    }


def load_or_create_tracked_clans(
    api, us, max_clans, min_members, metrics_store,
    core_fraction, rotation_days, rotation_count, force_refresh=False,
):
    stored = json_load(TRACKED_CLANS_FILE, {})
    tracked_state = normalize_tracked_state(
        stored, us, max_clans, min_members, core_fraction
    )

    info = maybe_rotate_clans(
        api=api,
        tracked_state=tracked_state,
        metrics_store=metrics_store,
        location_id=us["id"],
        max_clans=max_clans,
        min_members=min_members,
        core_fraction=core_fraction,
        rotation_days=rotation_days,
        rotation_count=rotation_count,
        force_refresh=force_refresh,
    )

    if not tracked_state.get("clans"):
        raise RuntimeError("No U.S.-located clans are being tracked.")

    json_save_atomic(TRACKED_CLANS_FILE, tracked_state)
    if info["rotated"]:
        print(
            f"\nClan pool updated: +{len(info['added'])} rotating clan(s), "
            f"-{len(info['removed'])} low-value rotating clan(s)."
        )
    else:
        core_count = sum(1 for c in tracked_state["clans"] if c.get("bucket") == "core")
        rot_count = len(tracked_state["clans"]) - core_count
        print(
            f"\nUsing {len(tracked_state['clans']):,} tracked U.S. clans "
            f"({core_count:,} core / {rot_count:,} rotating)."
        )
    return tracked_state, info


# ---------------------------------------------------------------------------
# Roster fetching, checkpoints, comparisons, and hot-clan second scan
# ---------------------------------------------------------------------------

def fetch_roster(api, clan):
    tag = normalize_tag(clan.get("tag"))
    try:
        members = api.get_members(tag)
        captured_at = iso_now()
        if members is None:
            return tag, None, captured_at, "not_found"
        member_map = {}
        for m in members:
            ptag = normalize_tag(m.get("tag"))
            if not ptag:
                continue
            member_map[ptag] = {
                "name": m.get("name", ""),
                "townHallLevel": safe_int(m.get("townHallLevel")),
                "expLevel": safe_int(m.get("expLevel")),
                "trophies": safe_int(m.get("trophies")),
            }
        return tag, member_map, captured_at, None
    except Exception as exc:
        return tag, None, iso_now(), str(exc)


def load_resume_checkpoint(clans, max_age_hours, previous_last_run_at=None):
    data = json_load(CHECKPOINT_FILE, {})
    if not isinstance(data, dict) or not data.get("rosters"):
        return None
    if data.get("fingerprint") != fingerprint_tags(clans):
        return None
    started = parse_iso(data.get("startedAt"))
    if not started:
        return None
    if utc_now() - started > timedelta(hours=max_age_hours):
        return None
    prev = parse_iso(previous_last_run_at)
    if prev and started <= prev:
        return None
    return data


def save_checkpoint(scan_id, started_at, clans, rosters, errors):
    json_save_atomic(CHECKPOINT_FILE, {
        "version": 1,
        "scanId": scan_id,
        "startedAt": started_at,
        "updatedAt": iso_now(),
        "fingerprint": fingerprint_tags(clans),
        "rosters": rosters,
        "errors": errors,
    })


def fetch_all_rosters(api, clans, workers, previous_last_run_at=None, checkpoint_max_age_hours=12):
    print("\nFetching current rosters from Supercell...")
    workers = max(1, min(workers, 20))
    scan_id = str(uuid.uuid4())
    started_at = iso_now()

    checkpoint = load_resume_checkpoint(
        clans,
        max_age_hours=checkpoint_max_age_hours,
        previous_last_run_at=previous_last_run_at,
    )

    current = {}
    errors = {}
    if checkpoint:
        scan_id = checkpoint.get("scanId") or scan_id
        started_at = checkpoint.get("startedAt") or started_at
        raw_rosters = checkpoint.get("rosters", {})
        if isinstance(raw_rosters, dict):
            current.update(raw_rosters)
        print(f"  Resuming checkpoint with {len(current):,} completed clan roster(s).")

    completed_tags = set(current)
    pending = [c for c in clans if normalize_tag(c.get("tag")) not in completed_tags]
    completed = len(current)
    total_members = sum(len(r.get("members", {})) for r in current.values() if isinstance(r, dict))

    if not pending:
        return current, errors, scan_id, started_at, True

    since_checkpoint = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_roster, api, clan): clan for clan in pending}

        for future in as_completed(futures):
            clan = futures[future]
            completed += 1
            since_checkpoint += 1
            try:
                tag, members, captured_at, err = future.result()
            except Exception as exc:
                tag = normalize_tag(clan.get("tag"))
                members = None
                captured_at = iso_now()
                err = str(exc)

            if members is not None:
                current[tag] = {
                    "name": clan.get("name", "Unknown clan"),
                    "capturedAt": captured_at,
                    "members": members,
                }
                total_members += len(members)
                errors.pop(tag, None)
            else:
                errors[tag] = err or "unknown error"
                log_error(
                    f"Roster fetch failed for {tag}: {errors[tag]}",
                    {"clanTag": tag, "clanName": clan.get("name", "")},
                )

            if since_checkpoint >= CHECKPOINT_SAVE_EVERY:
                save_checkpoint(scan_id, started_at, clans, current, errors)
                since_checkpoint = 0

            if completed % 50 == 0 or completed == len(clans):
                print(
                    f"  {completed:,}/{len(clans):,} clans | "
                    f"{total_members:,} member slots captured | "
                    f"{len(errors):,} current errors"
                )

    save_checkpoint(scan_id, started_at, clans, current, errors)
    return current, errors, scan_id, started_at, False


def dedupe_departures(departures):
    best = {}
    for d in departures:
        tag = normalize_tag(d.get("tag"))
        if not tag:
            continue
        d["tag"] = tag
        window = d.get("observationWindowSeconds")
        if window is None:
            window = seconds_between(d.get("previousRosterAt"), d.get("detectedAt"))
            d["observationWindowSeconds"] = window
        old = best.get(tag)
        if old is None:
            best[tag] = d
            continue
        a = window if window is not None else 10**18
        b_raw = old.get("observationWindowSeconds")
        b = b_raw if b_raw is not None else 10**18
        if a < b:
            best[tag] = d
        elif a == b:
            # If equally tight, keep the more recent detection.
            da = parse_iso(d.get("detectedAt")) or datetime.min.replace(tzinfo=timezone.utc)
            db = parse_iso(old.get("detectedAt")) or datetime.min.replace(tzinfo=timezone.utc)
            if da > db:
                best[tag] = d
    return list(best.values())


def compare_rosters(previous, current, skip_tags=None):
    skip_tags = {normalize_tag(x) for x in (skip_tags or set())}
    departures = []
    comparable_clans = 0
    per_clan_departures = {}

    previous_clans = previous.get("clans", {}) if isinstance(previous, dict) else {}

    for clan_tag, new_data in current.items():
        clan_tag = normalize_tag(clan_tag)
        if clan_tag in skip_tags:
            continue
        old_data = previous_clans.get(clan_tag)
        if not old_data:
            continue

        old_members = old_data.get("members", {}) or {}
        new_members = new_data.get("members", {}) or {}
        comparable_clans += 1
        count = 0

        for player_tag in set(old_members) - set(new_members):
            old_player = old_members[player_tag]
            d = {
                "tag": normalize_tag(player_tag),
                "name": old_player.get("name", ""),
                "townHallAtPreviousScan": safe_int(old_player.get("townHallLevel")),
                "sourceClanTag": clan_tag,
                "sourceClanName": old_data.get("name") or new_data.get("name") or "",
                "previousRosterAt": old_data.get("capturedAt"),
                "detectedAt": new_data.get("capturedAt"),
            }
            d["observationWindowSeconds"] = seconds_between(
                d["previousRosterAt"], d["detectedAt"]
            )
            departures.append(d)
            count += 1

        per_clan_departures[clan_tag] = count

    return dedupe_departures(departures), comparable_clans, per_clan_departures


def select_hot_clans(tracked_clans, metrics_store, count):
    if count <= 0:
        return []
    candidates = []
    for c in tracked_clans:
        m = metric_for(metrics_store, c.get("tag"))
        if safe_int(m.get("departuresDetected")) <= 0:
            continue
        candidates.append(c)
    candidates.sort(key=lambda c: clan_priority_tuple(c, metrics_store), reverse=True)
    return candidates[:count]


def hot_rescan(api, hot_clans, first_current, workers):
    """Second scan of high-turnover clans. Failures preserve first-scan rosters."""
    if not hot_clans:
        return first_current, [], {}, 0

    print(f"\nRe-scanning {len(hot_clans):,} high-turnover core clan(s)...")
    second = {}
    errors = {}
    workers = max(1, min(workers, 20))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_roster, api, clan): clan for clan in hot_clans}
        for future in as_completed(futures):
            clan = futures[future]
            try:
                tag, members, captured_at, err = future.result()
            except Exception as exc:
                tag = normalize_tag(clan.get("tag"))
                members = None
                captured_at = iso_now()
                err = str(exc)

            if members is None:
                errors[tag] = err or "unknown error"
                log_error(f"Hot rescan failed for {tag}: {errors[tag]}")
                continue
            second[tag] = {
                "name": clan.get("name", "Unknown clan"),
                "capturedAt": captured_at,
                "members": members,
            }

    # Compare first successful scan to the second successful scan for these clans.
    first_subset = {tag: first_current[tag] for tag in second if tag in first_current}
    hot_departures, comparable, per_clan = compare_rosters(
        {"clans": first_subset}, second, skip_tags=set()
    )

    final_current = dict(first_current)
    # Only replace first-scan roster when the second scan succeeded.
    final_current.update(second)
    hot_observed_slots = {
        tag: len(first_subset[tag].get("members", {})) for tag in first_subset
    }
    return final_current, hot_departures, per_clan, comparable, hot_observed_slots


# ---------------------------------------------------------------------------
# Candidate lifecycle, filters, duplicate cooldown
# ---------------------------------------------------------------------------

LIFECYCLE_NEW = "NEW"
LIFECYCLE_STILL = "STILL_CLANLESS"
LIFECYCLE_JOINED_MY = "JOINED_MY_CLAN"
LIFECYCLE_JOINED_OTHER = "JOINED_OTHER_CLAN"
LIFECYCLE_COOLDOWN = "COOLDOWN_CLANLESS"
LIFECYCLE_FILTERED = "BELOW_FILTERS"
LIFECYCLE_VERIFY_ERROR = "VERIFY_ERROR"
LIFECYCLE_ARCHIVED = "ARCHIVED"


def get_leaver_store(my_clan_tag):
    my_clan_tag = normalize_tag(my_clan_tag)
    data = json_load(LEAVERS_FILE, {"version": 5, "players": {}})
    if not isinstance(data, dict):
        data = {"version": 5, "players": {}}
    if not isinstance(data.get("players"), dict):
        data["players"] = {}
    data["version"] = 5

    # Migrate 3.x records in place without losing the old detections.
    for tag, rec in list(data["players"].items()):
        if not isinstance(rec, dict):
            data["players"].pop(tag, None)
            continue
        normalized_tag = normalize_tag(rec.get("tag") or tag)
        if normalized_tag != tag:
            data["players"].pop(tag, None)
            data["players"][normalized_tag] = rec
        rec["tag"] = normalized_tag

        if not rec.get("lifecycle"):
            old_status = rec.get("status")
            mapping = {
                "clanless": LIFECYCLE_STILL,
                "joined_another_clan": LIFECYCLE_JOINED_OTHER,
                "below_min_th": LIFECYCLE_FILTERED,
                "verify_error": LIFECYCLE_VERIFY_ERROR,
            }
            rec["lifecycle"] = mapping.get(old_status, LIFECYCLE_ARCHIVED)

        detected = rec.get("lastDepartureDetectedAt") or rec.get("detectedAt")

        # Upgrade the 4.0 generic JOINED_CLAN state without losing history.
        if rec.get("lifecycle") == "JOINED_CLAN":
            if normalize_tag(rec.get("currentClanTag")) == my_clan_tag:
                rec["lifecycle"] = LIFECYCLE_JOINED_MY
                if not rec.get("joinedMyClanAt"):
                    rec["joinedMyClanAt"] = rec.get("lastStatusChangedAt") or rec.get("lastVerifiedAt") or detected
            else:
                rec["lifecycle"] = LIFECYCLE_JOINED_OTHER

        if (
            rec.get("lifecycle") == LIFECYCLE_JOINED_MY
            and not rec.get("joinedMyClanAt")
        ):
            rec["joinedMyClanAt"] = rec.get("lastStatusChangedAt") or rec.get("lastVerifiedAt") or detected
        rec.setdefault("firstDetectedAt", detected)
        rec.setdefault("lastDepartureDetectedAt", detected)
        rec.setdefault("departureCount", 1 if detected else 0)
        rec.setdefault("events", [])
        rec.setdefault("firstClanlessVerifiedAt", rec.get("lastVerifiedAt") if rec.get("lifecycle") in (LIFECYCLE_NEW, LIFECYCLE_STILL) else None)
        rec.setdefault("lastClanlessVerifiedAt", rec.get("lastVerifiedAt") if rec.get("lifecycle") in (LIFECYCLE_NEW, LIFECYCLE_STILL) else None)
        rec.setdefault("lastStatusChangedAt", rec.get("lastVerifiedAt") or detected)
        # Treat old 3.x visible clanless records as already presented so the
        # upgrade itself does not flood the NEW section with duplicates.
        if rec.get("lifecycle") == LIFECYCLE_STILL:
            rec.setdefault("lastPresentedAt", detected)
            rec.setdefault("lastPresentedDepartureAt", detected)
        else:
            rec.setdefault("lastPresentedAt", None)
            rec.setdefault("lastPresentedDepartureAt", None)

    return data


def add_event(rec, event_type, at=None, **details):
    events = rec.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        rec["events"] = events
    event = {"type": event_type, "at": at or iso_now()}
    event.update({k: v for k, v in details.items() if v is not None})
    events.append(event)
    # Keep history useful without allowing one unusual player to grow forever.
    if len(events) > 100:
        del events[:-100]


def set_lifecycle(rec, new_lifecycle, reason=None, at=None):
    at = at or iso_now()
    old = rec.get("lifecycle")
    if old != new_lifecycle:
        rec["lifecycle"] = new_lifecycle
        rec["lastStatusChangedAt"] = at
        add_event(rec, "status_changed", at=at, old=old, new=new_lifecycle, reason=reason)


def update_profile_fields(rec, player):
    rec["name"] = player.get("name") or rec.get("name", "")
    rec["townHallLevel"] = safe_int(player.get("townHallLevel"))
    rec["expLevel"] = safe_int(player.get("expLevel"))
    rec["trophies"] = safe_int(player.get("trophies"))
    rec["bestTrophies"] = safe_int(player.get("bestTrophies"))
    rec["warStars"] = safe_int(player.get("warStars"))
    rec["attackWins"] = safe_int(player.get("attackWins"))
    rec["defenseWins"] = safe_int(player.get("defenseWins"))

    league = player.get("league") or {}
    tier = player.get("leagueTier") or {}
    rec["leagueName"] = league.get("name", "") if isinstance(league, dict) else ""
    rec["leagueId"] = safe_int(league.get("id")) if isinstance(league, dict) else 0
    rec["leagueTierName"] = tier.get("name", "") if isinstance(tier, dict) else ""
    rec["leagueTierId"] = safe_int(tier.get("id")) if isinstance(tier, dict) else 0
    rec["leagueTierScore"] = league_score_from_player(player)
    if not rec["leagueTierName"]:
        rec["leagueTierName"] = league_tier_label(rec["leagueTierScore"]) if rec["leagueTierScore"] else "Unranked"

    rec["profileLink"] = profile_link(rec.get("tag"))


def meets_filters(rec, filters):
    return (
        safe_int(rec.get("townHallLevel")) >= filters["min_th"]
        and safe_int(rec.get("warStars")) >= filters["min_war_stars"]
        and safe_int(rec.get("bestTrophies")) >= filters["min_best_trophies"]
        and safe_int(rec.get("trophies")) >= filters["min_current_trophies"]
        and safe_int(rec.get("expLevel")) >= filters["min_exp_level"]
        and league_score_from_record(rec) >= filters.get("min_league_score", 0)
    )


def cooldown_active(rec, cooldown_days, reference_at=None):
    last = parse_iso(rec.get("lastPresentedAt"))
    if not last:
        return False
    reference = parse_iso(reference_at) or utc_now()
    return reference - last < timedelta(days=cooldown_days)


def set_current_clan_state(rec, current_clan, my_clan_tag, now, reason):
    """Classify a verified clan membership, with your clan as a distinct state."""
    clan_tag = normalize_tag((current_clan or {}).get("tag"))
    clan_name = (current_clan or {}).get("name", "")
    rec["currentClanTag"] = clan_tag
    rec["currentClanName"] = clan_name

    if clan_tag and clan_tag == normalize_tag(my_clan_tag):
        first_detection = not rec.get("joinedMyClanAt")
        rec.setdefault("joinedMyClanAt", now)
        rec["lastJoinedMyClanVerifiedAt"] = now
        set_lifecycle(rec, LIFECYCLE_JOINED_MY, reason=reason, at=now)
        if first_detection:
            add_event(
                rec,
                "joined_my_clan_detected",
                at=now,
                clanTag=clan_tag,
                clanName=clan_name,
            )
    else:
        set_lifecycle(rec, LIFECYCLE_JOINED_OTHER, reason=reason, at=now)

    add_event(
        rec,
        "verified_in_clan",
        at=now,
        clanTag=clan_tag,
        clanName=clan_name,
    )


def sync_my_clan_membership(api, leaver_store, my_clan_tag, profile_cache=None):
    """
    Check your clan roster once per run and update every known candidate found in it.

    If the clan lookup fails, existing candidate states are preserved. A failed
    request can therefore never be interpreted as candidates leaving your clan.
    """
    profile_cache = profile_cache if profile_cache is not None else {}
    my_clan_tag = normalize_tag(my_clan_tag)
    result = {
        "ok": False,
        "clanTag": my_clan_tag,
        "clanName": "",
        "memberCount": 0,
        "candidateMembers": 0,
        "newCandidateJoins": 0,
    }

    try:
        clan = api.get_clan(my_clan_tag)
    except Exception as exc:
        log_error(f"Could not check your clan {my_clan_tag}: {exc}", {"clanTag": my_clan_tag})
        return result

    if not isinstance(clan, dict):
        log_error(f"Your clan {my_clan_tag} could not be found.", {"clanTag": my_clan_tag})
        return result

    clan_name = clan.get("name", "")
    members = clan.get("memberList") or []
    member_by_tag = {
        normalize_tag(m.get("tag")): m
        for m in members
        if isinstance(m, dict) and normalize_tag(m.get("tag"))
    }
    result.update({
        "ok": True,
        "clanName": clan_name,
        "memberCount": len(member_by_tag),
    })

    now = iso_now()
    previously_joined_now_missing = []

    for tag, rec in leaver_store["players"].items():
        tag = normalize_tag(tag)
        member = member_by_tag.get(tag)
        if member is not None:
            was_ever_joined = bool(rec.get("joinedMyClanAt"))
            # Refresh the fields supplied by the clan roster without erasing
            # richer player-profile fields that are absent from memberList.
            rec["name"] = member.get("name") or rec.get("name", "")
            if member.get("townHallLevel") is not None:
                rec["townHallLevel"] = safe_int(member.get("townHallLevel"))
            if member.get("expLevel") is not None:
                rec["expLevel"] = safe_int(member.get("expLevel"))
            if member.get("trophies") is not None:
                rec["trophies"] = safe_int(member.get("trophies"))
            rec["lastVerifiedAt"] = now
            set_current_clan_state(
                rec,
                {"tag": my_clan_tag, "name": clan_name},
                my_clan_tag,
                now,
                reason="found_in_my_clan_roster",
            )
            result["candidateMembers"] += 1
            if not was_ever_joined:
                result["newCandidateJoins"] += 1
        elif rec.get("lifecycle") == LIFECYCLE_JOINED_MY:
            # They were previously verified in your clan but are absent from
            # the current roster. Verify their profile before changing state.
            previously_joined_now_missing.append((tag, rec))

    for tag, rec in previously_joined_now_missing:
        player = profile_cache.get(tag)
        if player is None:
            try:
                player = api.get_player(tag)
                if player:
                    profile_cache[tag] = player
            except Exception as exc:
                log_error(
                    f"Could not reverify former member {tag} after leaving your clan roster: {exc}",
                    {"playerTag": tag, "clanTag": my_clan_tag},
                )
                continue

        if not isinstance(player, dict):
            continue

        check_time = iso_now()
        rec["lastVerifiedAt"] = check_time
        update_profile_fields(rec, player)
        current_clan = player.get("clan")
        if current_clan:
            set_current_clan_state(
                rec, current_clan, my_clan_tag, check_time, reason="left_my_clan_reverified_in_clan"
            )
        else:
            rec["currentClanTag"] = ""
            rec["currentClanName"] = ""
            # Do not silently turn a former member into a fresh candidate. A
            # tracked roster departure is still required for NEW eligibility.
            set_lifecycle(
                rec,
                LIFECYCLE_COOLDOWN,
                reason="left_my_clan_without_tracked_departure",
                at=check_time,
            )
            add_event(rec, "verified_clanless_after_my_clan", at=check_time)

    return result


def fetch_player_profiles_parallel(api, tags, profile_cache=None, workers=DEFAULT_PROFILE_WORKERS, label="player profiles"):
    """Fetch unique player profiles concurrently; never mutates candidate state.

    requests.Session objects remain thread-local inside OfficialAPI, while all
    candidate lifecycle mutations happen later on the main thread.
    """
    profile_cache = profile_cache if profile_cache is not None else {}
    ordered = []
    seen = set()
    for raw in tags:
        tag = normalize_tag(raw)
        if tag and tag not in seen:
            seen.add(tag)
            ordered.append(tag)

    pending = [tag for tag in ordered if not isinstance(profile_cache.get(tag), dict)]
    if not pending:
        return profile_cache, {}

    workers = max(1, min(safe_int(workers, DEFAULT_PROFILE_WORKERS), 20, len(pending)))
    print(f"  Fetching {len(pending):,} {label} with up to {workers} parallel worker(s)...")
    errors = {}
    completed = 0
    started = time.monotonic()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(api.get_player, tag): tag for tag in pending}
        for future in as_completed(futures):
            tag = futures[future]
            completed += 1
            try:
                player = future.result()
                if isinstance(player, dict):
                    profile_cache[tag] = player
                elif player is None:
                    errors[tag] = "player_not_found"
            except Exception as exc:
                errors[tag] = str(exc)

            if completed % 100 == 0 or completed == len(pending):
                elapsed = max(0.001, time.monotonic() - started)
                rate = completed / elapsed
                print(f"    {completed:,}/{len(pending):,} profiles | {rate:.1f}/sec | {len(errors):,} error(s)")

    return profile_cache, errors


def process_departures(api, departures, leaver_store, filters, cooldown_days, run_id, my_clan_tag, profile_workers=DEFAULT_PROFILE_WORKERS):
    if not departures:
        return {}, [], 0

    print(f"\nLive-checking {len(departures):,} possible departure(s)...")
    profile_cache = {}
    qualifying_departures = []
    clanless_count = 0

    departures = dedupe_departures(list(departures))
    departures.sort(
        key=lambda d: (
            d.get("observationWindowSeconds") is None,
            d.get("observationWindowSeconds") if d.get("observationWindowSeconds") is not None else 10**18,
        )
    )

    tags = [normalize_tag(d.get("tag")) for d in departures]
    profile_cache, fetch_errors = fetch_player_profiles_parallel(
        api, tags, profile_cache=profile_cache, workers=profile_workers, label="new-departure profiles"
    )

    for d in departures:
        tag = normalize_tag(d.get("tag"))
        player = profile_cache.get(tag)
        if not isinstance(player, dict):
            err = fetch_errors.get(tag, "no player profile returned")
            log_error(f"Could not verify departure {tag}: {err}", {"playerTag": tag})
            rec = leaver_store["players"].setdefault(tag, {"tag": tag, "events": [], "departureCount": 1, "firstDetectedAt": d.get("detectedAt"), "lastDepartureDetectedAt": d.get("detectedAt"), "detectedAt": d.get("detectedAt"), "previousRosterAt": d.get("previousRosterAt"), "observationWindowSeconds": d.get("observationWindowSeconds"), "sourceClanTag": d.get("sourceClanTag"), "sourceClanName": d.get("sourceClanName"), "lastDetectedRunId": run_id})
            set_lifecycle(rec, LIFECYCLE_VERIFY_ERROR, reason="departure_live_check_failed")
            rec["lastVerificationAttemptAt"] = iso_now()
            continue

        now = iso_now()
        rec = leaver_store["players"].get(tag)
        if not isinstance(rec, dict):
            rec = {
                "tag": tag,
                "events": [],
                "departureCount": 0,
                "firstDetectedAt": d.get("detectedAt") or now,
                "lastPresentedAt": None,
                "lastPresentedDepartureAt": None,
            }

        rec["departureCount"] = safe_int(rec.get("departureCount")) + 1
        rec["lastDepartureDetectedAt"] = d.get("detectedAt") or now
        rec["previousRosterAt"] = d.get("previousRosterAt")
        rec["detectedAt"] = d.get("detectedAt") or now
        rec["observationWindowSeconds"] = d.get("observationWindowSeconds")
        rec["sourceClanTag"] = d.get("sourceClanTag", "")
        rec["sourceClanName"] = d.get("sourceClanName", "")
        rec["lastDetectedRunId"] = run_id
        rec["lastVerifiedAt"] = now
        update_profile_fields(rec, player)

        add_event(
            rec,
            "departure_detected",
            at=rec["lastDepartureDetectedAt"],
            sourceClanTag=rec.get("sourceClanTag"),
            sourceClanName=rec.get("sourceClanName"),
            previousRosterAt=rec.get("previousRosterAt"),
            observationWindowSeconds=rec.get("observationWindowSeconds"),
        )

        current_clan = player.get("clan")
        if current_clan:
            set_current_clan_state(
                rec, current_clan, my_clan_tag, now, reason="currently_in_a_clan"
            )
        else:
            rec["currentClanTag"] = ""
            rec["currentClanName"] = ""
            rec["firstClanlessVerifiedAt"] = now
            rec["lastClanlessVerifiedAt"] = now
            add_event(rec, "verified_clanless", at=now)

            if not meets_filters(rec, filters):
                set_lifecycle(rec, LIFECYCLE_FILTERED, reason="does_not_meet_current_filters", at=now)
            elif cooldown_active(rec, cooldown_days, rec["lastDepartureDetectedAt"]):
                set_lifecycle(rec, LIFECYCLE_COOLDOWN, reason="duplicate_cooldown_active", at=now)
            else:
                set_lifecycle(rec, LIFECYCLE_NEW, reason="new_eligible_departure", at=now)
                clanless_count += 1
                qualifying_departures.append({
                    "playerTag": tag,
                    "sourceClanTag": rec.get("sourceClanTag", ""),
                    "detectedAt": rec.get("lastDepartureDetectedAt"),
                })
                print(
                    f"  NEW: {rec.get('name', '')} {tag} | TH{rec.get('townHallLevel', 0)} | "
                    f"{rec.get('leagueTierName','Unranked')} | "
                    f"leave window <= {human_duration(rec.get('observationWindowSeconds'))}"
                )

        leaver_store["players"][tag] = rec

    return profile_cache, qualifying_departures, clanless_count


def is_unpresented_new(rec):
    return (
        rec.get("lifecycle") == LIFECYCLE_NEW
        and rec.get("lastDepartureDetectedAt")
        and rec.get("lastPresentedDepartureAt") != rec.get("lastDepartureDetectedAt")
    )


def reverify_active_candidates(api, leaver_store, filters, active_days, profile_cache, my_clan_tag, profile_workers=DEFAULT_PROFILE_WORKERS):
    cutoff = utc_now() - timedelta(days=active_days)
    checkable = []

    for tag, rec in leaver_store["players"].items():
        detected = parse_iso(rec.get("lastDepartureDetectedAt") or rec.get("detectedAt"))
        if not detected or detected < cutoff:
            continue
        if rec.get("lifecycle") in (
            LIFECYCLE_NEW,
            LIFECYCLE_STILL,
            LIFECYCLE_COOLDOWN,
            LIFECYCLE_VERIFY_ERROR,
            LIFECYCLE_JOINED_MY,
            LIFECYCLE_JOINED_OTHER,
        ):
            checkable.append((tag, rec))

    checkable.sort(
        key=lambda pair: parse_iso(pair[1].get("lastDepartureDetectedAt"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    print(f"\nRe-verifying {len(checkable):,} active candidate record(s)...")
    if not checkable:
        return

    tags = [tag for tag, _ in checkable]
    cached_before = sum(1 for tag in tags if isinstance(profile_cache.get(tag), dict))
    started = time.monotonic()
    profile_cache, fetch_errors = fetch_player_profiles_parallel(
        api, tags, profile_cache=profile_cache, workers=profile_workers, label="active-candidate profiles"
    )

    for tag, rec in checkable:
        player = profile_cache.get(tag)
        if not isinstance(player, dict):
            err = fetch_errors.get(tag)
            if err:
                set_lifecycle(rec, LIFECYCLE_VERIFY_ERROR, reason="reverify_failed")
                rec["lastVerificationAttemptAt"] = iso_now()
                log_error(f"Could not reverify {tag}: {err}", {"playerTag": tag})
            continue

        now = iso_now()
        rec["lastVerifiedAt"] = now
        update_profile_fields(rec, player)
        current_clan = player.get("clan")

        previous_lifecycle = rec.get("lifecycle")
        if current_clan:
            set_current_clan_state(
                rec, current_clan, my_clan_tag, now, reason="reverified_in_clan"
            )
        else:
            rec["currentClanTag"] = ""
            rec["currentClanName"] = ""
            if not rec.get("firstClanlessVerifiedAt"):
                rec["firstClanlessVerifiedAt"] = now
            rec["lastClanlessVerifiedAt"] = now

            if not meets_filters(rec, filters):
                set_lifecycle(rec, LIFECYCLE_FILTERED, reason="does_not_meet_current_filters", at=now)
            elif previous_lifecycle in (LIFECYCLE_JOINED_MY, LIFECYCLE_JOINED_OTHER):
                set_lifecycle(
                    rec, LIFECYCLE_COOLDOWN,
                    reason="became_clanless_without_tracked_departure", at=now
                )
            elif rec.get("lifecycle") == LIFECYCLE_COOLDOWN:
                pass
            elif rec.get("lifecycle") == LIFECYCLE_NEW:
                if not is_unpresented_new(rec):
                    set_lifecycle(rec, LIFECYCLE_STILL, reason="still_clanless_after_presentation", at=now)
            else:
                set_lifecycle(rec, LIFECYCLE_STILL, reason="reverified_clanless", at=now)

        leaver_store["players"][tag] = rec

    elapsed = max(0.001, time.monotonic() - started)
    fetched = max(0, len(checkable) - cached_before)
    print(
        f"  Candidate reverification finished in {elapsed:.1f}s | "
        f"{fetched:,} API lookup(s) | {cached_before:,} cache hit(s) | {len(fetch_errors):,} error(s)"
    )


def archive_old_records(leaver_store, active_days):
    cutoff = utc_now() - timedelta(days=active_days)
    for rec in leaver_store["players"].values():
        detected = parse_iso(rec.get("lastDepartureDetectedAt") or rec.get("detectedAt"))
        if not detected or detected >= cutoff:
            continue
        if rec.get("lifecycle") == LIFECYCLE_JOINED_MY:
            # Current conversions remain visible. sync_my_clan_membership()
            # verifies this state against your live clan roster each run.
            continue
        if rec.get("lifecycle") != LIFECYCLE_ARCHIVED:
            rec["archivedFrom"] = rec.get("lifecycle")
            set_lifecycle(rec, LIFECYCLE_ARCHIVED, reason="outside_active_window")


def candidate_row(rec, now=None):
    now = now or utc_now()
    detected = rec.get("lastDepartureDetectedAt") or rec.get("detectedAt")
    first_clanless = rec.get("firstClanlessVerifiedAt")
    window = rec.get("observationWindowSeconds")
    return {
        "name": rec.get("name", "Unknown"),
        "tag": normalize_tag(rec.get("tag")),
        "townHallLevel": safe_int(rec.get("townHallLevel")),
        "expLevel": safe_int(rec.get("expLevel")),
        "trophies": safe_int(rec.get("trophies")),
        "bestTrophies": safe_int(rec.get("bestTrophies")),
        "warStars": safe_int(rec.get("warStars")),
        "attackWins": safe_int(rec.get("attackWins")),
        "leagueName": rec.get("leagueName", ""),
        "leagueTierName": rec.get("leagueTierName", "Unranked"),
        "leagueTierId": safe_int(rec.get("leagueTierId")),
        "leagueTierScore": league_score_from_record(rec),
        "lifecycle": rec.get("lifecycle", ""),
        "freshness": freshness_label(detected, now=now),
        "detectedAgo": age_text(detected, now=now),
        "leftWithin": human_duration(window),
        "observationWindowSeconds": window,
        "previousRosterAt": rec.get("previousRosterAt", ""),
        "detectedAt": detected or "",
        "firstClanlessVerifiedAt": first_clanless or "",
        "lastClanlessVerifiedAt": rec.get("lastClanlessVerifiedAt", ""),
        "lastVerifiedAt": rec.get("lastVerifiedAt", ""),
        "sourceClan": rec.get("sourceClanName", ""),
        "sourceClanTag": rec.get("sourceClanTag", ""),
        "currentClan": rec.get("currentClanName", ""),
        "currentClanTag": rec.get("currentClanTag", ""),
        "joinedMyClanAt": rec.get("joinedMyClanAt", ""),
        "lastJoinedMyClanVerifiedAt": rec.get("lastJoinedMyClanVerifiedAt", ""),
        "everJoinedMyClan": bool(rec.get("joinedMyClanAt")),
        "departureCount": safe_int(rec.get("departureCount")),
        "profileLink": rec.get("profileLink") or profile_link(rec.get("tag")),
        "lastStatusChangedAt": rec.get("lastStatusChangedAt", ""),
        "_detectedDt": parse_iso(detected) or datetime.min.replace(tzinfo=timezone.utc),
        "_window": window if window is not None else 10**18,
        "_unpresentedNew": is_unpresented_new(rec),
    }


def build_result_groups(leaver_store, filters, active_days, history_display_days, target, current_run_id=None):
    now = utc_now()
    active_cutoff = now - timedelta(days=active_days)
    history_cutoff = now - timedelta(days=history_display_days)
    new_rows = []
    still_rows = []
    joined_my = []
    no_longer = []

    for rec in leaver_store["players"].values():
        row = candidate_row(rec, now=now)
        detected = row["_detectedDt"]
        lifecycle = row["lifecycle"]

        # Card age is the departure detection, not a daily verification or
        # status change. Keep older records in the archive, off the card list.
        if detected < active_cutoff:
            continue

        if detected >= active_cutoff and lifecycle in (LIFECYCLE_NEW, LIFECYCLE_STILL) and meets_filters(rec, filters):
            # "NEW THIS SCAN" is literal: only departures detected by this
            # current run belong there. An older candidate that was not shown
            # because of the result cap can still surface later under STILL
            # AVAILABLE without being mislabeled as a new detection.
            if (
                row["_unpresentedNew"]
                and current_run_id
                and rec.get("lastDetectedRunId") == current_run_id
            ):
                new_rows.append(row)
            else:
                still_rows.append(row)
            continue

        if lifecycle == LIFECYCLE_JOINED_MY:
            joined_my.append(row)
            continue

        changed = parse_iso(row.get("lastStatusChangedAt")) or detected
        if changed >= history_cutoff and lifecycle in (
            LIFECYCLE_JOINED_OTHER,
            LIFECYCLE_COOLDOWN,
            LIFECYCLE_FILTERED,
            LIFECYCLE_VERIFY_ERROR,
            LIFECYCLE_ARCHIVED,
        ):
            no_longer.append(row)

    def active_sort_key(r):
        return (-r["_detectedDt"].timestamp(), r["_window"], -r["townHallLevel"], -r["warStars"])

    new_rows.sort(key=active_sort_key)
    still_rows.sort(key=active_sort_key)
    joined_my.sort(
        key=lambda r: parse_iso(r.get("joinedMyClanAt")) or r["_detectedDt"],
        reverse=True,
    )
    no_longer.sort(
        key=lambda r: parse_iso(r.get("lastStatusChangedAt")) or r["_detectedDt"],
        reverse=True,
    )

    # The scan target never evicts yesterday's cards. All candidates from the
    # rolling active window remain in the report; invitations are tracked by
    # the shared leadership service and filtered in the dashboard.
    active_combined = new_rows + still_rows

    return {
        "new": new_rows,
        "still": still_rows,
        "joined_my": joined_my,
        "no_longer": no_longer,
        "active_all_count": len(active_combined),
        "new_all_count": len(new_rows),
        "still_all_count": len(still_rows),
        "joined_my_all_count": len(joined_my),
    }


def mark_unpresented_rows_presented(leaver_store, rows):
    now = iso_now()
    for row in rows:
        rec = leaver_store["players"].get(row["tag"])
        if not rec or not is_unpresented_new(rec):
            continue
        dep = rec.get("lastDepartureDetectedAt")
        rec["lastPresentedAt"] = now
        rec["lastPresentedDepartureAt"] = dep
        add_event(rec, "presented_as_new_candidate", at=now, departureDetectedAt=dep)


# ---------------------------------------------------------------------------
# Metrics updates and exports
# ---------------------------------------------------------------------------

def update_clan_metrics(
    metrics_store,
    tracked_clans,
    previous,
    current,
    errors,
    per_clan_departures,
    qualifying_departures,
    extra_comparisons=None,
    extra_observed_slots=None,
):
    now = iso_now()
    previous_clans = previous.get("clans", {}) if isinstance(previous, dict) else {}
    extra_comparisons = extra_comparisons or {}
    extra_observed_slots = extra_observed_slots or {}
    qualifying_by_clan = {}
    for q in qualifying_departures:
        tag = normalize_tag(q.get("sourceClanTag"))
        if tag:
            qualifying_by_clan[tag] = qualifying_by_clan.get(tag, 0) + 1

    tracked_by_tag = {normalize_tag(c.get("tag")): c for c in tracked_clans}
    for tag, clan in tracked_by_tag.items():
        rec = metrics_store["clans"].get(tag, {})
        if not isinstance(rec, dict):
            rec = {}
        rec["tag"] = tag
        rec["name"] = clan.get("name", rec.get("name", "Unknown clan"))
        rec["bucket"] = clan.get("bucket", "rotating")
        rec.setdefault("firstTrackedAt", clan.get("addedAt") or now)
        rec["lastAttemptAt"] = now

        if tag in current:
            rec["successfulScans"] = safe_int(rec.get("successfulScans")) + 1
            rec["lastSuccessfulScanAt"] = current[tag].get("capturedAt")
            rec["lastMemberCount"] = len(current[tag].get("members", {}))
            rec["consecutiveErrors"] = 0
        elif tag in errors:
            rec["rosterErrors"] = safe_int(rec.get("rosterErrors")) + 1
            rec["consecutiveErrors"] = safe_int(rec.get("consecutiveErrors")) + 1
            rec["lastError"] = errors[tag]
            rec["lastErrorAt"] = now

        base_comparisons = 0
        observed_slots = 0
        if tag in current and tag in previous_clans and not clan.get("needsBaseline"):
            base_comparisons = 1
            observed_slots += len((previous_clans[tag].get("members") or {}))

        extra_count = safe_int(extra_comparisons.get(tag))
        if extra_count:
            observed_slots += safe_int(extra_observed_slots.get(tag))

        total_new_comparisons = base_comparisons + extra_count
        if total_new_comparisons:
            rec["comparableScans"] = safe_int(rec.get("comparableScans")) + total_new_comparisons
            rec["observedMemberSlots"] = safe_int(rec.get("observedMemberSlots")) + observed_slots
            deps = safe_int(per_clan_departures.get(tag))
            rec["departuresDetected"] = safe_int(rec.get("departuresDetected")) + deps
            if deps:
                rec["lastDepartureAt"] = current[tag].get("capturedAt") or now

        qcount = qualifying_by_clan.get(tag, 0)
        if qcount:
            rec["qualifyingClanlessDepartures"] = safe_int(rec.get("qualifyingClanlessDepartures")) + qcount
            rec["lastQualifyingDepartureAt"] = now

        rec["turnoverRatePercent"] = round(turnover_rate(rec), 4)
        rec["recruitingValue"] = recruiting_value(rec)
        metrics_store["clans"][tag] = rec

    metrics_store["updatedAt"] = now


def turnover_rows(metrics_store, tracked_clans):
    tracked_by_tag = {normalize_tag(c.get("tag")): c for c in tracked_clans}
    rows = []
    for tag, clan in tracked_by_tag.items():
        m = metric_for(metrics_store, tag)
        rows.append({
            "clanName": clan.get("name", m.get("name", "Unknown clan")),
            "clanTag": tag,
            "bucket": clan.get("bucket", m.get("bucket", "rotating")),
            "successfulScans": safe_int(m.get("successfulScans")),
            "comparableScans": safe_int(m.get("comparableScans")),
            "departuresDetected": safe_int(m.get("departuresDetected")),
            "qualifyingClanlessDepartures": safe_int(m.get("qualifyingClanlessDepartures")),
            "observedMemberSlots": safe_int(m.get("observedMemberSlots")),
            "turnoverRatePercent": round(turnover_rate(m), 2),
            "recruitingValue": recruiting_value(m),
            "lastDepartureAt": m.get("lastDepartureAt", ""),
        })
    value_rank = {"High": 2, "Medium": 1, "Low": 0}
    rows.sort(
        key=lambda r: (
            value_rank.get(r["recruitingValue"], 0),
            r["qualifyingClanlessDepartures"],
            r["departuresDetected"],
            r["turnoverRatePercent"],
        ),
        reverse=True,
    )
    return rows


def clean_row(row):
    return {k: v for k, v in row.items() if not k.startswith("_")}


def csv_safe(value):
    if isinstance(value, str) and value.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def save_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [clean_row(r) for r in rows]
    fields = [
        "name", "tag", "townHallLevel", "expLevel", "trophies", "bestTrophies",
        "warStars", "attackWins", "leagueName", "leagueTierName", "leagueTierId",
        "leagueTierScore", "lifecycle", "freshness", "detectedAgo",
        "leftWithin", "previousRosterAt", "detectedAt", "firstClanlessVerifiedAt",
        "lastClanlessVerifiedAt", "lastVerifiedAt", "sourceClan", "sourceClanTag",
        "currentClan", "currentClanTag", "joinedMyClanAt",
        "lastJoinedMyClanVerifiedAt", "everJoinedMyClan", "departureCount",
        "profileLink", "lastStatusChangedAt",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: csv_safe(v) for k,v in row.items()} for row in rows)


def save_history_csv(leaver_store, path):
    rows = [candidate_row(rec) for rec in leaver_store["players"].values()]
    rows.sort(key=lambda r: r["_detectedDt"], reverse=True)
    save_csv(rows, path)


def save_turnover_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "clanName", "clanTag", "bucket", "successfulScans", "comparableScans",
        "departuresDetected", "qualifyingClanlessDepartures", "observedMemberSlots",
        "turnoverRatePercent", "recruitingValue", "lastDepartureAt",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: csv_safe(v) for k,v in row.items()} for row in rows)


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

def local_time_span(iso_value, fallback="unknown"):
    if not iso_value:
        return html.escape(fallback)
    escaped = html.escape(str(iso_value), quote=True)
    return f'<span class="local-time" data-iso="{escaped}">{escaped}</span>'


def candidate_card(r, section):
    name = html.escape(str(r.get("name", "Unknown")))
    tag = html.escape(str(r.get("tag", "")))
    source = html.escape(str(r.get("sourceClan", "")))
    source_tag = html.escape(str(r.get("sourceClanTag", "")))
    lifecycle_labels = {'NEW':'New this scan', 'STILL_CLANLESS':'Still clanless',
                        'JOINED_MY_CLAN':'Joined War Haven', 'JOINED_OTHER_CLAN':'Joined another clan',
                        'BELOW_FILTERS':'Outside filters', 'ARCHIVED':'Archived',
                        'COOLDOWN_CLANLESS':'Duplicate cooldown', 'VERIFY_ERROR':'Needs verification'}
    lifecycle = html.escape(lifecycle_labels.get(str(r.get('lifecycle','')), str(r.get('lifecycle',''))))
    link = html.escape(str(r.get("profileLink", "")), quote=True)
    freshness = html.escape(str(r.get("freshness", "")))
    current_clan = html.escape(str(r.get("currentClan", "")))
    league_tier = html.escape(str(r.get("leagueTierName", "Unranked")))
    league_score = safe_int(r.get("leagueTierScore"))

    status_line = ""
    if section == "joined_my":
        status_line = (
            '<div class="joined-note">Currently in <strong>'
            + (current_clan or "your clan")
            + '</strong> · first detected there '
            + local_time_span(r.get("joinedMyClanAt"))
            + '.</div>'
        )
    elif section == "no_longer":
        if r.get("lifecycle") == LIFECYCLE_JOINED_OTHER:
            status_line = f'<div class="gone">Joined <strong>{current_clan or "another clan"}</strong>.</div>'
        elif r.get("lifecycle") == LIFECYCLE_COOLDOWN:
            status_line = '<div class="gone">Hidden by duplicate cooldown after a repeat departure.</div>'
        elif r.get("lifecycle") == LIFECYCLE_FILTERED:
            status_line = '<div class="gone">Does not meet the current recruiting filters.</div>'
        elif r.get("lifecycle") == LIFECYCLE_VERIFY_ERROR:
            status_line = '<div class="gone">Latest live verification failed; hidden for safety.</div>'
        else:
            status_line = '<div class="gone">Archived outside the active-candidate window.</div>'

    search_blob = html.escape(
        " ".join([
            str(r.get("name", "")), str(r.get("tag", "")), str(r.get("sourceClan", "")),
            str(r.get("sourceClanTag", "")), str(r.get("currentClan", "")),
            str(r.get("leagueTierName", "")), lifecycle,
        ]).lower(),
        quote=True,
    )

    return f"""
<article class="card candidate" data-section="{section}" data-th="{safe_int(r.get('townHallLevel'))}"
 data-war="{safe_int(r.get('warStars'))}" data-best="{safe_int(r.get('bestTrophies'))}"
 data-trophies="{safe_int(r.get('trophies'))}" data-xp="{safe_int(r.get('expLevel'))}"
 data-league="{league_score}" data-detected="{html.escape(str(r.get('detectedAt','')), quote=True)}"
 data-window="{safe_int(r.get('_window'), 10**18)}" data-search="{search_blob}">
  <div class="row">
    <div class="identity">
      <h3>{name}</h3>
      <div class="tag">{tag}</div>
    </div>
    <div class="th">TH{safe_int(r.get('townHallLevel'))}</div>
  </div>

  <div class="badges">
    <span class="badge">{freshness}</span>
    <span class="badge secondary">{lifecycle}</span>
    <span class="badge secondary">{league_tier}</span>
  </div>

  <div class="stats">
    <div><strong>{safe_int(r.get('warStars')):,}</strong><span>War stars</span></div>
    <div><strong>{safe_int(r.get('bestTrophies')):,}</strong><span>Best trophies</span></div>
    <div><strong>{safe_int(r.get('trophies')):,}</strong><span>Current trophies</span></div>
    <div><strong>{safe_int(r.get('expLevel')):,}</strong><span>XP</span></div>
  </div>

  <details class="timing"><summary>Verification &amp; departure history</summary>
    <div><strong>Last seen in clan:</strong> {local_time_span(r.get('previousRosterAt'))}</div>
    <div><strong>Departure detected:</strong> {local_time_span(r.get('detectedAt'))} ({html.escape(str(r.get('detectedAgo','')))})</div>
    <div><strong>Leave window:</strong> &le; {html.escape(str(r.get('leftWithin','unknown')))}</div>
    <div><strong>First verified clanless:</strong> {local_time_span(r.get('firstClanlessVerifiedAt'))}</div>
    <div><strong>Last live verification:</strong> {local_time_span(r.get('lastVerifiedAt'))}</div>
  </details>

  <div class="source">Former tracked clan: <strong>{source}</strong> {source_tag}</div>
  {status_line}
  <a class="open" href="{link}">Open in Clash</a>
</article>
"""


def save_html(groups, turnover, path, run_stats, filters, tracked_clans, my_clan_tag, my_clan_name):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    new_cards = "".join(candidate_card(r, "new") for r in groups["new"])
    still_cards = "".join(candidate_card(r, "still") for r in groups["still"])
    joined_cards = "".join(candidate_card(r, "joined_my") for r in groups["joined_my"])
    gone_cards = "".join(candidate_card(r, "no_longer") for r in groups["no_longer"])

    if not new_cards:
        new_cards = '<div class="empty">No brand-new qualifying candidates in this scan.</div>'
    if not still_cards:
        still_cards = '<div class="empty">No previously detected candidates are still available.</div>'
    if not joined_cards:
        joined_cards = '<div class="empty">No tracked recruiting candidates are currently in your clan.</div>'
    if not gone_cards:
        gone_cards = '<div class="empty">No recent candidate status changes to show.</div>'

    turnover_rows_html = []
    for r in turnover[:25]:
        turnover_rows_html.append(f"""
<tr>
  <td>{html.escape(str(r['clanName']))}<div class="mini">{html.escape(str(r['clanTag']))}</div></td>
  <td>{html.escape(str(r['bucket']).title())}</td>
  <td>{r['departuresDetected']:,}</td>
  <td>{r['qualifyingClanlessDepartures']:,}</td>
  <td>{r['turnoverRatePercent']:.2f}%</td>
  <td>{html.escape(str(r['recruitingValue']))}</td>
</tr>
""")

    core_count = sum(1 for c in tracked_clans if c.get("bucket") == "core")
    rotating_count = len(tracked_clans) - core_count
    league_options = []
    current_min_league = safe_int(filters.get("min_league_score"))
    for score in range(0, 37):
        label = "Any Ranked League" if score == 0 else league_tier_label(score)
        selected = " selected" if score == current_min_league else ""
        league_options.append(f'<option value="{score}"{selected}>{html.escape(label)}+</option>')
    league_options_html = "".join(league_options)

    baseline_note = '<div class="baseline">Cloud baseline saved. Later scans can detect new departures by comparing these rosters. Only candidates verified as clanless are listed.</div>' if run_stats.get("baselineCreated") else ''

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>War Haven Recruiter</title>
<meta name="theme-color" content="#0d1524">
<style>
{RECRUITER_CSS}
</style>
</head>
<body>
<main class="wrap">
<header class="hero"><div class="hero-top"><div><div class="eyebrow">War Haven · Leadership workspace</div><h1>Recruiting</h1></div><div class="hero-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="9" cy="7" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M19 7v8m-4-4h8"/></svg></div></div><p class="sub">Find your next clanmate. Verified clanless players from clans listed in the U.S., with departure windows and recruiting history for <strong>{html.escape(my_clan_name or my_clan_tag)}</strong>.</p><div class="snapshot"><span>Daily cloud scan</span><span>TH{filters['min_th']}+ · target {run_stats.get('target',50)}</span><span>Invitations stay manual</span><span>Saved {local_time_span(run_stats.get('runFinishedAt'))}</span></div></header>
{baseline_note}

<div class="summary">
  <div class="box"><strong>{groups['new_all_count']:,}</strong><span>New qualifying candidates</span></div>
  <div class="box"><strong>{groups['still_all_count']:,}</strong><span>Still available</span></div>
  <div class="box"><strong>{groups['joined_my_all_count']:,}</strong><span>Currently in your clan</span></div>
  <div class="box"><strong>{run_stats.get('everJoinedMyClanCount',0):,}</strong><span>Ever joined your clan</span></div>
  <div class="box"><strong>{run_stats.get('possibleDepartures',0):,}</strong><span>Departures detected</span></div>
  <div class="box"><strong>{run_stats.get('successfulClanScans',0):,}</strong><span>Successful clan scans</span></div>
  <div class="box"><strong>{core_count:,}</strong><span>Core clans</span></div>
  <div class="box"><strong>{rotating_count:,}</strong><span>Rotating clans</span></div>
</div>

<div class="filter-panel"><div class="filter-title">Find a candidate</div><div class="controls">
  <label class="wide" for="search">Search<input id="search" placeholder="Player, tag, or former clan"></label>
  <label for="sectionFilter">Status<select id="sectionFilter">
    <option value="all">All statuses</option>
    <option value="new">New this scan</option>
    <option value="still">Still available</option>
    <option value="joined_my">Joined your clan</option>
    <option value="no_longer">No longer available</option>
  </select></label>
  <label for="minTH">Minimum Town Hall<input id="minTH" type="number" min="1" value="{filters['min_th']}"></label>
  <label for="minWar">Minimum war stars<input id="minWar" type="number" min="0" value="{filters['min_war_stars']}"></label>
  <label for="minLeague">Minimum league<select id="minLeague">{league_options_html}</select></label>
  <label for="sortBy">Sort by<select id="sortBy">
    <option value="newest">Newest</option>
    <option value="window">Tightest leave window</option>
    <option value="th">Highest TH</option>
    <option value="war">Most war stars</option>
    <option value="best">Best trophies</option>
  </select></label>
</div></div>

<section data-section-wrap="new">
  <div class="section-head"><h2>New this scan</h2><span class="count">{len(groups['new']):,} shown</span></div>
  <div class="cards">{new_cards}</div>
</section>

<section data-section-wrap="still">
  <div class="section-head"><h2>Still available</h2><span class="count">{len(groups['still']):,} shown</span></div>
  <div class="cards">{still_cards}</div>
</section>

<section data-section-wrap="joined_my">
  <div class="section-head"><h2>Joined War Haven</h2><span class="count">{len(groups['joined_my']):,} current tracked member(s)</span></div>
  <div class="cards">{joined_cards}</div>
</section>

<section data-section-wrap="no_longer">
  <div class="section-head"><h2>No longer available</h2><span class="count">{len(groups['no_longer']):,} recent status changes</span></div>
  <div class="cards">{gone_cards}</div>
</section>

<h2 class="turnover-heading">Clan turnover</h2>
<div class="table-wrap">
<table>
<thead><tr><th>Clan</th><th>Pool</th><th>Leavers</th><th>Qualifying</th><th>Turnover</th><th>Value</th></tr></thead>
<tbody>{''.join(turnover_rows_html)}</tbody>
</table>
</div>

<div class="note">
Availability is verified at the saved scan time. A player may have joined a clan since then; check their profile before inviting. The U.S. clan listing does not confirm a player’s residence or language.<br><br>Your-clan conversion tracking uses the roster for {html.escape(my_clan_name or my_clan_tag)} {html.escape(my_clan_tag)} each run. If that lookup fails, prior conversion states are preserved rather than guessing that anyone left.
<br><br>Filters used by the script: TH{filters['min_th']}+ · {filters['min_war_stars']}+ war stars · {filters['min_best_trophies']}+ best trophies · {filters['min_current_trophies']}+ current trophies · XP {filters['min_exp_level']}+ · Ranked League {html.escape(filters.get('min_league_label','Any / Unranked'))}+.
"Leave window" means the player was present at the previous successful roster scan and absent at the later successful scan; it is not an exact leave timestamp. "First verified clanless" is the first live profile check for this detected departure and does not prove the player never briefly joined another clan between checks.
</div>
</main>
<script>
function fmtLocal(el) {{
  const raw = el.dataset.iso;
  const d = new Date(raw);
  if (!isNaN(d)) el.textContent = d.toLocaleString();
}}
document.querySelectorAll('.local-time').forEach(fmtLocal);

const search = document.getElementById('search');
const sectionFilter = document.getElementById('sectionFilter');
const minTH = document.getElementById('minTH');
const minWar = document.getElementById('minWar');
const minLeague = document.getElementById('minLeague');
const sortBy = document.getElementById('sortBy');

function applyFilters() {{
  const q = search.value.trim().toLowerCase();
  const sec = sectionFilter.value;
  const th = Number(minTH.value || 0);
  const war = Number(minWar.value || 0);
  const league = Number(minLeague.value || 0);
  document.querySelectorAll('.candidate').forEach(card => {{
    const show = (!q || card.dataset.search.includes(q)) &&
      (sec === 'all' || card.dataset.section === sec) &&
      Number(card.dataset.th) >= th && Number(card.dataset.war) >= war &&
      Number(card.dataset.league || 0) >= league;
    card.classList.toggle('hidden', !show);
  }});
  document.querySelectorAll('[data-section-wrap]').forEach(section => {{
    const wanted = sec === 'all' || section.dataset.sectionWrap === sec;
    section.classList.toggle('hidden', !wanted);
    const visible = section.querySelectorAll('.candidate:not(.hidden)').length;
    section.querySelector('.count').textContent = visible + ' shown';
  }});
  sortCards();
}}

function sortCards() {{
  const mode = sortBy.value;
  document.querySelectorAll('.cards').forEach(container => {{
    const cards = Array.from(container.querySelectorAll('.candidate'));
    cards.sort((a,b) => {{
      if (mode === 'window') return Number(a.dataset.window) - Number(b.dataset.window);
      if (mode === 'th') return Number(b.dataset.th) - Number(a.dataset.th);
      if (mode === 'war') return Number(b.dataset.war) - Number(a.dataset.war);
      if (mode === 'best') return Number(b.dataset.best) - Number(a.dataset.best);
      return new Date(b.dataset.detected) - new Date(a.dataset.detected);
    }});
    cards.forEach(c => container.appendChild(c));
  }});
}}

[search, sectionFilter, minTH, minWar, minLeague, sortBy].forEach(el => el.addEventListener('input', applyFilters));
applyFilters();
</script>
</body>
</html>"""

    path.write_text(document, encoding="utf-8")
    native = {'version': 1, 'updatedAt': run_stats.get('runFinishedAt'),
              'groups': {key: [clean_row(row) for row in groups[key]] for key in ('new', 'still', 'joined_my', 'no_longer')},
              'turnover': turnover, 'stats': run_stats, 'filters': filters}
    path.with_suffix('.json').write_text(json.dumps(native, ensure_ascii=False), encoding='utf-8')


# ---------------------------------------------------------------------------
# Command-line options and main
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="Clash_Recruitment.py",
        description="Track U.S. clan rosters and find newly clanless recruiting candidates."
    )
    p.add_argument("--my-clan-tag", default=DEFAULT_MY_CLAN_TAG,
                   help="Your clan tag. Known candidates found in this clan get JOINED_MY_CLAN status.")
    p.add_argument("--min-th", type=int, default=DEFAULT_MIN_TH)
    p.add_argument("--min-war-stars", type=int, default=DEFAULT_MIN_WAR_STARS)
    p.add_argument("--min-best-trophies", type=int, default=DEFAULT_MIN_BEST_TROPHIES)
    p.add_argument("--min-current-trophies", type=int, default=DEFAULT_MIN_CURRENT_TROPHIES)
    p.add_argument("--min-exp-level", type=int, default=DEFAULT_MIN_EXP_LEVEL)
    p.add_argument("--min-league", default=DEFAULT_MIN_LEAGUE,
                   help="Minimum current Ranked League. Examples: ANY, Valkyrie 14, Titan, Titan 25, Electro 33, Legend III.")
    p.add_argument("--target", type=int, default=DEFAULT_TARGET)
    p.add_argument("--max-clans", type=int, default=DEFAULT_MAX_CLANS)
    p.add_argument("--min-clan-members", type=int, default=DEFAULT_MIN_CLAN_MEMBERS)
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                   help="Parallel clan-roster workers (max 20).")
    p.add_argument("--profile-workers", type=int, default=DEFAULT_PROFILE_WORKERS,
                   help="Parallel player-profile workers for departures/candidate reverification (max 20).")
    p.add_argument("--active-days", type=int, default=DEFAULT_ACTIVE_DAYS)
    p.add_argument("--history-display-days", type=int, default=DEFAULT_HISTORY_DISPLAY_DAYS)
    p.add_argument("--duplicate-cooldown-days", type=int, default=DEFAULT_DUPLICATE_COOLDOWN_DAYS)
    p.add_argument("--rotation-days", type=int, default=DEFAULT_ROTATION_DAYS,
                   help="Days between automatic rotating-clan replacement. 0 disables rotation.")
    p.add_argument("--rotation-count", type=int, default=DEFAULT_ROTATION_COUNT,
                   help="Maximum low-value rotating clans to replace per rotation. 0 disables replacement.")
    p.add_argument("--core-fraction", type=float, default=DEFAULT_CORE_FRACTION,
                   help="Fraction of tracked clans kept in the core pool (0.05 to 0.95).")
    p.add_argument("--hot-rescan", type=int, default=DEFAULT_HOT_RESCAN_COUNT,
                   help="Second-scan up to this many high-turnover clans each run. 0 disables.")
    p.add_argument("--checkpoint-max-age-hours", type=int, default=DEFAULT_CHECKPOINT_MAX_AGE_HOURS)
    p.add_argument("--refresh-clans", action="store_true",
                   help="Replace the entire tracked clan set. New clans begin baseline-only.")
    p.add_argument("--reset-baseline", action="store_true",
                   help="Delete previous roster baseline and create a fresh baseline this run.")
    p.add_argument("--output", default=str(DEFAULT_CSV))
    p.add_argument("--history-output", default=str(DEFAULT_HISTORY_CSV))
    p.add_argument("--turnover-output", default=str(DEFAULT_TURNOVER_CSV))
    p.add_argument("--html-output", default=str(DEFAULT_HTML))
    return p


def validate_args(args):
    args.my_clan_tag = normalize_tag(args.my_clan_tag)
    if not args.my_clan_tag or len(args.my_clan_tag) < 4:
        raise SystemExit("--my-clan-tag must be a valid Clash clan tag.")

    try:
        args.min_league_score, args.min_league_label = parse_league_requirement(args.min_league)
    except ValueError as exc:
        raise SystemExit(f"--min-league: {exc}")

    positive = {
        "min-th": args.min_th,
        "target": args.target,
        "max-clans": args.max_clans,
        "min-clan-members": args.min_clan_members,
        "workers": args.workers,
        "profile-workers": args.profile_workers,
        "active-days": args.active_days,
        "history-display-days": args.history_display_days,
        "duplicate-cooldown-days": args.duplicate_cooldown_days,
        "checkpoint-max-age-hours": args.checkpoint_max_age_hours,
    }
    for name, value in positive.items():
        if value < 1:
            raise SystemExit(f"--{name} must be at least 1.")

    nonnegative = {
        "min-war-stars": args.min_war_stars,
        "min-best-trophies": args.min_best_trophies,
        "min-current-trophies": args.min_current_trophies,
        "min-exp-level": args.min_exp_level,
        "rotation-days": args.rotation_days,
        "rotation-count": args.rotation_count,
        "hot-rescan": args.hot_rescan,
    }
    for name, value in nonnegative.items():
        if value < 0:
            raise SystemExit(f"--{name} cannot be negative.")

    if not 0.05 <= args.core_fraction <= 0.95:
        raise SystemExit("--core-fraction must be between 0.05 and 0.95.")


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate_args(args)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    run_started_at = iso_now()

    filters = {
        "min_th": args.min_th,
        "min_war_stars": args.min_war_stars,
        "min_best_trophies": args.min_best_trophies,
        "min_current_trophies": args.min_current_trophies,
        "min_exp_level": args.min_exp_level,
        "min_league_score": args.min_league_score,
        "min_league_label": args.min_league_label,
    }

    print(f"\nClash Recruitment {VERSION} — LIVE RECRUITING DASHBOARD")
    print("=" * 72)
    print("Data source               : Supercell official API only")
    print(f"Your clan tag             : {args.my_clan_tag}")
    print(f"Minimum Town Hall         : {args.min_th}")
    print(f"Minimum war stars         : {args.min_war_stars}")
    print(f"Minimum best trophies     : {args.min_best_trophies}")
    print(f"Minimum current trophies  : {args.min_current_trophies}")
    print(f"Minimum XP                : {args.min_exp_level}")
    print(f"Minimum Ranked League     : {args.min_league_label}")
    print(f"Target active results     : {args.target}")
    print(f"Tracked U.S. clans        : up to {args.max_clans:,}")
    print(f"Core / rotating split     : {args.core_fraction:.0%} / {1-args.core_fraction:.0%}")
    print(f"Rotation                  : every {args.rotation_days} day(s), up to {args.rotation_count}")
    print(f"Duplicate cooldown        : {args.duplicate_cooldown_days} days")
    print(f"Hot-clan second scan      : up to {args.hot_rescan}")
    print(f"Player profile workers    : up to {min(args.profile_workers, 20)}")
    print("=" * 72)

    tokens = get_tokens()
    print(f"Configured API keys       : {len(tokens)}")
    api = OfficialAPI(tokens)

    try:
        us = get_us_location(api)
    except Exception as exc:
        log_error(f"Could not initialize U.S. search: {exc}")
        raise SystemExit(f"\nCould not initialize the U.S. search: {exc}")

    print(f"\nUnited States location ID: {us.get('id')}")
    print(f"Working API key           : {api.active_key_number} of {api.key_count}")

    if args.reset_baseline:
        if ROSTERS_FILE.exists():
            ROSTERS_FILE.unlink()
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
        print("Previous roster baseline and incomplete scan checkpoint deleted.")

    metrics_store = get_metrics_store()

    try:
        tracked_state, rotation_info = load_or_create_tracked_clans(
            api=api,
            us=us,
            max_clans=args.max_clans,
            min_members=args.min_clan_members,
            metrics_store=metrics_store,
            core_fraction=args.core_fraction,
            rotation_days=args.rotation_days,
            rotation_count=args.rotation_count,
            force_refresh=args.refresh_clans,
        )
    except Exception as exc:
        log_error(f"Could not establish tracked clans: {exc}")
        raise SystemExit(f"Could not establish tracked U.S. clans: {exc}")

    tracked_clans = tracked_state["clans"]
    previous = json_load(ROSTERS_FILE, {})
    has_previous = bool(isinstance(previous, dict) and previous.get("clans"))
    previous_last_run_at = previous.get("lastRunAt") if isinstance(previous, dict) else None

    current, errors, scan_id, scan_started_at, resumed_complete = fetch_all_rosters(
        api,
        tracked_clans,
        workers=args.workers,
        previous_last_run_at=previous_last_run_at,
        checkpoint_max_age_hours=args.checkpoint_max_age_hours,
    )

    if not current:
        raise SystemExit(
            "\nNo clan rosters were fetched successfully, so the previous baseline "
            "was NOT changed."
        )

    baseline_created = not has_previous
    needs_baseline_tags = {
        normalize_tag(c.get("tag")) for c in tracked_clans if c.get("needsBaseline")
    }

    departures = []
    comparable_clans = 0
    per_clan_departures = {}

    if has_previous:
        departures, comparable_clans, per_clan_departures = compare_rosters(
            previous, current, skip_tags=needs_baseline_tags
        )
        print("\nRoster comparison")
        print("-" * 72)
        print(f"Comparable clans          : {comparable_clans:,}")
        print(f"Baseline-only new clans   : {len(needs_baseline_tags):,}")
        print(f"Possible departures       : {len(departures):,}")
    else:
        print("\nFIRST RUN/RESET: creating a live roster baseline.")
        print("Fresh departures can be detected beginning with the next successful scan.")

    # High-turnover clans get a second scan during the run. This can tighten the
    # observation window and catch a departure that occurs while the full scan
    # is still running. Failed second scans never replace successful first scans.
    hot_clans = select_hot_clans(tracked_clans, metrics_store, args.hot_rescan)
    hot_extra_comparisons = {}
    hot_extra_observed_slots = {}
    if hot_clans:
        current, hot_departures, hot_per_clan, hot_comparable, hot_observed_slots = hot_rescan(
            api, hot_clans, current, workers=args.workers
        )
        hot_extra_comparisons = {tag: 1 for tag in hot_per_clan}
        hot_extra_observed_slots = hot_observed_slots
        departures = dedupe_departures(departures + hot_departures)
        for tag, count in hot_per_clan.items():
            per_clan_departures[tag] = safe_int(per_clan_departures.get(tag)) + safe_int(count)
        comparable_clans += hot_comparable
        if hot_departures:
            print(f"  Additional hot-scan departures: {len(hot_departures):,}")

    leaver_store = get_leaver_store(args.my_clan_tag)
    profile_cache = {}
    qualifying_departures = []

    if has_previous and departures:
        profile_cache, qualifying_departures, _ = process_departures(
            api=api,
            departures=departures,
            leaver_store=leaver_store,
            filters=filters,
            cooldown_days=args.duplicate_cooldown_days,
            run_id=run_id,
            my_clan_tag=args.my_clan_tag,
            profile_workers=args.profile_workers,
        )

    reverify_active_candidates(
        api=api,
        leaver_store=leaver_store,
        filters=filters,
        active_days=args.active_days,
        profile_cache=profile_cache,
        my_clan_tag=args.my_clan_tag,
        profile_workers=args.profile_workers,
    )

    my_clan_status = sync_my_clan_membership(
        api=api,
        leaver_store=leaver_store,
        my_clan_tag=args.my_clan_tag,
        profile_cache=profile_cache,
    )
    archive_old_records(leaver_store, active_days=args.active_days)

    # Metrics use the pre-merge previous baseline and current successful rosters.
    update_clan_metrics(
        metrics_store=metrics_store,
        tracked_clans=tracked_clans,
        previous=previous,
        current=current,
        errors=errors,
        per_clan_departures=per_clan_departures,
        qualifying_departures=qualifying_departures,
        extra_comparisons=hot_extra_comparisons,
        extra_observed_slots=hot_extra_observed_slots,
    )

    # Now that metrics are current, promote the best clans to the core pool.
    reclassify_clan_buckets(tracked_state, metrics_store, args.core_fraction)

    # A newly added clan stops being baseline-only only after its first successful
    # roster was actually captured.
    successful_tags = set(current)
    for c in tracked_state["clans"]:
        tag = normalize_tag(c.get("tag"))
        if tag in successful_tags:
            c["needsBaseline"] = False
            c["lastSeenAt"] = current[tag].get("capturedAt")
        m = metric_for(metrics_store, tag)
        if m:
            c["name"] = m.get("name") or c.get("name")

    # Build the next roster snapshot. Preserve old snapshots for currently
    # tracked clans whose request failed; never turn an API failure into a mass
    # departure. Remove snapshots for clans no longer in the active pool.
    tracked_tags = {normalize_tag(c.get("tag")) for c in tracked_state["clans"]}
    if has_previous:
        previous_clans = previous.get("clans", {}) if isinstance(previous, dict) else {}
        merged_clans = {
            tag: roster for tag, roster in previous_clans.items()
            if normalize_tag(tag) in tracked_tags
        }
    else:
        merged_clans = {}
    merged_clans.update(current)

    merged_snapshot = {
        "version": 2,
        "createdAt": previous.get("createdAt") if has_previous else iso_now(),
        "lastRunAt": iso_now(),
        "scanId": scan_id,
        "trackedClanCount": len(tracked_state["clans"]),
        "successfulClanCount": len(current),
        "clans": merged_clans,
    }

    groups = build_result_groups(
        leaver_store=leaver_store,
        filters=filters,
        active_days=args.active_days,
        history_display_days=args.history_display_days,
        target=args.target,
        current_run_id=run_id,
    )

    # Only unpresented departure events that are actually included in the
    # visible active result set count as presented for duplicate-cooldown
    # purposes. This includes overflow candidates first shown on a later run.
    active_rows = groups["new"] + groups["still"]
    mark_unpresented_rows_presented(leaver_store, active_rows)
    turnover = turnover_rows(metrics_store, tracked_state["clans"])

    captured_member_slots = sum(
        len((roster.get("members") or {})) for roster in current.values() if isinstance(roster, dict)
    )
    previous_clans_for_stats = previous.get("clans", {}) if isinstance(previous, dict) else {}
    compared_member_slots = 0
    for tag, roster in current.items():
        if normalize_tag(tag) not in needs_baseline_tags and tag in previous_clans_for_stats:
            compared_member_slots += len((previous_clans_for_stats[tag].get("members") or {}))
    compared_member_slots += sum(safe_int(v) for v in hot_extra_observed_slots.values())
    cooldown_hidden_count = sum(
        1 for rec in leaver_store["players"].values()
        if rec.get("lifecycle") == LIFECYCLE_COOLDOWN
    )

    run_stats = {
        "version": VERSION,
        "target": args.target,
        "runId": run_id,
        "runStartedAt": run_started_at,
        "runFinishedAt": iso_now(),
        "baselineCreated": baseline_created,
        "trackedClanCount": len(tracked_state["clans"]),
        "successfulClanScans": len(current),
        "capturedMemberSlots": captured_member_slots,
        "comparedMemberSlots": compared_member_slots,
        "rosterErrors": len(errors),
        "comparableClans": comparable_clans,
        "possibleDepartures": len(departures),
        "qualifyingNewDepartures": len(qualifying_departures),
        "newCandidatesShown": len(groups["new"]),
        "stillAvailableShown": len(groups["still"]),
        "joinedMyClanCurrent": groups["joined_my_all_count"],
        "everJoinedMyClanCount": sum(
            1 for rec in leaver_store["players"].values() if rec.get("joinedMyClanAt")
        ),
        "newCandidateJoinsThisRun": safe_int(my_clan_status.get("newCandidateJoins")),
        "myClanLookupOk": bool(my_clan_status.get("ok")),
        "myClanName": my_clan_status.get("clanName", ""),
        "myClanTag": args.my_clan_tag,
        "activeCandidateCountBeforeTarget": groups["active_all_count"],
        "cooldownDuplicatesHidden": cooldown_hidden_count,
        "trackedCandidateHistoryCount": len(leaver_store["players"]),
        "rotation": rotation_info,
        "hotClansRescanned": len(hot_clans),
        "checkpointResumedWithAllRosters": resumed_complete,
        "filters": filters,
    }

    # Commit all state atomically, then remove the now-completed checkpoint.
    save_generation([(ROSTERS_FILE, merged_snapshot), (LEAVERS_FILE, leaver_store), (CLAN_METRICS_FILE, metrics_store), (TRACKED_CLANS_FILE, tracked_state), (RUN_STATS_FILE, run_stats)])

    save_csv(active_rows, args.output)
    save_history_csv(leaver_store, args.history_output)
    save_turnover_csv(turnover, args.turnover_output)
    save_html(
        groups=groups,
        turnover=turnover,
        path=args.html_output,
        run_stats=run_stats,
        filters=filters,
        tracked_clans=tracked_state["clans"],
        my_clan_tag=args.my_clan_tag,
        my_clan_name=my_clan_status.get("clanName", ""),
    )

    try:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
    except Exception as exc:
        log_error(f"Could not remove completed checkpoint: {exc}")

    print("\n" + "=" * 72)
    print("FINISHED")
    print(f"Tracked U.S. clans         : {len(tracked_state['clans']):,}")
    print(f"Successful roster scans    : {len(current):,}")
    print(f"Member slots captured      : {captured_member_slots:,}")
    print(f"Member slots compared      : {compared_member_slots:,}")
    print(f"Roster errors              : {len(errors):,}")
    print(f"Comparable clan scans      : {comparable_clans:,}")
    print(f"Possible departures        : {len(departures):,}")
    print(f"New qualifying departures  : {len(qualifying_departures):,}")
    print(f"NEW candidates shown       : {len(groups['new']):,}")
    print(f"STILL available shown      : {len(groups['still']):,}")
    print(f"JOINED YOUR CLAN current   : {len(groups['joined_my']):,}")
    print(f"Ever joined your clan      : {run_stats['everJoinedMyClanCount']:,}")
    print(f"New joins detected this run: {run_stats['newCandidateJoinsThisRun']:,}")
    print(f"NO LONGER recent records   : {len(groups['no_longer']):,}")
    print(f"Cooldown duplicates hidden : {cooldown_hidden_count:,}")
    print(f"Candidate history records  : {len(leaver_store['players']):,}")
    print(f"CSV                         : {args.output}")
    print(f"History CSV                 : {args.history_output}")
    print(f"Clan turnover CSV           : {args.turnover_output}")
    print(f"Dashboard                   : {args.html_output}")
    print(f"Error log                   : {ERROR_LOG_FILE}")

    if errors:
        print(
            "\nSome clan requests failed. Their previous successful roster snapshots "
            "were preserved, so those failures were NOT treated as departures."
        )

    if baseline_created:
        print(
            "\nThis run created a baseline. Run the same script again later to detect "
            "actual roster departures."
        )
    else:
        print("\nOpen recruiting_candidates.html for the filterable recruiting dashboard.")

    api.close()


if __name__ == "__main__":
    main()

