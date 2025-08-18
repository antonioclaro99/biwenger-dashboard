import requests
import pandas as pd
from datetime import datetime

EMAIL = None
PASSWORD = None
LEAGUE_ID = None
USER_ID = None

LOGIN_URL = "https://biwenger.as.com/api/v2/auth/login"

# ==============================
# HEADERS BASE
# ==============================
HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://biwenger.as.com/",
    "Origin": "https://biwenger.as.com",
}

# ==============================
# FUNCIONES
# ==============================
def get_biwenger_token(email: str, password: str):
    user = {"email": email, "password": password}
    headers = {"Content-Type": "application/json"}
    response = requests.post(LOGIN_URL, headers=headers, json=user)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("token")
    return None


def get_league_data(league_id, token, user_id):
    url = f"https://biwenger.as.com/api/v2/league?include=all,-lastAccess&fields=*,standings,tournaments,group,settings(description)"
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}", "X-League": league_id, "X-User": user_id}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()["data"]

    # Liga
    df_liga = pd.DataFrame([{
        "id": data.get("id"),
        "nombre": data.get("name"),
        "tipo": data.get("type"),
        "modo": data.get("mode"),
        "competicion": data.get("competition"),
        "icono": f"https://cdn.biwenger.com/{data.get('icon')}" if data.get("icon") else None,
        "portada": f"https://cdn.biwenger.com/{data.get('cover')}" if data.get("cover") else None,
        "creada": datetime.fromtimestamp(data["created"]) if data.get("created") else None,
        "descripcion": data.get("settings", {}).get("description", "")
    }])

    # Usuarios
    standings = data.get("standings", [])
    df_users = pd.DataFrame([{
        "id": u.get("id"),
        "nombre": u.get("name"),
        "imagen": (
            u.get("icon") if u.get("icon", "").startswith("http")
            else (f"https://cdn.biwenger.com/{u.get('icon')}" if u.get("icon") else "https://cdn.biwenger.com/img/user.svg")
        ),
        "puntos": u.get("points"),
        "valor_equipo": u.get("teamValue"),
        "variacion_valor": u.get("teamValueInc"),
        "tamano_equipo": u.get("teamSize"),
        "rol": u.get("role"),
        "posicion": u.get("position")
    } for u in standings])

    return df_liga, df_users


def get_public_players():
    url = "https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=es&score=2"
    resp = requests.get(url, headers=HEADERS_BASE)
    resp.raise_for_status()
    players = resp.json()["data"]["players"]

    position_map = {1: "Portero", 2: "Defensa", 3: "Centrocampista", 4: "Delantero"}
    teams_data = resp.json()["data"]["teams"]

    df_teams = pd.DataFrame([{
        "teamID": int(team["id"]),
        "equipo": team["name"],
        "slug_equipo": team["slug"]
    } for team in teams_data.values()])

    df_players_public = pd.DataFrame([{
        "id": p.get("id"),
        "slug": p.get("slug"),
        "nombre": p.get("name"),
        "teamID": p.get("teamID"),
        "posicion": position_map.get(p.get("position")),
        "puntos": p.get("points"),
        "valor_actual": p.get("price"),
        "variacion_diaria": p.get("priceIncrement"),
        "enlace_imagen": f"https://cdn.biwenger.com/cdn-cgi/image/f=avif/i/p/{p.get('id')}.png"
    } for p in players.values()])

    df_players_public["teamID"] = df_players_public["teamID"].astype("Int64")
    df_teams["teamID"] = df_teams["teamID"].astype("Int64")

    return df_players_public.merge(df_teams, on="teamID", how="inner")


def get_user_players(x_user, user_id, league_id, token):
    url = f"https://biwenger.as.com/api/v2/user/{user_id}?fields=players(*,fitness,team,owner)"
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}", "X-League": league_id, "X-User": x_user}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()["data"]

    players = data.get("players", [])

    df_players_owned = pd.DataFrame([
        {
            "id": p.get("id"),
            "propietario_id": user_id,
            "valor_clausula": int((p.get("owner") or {}).get("clause") or 0),
            "fecha_desbloqueo": (
                datetime.fromtimestamp((p.get("owner") or {}).get("clauseLockedUntil"))
                if (p.get("owner") or {}).get("clauseLockedUntil") else None
            ),
            "precio_compra": int((p.get("owner") or {}).get("price") or 0),
            "fecha_compra": (
                datetime.fromtimestamp((p.get("owner") or {}).get("date"))
                if (p.get("owner") or {}).get("date") else None
            ),
            "loan_to": (
                (p.get("owner") or {}).get("loan", {}).get("user", {}).get("name")
                if (p.get("owner") or {}).get("loan") else None
            ),
            "loan_duration": (
                (p.get("owner") or {}).get("loan", {}).get("rounds")
                if (p.get("owner") or {}).get("loan") else None
            )
        }
        for p in players
        if not ((p.get("owner") or {}).get("loan") and (p["owner"]["loan"].get("type") == "in"))
    ])

    return df_players_owned


def obtener_clausulas_ejecutadas(league_id, user_id, token, limit=8) -> pd.DataFrame:
    url = f"https://biwenger.as.com/api/v2/league/{league_id}/board?type=clauses&limit={limit}"
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}", "X-League": league_id, "X-User": user_id}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()["data"]

    registros = []
    for entry in data:
        for content in entry.get("content", []):
            registros.append({
                "player_id": content.get("player"),
                "from_id": content.get("from", {}).get("id"),
                "from_name": content.get("from", {}).get("name"),
                "to_id": content.get("to", {}).get("id"),
                "to_name": content.get("to", {}).get("name"),
                "to_icon": content.get("to", {}).get("icon"),
                "amount": content.get("amount"),
                "clause_type": content.get("type"),
                "entry_type": entry.get("type"),
                "entry_title": entry.get("title"),
                "entry_date": entry.get("date"),
                "entry_fixed": entry.get("fixed"),
                "entry_author": entry.get("author")
            })

    df_clausulas = pd.DataFrame(registros)

    int_columns = ["player_id", "from_id", "to_id", "amount"]
    for col in int_columns:
        if col in df_clausulas:
            df_clausulas[col] = pd.to_numeric(df_clausulas[col], errors="coerce").astype("Int64")

    df_clausulas["entry_date"] = pd.to_datetime(df_clausulas["entry_date"], unit="s")

    return df_clausulas
