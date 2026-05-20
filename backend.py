import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import requests
from supisky import RUČNÉ_SÚPISKY 

app = Flask(__name__)

# Konfigurácia
API_KEY = "0353c89659b9409bbba986dc1555a1d7"
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
LEAGUES = {"PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga", "SA": "Serie A", "FL1": "Ligue 1", "CL": "Champions League"}

cache = {}

def get_cached_data(cache_key, url):
    if cache_key in cache:
        data, timestamp = cache[cache_key]
        if datetime.now() - timestamp < timedelta(minutes=15):
            return data
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache[cache_key] = (data, datetime.now())
            return data
    except: pass
    return None

def preloz_fazu_ucl(stage):
    return {"PRELIMINARY_ROUND": "Predkolo", "PLAYOFF_ROUND": "Play-off", "LEAGUE_STAGE": "Ligová fáza", "ROUND_OF_16": "Osemfinále", "QUARTER_FINALS": "Štvrťfinále", "SEMI_FINALS": "Semifinále", "FINAL": "Finále"}.get(stage, stage)

@app.route("/")
def index():
    datum = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    data = get_cached_data(f"matches_{datum}", f"{BASE_URL}/matches?date={datum}")
    zápasy = []
    if data and "matches" in data:
        for m in data["matches"]:
            if m["competition"]["code"] in LEAGUES:
                zápasy.append({
                    "id": m["id"], "league": LEAGUES[m["competition"]["code"]],
                    "homeTeam": m["homeTeam"], "awayTeam": m["awayTeam"],
                    "score": m["score"]["fullTime"], "status": m["status"], "minute": m.get("minute")
                })
    return render_template("index.html", zápasy=zápasy, aktualny_datum=datum, povedz_datum=datum)

@app.route("/tabulka/<liga_kod>")
def tabulka_ligy(liga_kod):
    if liga_kod == "CL":
        data = get_cached_data("standings_CL", f"{BASE_URL}/competitions/CL/standings")
        matches = get_cached_data("matches_CL", f"{BASE_URL}/competitions/CL/matches")
        tabulka = data["standings"][0]["table"] if data else []
        vyradovacie = []
        if matches and "matches" in matches:
            vyradovacie = [{"id": m["id"], "faza_sk": preloz_fazu_ucl(m["stage"]), "homeTeam": m["homeTeam"], "awayTeam": m["awayTeam"], "score_home": m["score"]["fullTime"]["home"], "score_away": m["score"]["fullTime"]["away"]} for m in matches["matches"] if m["stage"] != "LEAGUE_STAGE"]
        return render_template("liga_majstrov.html", tabulka=tabulka, vyradovacie_zapasy=vyradovacie)
    
    data = get_cached_data(f"standings_{liga_kod}", f"{BASE_URL}/competitions/{liga_kod}/standings")
    return render_template("tabulka.html", liga=LEAGUES.get(liga_kod), tabulka=data["standings"][0]["table"] if data else [])

@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    tim_data = get_cached_data(f"team_{tim_id}", f"{BASE_URL}/teams/{tim_id}") or {}
    trener = "Neznámy"
    if tim_id in RUČNÉ_SÚPISKY:
        tim_data["squad"] = RUČNÉ_SÚPISKY[tim_id].get("players", [])
        trener = RUČNÉ_SÚPISKY[tim_id].get("coach", {}).get("name", "Neznámy")
    
    matches = get_cached_data(f"team_matches_{tim_id}", f"{BASE_URL}/teams/{tim_id}/matches?status=FINISHED&limit=5")
    posledne_zapasy = [f"{m['utcDate'][:10]}: {m['homeTeam']['name']} {m['score']['fullTime']['home']}:{m['score']['fullTime']['away']} {m['awayTeam']['name']}" for m in matches["matches"]] if matches else []
    
    return render_template("tim.html", tim=tim_data, trener=trener, posledne_zapasy=posledne_zapasy, trofeje="Aktuálne dáta z API")

@app.route("/api/zapas/<int:zapas_id>")
def api_zapas(zapas_id):
    data = get_cached_data(f"match_{zapas_id}", f"{BASE_URL}/matches/{zapas_id}")
    if not data: return jsonify({"venue": "Nedostupné", "referee": "Neznámy"})
    return jsonify({
        "venue": data.get("venue", "Neznámy"),
        "referee": data.get("referees", [{}])[0].get("name", "Neznámy") if data.get("referees") else "Neznámy",
        "goals": [f"{g['minute']}' {g['scorer']['name']}" for g in data.get("goals", [])]
    })

if __name__ == "__main__":
    app.run(debug=True)