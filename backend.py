from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = "e0cad9070cfc48898499f4c78c69141d"

NAZVY_LIG = {
    "PL": "Premier League (Anglicko)",
    "BL1": "Bundesliga (Nemecko)",
    "PD": "La Liga (Španielsko)",
    "FL1": "Ligue 1 (Francúzsko)",
    "SA": "Serie A (Taliansko)",
    "CL": "Liga Majstrov"
}

# 🏆 Ručne pridané trofeje pre najznámejšie kluby (keďže API ich nemá)
TROFEJE_KLUBOV = {
    "Real Madrid CF": "15x Liga majstrov, 36x La Liga, 20x Copa del Rey",
    "FC Barcelona": "5x Liga majstrov, 27x La Liga, 31x Copa del Rey",
    "FC Bayern München": "6x Liga majstrov, 33x Bundesliga, 20x Nemecký pohár",
    "Manchester City FC": "1x Liga majstrov, 10x Premier League, 7x FA Cup",
    "Liverpool FC": "6x Liga majstrov, 19x Premier League, 8x FA Cup",
    "Manchester United FC": "3x Liga majstrov, 20x Premier League, 13x FA Cup",
    "Arsenal FC": "13x Premier League, 14x FA Cup",
    "Paris Saint-Germain FC": "12x Ligue 1, 15x Francúzsky pohár",
    "Juventus FC": "2x Liga majstrov, 36x Serie A, 15x Taliansky pohár",
    "FC Internazionale Milano": "3x Liga majstrov, 20x Serie A, 9x Taliansky pohár",
    "AC Milan": "7x Liga majstrov, 19x Serie A, 5x Taliansky pohár",
    "Borussia Dortmund": "1x Liga majstrov, 8x Bundesliga, 5x Nemecký pohár",
    "Atlético Madrid": "11x La Liga, 10x Copa del Rey, 3x Európska liga"
}

def stiahni_realne_zapasy(vybrany_datum):
    url = f"https://api.football-data.org/v4/matches?dateFrom={vybrany_datum}&dateTo={vybrany_datum}"
    headers = { "X-Auth-Token": API_KEY }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200: return []
        data = response.json()
        vsetky_zapasy = data.get("matches", [])
        spracovane_zapasy = []
        for z in vsetky_zapasy:
            status = z.get("status")
            if status in ["IN_PLAY", "PAUSED"]:
                nas_status = "LIVE"; minuta = "Živo"
            elif status == "FINISHED":
                nas_status = "FINISHED"; minuta = "Koniec"
            else:
                nas_status = "SCHEDULED"
                utc_time = z.get("utcDate", "")
                minuta = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M") if utc_time else "Plán"

            goals_list = []
            for goal in z.get("goals", []):
                minute = goal.get("minute")
                p_name = goal.get("player", {}).get("name")
                t_name = goal.get("team", {}).get("name")
                goals_list.append(f"⚽ {minute}' {p_name} ({t_name})")
            
            if not goals_list: goals_list = ["Žiadne góly alebo API nedodalo detaily"]

            spracovane_zapasy.append({
                "id": z.get("id"),
                "homeTeam": {"id": z.get("homeTeam", {}).get("id"), "name": z.get("homeTeam", {}).get("name", "Neznámy"), "logo": "⚽"},
                "awayTeam": {"id": z.get("awayTeam", {}).get("id"), "name": z.get("awayTeam", {}).get("name", "Neznámy"), "logo": "⚽"},
                "score": {"home": z.get("score", {}).get("fullTime", {}).get("home"), "away": z.get("score", {}).get("fullTime", {}).get("away")},
                "status": nas_status, "minute": minuta, "league": z.get("competition", {}).get("name", "Ostatné ligy"),
                "details": {"venue": z.get("venue", "Neznámy štadión"), "referee": z.get("referees", [{}])[0].get("name", "Neznámy") if z.get("referees") else "Neznámy", "goals": goals_list}
            })
        return spracovane_zapasy
    except: return []

@app.route("/")
def home():
    vybrany_datum = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    dni_menu = []
    for i in range(5):
        den = datetime.now() + timedelta(days=i)
        dni_menu.append({"datum_url": den.strftime("%Y-%m-%d"), "pekny_nazov": "Dnes" if i == 0 else "Zajtra" if i == 1 else den.strftime("%d.%m. (%a)")})
    zapasy = stiahni_realne_zapasy(vybrany_datum)
    povedz_datum = datetime.strptime(vybrany_datum, "%Y-%m-%d").strftime("%d.%m.%Y")
    return render_template("index.html", zápasy=zapasy, dni_menu=dni_menu, aktualny_datum=vybrany_datum, povedz_datum=povedz_datum)

@app.route("/api/zapasy")
def get_api_zapasy():
    vybrany_datum = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    return jsonify(stiahni_realne_zapasy(vybrany_datum))

@app.route("/api/zapas/<int:zapas_id>")
def ziskaj_detail_zapasu(zapas_id):
    url = f"https://api.football-data.org/v4/matches/{zapas_id}"
    headers = { "X-Auth-Token": API_KEY }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            z = response.json()
            goals_list = [f"⚽ {g.get('minute')}' {g.get('player', {}).get('name')} ({g.get('team', {}).get('name')})" for g in z.get("goals", [])]
            return jsonify({"venue": z.get("venue", "Neznámy štadión"), "referee": z.get("referees", [{}])[0].get("name", "Neznámy") if z.get("referees") else "Neznámy", "goals": goals_list if goals_list else ["Zápas neskončil gólom alebo detaily nie sú dostupné."]})
    except: pass
    return jsonify({"venue": "Neznámy štadión", "referee": "Neznámy", "goals": ["Chyba rozhrania API"]})

# 🔥 NOVÁ ROUTE PRE PROFIL TÍMU (ŠTADIÓN, SÚPISKA, TROFEJE)
@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    url = f"https://api.football-data.org/v4/teams/{tim_id}"
    headers = { "X-Auth-Token": API_KEY }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            nazov_klubu = data.get("name", "Neznámy klub")
            
            # Vytiahneme trofeje z nášho slovníka, alebo dáme univerzálny text
            trofeje = TROFEJE_KLUBOV.get(nazov_klubu, "Klub má na konte domáce tituly a pohárové úspechy (detaily v free API nedostupné).")
            
            return render_template("tim.html", tim=data, trofeje=trofeje)
    except Exception as e:
        print(e)
        
    return "Chyba pri načítaní profilu tímu. Skontrolujte limit API požiadaviek.", 404

@app.route("/tabulka")
@app.route("/tabulka/<liga_kod>")
def tabulka(liga_kod="PL"):
    if liga_kod not in NAZVY_LIG: liga_kod = "PL"
    url_standings = f"https://api.football-data.org/v4/competitions/{liga_kod}/standings"
    headers = { "X-Auth-Token": API_KEY }
    stojisko = []
    vyradovacie_zapasy = []
    
    try:
        response = requests.get(url_standings, headers=headers)
        if response.status_code == 200:
            stojisko = response.json().get("standings", [{}])[0].get("table", [])
    except: pass

    if liga_kod == "CL":
        url_matches = f"https://api.football-data.org/v4/competitions/CL/matches"
        try:
            res_matches = requests.get(url_matches, headers=headers)
            if res_matches.status_code == 200:
                vsetky_cl_zapasy = res_matches.json().get("matches", [])
                fazy_playoff = ["PLAY_OFF_ROUND", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
                preklady_faz = {"PLAY_OFF_ROUND": "Play-off o osemfinále", "ROUND_OF_16": "Osemfinále", "QUARTER_FINALS": "Štvrťfinále", "SEMI_FINALS": "Semifinále", "FINAL": "🏆 FINÁLE"}
                for zm in vsetky_cl_zapasy:
                    if zm.get("stage") in fazy_playoff:
                        vyradovacie_zapasy.append({
                            "id": zm.get("id"), "faza_sk": preklady_faz.get(zm.get("stage"), zm.get("stage")),
                            "homeTeam": zm.get("homeTeam", {}).get("name", "Neznámy"), "awayTeam": zm.get("awayTeam", {}).get("name", "Neznámy"),
                            "score_home": zm.get("score", {}).get("fullTime", {}).get("home"), "score_away": zm.get("score", {}).get("fullTime", {}).get("away"), "status": zm.get("status")
                        })
        except: pass
        return render_template("liga_majstrov.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod, vyradovacie_zapasy=vyradovacie_zapasy)
        
    return render_template("tabulka.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod)

if __name__ == "__main__":
    app.run(debug=True)