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

# 🛡️ Záchranná reálna súpiska pre Real Madrid (keďže API posiela bludy)
REAL_MADRID_SQUAD_FIX = [
    {"name": "Thibaut Courtois", "position": "Goalkeeper", "nationality": "Belgium"},
    {"name": "Andriy Lunin", "position": "Goalkeeper", "nationality": "Ukraine"},
    {"name": "Éder Militão", "position": "Defender", "nationality": "Brazil"},
    {"name": "Antonio Rüdiger", "position": "Defender", "nationality": "Germany"},
    {"name": "David Alaba", "position": "Defender", "nationality": "Austria"},
    {"name": "Dani Carvajal", "position": "Defender", "nationality": "Spain"},
    {"name": "Ferland Mendy", "position": "Defender", "nationality": "France"},
    {"name": "Fran García", "position": "Defender", "nationality": "Spain"},
    {"name": "Lucas Vázquez", "position": "Defender", "nationality": "Spain"},
    {"name": "Jude Bellingham", "position": "Midfielder", "nationality": "England"},
    {"name": "Federico Valverde", "position": "Midfielder", "nationality": "Uruguay"},
    {"name": "Eduardo Camavinga", "position": "Midfielder", "nationality": "France"},
    {"name": "Aurélien Tchouaméni", "position": "Midfielder", "nationality": "France"},
    {"name": "Luka Modrić", "position": "Midfielder", "nationality": "Croatia"},
    {"name": "Dani Ceballos", "position": "Midfielder", "nationality": "Spain"},
    {"name": "Arda Güler", "position": "Midfielder", "nationality": "Turkey"},
    {"name": "Vinícius Júnior", "position": "Forward", "nationality": "Brazil"},
    {"name": "Kylian Mbappé", "position": "Forward", "nationality": "France"},
    {"name": "Rodrygo", "position": "Forward", "nationality": "Brazil"},
    {"name": "Brahim Díaz", "position": "Forward", "nationality": "Morocco"},
    {"name": "Endrick", "position": "Forward", "nationality": "Brazil"}
]

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
                # 🔥 PRIDANÉ ID TÍMOV PRE KLIKATEĽNOSŤ NA HLAVNEJ STRÁNKE
                "homeTeam": {"id": z.get("homeTeam", {}).get("id"), "name": z.get("homeTeam", {}).get("name", "Neznámy")},
                "awayTeam": {"id": z.get("awayTeam", {}).get("id"), "name": z.get("awayTeam", {}).get("name", "Neznámy")},
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

@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    headers = { "X-Auth-Token": API_KEY }
    url_team = f"https://api.football-data.org/v4/teams/{tim_id}"
    url_matches = f"https://api.football-data.org/v4/teams/{tim_id}/matches?limit=100"
    
    tim_data = {}
    odohrane = []
    naplanovane = []
    trofeje = "Klub má na konte domáce tituly a pohárové úspechy."
    trener = "Neznámy (Nedodané cez API)"

    # Tréneri natvrdo pre top tímy, keďže ich free API vymazalo
    TRENERI = {
        86: "Carlo Ancelotti",      # Real Madrid
        81: "Hansi Flick",          # Barcelona
        65: "Pep Guardiola",        # Manchester City
        64: "Arne Slot",            # Liverpool
        57: "Rúben Amorim",         # Manchester United
        521: "Vincent Kompany",     # Bayern
        524: "Nuri Şahin",          # Dortmund
        98: "Luis Enrique",         # PSG
        109: "Thiago Motta",        # Juventus
        110: "Simone Inzaghi",      # Inter Milan
        113: "Paulo Fonseca",       # AC Milan
        78: "Diego Simeone"         # Atlético Madrid
    }
    
    trener = TRENERI.get(tim_id, trener)

    try:
        res_team = requests.get(url_team, headers=headers)
        if res_team.status_code == 200:
            tim_data = res_team.json()
            nazov_klubu = tim_data.get("name", "")
            trofeje = TROFEJE_KLUBOV.get(nazov_klubu, trofeje)
            
            # 🔥 OPRAVA SÚPISKY PRE REAL MADRID
            if tim_id == 86:
                tim_data["squad"] = REAL_MADRID_SQUAD_FIX
    except Exception as e:
        print(f"Chyba profilu tímu: {e}")

    try:
        res_matches = requests.get(url_matches, headers=headers)
        if res_matches.status_code == 200:
            vsetky_zapasy = res_matches.json().get("matches", [])
            for m in vsetky_zapasy:
                status = m.get("status")
                datum_raw = m.get("utcDate", "")
                pekny_datum = datetime.strptime(datum_raw, "%Y-%m-%dT%H:%M:%SZ").strftime("%d.%m.%Y") if datum_raw else ""
                
                zapas_info = {
                    "datum": pekny_datum,
                    "sutaz": m.get("competition", {}).get("name", "Súťaž"),
                    "homeTeam": m.get("homeTeam", {}).get("name", "Neznámy"),
                    "awayTeam": m.get("awayTeam", {}).get("name", "Neznámy"),
                    "score_home": m.get("score", {}).get("fullTime", {}).get("home"),
                    "score_away": m.get("score", {}).get("fullTime", {}).get("away")
                }
                if status == "FINISHED":
                    odohrane.append(zapas_info)
                else:
                    zapas_info["cas"] = datetime.strptime(datum_raw, "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M") if datum_raw else ""
                    naplanovane.append(zapas_info)
            odohrane.reverse()
    except Exception as e:
        print(f"Chyba zápasov tímu: {e}")

    if not tim_data:
        return "Chyba pri načítaní profilu tímu.", 404

    return render_template(
        "tim.html", 
        tim=tim_data, 
        trofeje=trofeje, 
        trener=trener,
        posledne_zapasy=odohrane[:5], 
        nasledujuce_zapasy=naplanovane[:5]
    )

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
                            # 🔥 PRIDANÉ AJ ID TÍMOV PRE LIGU MAJSTROV
                            "homeTeam": {"id": zm.get("homeTeam", {}).get("id"), "name": zm.get("homeTeam", {}).get("name")},
                            "awayTeam": {"id": zm.get("awayTeam", {}).get("id"), "name": zm.get("awayTeam", {}).get("name")},
                            "score_home": zm.get("score", {}).get("fullTime", {}).get("home"), "score_away": zm.get("score", {}).get("fullTime", {}).get("away"), "status": zm.get("status")
                        })
        except: pass
        return render_template("liga_majstrov.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod, vyradovacie_zapasy=vyradovacie_zapasy)
        
    return render_template("tabulka.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod)

if __name__ == "__main__":
    app.run(debug=True)