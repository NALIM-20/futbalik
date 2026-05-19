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

def stiahni_realne_zapasy(vybrany_datum):
    url = f"https://api.football-data.org/v4/matches?dateFrom={vybrany_datum}&dateTo={vybrany_datum}"
    headers = { "X-Auth-Token": API_KEY }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return []
            
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
            
            if not goals_list: 
                goals_list = ["Žiadne góly alebo API nedodalo detaily"]

            spracovane_zapasy.append({
                "id": z.get("id"),
                "homeTeam": {"name": z.get("homeTeam", {}).get("name", "Neznámy"), "logo": "⚽"},
                "awayTeam": {"name": z.get("awayTeam", {}).get("name", "Neznámy"), "logo": "⚽"},
                "score": {
                    "home": z.get("score", {}).get("fullTime", {}).get("home"),
                    "away": z.get("score", {}).get("fullTime", {}).get("away")
                },
                "status": nas_status,
                "minute": minuta,
                "league": z.get("competition", {}).get("name", "Ostatné ligy"),
                "details": {
                    "venue": z.get("venue", "Neznámy štadión"),
                    "referee": z.get("referees", [{}])[0].get("name", "Neznámy rozhodca") if z.get("referees") else "Neznámy rozhodca",
                    "goals": goals_list
                }
            })
            
        return spracovane_zapasy
    except Exception as e:
        print(f"Chyba pri sťahovaní zápasov: {e}")
        return []

@app.route("/")
def home():
    vybrany_datum = request.args.get("date")
    dnes_str = datetime.now().strftime("%Y-%m-%d")
    
    if not vybrany_datum:
        vybrany_datum = dnes_str

    dni_menu = []
    for i in range(5):
        den = datetime.now() + timedelta(days=i)
        dni_menu.append({
            "datum_url": den.strftime("%Y-%m-%d"),
            "pekny_nazov": "Dnes" if i == 0 else "Zajtra" if i == 1 else den.strftime("%d.%m. (%a)")
        })

    zapasy = stiahni_realne_zapasy(vybrany_datum)
    povedz_datum = datetime.strptime(vybrany_datum, "%Y-%m-%d").strftime("%d.%m.%Y")

    return render_template("index.html", zápasy=zapasy, dni_menu=dni_menu, aktualny_datum=vybrany_datum, povedz_datum=povedz_datum)

@app.route("/api/zapasy")
def get_api_zapasy():
    vybrany_datum = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    zapasy = stiahni_realne_zapasy(vybrany_datum)
    return jsonify(zapasy)

@app.route("/tabulka")
@app.route("/tabulka/<liga_kod>")
def tabulka(liga_kod="PL"):
    if liga_kod not in NAZVY_LIG:
        liga_kod = "PL"
        
    url_standings = f"https://api.football-data.org/v4/competitions/{liga_kod}/standings"
    headers = { "X-Auth-Token": API_KEY }
    stojisko = []
    vyradovacie_zapasy = []
    
    try:
        response = requests.get(url_standings, headers=headers)
        if response.status_code == 200:
            data = response.json()
            standings_data = data.get("standings", [])
            if standings_data:
                stojisko = standings_data[0].get("table", [])
    except:
        pass

    if not stojisko:
        for i in range(1, 18):
            stojisko.append({
                "position": i,
                "team": {"name": f"Ligový Tím {i} ({liga_kod})"},
                "playedGames": 22, "won": 10, "draw": 6, "lost": 6, "points": 36
            })

    if liga_kod == "CL":
        url_matches = f"https://api.football-data.org/v4/competitions/CL/matches"
        try:
            res_matches = requests.get(url_matches, headers=headers)
            if res_matches.status_code == 200:
                vsetky_cl_zapasy = res_matches.json().get("matches", [])
                fazy_playoff = ["PLAY_OFF_ROUND", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
                
                for zm in vsetky_cl_zapasy:
                    if zm.get("stage") in fazy_playoff:
                        preklady_faz = {
                            "PLAY_OFF_ROUND": "Play-off o osemfinále",
                            "ROUND_OF_16": "Osemfinále",
                            "QUARTER_FINALS": "Štvrťfinále",
                            "SEMI_FINALS": "Semifinále",
                            "FINAL": "🏆 FINÁLE"
                        }
                        
                        # Spracovanie strelcov gólov pre Ligu majstrov
                        goals_list = []
                        for goal in zm.get("goals", []):
                            minute = goal.get("minute")
                            p_name = goal.get("player", {}).get("name")
                            t_name = goal.get("team", {}).get("name")
                            goals_list.append(f"⚽ {minute}' {p_name} ({t_name})")
                        
                        if not goals_list:
                            goals_list = ["Žiadne góly alebo zápas ešte nezačal"]

                        vyradovacie_zapasy.append({
                            "id": zm.get("id"),
                            "faza_sk": preklady_faz.get(zm.get("stage"), zm.get("stage")),
                            "homeTeam": zm.get("homeTeam", {}).get("name", "Neznámy"),
                            "awayTeam": zm.get("awayTeam", {}).get("name", "Neznámy"),
                            "score_home": zm.get("score", {}).get("fullTime", {}).get("home"),
                            "score_away": zm.get("score", {}).get("fullTime", {}).get("away"),
                            "status": zm.get("status"),
                            "venue": zm.get("venue", "Neznámy štadión"),
                            "referee": zm.get("referees", [{}])[0].get("name", "Neznámy rozhodca") if zm.get("referees") else "Neznámy rozhodca",
                            "goals": goals_list
                        })
        except Exception as e:
            print(f"Chyba pri sťahovaní CL zápasov: {e}")

        return render_template("liga_majstrov.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod, vyradovacie_zapasy=vyradovacie_zapasy)
        
    return render_template("tabulka.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod)

if __name__ == "__main__":
    app.run(debug=True)