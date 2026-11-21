import streamlit as st
import sqlite3
import requests
import json
import hashlib
import secrets
import urllib.parse
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components

DB = Path(__file__).with_name("highway_alerts.db")
API = "https://api.open-meteo.com/v1/forecast"

# Balochistan Highway Corridors with coordinates, elevation, and verified alternative routes
ROUTES_DATA = {
    "Quetta–Karachi (N-25)": {
        "code": "N-25",
        "distance": "688 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Sukkur → Karachi (N-5/M-9) [All-Weather Bypass]",
        "alt_reason": "Avoids Kalat/Surab snow & Khuzdar/Wadh flash-flood gorges via low-elevation Indus Highway.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Mastung", "lat": 29.7997, "lon": 66.8455, "elevation": "1,701m"},
            {"name": "Kalat", "lat": 29.0266, "lon": 66.5936, "elevation": "2,007m"},
            {"name": "Surab", "lat": 28.4914, "lon": 66.2585, "elevation": "1,750m"},
            {"name": "Khuzdar", "lat": 27.8000, "lon": 66.6167, "elevation": "1,237m"},
            {"name": "Wadh", "lat": 27.3436, "lon": 66.3708, "elevation": "1,220m"},
            {"name": "Lasbela", "lat": 26.2289, "lon": 66.3106, "elevation": "87m"},
            {"name": "Hub", "lat": 25.0244, "lon": 66.8906, "elevation": "24m"},
        ]
    },
    "Quetta–Zhob (N-50)": {
        "code": "N-50",
        "distance": "331 km",
        "alt_route": "Quetta → Ziarat Cross → Loralai (N-70) → Mekhtar → Zhob Link Road",
        "alt_reason": "Bypasses Khan Mehtarzai (2,224m) snow/blizzard pass via lower Loralai valley.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khan Mehtarzai", "lat": 30.4833, "lon": 67.6167, "elevation": "2,224m"},
            {"name": "Muslim Bagh", "lat": 30.8317, "lon": 67.7408, "elevation": "1,787m"},
            {"name": "Qilla Saifullah", "lat": 30.7000, "lon": 68.3600, "elevation": "1,550m"},
            {"name": "Zhob", "lat": 31.3411, "lon": 69.4481, "elevation": "1,426m"},
        ]
    },
    "Quetta–Sibi (N-65)": {
        "code": "N-65",
        "distance": "163 km",
        "alt_route": "Quetta → Harnai → Shahrag → Sibi (via Ziarat-Harnai Corridor)",
        "alt_reason": "Alternative detour when Kolpur/Bolan Pass experiences rockslides or flash flooding.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kolpur (Bolan Pass)", "lat": 29.9000, "lon": 67.1500, "elevation": "1,790m"},
            {"name": "Mach", "lat": 29.8637, "lon": 67.3302, "elevation": "1,006m"},
            {"name": "Dhadar", "lat": 29.4749, "lon": 67.6514, "elevation": "132m"},
            {"name": "Sibi", "lat": 29.5430, "lon": 67.8773, "elevation": "130m"},
        ]
    },
    "Quetta–Chaman (N-25 North)": {
        "code": "N-25N",
        "distance": "125 km",
        "alt_route": "Quetta → Kuchlak → Pishin → Gulistan → Boghra Pass → Chaman",
        "alt_reason": "Bypasses Khojak Pass (2,290m) during heavy snow or dense winter fog.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khojak Pass (Shelabagh)", "lat": 30.8050, "lon": 66.5680, "elevation": "2,290m"},
            {"name": "Chaman", "lat": 30.9177, "lon": 66.4526, "elevation": "1,338m"},
        ]
    },
    "Quetta–Nushki–Taftan (N-40)": {
        "code": "N-40",
        "distance": "610 km",
        "alt_route": "Quetta → Mastung → Khuzdar → Basima → Washuk → Dalbandin Link",
        "alt_reason": "Alternative southern detour if Lakpass tunnel or Nushki sandstorms block N-40.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Lakpass", "lat": 29.9650, "lon": 66.8200, "elevation": "1,810m"},
            {"name": "Nushki", "lat": 29.5522, "lon": 66.0215, "elevation": "1,020m"},
            {"name": "Dalbandin", "lat": 28.8885, "lon": 64.4062, "elevation": "843m"},
            {"name": "Nok Kundi", "lat": 28.8261, "lon": 62.7489, "elevation": "680m"},
            {"name": "Taftan", "lat": 28.9667, "lon": 61.5833, "elevation": "910m"},
        ]
    },
    "Quetta–Loralai–DG Khan (N-70)": {
        "code": "N-70",
        "distance": "425 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Kashmore → Rajanpur → DG Khan (N-55)",
        "alt_reason": "Safe lowland Indus Highway alternative during Fort Munro / Rakhni hill-torrent closures.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Ziarat Cross", "lat": 30.3824, "lon": 67.7256, "elevation": "2,450m"},
            {"name": "Sanjawi", "lat": 30.2856, "lon": 68.3489, "elevation": "1,620m"},
            {"name": "Loralai", "lat": 30.3705, "lon": 68.5979, "elevation": "1,430m"},
            {"name": "Rakhni", "lat": 30.0683, "lon": 69.9214, "elevation": "1,110m"},
        ]
    },
}

# Verified Roadside Emergency & Safe-Haven Facilities across Balochistan Corridors
NEARBY_FACILITIES = [
    {"route": "Quetta–Karachi (N-25)", "sector": "Quetta", "type": "Hospital / Trauma", "name": "Bolan Medical Complex (BMC) Trauma Center", "lat": 30.1845, "lon": 66.9680, "phone": "081-9213030", "notes": "24/7 Emergency & Ambulance"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Mastung", "type": "Safe Rest Area", "name": "Mastung NHA Toll Plaza & Safe Haven", "lat": 29.8050, "lon": 66.8500, "phone": "130 (NHA)", "notes": "Illuminated heavy-vehicle parking & Levies post"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Kalat", "type": "Hospital / Trauma", "name": "DHQ Hospital Kalat Emergency Wing", "lat": 29.0290, "lon": 66.5910, "phone": "0844-210222", "notes": "24/7 Trauma & Cold-Weather Medical Aid"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Surab", "type": "Petrol / Fuel", "name": "PSO Highway Fuel & Tire Station Surab", "lat": 28.4940, "lon": 66.2610, "phone": "0844-410115", "notes": "24/7 Diesel, Petrol & Heavy Truck Air"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Hospital / Trauma", "name": "Teaching Hospital Khuzdar Trauma Unit", "lat": 27.8040, "lon": 66.6120, "phone": "0848-412555", "notes": "Regional Trauma & Rescue 1122 Base"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Repair Workshop", "name": "Al-Baloch Heavy Truck & Engine Workshop", "lat": 27.7950, "lon": 66.6210, "phone": "0333-7891102", "notes": "24/7 Crane, Brake & Axle Recovery"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Lasbela", "type": "Safe Rest Area", "name": "Uthal Highway Rest Stop & Fuel Complex", "lat": 25.8070, "lon": 66.6210, "phone": "0853-610400", "notes": "Safe overnight parking, mosque & diner"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Khan Mehtarzai", "type": "Safe Rest Area", "name": "PDMA Snow Shelter & Levies Post", "lat": 30.4850, "lon": 67.6190, "phone": "1122 / PDMA", "notes": "Heated shelter, snow-clearing machinery"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Qilla Saifullah", "type": "Hospital / Trauma", "name": "DHQ Hospital Qilla Saifullah", "lat": 30.7040, "lon": 68.3580, "phone": "0823-610333", "notes": "24/7 Emergency Ward"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Zhob", "type": "Petrol / Fuel", "name": "Shell / Attock Highway Station Zhob", "lat": 31.3390, "lon": 69.4450, "phone": "0822-412890", "notes": "Fuel, mechanic & safe parking"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Kolpur (Bolan Pass)", "type": "Safe Rest Area", "name": "Kolpur Levies & NHA Checkpoint Safe Zone", "lat": 29.9030, "lon": 67.1520, "phone": "130 (NHA)", "notes": "Mandatory convoy hold area during rain"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Mach", "type": "Hospital / Trauma", "name": "Civil Hospital Mach & Rescue 1122 Post", "lat": 29.8650, "lon": 67.3320, "phone": "0832-210112", "notes": "Bolan Pass emergency medical response"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Sibi", "type": "Repair Workshop", "name": "Sibi Grand Trunk Heavy Auto Workshop", "lat": 29.5450, "lon": 67.8750, "phone": "0833-412770", "notes": "Radiator, AC & heavy truck recovery"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Khojak Pass (Shelabagh)", "type": "Safe Rest Area", "name": "Shelabagh Tunnel Safety & Recovery Post", "lat": 30.8070, "lon": 66.5660, "phone": "130 / Levies", "notes": "Snow chains & emergency towing"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Chaman", "type": "Hospital / Trauma", "name": "DHQ Hospital Chaman Emergency", "lat": 30.9190, "lon": 66.4540, "phone": "0826-613222", "notes": "24/7 Trauma & Ambulance"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Nushki", "type": "Hospital / Trauma", "name": "DHQ Hospital Nushki", "lat": 29.5550, "lon": 66.0240, "phone": "0825-871444", "notes": "24/7 Emergency & Heatstroke Unit"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Dalbandin", "type": "Petrol / Fuel", "name": "PSO RCD Highway Fuel & Rest Complex", "lat": 28.8900, "lon": 64.4090, "phone": "0825-210300", "notes": "Desert transit safe haven & water"},
    {"route": "Quetta–Loralai–DG Khan (N-70)", "sector": "Loralai", "type": "Hospital / Trauma", "name": "Teaching Hospital Loralai", "lat": 30.3720, "lon": 68.5990, "phone": "0824-660555", "notes": "24/7 Trauma & Surgical Unit"},
]

ROUTES = list(ROUTES_DATA.keys())
LANGUAGES = ["Urdu", "English", "Pashto", "Balochi"]
ROAD_STATUSES = ["Open (Verified)", "Restricted — Caution", "Closed — Emergency", "Clearance Pending"]
SOS_TYPES = ["Accident / Collision", "Vehicle Breakdown", "Medical Emergency", "Stranded in Weather / Flood"]

st.set_page_config(
    page_title="Balochistan Smart Highway Watch | Safety & Monitoring",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOGO_PATH = Path(__file__).with_name("logo.png")

@st.cache_data(show_spinner=False)
def get_logo_b64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return ""

def logo_svg(size=46):
    b64 = get_logo_b64()
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:{size}px;height:{size}px;object-fit:cover;border-radius:12px;'
            f'border:1px solid rgba(56,189,248,0.38);box-shadow:0 4px 14px rgba(0,0,0,0.45);" '
            f'alt="Highway Watch Logo"/>'
        )
    return ""

def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    if not stored_hash:
        return (False, False)
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$", 2)
        if len(parts) != 3:
            return (False, False)
        _, salt, expected_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return (secrets.compare_digest(dk.hex(), expected_hex), False)
    legacy_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if secrets.compare_digest(legacy_hex, stored_hash):
        return (True, True)
    return (False, False)

def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username))

def is_valid_pk_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    return bool(re.fullmatch(r"(\+92|0092|0)?3\d{9}", cleaned))

def is_valid_plate(plate: str) -> bool:
    cleaned = re.sub(r"\s+", "", plate.strip().upper())
    return bool(re.fullmatch(r"[A-Z]{2,5}-?\d{2,4}[A-Z]?", cleaned))

def connect():
    con = sqlite3.connect(DB, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT 'PDMA / NHA Operations',
            role TEXT DEFAULT 'Control Room Operator',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            vehicle_type TEXT DEFAULT 'Heavy Transport',
            route TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT DEFAULT 'Active on Route',
            current_sector TEXT DEFAULT 'Quetta',
            next_checkpoint TEXT DEFAULT 'Mastung',
            expected_eta TEXT,
            last_checkin TEXT,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            route TEXT NOT NULL,
            location TEXT NOT NULL,
            officer_incharge TEXT DEFAULT 'Duty Officer',
            qr_scans INTEGER DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS road_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            area TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_score INTEGER DEFAULT 2,
            authority_note TEXT NOT NULL,
            verified_by TEXT DEFAULT 'Control Room Quetta',
            updated_at TEXT NOT NULL,
            UNIQUE(route, area))""")
        con.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            route TEXT NOT NULL,
            language TEXT DEFAULT 'Urdu',
            severity TEXT DEFAULT 'Advisory',
            message TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sos_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sos_code TEXT UNIQUE,
            driver_id INTEGER,
            driver_name TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            phone TEXT NOT NULL,
            route TEXT NOT NULL,
            sector TEXT NOT NULL,
            lat REAL,
            lon REAL,
            emergency_type TEXT NOT NULL,
            source TEXT DEFAULT 'Driver SOS Button',
            details TEXT,
            status TEXT DEFAULT 'ACTIVE SOS',
            dispatched_unit TEXT DEFAULT 'Pending Dispatch',
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")

        existing_cols = {
            "drivers": [r[1] for r in con.execute("PRAGMA table_info(drivers)").fetchall()],
            "checkpoints": [r[1] for r in con.execute("PRAGMA table_info(checkpoints)").fetchall()],
            "road_status": [r[1] for r in con.execute("PRAGMA table_info(road_status)").fetchall()],
            "alerts": [r[1] for r in con.execute("PRAGMA table_info(alerts)").fetchall()],
        }
        migrations = [
            ("drivers", "driver_code", "TEXT"),
            ("drivers", "vehicle_type", "TEXT DEFAULT 'Heavy Transport'"),
            ("drivers", "status", "TEXT DEFAULT 'Active on Route'"),
            ("drivers", "current_sector", "TEXT DEFAULT 'Quetta'"),
            ("drivers", "next_checkpoint", "TEXT DEFAULT 'Mastung'"),
            ("drivers", "expected_eta", "TEXT"),
            ("drivers", "last_checkin", "TEXT"),
            ("checkpoints", "code", "TEXT"),
            ("checkpoints", "officer_incharge", "TEXT DEFAULT 'Duty Officer'"),
            ("checkpoints", "qr_scans", "INTEGER DEFAULT 0"),
            ("road_status", "risk_score", "INTEGER DEFAULT 2"),
            ("road_status", "verified_by", "TEXT DEFAULT 'Control Room Quetta'"),
            ("alerts", "language", "TEXT DEFAULT 'Urdu'"),
            ("alerts", "severity", "TEXT DEFAULT 'Advisory'"),
        ]
        for tbl, col, col_def in migrations:
            if col not in existing_cols[tbl]:
                con.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")

        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_road_route_area ON road_status(route, area)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_code ON drivers(driver_code)")

def rows(q, p=()):
    with connect() as con:
        return [dict(x) for x in con.execute(q, p).fetchall()]

def run(q, p=()):
    with connect() as con:
        cur = con.execute(q, p)
        con.commit()
        return cur.lastrowid

def seed():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    if not rows("SELECT id FROM users LIMIT 1"):
        run(
            "INSERT OR IGNORE INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
            ("Quetta Control Admin", "admin", "PDMA / NHA Balochistan", "Chief Command Officer", hash_password("admin123"), now_str)
        )
    if not rows("SELECT id FROM checkpoints LIMIT 1"):
        idx = 101
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                run(
                    "INSERT OR IGNORE INTO checkpoints(code,name,route,location,officer_incharge,qr_scans) VALUES(?,?,?,?,?,?)",
                    (f"CP-{idx}", f"{pt['name']} Highway Gate", route, pt["name"], "Levies / NHA Post", idx % 47 + 12)
                )
                idx += 1
    if not rows("SELECT id FROM road_status LIMIT 1"):
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                default_status = "Open (Verified)"
                default_risk = 2
                note = "Normal traffic flow; regular patrol active."
                if "Khan Mehtarzai" in pt["name"] or "Khojak" in pt["name"]:
                    default_status = "Restricted — Caution"
                    default_risk = 6
                    note = "High altitude pass; strong crosswinds & low night visibility."
                elif "Kolpur" in pt["name"]:
                    default_status = "Open (Verified)"
                    default_risk = 4
                    note = "Bolan sector clear; watch for slippery bends."
                run(
                    "INSERT OR IGNORE INTO road_status(route,area,status,risk_score,authority_note,verified_by,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (route, pt["name"], default_status, default_risk, note, "PDMA / NHA Control Room", now_str)
                )
    if not rows("SELECT id FROM drivers LIMIT 1"):
        future_eta = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        overdue_eta = (now - timedelta(minutes=38)).strftime("%Y-%m-%d %H:%M")
        sample_drivers = [
            ("BHW-2401", "Haji Abdul Wahid", "0300-8381920", "QTA-4821", "Cargo Truck", "Quetta–Karachi (N-25)", "Urdu", "Active on Route", "Mastung", "Kalat", future_eta, now_str),
            ("BHW-2402", "Sardar Khan Kakar", "0333-7812094", "ZHB-1190", "Passenger Coach", "Quetta–Zhob (N-50)", "Pashto", "Overdue — Welfare Check", "Khan Mehtarzai", "Muslim Bagh", overdue_eta, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")),
            ("BHW-2403", "Mirwais Baloch", "0321-8904412", "KZD-7734", "Oil Tanker", "Quetta–Nushki–Taftan (N-40)", "Balochi", "Verified at Gate", "Nushki", "Dalbandin", future_eta, now_str),
            ("BHW-2404", "Noor Muhammad", "0312-9045123", "SIB-3092", "Pickup / Utility", "Quetta–Sibi (N-65)", "Urdu", "Active on Route", "Kolpur (Bolan Pass)", "Mach", future_eta, now_str),
        ]
        for d in sample_drivers:
            run(
                """INSERT OR IGNORE INTO drivers
                (driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*d, now_str)
            )
    if not rows("SELECT id FROM sos_incidents LIMIT 1"):
        run(
            """INSERT OR IGNORE INTO sos_incidents
            (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("SOS-901", 2, "Sardar Khan Kakar", "ZHB-1190", "0333-7812094", "Quetta–Zhob (N-50)", "Khan Mehtarzai", 30.4833, 67.6167,
             "Stranded in Weather / Flood", "Auto Checkpoint Monitor", "Missed Muslim Bagh checkpoint ETA by 38 mins in sub-zero crosswinds.",
             "ACTIVE SOS", "Levies Mobile Unit #4", now_str)
        )

def generate_unique_driver_code() -> str:
    existing = {r["driver_code"] for r in rows("SELECT driver_code FROM drivers WHERE driver_code IS NOT NULL")}
    num = 2401 + len(rows("SELECT id FROM drivers"))
    while f"BHW-{num}" in existing:
        num += 1
    return f"BHW-{num}"

def generate_unique_sos_code() -> str:
    existing = {r["sos_code"] for r in rows("SELECT sos_code FROM sos_incidents WHERE sos_code IS NOT NULL")}
    num = 901 + len(rows("SELECT id FROM sos_incidents"))
    while f"SOS-{num}" in existing:
        num += 1
    return f"SOS-{num}"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m,wind_gusts_10m,surface_pressure",
        "hourly": "temperature_2m,precipitation_probability,precipitation,visibility,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": 7,
        "timezone": "Asia/Karachi"
    }
    response = requests.get(API, params=params, timeout=12)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "current" not in data:
        raise ValueError("Invalid weather payload received")
    return data

def safe_float(val, default=None):
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default

def weather_info(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1
    if code == 0:
        return ("Clear Sky", "صاف موسم", "☀️", 1)
    if code in (1, 2, 3):
        return ("Partly Cloudy", "ابر آلود", "⛅", 2)
    if code in (45, 48):
        return ("Dense Fog", "گہری دھند", "🌫️", 7)
    if code in (51, 53, 55, 56, 57):
        return ("Light Drizzle", "ہلکی بوندا باندی", "🌦️", 4)
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ("Heavy Rain", "بارش / پھسلن", "🌧️", 7)
    if code in (71, 73, 75, 77, 85, 86):
        return ("Snowfall / Ice", "برف باری", "❄️", 9)
    if code in (95, 96, 99):
        return ("Thunderstorm", "آندھی اور گرج چمک", "⛈️", 9)
    return ("Variable / Telemetry", "موسمی تبدیلی", "🌤️", 3)

def compute_risk_score(cur, road_status_str, manual_risk=None):
    if "Closed" in (road_status_str or ""):
        return 10
    score = 1
    if "Restricted" in (road_status_str or ""):
        score = max(score, 6)
    elif "Pending" in (road_status_str or ""):
        score = max(score, 4)
    if manual_risk is not None:
        try:
            score = max(score, int(manual_risk))
        except (TypeError, ValueError):
            pass
    if cur:
        code = cur.get("weather_code")
        if code is not None:
            _, _, _, w_risk = weather_info(code)
            score = max(score, w_risk)
        wind = safe_float(cur.get("wind_speed_10m"), 0.0)
        precip = safe_float(cur.get("precipitation"), 0.0)
        if wind > 35:
            score = max(score, 7)
        elif wind > 22:
            score = max(score, 5)
        if precip > 2.0:
            score = max(score, 8)
    return max(1, min(int(score), 10))

def journey_risk_tier(score: int) -> tuple[str, str, str]:
    if score <= 3:
        return ("LOW", "#10b981", "rgba(16,185,129,0.16)")
    if score <= 6:
        return ("MODERATE", "#f59e0b", "rgba(245,158,11,0.18)")
    if score <= 8:
        return ("HIGH", "#f97316", "rgba(249,115,22,0.22)")
    return ("SEVERE", "#ef4444", "rgba(239,68,68,0.24)")

def risk_meta(score):
    tier, color, bg = journey_risk_tier(score)
    return (f"{tier} RISK", color, bg)

def get_overdue_drivers(drivers_list):
    now = datetime.now()
    overdue = []
    for d in drivers_list:
        st_val = d.get("status") or ""
        if "Safe" in st_val or "Completed" in st_val:
            continue
        eta_str = d.get("expected_eta")
        is_flagged = "Overdue" in st_val or "SOS" in st_val
        mins_late = 0
        if eta_str:
            try:
                eta_dt = datetime.strptime(eta_str, "%Y-%m-%d %H:%M")
                if now > eta_dt:
                    is_flagged = True
                    mins_late = int((now - eta_dt).total_seconds() // 60)
            except ValueError:
                pass
        if is_flagged:
            d_copy = dict(d)
            d_copy["mins_late"] = max(mins_late, 15)
            overdue.append(d_copy)
    return overdue

def to_phonetic_tts_script(text: str, lang: str) -> tuple[str, str]:
    clean = text.replace("→", " سے ").replace("—", " ، ").replace("–", " ")
    clean = re.sub(r"\bN-(\d+)\b", r"این \1", clean)
    clean = re.sub(r"\bM-(\d+)\b", r"ایم \1", clean)
    clean = re.sub(r"[()\[\]•|/]+", " ، ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if lang == "English":
        en_clean = text.replace("→", " to ").replace("—", ", ").replace("–", " ")
        en_clean = re.sub(r"[()\[\]•|/]+", ", ", en_clean)
        en_clean = re.sub(r"\s+", " ", en_clean).strip()
        return en_clean, "en"
    if lang == "Urdu":
        return clean, "ur"
    elif lang == "Pashto":
        pashto_norm = (
            clean.replace("ښ", "ش")
            .replace("ږ", "ژ")
            .replace("څ", "تس")
            .replace("ځ", "دز")
            .replace("ډ", "ڈ")
            .replace("ړ", "ڑ")
            .replace("ڼ", "ن")
            .replace("ټ", "ٹ")
            .replace("ګ", "گ")
            .replace("ې", "ے")
            .replace("ۍ", "ئی")
            .replace("ۀ", "ہ")
        )
        return pashto_norm, "ur"
    else:
        balochi_norm = (
            clean.replace("ءِ", " ءِ ")
            .replace("ءَ", " ءَ ")
            .replace("ءُ", " اور ")
            .replace("گوں", " گون ")
            .replace("پچ انت", " پچ اَنت ")
            .replace("بند انت", " بند اَنت ")
            .replace("المی انت", " المی اَنت ")
        )
        return balochi_norm, "ur"

@st.cache_data(ttl=1800, show_spinner=False)
def synthesize_voice_mp3(text: str, lang: str) -> bytes | None:
    try:
        from gtts import gTTS
        import io
        spoken_text, tts_lang = to_phonetic_tts_script(text, lang)
        if lang == "English":
            buf = io.BytesIO()
            gTTS(text=spoken_text, lang="en", tld="co.uk", slow=False).write_to_fp(buf)
            return buf.getvalue()
        if lang == "Pashto":
            try:
                buf = io.BytesIO()
                gTTS(text=text, lang="ps", slow=False).write_to_fp(buf)
                return buf.getvalue()
            except Exception:
                pass
        buf = io.BytesIO()
        gTTS(text=spoken_text, lang=tts_lang, slow=False).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None

def localize_weather_term(weather_en: str, lang: str) -> str:
    mapping = {
        "Clear Sky": {"Urdu": "صاف موسم", "English": "Clear Sky", "Pashto": "ساحو او صفا هوا", "Balochi": "ساپ ءُ وشیں موسم"},
        "Partly Cloudy": {"Urdu": "جزوی ابر آلود", "English": "Partly Cloudy", "Pashto": "نیمه وریځ", "Balochi": "نيم جمبر"},
        "Dense Fog": {"Urdu": "گہری دھند", "English": "Dense Fog", "Pashto": "سخته لړه او غبار", "Balochi": "گورم ءُ دنز"},
        "Light Drizzle": {"Urdu": "ہلکی بوندا باندی", "English": "Light Drizzle", "Pashto": "نرم باران", "Balochi": "هورتیں هور"},
        "Heavy Rain": {"Urdu": "تیز بارش اور پھسلن", "English": "Heavy Rain & Flash Flood Risk", "Pashto": "تیز باران او ښویدنه", "Balochi": "تيزیں هور ءُ لگوشگ"},
        "Snowfall / Ice": {"Urdu": "برف باری اور کہرا", "English": "Heavy Snowfall & Black Ice", "Pashto": "واوره او یخ وهنه", "Balochi": "برپ ءُ يخبندی"},
        "Thunderstorm": {"Urdu": "آندھی اور گرج چمک", "English": "Severe Thunderstorm & Squalls", "Pashto": "توفان، تندر او تیز باد", "Balochi": "توپان ءُ گرند ءُ گروک"},
    }
    if weather_en in mapping and lang in mapping[weather_en]:
        return mapping[weather_en][lang]
    if lang == "English":
        return weather_en
    if lang == "Urdu":
        return "موسمی تبدیلی"
    if lang == "Pashto":
        return "د هوا بدلون"
    return "موسم ءِ بدلی"

def generate_multilingual_alert(area, route, weather_en, weather_ur, road, lang):
    w_local = localize_weather_term(weather_en, lang)
    alt_str = ROUTES_DATA[route]["alt_route"]
    if lang == "English":
        if "Closed" in road:
            return (
                f"EMERGENCY HIGHWAY ALERT ({route}): The road at {area} is CLOSED due to {w_local}. "
                f"Halt immediately at the nearest safe rest area or Levies checkpoint. Verified Alternative Route: {alt_str}.",
                f"Route Closed — Use Verified Detour: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"TRAVEL CAUTION ({route}): Restricted movement at {area} due to {w_local}. "
                f"Reduce speed, use fog lights, and stop at the nearest safe haven if visibility drops.",
                "Proceed with caution or pause at nearest safe rest area."
            )
        return (
            f"HIGHWAY ADVISORY ({route}): {area} corridor is OPEN with {w_local}. "
            f"Maintain safe speed limits and scan your QR pass at the next checkpoint.",
            "Corridor verified open — safe to proceed."
        )
    elif lang == "Urdu":
        if "Closed" in road:
            return (
                f"ہنگامی شاہراہ الرٹ: {route} پر {area} کے مقام پر سڑک {w_local} کے باعث بند کر دی گئی ہے۔ "
                f"قریبی محفوظ ریسٹ ایریا پر رک جائیں۔ متبادل محفوظ راستہ: {alt_str}۔",
                f"مقام بند ہے — متبادل راستہ اختیار کریں: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"سفری انتباہ: {route} کے {area} سیکٹر میں {w_local} کے باعث احتیاطی پابندی نافذ ہے۔ "
                f"رفتار کم رکھیں، فوگ لائٹس آن رکھیں اور ضرورت پڑنے پر قریبی محفوظ اسٹاپ پر رک جائیں۔",
                "پہاڑی دروں پر احتیاط کریں یا محفوظ ریسٹ ایریا پر قیام کریں۔"
            )
        return (
            f"موسمی اپ ڈیٹ: {route} پر {area} کے اطراف میں موسم {w_local} ہے اور شاہراہ کھلی ہے۔ "
            f"محفوظ ڈرائیونگ کے اصولوں پر عمل کریں اور چیک پوسٹ پر کیو آر کوڈ اسکین کروائیں۔",
            "سفر جاری رکھا جا سکتا ہے — رفتار کی حد کی پابندی کریں۔"
        )
    elif lang == "Pashto":
        if "Closed" in road:
            return (
                f"بیړنی خبرتیا: د {route} پر لویه لاره د {area} په سیمه کې د {w_local} له امله تړل شوې ده. "
                f"مهرباني وکړئ په نږدې خوندي تمځای کې ودریږئ. بدیله خوندي لاره: {alt_str}.",
                f"لاره تړلې ده — بدیله لاره وکاروئ: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"د احتیاط خبرتیا: د {route} پر لاره د {area} په سیمه کې د {w_local} له امله احتیاط اړین دی. "
                f"مهرباني وکړئ سرعت کم کړئ او د اړتیا په صورت کې په خوندي ځای کې تم شئ.",
                "په غرنیو لارو کې په پوره احتیاط سره موټر چلوئ."
            )
        return (
            f"د هوا او لارې تازه معلومات: د {route} پر لاره د {area} په سیمه کې هوا {w_local} ده او لویه لاره خلاصه ده. "
            f"ترافیکي قوانین مراعات کړئ او په پوسته کې کیو آر کوڈ سکین کړئ.",
            "لاره خلاصه ده — خپل سفر په خوندي توګه ترسره کړئ."
        )
    else:
        if "Closed" in road:
            return (
                f"هنگامی حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ راه {w_local} ءِ سوب ءَ بند کنگ بوتگ۔ "
                f"نزیکیں محفوظیں ریسٹ ایریا ءَ اوشت ات۔ دومی محفوظیں راه: {alt_str}۔",
                f"راه بند انت — دومی محفوظیں راه ءَ بہ رو ات: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"هوشیاری حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ {w_local} ءِ سوب ءَ هوشیاری المی انت۔ "
                f"گاڑی ءِ رفتار کم بہ کن ات ءُ نزیکیں محفوظیں جاہ ءَ اوشت ات۔",
                "کوهی راهانی سر ءَ گوں هوشیاری ءَ سفر بہ کن ات۔"
            )
        return (
            f"موسمی ءُ راه ءِ نوکیں حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ موسم {w_local} انت ءُ شاهراہ پچ انت۔ "
            f"سلامتی ءَ گوں سفر بہ کن ات ءُ چیک پوسٹ ءَ کیو آر کوڈ اسکین بہ کنائین ات۔",
            "شاهراہ پچ انت — ٹریفک ءِ رهبندانی پابندی ءَ بہ کن ات۔"
        )

def render_balochistan_map(selected_route, weather_cache, road_map, layers, sos_list=None, facilities_list=None):
    routes_payload = []
    for r_name, r_data in ROUTES_DATA.items():
        pts_out = []
        max_r = 1
        for pt in r_data["points"]:
            w_cur = weather_cache.get(pt["name"], {})
            r_row = road_map.get((r_name, pt["name"]), {})
            r_stat = r_row.get("status", "Open (Verified)")
            r_score = compute_risk_score(w_cur, r_stat, r_row.get("risk_score"))
            max_r = max(max_r, r_score)
            has_weather = bool(w_cur and ("temperature_2m" in w_cur or "weather_code" in w_cur))
            label_txt, _, _, _ = weather_info(w_cur.get("weather_code")) if has_weather else ("Cached / Telemetry", "", "🛰️", 2)
            temp_disp = f"{safe_float(w_cur.get('temperature_2m')):.1f}" if safe_float(w_cur.get("temperature_2m")) is not None else "—"
            wind_disp = f"{safe_float(w_cur.get('wind_speed_10m')):.1f}" if safe_float(w_cur.get("wind_speed_10m")) is not None else "—"
            precip_disp = f"{safe_float(w_cur.get('precipitation')):.1f}" if safe_float(w_cur.get("precipitation")) is not None else "—"
            tier_lbl, _, _ = journey_risk_tier(r_score)
            pts_out.append({
                "name": pt["name"],
                "lat": pt["lat"],
                "lon": pt["lon"],
                "elev": pt["elevation"],
                "temp": temp_disp,
                "wind": wind_disp,
                "precip": precip_disp,
                "weather": label_txt,
                "status": r_stat,
                "risk": r_score,
                "tier": tier_lbl
            })
        _, color_hex, _ = risk_meta(max_r)
        routes_payload.append({
            "name": r_name,
            "code": r_data["code"],
            "distance": r_data["distance"],
            "selected": (r_name == selected_route),
            "color": color_hex,
            "max_risk": max_r,
            "points": pts_out
        })

    sos_payload = []
    for s in (sos_list or []):
        if s.get("status") == "ACTIVE SOS" and s.get("lat") and s.get("lon"):
            sos_payload.append({
                "code": s.get("sos_code", "SOS"),
                "driver": s.get("driver_name", ""),
                "vehicle": s.get("vehicle", ""),
                "type": s.get("emergency_type", "Emergency"),
                "sector": s.get("sector", ""),
                "lat": float(s["lat"]),
                "lon": float(s["lon"]),
                "details": s.get("details", "")
            })

    fac_payload = []
    for fc in (facilities_list or []):
        if fc.get("route") == selected_route or layers.get("all_facilities"):
            fac_payload.append({
                "type": fc["type"],
                "name": fc["name"],
                "sector": fc["sector"],
                "phone": fc["phone"],
                "notes": fc["notes"],
                "lat": fc["lat"],
                "lon": fc["lon"]
            })

    payload_json = json.dumps(routes_payload).replace("</", "<\\/")
    sos_json = json.dumps(sos_payload).replace("</", "<\\/")
    fac_json = json.dumps(fac_payload).replace("</", "<\\/")
    layers_json = json.dumps(layers).replace("</", "<\\/")
    hud_route_safe = json.dumps(selected_route).replace("</", "<\\/")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        html, body, #map {{
          height: 100%; width: 100%; margin: 0; padding: 0;
          background: #060e1a; font-family: 'Inter', system-ui, sans-serif;
        }}
        .leaflet-container {{ background: #060e1a !important; }}
        .legend-bar {{
          position: absolute; top: 12px; left: 54px; z-index: 999;
          background: rgba(9, 20, 36, 0.92); backdrop-filter: blur(10px);
          border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px;
          padding: 7px 14px; color: #e2e8f0; font-size: 11px;
          display: flex; align-items: center; gap: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}
        .pill {{ padding: 2px 8px; border-radius: 5px; font-weight: 800; font-size: 10px; }}
        .map-hud {{
          position: absolute; bottom: 16px; left: 16px; z-index: 999;
          background: rgba(9, 20, 36, 0.93); backdrop-filter: blur(10px);
          border: 1px solid rgba(20, 184, 166, 0.35); border-radius: 12px;
          padding: 12px 16px; color: #f1f5f9; min-width: 250px; max-width: 360px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }}
        .hud-title {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #2dd4bf; font-weight: 700; }}
        .hud-route {{ font-size: 15px; font-weight: 800; margin: 3px 0 5px 0; }}
        .hud-meta {{ font-size: 11px; color: #94a3b8; line-height: 1.5; }}
        .custom-popup .leaflet-popup-content-wrapper {{
          background: #0b192c; color: #f1f5f9; border: 1px solid #1e3a5f; border-radius: 12px;
        }}
        .custom-popup .leaflet-popup-tip {{ background: #0b192c; }}
        @keyframes pulseSOS {{
          0% {{ transform: scale(0.95); opacity: 0.95; }}
          50% {{ transform: scale(1.25); opacity: 0.55; }}
          100% {{ transform: scale(0.95); opacity: 0.95; }}
        }}
        .sos-badge-icon {{
          background: #ef4444; color: #fff; font-weight: 900; font-size: 10px;
          border: 2px solid #fff; border-radius: 50%; width: 28px; height: 28px;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 0 16px #ef4444; animation: pulseSOS 1.3s infinite;
        }}
        .fac-badge-icon {{
          background: #0284c7; color: #fff; font-weight: 800; font-size: 11px;
          border: 1.5px solid #bae6fd; border-radius: 6px; width: 22px; height: 22px;
          display: flex; align-items: center; justify-content: center;
        }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <div class="legend-bar">
        <span style="font-weight:700;color:#94a3b8;">JOURNEY RISK RATING:</span>
        <span class="pill" style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid #10b981;">LOW</span>
        <span class="pill" style="background:rgba(245,158,11,0.2);color:#fbbf24;border:1px solid #f59e0b;">MODERATE</span>
        <span class="pill" style="background:rgba(249,115,22,0.22);color:#fb923c;border:1px solid #f97316;">HIGH</span>
        <span class="pill" style="background:rgba(239,68,68,0.25);color:#f87171;border:1px solid #ef4444;">SEVERE</span>
        <span style="color:#38bdf8;font-weight:700;">✚ Facilities</span>
        <span style="color:#ef4444;font-weight:700;">🚨 SOS</span>
      </div>

      <div class="map-hud" id="hudCard">
        <div class="hud-title">CORRIDOR TELEMETRY & SAFETY HUD</div>
        <div class="hud-route" id="hudRouteName"></div>
        <div class="hud-meta" id="hudRouteMeta">Click any checkpoint, hospital, safe haven, or SOS beacon for live details.</div>
      </div>

      <script>
        const routesData = {payload_json};
        const sosData = {sos_json};
        const facData = {fac_json};
        const activeLayers = {layers_json};
        document.getElementById('hudRouteName').innerText = {hud_route_safe};

        const map = L.map('map', {{ center: [28.95, 65.85], zoom: 6, zoomControl: true }});

        const primaryTiles = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
          attribution: '&copy; OpenStreetMap &copy; CARTO | Balochistan Smart Highway Watch',
          subdomains: 'abcd', maxZoom: 18
        }});
        const fallbackTiles = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          attribution: '&copy; OpenStreetMap contributors', maxZoom: 18
        }});
        let fallbackApplied = false;
        primaryTiles.on('tileerror', () => {{
          if (!fallbackApplied) {{
            fallbackApplied = true;
            map.removeLayer(primaryTiles);
            fallbackTiles.addTo(map);
          }}
        }});
        primaryTiles.addTo(map);

        let selectedBounds = [];

        routesData.forEach(route => {{
          const latlngs = route.points.map(p => [p.lat, p.lon]);
          const isSel = route.selected;

          if (activeLayers.highways) {{
            L.polyline(latlngs, {{
              color: route.color, weight: isSel ? 12 : 6, opacity: isSel ? 0.25 : 0.12
            }}).addTo(map);
            const line = L.polyline(latlngs, {{
              color: route.color, weight: isSel ? 4.5 : 2.5, opacity: isSel ? 0.95 : 0.65,
              dashArray: isSel ? null : '6, 6'
            }}).addTo(map);
            line.bindTooltip(`${{route.name}} (${{route.distance}}) • Max Risk: ${{route.max_risk}}/10`, {{sticky: true}});
          }}

          route.points.forEach(pt => {{
            if (isSel) selectedBounds.push([pt.lat, pt.lon]);

            let ptColor = '#10b981';
            if (pt.risk >= 9) ptColor = '#ef4444';
            else if (pt.risk >= 7) ptColor = '#f97316';
            else if (pt.risk >= 4) ptColor = '#f59e0b';

            if (activeLayers.weather_radar) {{
              L.circle([pt.lat, pt.lon], {{
                radius: isSel ? 32000 : 20000, color: ptColor, weight: 1,
                fillColor: ptColor, fillOpacity: isSel ? 0.16 : 0.08
              }}).addTo(map);
            }}

            if (activeLayers.checkpoints) {{
              const marker = L.circleMarker([pt.lat, pt.lon], {{
                radius: isSel ? 7.5 : 5, fillColor: ptColor, color: '#ffffff',
                weight: isSel ? 2 : 1, opacity: 1, fillOpacity: 0.95
              }}).addTo(map);

              const popupHtml = `
                <div style="min-width:215px;font-family:Inter,sans-serif;">
                  <div style="font-size:10px;color:#2dd4bf;font-weight:700;">${{route.code}} CHECKPOINT</div>
                  <div style="font-size:15px;font-weight:800;margin:2px 0 8px 0;">${{pt.name}} <span style="font-size:11px;color:#94a3b8;">(${{pt.elev}})</span></div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;background:#07111f;padding:8px;border-radius:8px;margin-bottom:8px;">
                    <div><span style="color:#64748b;">Temp:</span> <b>${{pt.temp}} °C</b></div>
                    <div><span style="color:#64748b;">Wind:</span> <b>${{pt.wind}} km/h</b></div>
                    <div><span style="color:#64748b;">Rain:</span> <b>${{pt.precip}} mm</b></div>
                    <div><span style="color:#64748b;">Rating:</span> <b style="color:${{ptColor}};">${{pt.tier}} (${{pt.risk}}/10)</b></div>
                  </div>
                  <div style="font-size:11px;"><b>Weather:</b> ${{pt.weather}}</div>
                  <div style="font-size:11px;margin-top:3px;"><b>Road Status:</b> <span style="color:${{ptColor}};">${{pt.status}}</span></div>
                </div>
              `;
              marker.bindPopup(popupHtml, {{className: 'custom-popup'}});
              marker.on('click', () => {{
                document.getElementById('hudRouteMeta').innerHTML =
                  `<b>${{pt.name}}</b> (${{pt.elev}}) • Temp: <b>${{pt.temp}}°C</b> • Rating: <b style="color:${{ptColor}};">${{pt.tier}}</b><br/>Status: ${{pt.status}}`;
              }});

              if (isSel) {{
                marker.bindTooltip(`${{pt.name}} (${{pt.tier}})`, {{
                  permanent: true, direction: 'top', offset: [0, -8]
                }});
              }}
            }}
          }});
        }});

        if (activeLayers.facilities) {{
          facData.forEach(fc => {{
            let symbol = '🏥';
            if (fc.type.includes('Petrol')) symbol = '⛽';
            else if (fc.type.includes('Repair')) symbol = '🔧';
            else if (fc.type.includes('Safe')) symbol = '🛡️';

            const fIcon = L.divIcon({{
              className: '',
              html: `<div class="fac-badge-icon">${{symbol}}</div>`,
              iconSize: [22, 22], iconAnchor: [11, 11]
            }});
            const fm = L.marker([fc.lat + 0.04, fc.lon + 0.04], {{icon: fIcon}}).addTo(map);
            fm.bindPopup(`
              <div style="min-width:200px;font-family:Inter,sans-serif;">
                <div style="font-size:10px;color:#38bdf8;font-weight:800;">${{fc.type.toUpperCase()}}</div>
                <div style="font-size:14px;font-weight:800;margin:2px 0 6px 0;">${{fc.name}}</div>
                <div style="font-size:11px;color:#cbd5e1;">Sector: <b>${{fc.sector}}</b></div>
                <div style="font-size:11px;color:#2dd4bf;margin:3px 0;">Helpline: <b>${{fc.phone}}</b></div>
                <div style="font-size:11px;color:#94a3b8;">${{fc.notes}}</div>
              </div>
            `, {{className: 'custom-popup'}});
          }});
        }}

        sosData.forEach(s => {{
          const sIcon = L.divIcon({{
            className: '',
            html: `<div class="sos-badge-icon">SOS</div>`,
            iconSize: [28, 28], iconAnchor: [14, 14]
          }});
          const sm = L.marker([s.lat, s.lon], {{icon: sIcon}}).addTo(map);
          sm.bindPopup(`
            <div style="min-width:210px;font-family:Inter,sans-serif;">
              <div style="font-size:10px;color:#ef4444;font-weight:800;">🚨 ACTIVE EMERGENCY (${{s.code}})</div>
              <div style="font-size:14px;font-weight:800;margin:2px 0 6px 0;">${{s.vehicle}} • ${{s.driver}}</div>
              <div style="font-size:11px;"><b>Type:</b> ${{s.type}}</div>
              <div style="font-size:11px;"><b>Location:</b> ${{s.sector}}</div>
              <div style="font-size:11px;color:#fca5a5;margin-top:4px;">${{s.details}}</div>
            </div>
          `, {{className: 'custom-popup'}});
        }});

        if (selectedBounds.length > 1) {{
          map.fitBounds(selectedBounds, {{padding: [55, 55]}});
        }}
        setTimeout(() => {{ map.invalidateSize(); }}, 200);
      </script>
    </body>
    </html>
    """
    components.html(html, height=490, scrolling=False)

if "_db_initialized" not in st.session_state:
    init_db()
    seed()
    st.session_state["_db_initialized"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

:root {
  --bg-deep: #050b14;
  --bg-panel: #0a1626;
  --bg-card: #0e1e33;
  --teal: #14b8a6;
  --cyan: #38bdf8;
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
}

.stApp {
  background: radial-gradient(circle at 18% 0%, #0d263d 0%, #060e1a 45%, #040811 100%);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #071220 0%, #0a192c 100%);
  border-right: 1px solid rgba(20, 184, 166, 0.2);
}

.block-container {
  padding-top: 1.0rem;
  padding-bottom: 2rem;
  max-width: 1580px;
}

h1, h2, h3, h4 {
  color: #f8fafc !important;
  font-family: 'Inter', sans-serif;
  letter-spacing: -0.02em;
}

.cmd-topbar {
  background: linear-gradient(90deg, rgba(10, 25, 44, 0.94) 0%, rgba(13, 39, 64, 0.90) 100%);
  border: 1px solid rgba(45, 212, 191, 0.28);
  border-radius: 16px;
  padding: 14px 22px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}
.cmd-title { font-size: 20px; font-weight: 800; color: #f8fafc; margin: 0; }
.cmd-sub { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.tagline-pill {
  background: rgba(20, 184, 166, 0.14); border: 1px solid rgba(45, 212, 191, 0.4);
  color: #5eead4; padding: 4px 12px; border-radius: 999px; font-size: 11px; font-weight: 700;
}
.live-badge {
  display: inline-flex; align-items: center; gap: 7px;
  background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.45);
  color: #34d399; padding: 5px 12px; border-radius: 999px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
}
.live-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.stat-card {
  background: linear-gradient(155deg, #0e1f36 0%, #091423 100%);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}
.stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; font-weight: 600; }
.stat-val { font-size: 26px; font-weight: 800; color: #f8fafc; margin: 4px 0; font-family: 'JetBrains Mono', monospace; }
.stat-foot { font-size: 11px; color: #2dd4bf; }

.gauge-box {
  background: #0b1829;
  border: 1px solid rgba(56, 189, 248, 0.16);
  border-radius: 14px;
  padding: 12px 8px;
  text-align: center;
}
.gauge-ring {
  width: 68px; height: 68px; border-radius: 50%;
  margin: 6px auto;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 14px; color: #f8fafc;
}
.gauge-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; font-weight: 700; }
.gauge-sub { font-size: 10px; color: #64748b; }

.side-panel-card {
  background: linear-gradient(180deg, #0c1b2e 0%, #081220 100%);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 14px;
}
.auth-card {
  background: linear-gradient(160deg, rgba(14, 31, 54, 0.96) 0%, rgba(8, 19, 34, 0.98) 100%);
  border: 1px solid rgba(45, 212, 191, 0.32);
  border-radius: 20px;
  padding: 28px 30px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65);
}
.sos-banner {
  background: linear-gradient(90deg, rgba(153, 27, 27, 0.55) 0%, rgba(127, 29, 29, 0.45) 100%);
  border: 1px solid #ef4444;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.notif-item {
  background: rgba(15, 31, 53, 0.85);
  border-left: 3px solid #f59e0b;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 9px;
}
.notif-item.danger { border-left-color: #ef4444; }
.notif-item.safe { border-left-color: #10b981; }
.urdu-box {
  font-family: 'Noto Nastaliq Urdu', 'Inter', sans-serif;
  direction: rtl;
  text-align: right;
  line-height: 2.0;
  font-size: 15px;
  background: #081322;
  border: 1px solid rgba(20, 184, 166, 0.35);
  border-radius: 12px;
  padding: 14px 18px;
  color: #f1f5f9;
}
.ltr-box {
  font-family: 'Inter', sans-serif;
  direction: ltr;
  text-align: left;
  line-height: 1.65;
  font-size: 14px;
  background: #081322;
  border: 1px solid rgba(56, 189, 248, 0.35);
  border-radius: 12px;
  padding: 14px 18px;
  color: #f1f5f9;
}

.stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(45, 212, 191, 0.45);
  background: linear-gradient(90deg, #0d9488 0%, #0284c7 100%);
  color: #ffffff;
  font-weight: 700;
  transition: all 0.2s ease;
}
.stButton > button:hover {
  border-color: #5eead4;
  box-shadow: 0 0 16px rgba(20, 184, 166, 0.45);
  color: #ffffff;
}
</style>
""", unsafe_allow_html=True)

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if st.session_state["auth_user"] is None:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1.05, 1.35, 1.05])

    with center_col:
        st.markdown(f"""
        <div class="auth-card" style="text-align:center;margin-bottom:14px;">
          {logo_svg(68)}
          <div style="font-size:22px;font-weight:800;color:#f8fafc;margin-top:10px;letter-spacing:-0.3px;">
            Balochistan Smart Highway Watch
          </div>
          <div style="font-size:12px;color:#2dd4bf;font-weight:700;letter-spacing:1px;margin-top:3px;">
            PROACTIVE TRANSPORT SAFETY & WEATHER INTELLIGENCE
          </div>
          <div style="font-size:12px;color:#cbd5e1;font-style:italic;margin-top:8px;">
            “We don’t just predict dangerous journeys. We help prevent them.”
          </div>
        </div>
        """, unsafe_allow_html=True)

        tab_signin, tab_signup = st.tabs(["🔐 Sign In (Control Room)", "📝 Sign Up (Register Officer)"])

        with tab_signin:
            with st.form("signin_form"):
                u_login = st.text_input("Username", placeholder="Enter username (default: admin)")
                p_login = st.text_input("Password", type="password", placeholder="Enter password (default: admin123)")
                btn_login = st.form_submit_button("Sign In to Command Center", use_container_width=True)

            if btn_login:
                uname_clean = u_login.strip()
                if uname_clean and p_login:
                    matched = rows("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (uname_clean,))
                    if matched:
                        user_rec = matched[0]
                        is_ok, needs_upg = verify_password(p_login, user_rec["password_hash"])
                        if is_ok:
                            if needs_upg:
                                new_h = hash_password(p_login)
                                run("UPDATE users SET password_hash=? WHERE id=?", (new_h, user_rec["id"]))
                                user_rec["password_hash"] = new_h
                            st.session_state["auth_user"] = user_rec
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please try again.")
                    else:
                        st.error("Invalid username or password. Please try again.")
                else:
                    st.warning("Please enter both username and password.")

            st.caption("Default Control Room Credentials: Username `admin` • Password `admin123`")

        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                s_fullname = st.text_input("Officer Full Name", placeholder="e.g., Capt. Tariq Mahmood")
                s_username = st.text_input("Choose Username", placeholder="e.g., tariq_nha (letters, numbers, _, .)")
                c_dept, c_role = st.columns(2)
                s_dept = c_dept.selectbox("Department / Wing", ["PDMA Balochistan", "National Highway Authority (NHA)", "Balochistan Levies Force", "Highway Police", "District Administration"])
                s_role = c_role.selectbox("Designation / Role", ["Control Room Operator", "Checkpoint Supervisor", "Regional Coordinator", "Command Officer"])
                c_p1, c_p2 = st.columns(2)
                s_pass1 = c_p1.text_input("Create Password", type="password", placeholder="Min 6 characters")
                s_pass2 = c_p2.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                btn_signup = st.form_submit_button("Create Official Account", use_container_width=True)

            if btn_signup:
                fn = s_fullname.strip()
                un = s_username.strip()
                if not (fn and un and s_pass1):
                    st.error("Please fill all required fields.")
                elif not is_valid_username(un):
                    st.error("Username must be 3–30 characters using only letters, numbers, '_', '.', or '-'.")
                elif len(s_pass1) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif s_pass1 != s_pass2:
                    st.error("Passwords do not match.")
                else:
                    exists = rows("SELECT id FROM users WHERE LOWER(username)=LOWER(?)", (un,))
                    if exists:
                        st.error("This username is already taken. Choose another username.")
                    else:
                        try:
                            new_uid = run(
                                "INSERT INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                                (fn, un, s_dept, s_role, hash_password(s_pass1), datetime.now().strftime("%Y-%m-%d %H:%M"))
                            )
                            created_user = rows("SELECT * FROM users WHERE id=?", (new_uid,))[0]
                            st.session_state["auth_user"] = created_user
                            st.success("Account created! Entering Command Center...")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("This username is already registered.")

    st.stop()

current_user = st.session_state["auth_user"]
road_rows_all = rows("SELECT * FROM road_status")
road_lookup = {(r["route"], r["area"]): r for r in road_rows_all}
all_drivers_global = rows("SELECT * FROM drivers ORDER BY id DESC")
active_sos_global = rows("SELECT * FROM sos_incidents WHERE status='ACTIVE SOS' ORDER BY id DESC")
overdue_drivers_global = get_overdue_drivers(all_drivers_global)

with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:6px 0 14px 0;">
      {logo_svg(48)}
      <div>
        <div style="font-weight:800;font-size:15px;color:#f8fafc;letter-spacing:0.3px;">HIGHWAY WATCH</div>
        <div style="font-size:10px;color:#2dd4bf;font-weight:700;letter-spacing:1.1px;">SAFETY & MONITORING</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#081322;border:1px solid rgba(45,212,191,0.3);border-radius:12px;padding:10px 12px;margin-bottom:14px;">
      <div style="font-size:10px;color:#2dd4bf;font-weight:700;letter-spacing:0.8px;">SIGNED IN OPERATOR</div>
      <div style="font-size:13px;font-weight:800;color:#f8fafc;margin-top:2px;">{current_user['full_name']}</div>
      <div style="font-size:11px;color:#94a3b8;">{current_user['role']} • {current_user['department']}</div>
    </div>
    """, unsafe_allow_html=True)

    sos_badge_txt = f" ({len(active_sos_global)} ACTIVE)" if active_sos_global else ""
    nav_choice = st.radio(
        "OPERATIONS MENU",
        [
            "Admin Control Dashboard",
            f"Emergency SOS & Welfare{sos_badge_txt}",
            "Driver Portal & Journey Risk",
            "Highway Map & Safe Routes",
            "Multilingual Alert & Voice",
            "Road Clearance & Logs"
        ],
        label_visibility="visible"
    )

    st.markdown("---")
    selected_corridor = st.selectbox("Active Highway Corridor", ROUTES, key="active_corridor_sel")

    if st.button("Sync Live Weather Feed", use_container_width=True):
        fetch_weather.clear()
        st.rerun()

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("""
    <div style="margin-top:12px;padding:11px;background:#081322;border:1px solid rgba(56,189,248,0.18);border-radius:12px;font-size:11px;color:#94a3b8;">
      <div style="color:#2dd4bf;font-weight:700;margin-bottom:3px;">MISSION STATEMENT</div>
      <div style="font-style:italic;color:#cbd5e1;">“We don’t just predict dangerous journeys. We help prevent them.”</div>
    </div>
    """, unsafe_allow_html=True)

now_str = datetime.now().strftime("%d %b %Y • %H:%M PKT")
st.markdown(f"""
<div class="cmd-topbar">
  <div style="display:flex;align-items:center;gap:14px;">
    {logo_svg(44)}
    <div>
      <div class="cmd-title">Balochistan Smart Highway & Weather Intelligence</div>
      <div class="cmd-sub">“We don’t just predict dangerous journeys. We help prevent them.” • Operator: {current_user['full_name']}</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <span class="tagline-pill">PROVINCIAL COMMAND CENTER</span>
    <span style="font-size:12px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">{now_str}</span>
    <span class="live-badge"><span class="live-dot"></span> LIVE</span>
  </div>
</div>
""", unsafe_allow_html=True)

if active_sos_global:
    top_sos = active_sos_global[0]
    st.markdown(f"""
    <div class="sos-banner">
      <div>
        <span style="background:#ef4444;color:#fff;font-weight:900;font-size:11px;padding:3px 9px;border-radius:6px;margin-right:8px;">🚨 ACTIVE EMERGENCY SOS</span>
        <strong style="color:#fff;">{top_sos['sos_code']} • {top_sos['vehicle']} ({top_sos['driver_name']})</strong>
        <span style="color:#fecaca;font-size:13px;"> — {top_sos['emergency_type']} at <b>{top_sos['sector']}</b> ({top_sos['route']})</span>
      </div>
      <div style="font-size:12px;color:#fecaca;font-family:'JetBrains Mono',monospace;">Response: {top_sos['dispatched_unit']}</div>
    </div>
    """, unsafe_allow_html=True)

def get_corridor_weather(route_name):
    cache = {}
    full_payloads = {}
    failed_points = []
    for pt in ROUTES_DATA[route_name]["points"]:
        try:
            res = fetch_weather(pt["lat"], pt["lon"])
            cache[pt["name"]] = res.get("current", {})
            full_payloads[pt["name"]] = res
        except Exception:
            cache[pt["name"]] = {}
            failed_points.append(pt["name"])
    return cache, full_payloads, failed_points

def compute_corridor_overall_risk(route_name, w_cache):
    max_s = 1
    worst_sector = ROUTES_DATA[route_name]["points"][0]["name"]
    for pt in ROUTES_DATA[route_name]["points"]:
        cur = w_cache.get(pt["name"], {})
        r_obj = road_lookup.get((route_name, pt["name"]), {})
        sc = compute_risk_score(cur, r_obj.get("status", "Open (Verified)"), r_obj.get("risk_score"))
        if sc >= max_s:
            max_s = sc
            worst_sector = pt["name"]
    tier, color, bg = journey_risk_tier(max_s)
    return max_s, tier, color, bg, worst_sector

if nav_choice == "Admin Control Dashboard":
    checkpoints = rows("SELECT * FROM checkpoints")
    alerts_log = rows("SELECT * FROM alerts ORDER BY id DESC")
    restricted_count = sum(1 for r in road_rows_all if "Closed" in r["status"] or "Restricted" in r["status"])

    w_cache, w_full, failed_pts = get_corridor_weather(selected_corridor)
    c_score, c_tier, c_color, c_bg, c_worst = compute_corridor_overall_risk(selected_corridor, w_cache)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f'<div class="stat-card"><div class="stat-label">Registered Vehicles</div><div class="stat-val">{len(all_drivers_global)}</div><div class="stat-foot">Active Journeys Tracked</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="stat-card"><div class="stat-label">Active SOS Alerts</div><div class="stat-val" style="color:#ef4444;">{len(active_sos_global)}</div><div class="stat-foot">Emergency Beacons</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="stat-card"><div class="stat-label">Dangerous Sectors</div><div class="stat-val" style="color:#f59e0b;">{restricted_count}</div><div class="stat-foot">Caution / Blocked Roads</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="stat-card"><div class="stat-label">Overdue Checkpoints</div><div class="stat-val" style="color:#fb923c;">{len(overdue_drivers_global)}</div><div class="stat-foot">Auto Welfare Monitor</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div class="stat-card"><div class="stat-label">Corridor Risk Rating</div><div class="stat-val" style="color:{c_color};">{c_tier}</div><div class="stat-foot">Peak: {c_worst} ({c_score}/10)</div></div>', unsafe_allow_html=True)

    if "demo_banner_msg" not in st.session_state:
        st.session_state["demo_banner_msg"] = None

    if st.session_state["demo_banner_msg"]:
        b_type, b_text = st.session_state["demo_banner_msg"]
        if b_type == "success":
            st.success(b_text)
        else:
            st.info(b_text)

    with st.expander("🎯 Live Safety Demonstration Simulator (Quetta → Karachi N-25)", expanded=bool(st.session_state["demo_banner_msg"])):
        st.markdown("""
        **Demonstrate the complete preventive safety lifecycle in 1 click:**
        1. Registers Truck **QTA-9921 (Driver: Ustad Gul Muhammad)** at Quetta Toll Plaza on **Quetta–Karachi (N-25)**.
        2. Triggers severe weather/flash-flood alert at **Kalat & Khuzdar** (`SEVERE` Journey Risk).
        3. Sends multilingual SMS/Voice warning recommending halt at **Mastung NHA Safe Haven** + suggests **N-65 Sibi-Sukkur Alternative Route**.
        4. Updates vehicle status to **Halted at Safe Haven (Prevented Hazard)** on the Admin Dashboard.
        """)
        sim_c1, sim_c2 = st.columns([1.2, 1])
        if sim_c1.button("▶️ Run Live Quetta → Karachi Preventive Demo", key="btn_run_demo", use_container_width=True):
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
            eta_s = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
            existing_demo = rows("SELECT id FROM drivers WHERE vehicle='QTA-9921'")
            if existing_demo:
                demo_id = existing_demo[0]["id"]
                run(
                    "UPDATE drivers SET status='Halted at Safe Haven (Prevented)', current_sector='Mastung', next_checkpoint='Kalat', expected_eta=?, last_checkin=? WHERE id=?",
                    (eta_s, now_s, demo_id)
                )
            else:
                demo_id = run(
                    """INSERT INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("BHW-9921", "Ustad Gul Muhammad", "0300-9214455", "QTA-9921", "Cargo Truck", "Quetta–Karachi (N-25)", "Urdu",
                     "Halted at Safe Haven (Prevented)", "Mastung", "Kalat", eta_s, now_s, now_s)
                )
            run(
                "UPDATE road_status SET status='Restricted — Caution', risk_score=9, authority_note='Severe rain & flash flood risk near Kalat & Khuzdar. Heavy trucks advised to halt at Mastung Safe Haven.', updated_at=? WHERE route='Quetta–Karachi (N-25)' AND area IN ('Kalat','Khuzdar')",
                (now_s,)
            )
            run("DELETE FROM alerts WHERE driver_id=?", (demo_id,))
            run(
                "INSERT INTO alerts(driver_id,route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (demo_id, "Quetta–Karachi (N-25)", "Urdu", "Emergency",
                 "ہنگامی انتباہ (QTA-9921): قلات اور خضدار میں شدید بارش کے باعث خطرہ شدید (SEVERE) ہے۔ براہِ کرم مستونگ NHA سیف ہیون پر رک جائیں یا سبی-سکھر متبادل راستہ اختیار کریں۔",
                 "SMS Gateway, Automated Voice Call (IVR)", "Delivered — Truck Halted Safely", now_s)
            )
            st.session_state["demo_banner_msg"] = (
                "success",
                "✅ Live Demo Executed! Truck QTA-9921 registered on N-25, warned via Urdu SMS & IVR Voice, and safely halted at Mastung Safe Haven (Hazard Prevented)."
            )
            st.rerun()

        if sim_c2.button("🔄 Reset Demo Scenario", key="btn_reset_demo", use_container_width=True):
            existing_demo = rows("SELECT id FROM drivers WHERE vehicle='QTA-9921'")
            for ed in existing_demo:
                run("DELETE FROM alerts WHERE driver_id=?", (ed["id"],))
            run("DELETE FROM drivers WHERE vehicle='QTA-9921'")
            run("UPDATE road_status SET status='Open (Verified)', risk_score=2, authority_note='Normal traffic flow; regular patrol active.' WHERE route='Quetta–Karachi (N-25)' AND area IN ('Kalat','Khuzdar')")
            st.session_state["demo_banner_msg"] = (
                "info",
                "🔄 Demo scenario reset to normal baseline."
            )
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if c_score >= 6:
        st.warning(
            f"**⚠️ {c_tier} RISK DETECTED ON {selected_corridor} (Peak Sector: {c_worst})** — "
            f"**Recommended Verified Alternative Route:** `{ROUTES_DATA[selected_corridor]['alt_route']}` "
            f"({ROUTES_DATA[selected_corridor]['alt_reason']})"
        )

    col_main, col_right = st.columns([2.25, 1.0], gap="medium")

    with col_main:
        render_balochistan_map(
            selected_corridor,
            w_cache,
            road_lookup,
            {"highways": True, "weather_radar": True, "checkpoints": True, "facilities": True},
            sos_list=active_sos_global,
            facilities_list=NEARBY_FACILITIES
        )

        hub_point = ROUTES_DATA[selected_corridor]["points"][-1]["name"]
        hub_cur = w_cache.get(hub_point, {})
        hub_road_obj = road_lookup.get((selected_corridor, hub_point), {})
        hub_road = hub_road_obj.get("status", "Open (Verified)")

        wind_f = safe_float(hub_cur.get("wind_speed_10m"))
        rain_f = safe_float(hub_cur.get("precipitation"))
        press_f = safe_float(hub_cur.get("surface_pressure"))
        hum_f = safe_float(hub_cur.get("relative_humidity_2m"))

        wind_disp = f"{wind_f:.1f}" if wind_f is not None else "—"
        rain_disp = f"{rain_f:.1f}" if rain_f is not None else "—"
        press_disp = f"{int(press_f)}" if press_f is not None else "—"
        hum_disp = f"{int(hum_f)}%" if hum_f is not None else "—"

        r_score = compute_risk_score(hub_cur, hub_road, hub_road_obj.get("risk_score"))
        r_tier, r_color, _ = journey_risk_tier(r_score)

        g1, g2, g3, g4, g5 = st.columns(5)
        gauges = [
            (g1, "WIND SPEED", wind_disp, "km/h", "#38bdf8", min(int((wind_f or 0) * 2), 100)),
            (g2, "RAINFALL", rain_disp, "mm/hr", "#14b8a6", min(int((rain_f or 0) * 15), 100)),
            (g3, "PRESSURE", press_disp, "hPa", "#818cf8", min(max(int(((press_f or 1012) - 960) * 1.1), 10), 100)),
            (g4, "HUMIDITY", hum_disp, "Relative", "#2dd4bf", min(max(int(hum_f or 0), 0), 100)),
            (g5, "JOURNEY RISK", r_tier, f"Score {r_score}/10", r_color, r_score * 10),
        ]
        for col_obj, title, val, sub, color, pct in gauges:
            col_obj.markdown(f"""
            <div class="gauge-box">
              <div class="gauge-title">{title}</div>
              <div class="gauge-ring" style="background: radial-gradient(closest-side, #0b1829 76%, transparent 80% 100%), conic-gradient({color} {pct}%, #172a45 0);">{val}</div>
              <div class="gauge-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div style="font-size:12px;font-weight:800;letter-spacing:0.8px;color:#ef4444;margin-bottom:6px;">🚨 LIVE SOS & WELFARE MONITOR</div>', unsafe_allow_html=True)
        if active_sos_global:
            for s in active_sos_global[:3]:
                st.markdown(f"""
                <div class="notif-item danger">
                  <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:800;">
                    <span style="color:#fca5a5;">{s['sos_code']} • {s['vehicle']}</span>
                    <span style="color:#ef4444;">{s['emergency_type']}</span>
                  </div>
                  <div style="font-size:11px;color:#f1f5f9;margin-top:2px;"><b>{s['driver_name']}</b> at <b>{s['sector']}</b></div>
                  <div style="font-size:10px;color:#cbd5e1;margin-top:2px;">{s.get('details','')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="notif-item safe"><div style="font-size:11px;color:#34d399;font-weight:700;">All SOS beacons clear.</div></div>', unsafe_allow_html=True)

        if overdue_drivers_global:
            st.markdown('<div style="font-size:12px;font-weight:800;letter-spacing:0.8px;color:#fb923c;margin:8px 0 6px 0;">⏱️ AUTO WELFARE CHECK (MISSED ETA)</div>', unsafe_allow_html=True)
            for od in overdue_drivers_global[:3]:
                st.markdown(f"""
                <div class="notif-item">
                  <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:800;">
                    <span style="color:#fed7aa;">{od['vehicle']} ({od['name']})</span>
                    <span style="color:#fb923c;">+{od['mins_late']}m Late</span>
                  </div>
                  <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Expected at <b>{od.get('next_checkpoint','Checkpoint')}</b> ({od['route']})</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:12px;font-weight:800;letter-spacing:0.8px;color:#f8fafc;margin:10px 0 6px 0;">ACTIVE FLEET STATUS</div>', unsafe_allow_html=True)
        for d in all_drivers_global[:4]:
            st_d = d.get("status") or "Active on Route"
            cls_d = "danger" if ("Overdue" in st_d or "SOS" in st_d) else ("safe" if ("Safe" in st_d or "Verified" in st_d) else "")
            st.markdown(f"""
            <div class="notif-item {cls_d}">
              <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:700;">
                <span style="color:#f8fafc;">{d['vehicle']} • {d['name']}</span>
                <span style="color:#2dd4bf;">{st_d}</span>
              </div>
              <div style="font-size:10px;color:#94a3b8;margin-top:2px;">{d['route']} • Sector: {d.get('current_sector','Quetta')}</div>
            </div>
            """, unsafe_allow_html=True)

elif nav_choice.startswith("Emergency SOS & Welfare"):
    st.subheader("🚨 One-Tap Driver Emergency SOS & Automatic Welfare Monitoring")
    c_sos_trigger, c_sos_board = st.columns([1.05, 1.55], gap="large")

    with c_sos_trigger:
        st.markdown('<div class="side-panel-card"><div style="font-weight:800;font-size:15px;color:#fca5a5;margin-bottom:6px;">Driver One-Button Emergency SOS</div><div style="font-size:12px;color:#94a3b8;margin-bottom:10px;">Instantly transmits vehicle plate, GPS coordinates, and emergency category to PDMA/Levies Control Room.</div>', unsafe_allow_html=True)
        with st.form("driver_sos_form", clear_on_submit=True):
            if all_drivers_global:
                drv_choices = {f"{d['vehicle']} • {d['name']} ({d['route']})": d for d in all_drivers_global}
                chosen_drv = drv_choices[st.selectbox("Select Registered Vehicle / Driver", list(drv_choices.keys()))]
                def_route_idx = ROUTES.index(chosen_drv["route"]) if chosen_drv["route"] in ROUTES else 0
            else:
                chosen_drv = None
                def_route_idx = 0

            sos_route = st.selectbox("Highway Corridor", ROUTES, index=def_route_idx)
            sos_sector = st.selectbox("Nearest Checkpoint / Location", [p["name"] for p in ROUTES_DATA[sos_route]["points"]])
            sos_type = st.selectbox("Emergency Category", SOS_TYPES)
            sos_notes = st.text_input("Brief Situation Note (Optional)", placeholder="e.g., Brake failure on descent / Medical emergency")
            send_sos = st.form_submit_button("🚨 TRIGGER EMERGENCY SOS NOW", use_container_width=True)

        if send_sos:
            pt_obj = next((p for p in ROUTES_DATA[sos_route]["points"] if p["name"] == sos_sector), ROUTES_DATA[sos_route]["points"][0])
            s_code = generate_unique_sos_code()
            d_id = chosen_drv["id"] if chosen_drv else None
            d_name = chosen_drv["name"] if chosen_drv else "Unregistered Motorist"
            d_veh = chosen_drv["vehicle"] if chosen_drv else "TEMP-SOS"
            d_ph = chosen_drv["phone"] if chosen_drv else "0300-0000000"
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")

            run(
                """INSERT INTO sos_incidents
                (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s_code, d_id, d_name, d_veh, d_ph, sos_route, sos_sector, pt_obj["lat"], pt_obj["lon"],
                 sos_type, "Driver One-Tap SOS", sos_notes.strip() or f"Driver pressed Emergency SOS at {sos_sector}.",
                 "ACTIVE SOS", "Rescue 1122 & Levies Dispatched", now_s)
            )
            if d_id:
                run("UPDATE drivers SET status='ACTIVE SOS', current_sector=? WHERE id=?", (sos_sector, d_id))
            st.error(f"🚨 SOS {s_code} TRANSMITTED! Control Room alerted with GPS ({pt_obj['lat']}, {pt_obj['lon']}) for {d_veh}.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_sos_board:
        st.markdown("### Active Control Room SOS Queue")
        all_sos = rows("SELECT * FROM sos_incidents ORDER BY id DESC")
        if all_sos:
            for item in all_sos:
                is_act = item["status"] == "ACTIVE SOS"
                border_c = "#ef4444" if is_act else "#10b981"
                st.markdown(f"""
                <div style="background:#0b1829;border:1px solid {border_c};border-left:5px solid {border_c};border-radius:12px;padding:12px 16px;margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:800;font-size:14px;color:#f8fafc;">{item['sos_code']} • {item['vehicle']} ({item['driver_name']})</span>
                    <span style="background:{border_c};color:#fff;font-size:10px;font-weight:800;padding:3px 9px;border-radius:999px;">{item['status']}</span>
                  </div>
                  <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">
                    <b>Type:</b> {item['emergency_type']} | <b>Sector:</b> {item['sector']} ({item['route']}) | <b>Phone:</b> {item['phone']}
                  </div>
                  <div style="font-size:11px;color:#94a3b8;margin-top:3px;">
                    GPS: {item.get('lat')}, {item.get('lon')} • Source: {item.get('source')} • {item.get('details')}
                  </div>
                </div>
                """, unsafe_allow_html=True)
                if is_act:
                    b1, b2 = st.columns([1.3, 1])
                    if b1.button(f"✅ Mark {item['sos_code']} Resolved & Safe", key=f"res_{item['id']}", use_container_width=True):
                        run("UPDATE sos_incidents SET status='RESOLVED', dispatched_unit='Rescue Completed' WHERE id=?", (item["id"],))
                        if item.get("driver_id"):
                            run("UPDATE drivers SET status='Safe — Assisted' WHERE id=?", (item["driver_id"],))
                        st.rerun()

        st.markdown("### ⏱️ Automatic Checkpoint Monitoring (Overdue Welfare Flagging)")
        if overdue_drivers_global:
            for od in overdue_drivers_global:
                st.warning(
                    f"**Welfare Flag:** Vehicle **{od['vehicle']}** ({od['name']}, {od['phone']}) is **{od['mins_late']} mins overdue** "
                    f"at **{od.get('next_checkpoint')}** on **{od['route']}**."
                )
                c_w1, c_w2 = st.columns(2)
                if c_w1.button(f"🚨 Escalate {od['vehicle']} to Auto-SOS", key=f"esc_{od['id']}", use_container_width=True):
                    pt_o = next((p for p in ROUTES_DATA[od["route"]]["points"] if p["name"] == od.get("current_sector")), ROUTES_DATA[od["route"]]["points"][0])
                    s_c = generate_unique_sos_code()
                    now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                    run(
                        """INSERT INTO sos_incidents
                        (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (s_c, od["id"], od["name"], od["vehicle"], od["phone"], od["route"], od.get("current_sector", "En Route"),
                         pt_o["lat"], pt_o["lon"], "Missed Checkpoint / Welfare Check", "Automatic Journey Monitor",
                         f"Vehicle missed {od.get('next_checkpoint')} ETA by {od['mins_late']} mins.", "ACTIVE SOS", "Patrol Welfare Check", now_s)
                    )
                    run("UPDATE drivers SET status='ACTIVE SOS' WHERE id=?", (od["id"],))
                    st.rerun()
                if c_w2.button(f"✓ Confirm Driver Safe ({od['vehicle']})", key=f"ok_{od['id']}", use_container_width=True):
                    new_eta = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                    run("UPDATE drivers SET status='Active on Route', expected_eta=?, last_checkin=? WHERE id=?", (new_eta, datetime.now().strftime("%Y-%m-%d %H:%M"), od["id"]))
                    st.rerun()
        else:
            st.success("All active vehicles are within expected checkpoint arrival windows.")

elif nav_choice == "Driver Portal & Journey Risk":
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")
    checkpoints = rows("SELECT * FROM checkpoints ORDER BY id ASC")

    st.subheader("Pre-Journey Risk Assessment & Vehicle Registration")

    jr1, jr2 = st.columns([1.15, 1.35], gap="large")
    with jr1:
        st.markdown('<div class="side-panel-card"><div style="font-weight:800;font-size:15px;margin-bottom:6px;">🧭 Journey Risk Score Calculator</div><div style="font-size:12px;color:#94a3b8;margin-bottom:10px;">Evaluates Low, Moderate, High, or Severe journey risk using live Open-Meteo weather + verified NHA/PDMA road clearance.</div>', unsafe_allow_html=True)
        calc_route = st.selectbox("Select Planned Corridor", ROUTES, index=ROUTES.index(selected_corridor), key="calc_rt")
        w_calc, _, _ = get_corridor_weather(calc_route)
        j_score, j_tier, j_color, j_bg, j_worst = compute_corridor_overall_risk(calc_route, w_calc)

        st.markdown(f"""
        <div style="background:{j_bg};border:2px solid {j_color};border-radius:14px;padding:16px;text-align:center;margin-top:8px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:1px;color:#cbd5e1;">OVERALL JOURNEY RISK RATING</div>
          <div style="font-size:32px;font-weight:900;color:{j_color};margin:4px 0;font-family:'JetBrains Mono',monospace;">{j_tier} ({j_score}/10)</div>
          <div style="font-size:12px;color:#f1f5f9;">Critical Sector: <b>{j_worst}</b> • Distance: {ROUTES_DATA[calc_route]['distance']}</div>
        </div>
        """, unsafe_allow_html=True)
        if j_score >= 6:
            st.info(f"**Preventive Detour:** `{ROUTES_DATA[calc_route]['alt_route']}`")
        st.markdown("</div>", unsafe_allow_html=True)

    with jr2:
        st.markdown("#### Register Vehicle & Start Monitored Journey")
        with st.form("driver_reg_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d_name = c1.text_input("Driver Full Name", placeholder="e.g., Muhammad Aslam")
            d_phone = c2.text_input("Mobile Number (SMS/Voice)", placeholder="0300-XXXXXXX")
            c3, c4 = st.columns(2)
            d_veh = c3.text_input("Vehicle Plate No.", placeholder="QTA-9081")
            d_vtype = c4.selectbox("Vehicle Category", ["Cargo Truck", "Passenger Coach", "Oil Tanker", "Ambulance / Emergency", "Private SUV / Car"])
            c5, c6, c7 = st.columns(3)
            d_route = c5.selectbox("Assigned Corridor", ROUTES)
            d_lang = c6.selectbox("Alert Language", LANGUAGES)
            eta_hrs = c7.number_input("Next Checkpoint ETA (hrs)", min_value=1, max_value=12, value=2)
            submitted = st.form_submit_button("Register & Issue Digital QR Pass", use_container_width=True)

        if submitted:
            fn_d = d_name.strip()
            ph_d = d_phone.strip()
            vh_d = re.sub(r"\s+", "", d_veh.strip().upper())
            if not (fn_d and ph_d and vh_d):
                st.error("Please fill Driver Name, Mobile Number, and Vehicle Plate.")
            elif not is_valid_pk_phone(ph_d):
                st.error("Please enter a valid Pakistani mobile number (e.g., 0300-1234567).")
            elif not is_valid_plate(vh_d):
                st.error("Please enter a valid vehicle plate number (e.g., QTA-9081).")
            else:
                d_code = generate_unique_driver_code()
                pts = ROUTES_DATA[d_route]["points"]
                start_sec = pts[0]["name"]
                next_sec = pts[1]["name"] if len(pts) > 1 else pts[0]["name"]
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                eta_s = (datetime.now() + timedelta(hours=int(eta_hrs))).strftime("%Y-%m-%d %H:%M")
                run(
                    """INSERT INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (d_code, fn_d, ph_d, vh_d, d_vtype, d_route, d_lang, "Active on Route", start_sec, next_sec, eta_s, now_s, now_s)
                )
                st.success(f"Vehicle registered! Pass ID: {d_code} • Next Checkpoint: {next_sec} (ETA {eta_s})")
                st.rerun()

    st.markdown("---")
    col_tbl, col_qr = st.columns([1.65, 1.0], gap="large")
    with col_tbl:
        st.markdown("#### Active Monitored Vehicles")
        if drivers:
            df_drv = pd.DataFrame(drivers)[["driver_code", "name", "vehicle", "route", "current_sector", "next_checkpoint", "expected_eta", "status"]]
            df_drv.columns = ["Pass ID", "Driver", "Plate", "Corridor", "Current Sector", "Next Gate", "Expected ETA", "Status"]
            st.dataframe(df_drv, use_container_width=True, hide_index=True)

    with col_qr:
        st.markdown("#### Checkpoint QR Scan & Safe Haven Check-In")
        if drivers:
            label_to_driver = {f"{d.get('driver_code')} • {d['name']} ({d['vehicle']})": d for d in drivers}
            sel_d = label_to_driver[st.selectbox("Select Vehicle", list(label_to_driver.keys()))]
            code_disp = sel_d.get("driver_code") or f"BHW-{sel_d['id']}"
            qr_payload = urllib.parse.quote(f"BHW-PASS|{code_disp}|{sel_d['name']}|{sel_d['vehicle']}|{sel_d['route']}")
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=155x155&data={qr_payload}&bgcolor=0b1829&color=2dd4bf"

            st.markdown(f"""
            <div class="side-panel-card" style="text-align:center;">
              <div style="font-size:11px;color:#2dd4bf;font-weight:700;">DIGITAL CHECKPOINT PASS</div>
              <div style="font-size:16px;font-weight:800;margin:3px 0;">{sel_d['name']} ({sel_d['vehicle']})</div>
              <img src="{qr_url}" alt="QR Pass" style="border-radius:10px;border:2px solid #14b8a6;padding:5px;background:#0b1829;margin:6px 0;"/>
              <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#38bdf8;">{code_disp} • {sel_d['language']}</div>
            </div>
            """, unsafe_allow_html=True)

            b_scan, b_halt = st.columns(2)
            if b_scan.button("✅ Checkpoint QR Scan", use_container_width=True):
                pts = ROUTES_DATA[sel_d["route"]]["points"]
                names = [p["name"] for p in pts]
                cur_s = sel_d.get("next_checkpoint") or names[0]
                idx_n = names.index(cur_s) if cur_s in names else 0
                nxt_s = names[min(idx_n + 1, len(names) - 1)]
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                eta_s = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                run("UPDATE drivers SET status='Verified at Gate', current_sector=?, next_checkpoint=?, expected_eta=?, last_checkin=? WHERE id=?",
                    (cur_s, nxt_s, eta_s, now_s, sel_d["id"]))
                st.success(f"Scanned at {cur_s}! Next ETA: {nxt_s}")
                st.rerun()
            if b_halt.button("🛡️ Halt at Safe Haven", use_container_width=True):
                run("UPDATE drivers SET status='Halted at Safe Haven (Prevented)' WHERE id=?", (sel_d["id"],))
                st.info("Vehicle marked safely halted at rest area.")
                st.rerun()

elif nav_choice == "Highway Map & Safe Routes":
    st.subheader("Alternative Safe Routes & Roadside Emergency Facilities")
    c_opt, c_map = st.columns([1.15, 2.85], gap="medium")

    with c_opt:
        map_route = st.selectbox("Select Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        w_cache, _, _ = get_corridor_weather(map_route)
        m_score, m_tier, m_color, m_bg, m_worst = compute_corridor_overall_risk(map_route, w_cache)

        st.markdown(f"""
        <div style="background:{m_bg};border:1px solid {m_color};border-radius:12px;padding:12px;margin-bottom:10px;">
          <div style="font-size:10px;font-weight:800;color:{m_color};">CORRIDOR RISK RATING: {m_tier} ({m_score}/10)</div>
          <div style="font-size:12px;font-weight:700;color:#f8fafc;margin-top:4px;">Verified Alternative Safe Route:</div>
          <div style="font-size:11px;color:#5eead4;margin-top:2px;">{ROUTES_DATA[map_route]['alt_route']}</div>
          <div style="font-size:10px;color:#cbd5e1;margin-top:4px;">{ROUTES_DATA[map_route]['alt_reason']}</div>
        </div>
        """, unsafe_allow_html=True)

        show_fac = st.checkbox("Show Hospitals, Fuel, Workshops & Safe Havens", value=True)
        show_all_fac = st.checkbox("Show Facilities Across All Corridors", value=False)
        fac_filter = st.selectbox("Filter Facility Type", ["All Types", "Hospital / Trauma", "Safe Rest Area", "Petrol / Fuel", "Repair Workshop"])

        st.markdown("**Nearby Verified Facilities**")
        filtered_facs = [
            f for f in NEARBY_FACILITIES
            if (show_all_fac or f["route"] == map_route)
            and (fac_filter == "All Types" or f["type"] == fac_filter)
        ]
        for fc in filtered_facs:
            st.markdown(f"""
            <div class="notif-item safe">
              <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:800;">
                <span style="color:#f8fafc;">{fc['name']}</span>
                <span style="color:#38bdf8;">{fc['type']}</span>
              </div>
              <div style="font-size:11px;color:#2dd4bf;margin-top:2px;">Sector: {fc['sector']} • 📞 {fc['phone']}</div>
              <div style="font-size:10px;color:#94a3b8;">{fc['notes']}</div>
            </div>
            """, unsafe_allow_html=True)

    with c_map:
        render_balochistan_map(
            map_route,
            w_cache,
            road_lookup,
            {"highways": True, "weather_radar": True, "checkpoints": True, "facilities": show_fac, "all_facilities": show_all_fac},
            sos_list=active_sos_global,
            facilities_list=filtered_facs
        )

elif nav_choice == "Multilingual Alert & Voice":
    st.subheader("Multilingual Emergency & Preventive Alerts (Urdu • English • Pashto • Balochi)")
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")

    c_left, c_right = st.columns([1.15, 1.35], gap="large")
    with c_left:
        target_mode = st.radio("Target Audience", ["All Drivers on Corridor", "Individual Registered Driver"], horizontal=True)
        al_route = st.selectbox("Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        al_area = st.selectbox("Checkpoint / Sector", [p["name"] for p in ROUTES_DATA[al_route]["points"]])
        al_lang = st.selectbox("Broadcast Language (4 Languages)", LANGUAGES)
        al_channel = st.multiselect("Dispatch Channels", ["SMS Gateway", "Automated Voice Call (IVR)", "Checkpoint Display"], default=["SMS Gateway", "Automated Voice Call (IVR)"])

        sel_driver_id = None
        if target_mode == "Individual Registered Driver":
            if drivers:
                d_opts = {f"{d.get('driver_code')} • {d['name']} ({d['phone']})": d for d in drivers}
                chosen_d = d_opts[st.selectbox("Select Driver", list(d_opts.keys()))]
                sel_driver_id = chosen_d["id"]
            else:
                st.warning("No registered drivers found.")

    with c_right:
        w_cache, _, _ = get_corridor_weather(al_route)
        cur_w = w_cache.get(al_area, {})
        has_w = cur_w is not None and cur_w.get("weather_code") is not None
        w_en, w_ur, _, _ = weather_info(cur_w.get("weather_code")) if has_w else ("Clear Sky", "صاف موسم", "", 1)
        road_st = road_lookup.get((al_route, al_area), {}).get("status", "Open (Verified)")

        msg_body, travel_guidance = generate_multilingual_alert(al_area, al_route, w_en, w_ur, road_st, al_lang)
        edited_msg = st.text_area(f"{al_lang} Alert Message Preview", value=msg_body, height=110)

        box_cls = "ltr-box" if al_lang == "English" else "urdu-box"
        st.markdown(f'<div class="{box_cls}">{edited_msg}</div>', unsafe_allow_html=True)
        st.info(f"**Preventive Travel Guidance:** {travel_guidance}")

        spoken_preview_text, _ = to_phonetic_tts_script(edited_msg, al_lang)
        mp3_bytes = synthesize_voice_mp3(edited_msg, al_lang)

        st.markdown(f"**🔊 Automated IVR Voice Call Preview ({al_lang} — Full Message Audio)**")
        if mp3_bytes:
            st.audio(mp3_bytes, format="audio/mp3")
        else:
            st.caption("Using browser speech synthesizer.")

        safe_speech_text = json.dumps(spoken_preview_text).replace("</", "<\\/")
        speech_lang_code = "en-US" if al_lang == "English" else ("ps-AF" if al_lang == "Pashto" else "ur-PK")
        components.html(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:4px 0 10px 0;">
          <button onclick="playAlertVoice()" style="background:#0ea5e9;color:#fff;border:none;padding:8px 15px;border-radius:8px;font-weight:700;cursor:pointer;font-family:Inter,sans-serif;font-size:12px;">
            ▶️ Speak Full {al_lang} Text (Browser Voice)
          </button>
          <button onclick="stopAlertVoice()" style="background:#1e293b;color:#cbd5e1;border:1px solid #334155;padding:8px 13px;border-radius:8px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif;font-size:12px;">
            ⏹ Stop
          </button>
          <span id="vstat" style="font-size:12px;color:#94a3b8;font-family:Inter,sans-serif;">Ready</span>
        </div>
        <script>
          let stopRequested = false;
          function stopAlertVoice() {{
            stopRequested = true;
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            document.getElementById('vstat').innerText = 'Stopped.';
          }}
          function pickBestVoice(voices, preferredLang) {{
            if (!voices || !voices.length) return null;
            const isNatural = v => /natural|neural|online|google|microsoft|aria|jenny|uzma|asad|salman|gul/i.test(v.name);
            if (preferredLang.startsWith('en')) {{
              return (
                voices.find(v => v.lang.toLowerCase().startsWith('en') && isNatural(v)) ||
                voices.find(v => v.lang.toLowerCase().startsWith('en')) ||
                voices[0]
              );
            }}
            const langMatches = voices.filter(v =>
              v.lang.toLowerCase() === preferredLang.toLowerCase() ||
              v.lang.toLowerCase().startsWith('ur') ||
              v.lang.toLowerCase().startsWith('ps') ||
              v.lang.toLowerCase().startsWith('hi')
            );
            return langMatches.find(isNatural) || langMatches[0] || voices[0];
          }}
          function splitIntoSentences(txt) {{
            return txt.split(/(?<=[۔\\.!؟\\?])\\s+|\\n+/).map(s => s.trim()).filter(Boolean);
          }}
          function playAlertVoice() {{
            if (!('speechSynthesis' in window)) return;
            stopRequested = false;
            window.speechSynthesis.cancel();
            const chunks = splitIntoSentences({safe_speech_text});
            const chosenVoice = pickBestVoice(window.speechSynthesis.getVoices(), '{speech_lang_code}');
            let idx = 0;
            function speakNext() {{
              if (stopRequested || idx >= chunks.length) {{
                if (!stopRequested) document.getElementById('vstat').innerText = 'Completed full {al_lang} broadcast.';
                return;
              }}
              const utter = new SpeechSynthesisUtterance(chunks[idx]);
              if (chosenVoice) {{ utter.voice = chosenVoice; utter.lang = chosenVoice.lang; }}
              else {{ utter.lang = '{speech_lang_code}'; }}
              utter.rate = 0.88;
              utter.onstart = () => document.getElementById('vstat').innerText = `Speaking part ${{idx + 1}}/${{chunks.length}} ({al_lang})...`;
              utter.onend = () => {{ idx += 1; speakNext(); }};
              utter.onerror = () => {{ idx += 1; speakNext(); }};
              window.speechSynthesis.speak(utter);
            }}
            speakNext();
          }}
        </script>
        """, height=46)

        if st.button("Dispatch Official Alert Now", use_container_width=True):
            if not edited_msg.strip():
                st.error("Alert message cannot be empty.")
            elif target_mode == "Individual Registered Driver" and sel_driver_id is None:
                st.error("Please select a valid individual driver.")
            else:
                ch_str = ", ".join(al_channel) if al_channel else "SMS Gateway"
                sev = "Emergency" if "Closed" in road_st else ("Warning" if "Restricted" in road_st else "Advisory")
                run(
                    "INSERT INTO alerts(driver_id,route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (sel_driver_id, al_route, al_lang, sev, edited_msg.strip(), ch_str, "Dispatched & Logged", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                st.success(f"Alert dispatched in {al_lang} via {ch_str}!")

elif nav_choice == "Road Clearance & Logs":
    st.subheader("Road Clearance Control & Provincial Dispatch Logs")
    all_roads = rows("SELECT * FROM road_status ORDER BY route, id")
    seg_map = {f"{r['route']}  |  {r['area']}  ({r['status']})": r for r in all_roads}

    c1, c2 = st.columns([1.1, 1.5], gap="large")
    with c1:
        if seg_map:
            seg = seg_map[st.selectbox("Select Highway Segment", list(seg_map.keys()))]
            with st.form("clearance_form"):
                new_st = st.selectbox("Official Road Status", ROAD_STATUSES, index=ROAD_STATUSES.index(seg["status"]) if seg["status"] in ROAD_STATUSES else 0)
                new_risk = st.slider("Operator Risk Override (1=Low, 10=Severe)", 1, 10, int(seg.get("risk_score") or 3))
                new_officer = st.text_input("Verifying Authority", value=seg.get("verified_by") or current_user["full_name"])
                new_note = st.text_area("Official Directive / Reason", value=seg.get("authority_note") or "", height=85)
                if st.form_submit_button("Verify & Publish Status", use_container_width=True):
                    if new_officer.strip() and new_note.strip():
                        run(
                            "UPDATE road_status SET status=?, risk_score=?, verified_by=?, authority_note=?, updated_at=? WHERE id=?",
                            (new_st, new_risk, new_officer.strip(), new_note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M"), seg["id"])
                        )
                        st.success("Road clearance updated across live map and risk calculator.")
                        st.rerun()
                    else:
                        st.error("Authority and directive are required.")

    with c2:
        st.markdown("**Provincial Highway Clearance Matrix**")
        if all_roads:
            df_roads = pd.DataFrame(all_roads)[["route", "area", "status", "risk_score", "verified_by", "updated_at"]]
            df_roads.columns = ["Corridor", "Sector", "Clearance Status", "Risk (1-10)", "Verified By", "Updated"]
            st.dataframe(df_roads, use_container_width=True, hide_index=True, height=280)

    st.markdown("### Provincial Alert Dispatch History")
    logs = rows("""
        SELECT alerts.id, alerts.created_at, alerts.route, alerts.language, alerts.severity,
               COALESCE(drivers.name, 'Corridor Broadcast') AS recipient,
               alerts.channel, alerts.status, alerts.message
        FROM alerts
        LEFT JOIN drivers ON drivers.id = alerts.driver_id
        ORDER BY alerts.id DESC
    """)
    if logs:
        df_logs = pd.DataFrame(logs)
        df_logs.columns = ["ID", "Timestamp", "Corridor", "Language", "Severity", "Recipient", "Channels", "Status", "Message"]
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
