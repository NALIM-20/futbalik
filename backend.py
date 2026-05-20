from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
# 🔥 OPRAVENÝ IMPORT: Teraz ťahá dáta priamo z priečinka cez __init__.py
from supisky import RUČNÉ_SÚPISKY

app = Flask(__name__)

API_KEY = "e0cad9070cfc48898499f4c78c69141d"

CACHE_DATA = {}

def ziskaj_z_cache_alebo_api(url, cache_kluc, sekundy_platnosti=300):
    teraz = datetime.now()
    if cache_kluc in CACHE_DATA:
        data_v_pamati, cas_ulozenia = CACHE_DATA[cache_kluc]
        if teraz - cas_ulozenia < timedelta(seconds=sekundy_platnosti):
            print(f"⚡ Načítavam z CACHE: {cache_kluc}")
            return data_v_pamati

    headers = { "X-Auth-Token": API_KEY }
    try:
        print(f"🌐 Volám REÁLNE API: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            json_data = response.json()
            CACHE_DATA[cache_kluc] = (json_data, teraz)
            return json_data
    except Exception as e:
        print(f"Chyba pri volaní API: {e}")
    
    if cache_kluc in CACHE_DATA:
        return CACHE_DATA[cache_kluc][0]
    return None

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

TRENERI = {
    86: "Carlo Ancelotti", 81: "Hansi Flick", 65: "Pep Guardiola", 64: "Arne Slot",
    57: "Rúben Amorim", 521: "Vincent Kompany", 524: "Nuri Şahin", 98: "Luis Enrique",
    109: "Thiago Motta", 110: "Simone Inzaghi", 113: "Paulo Fonseca", 78: "Diego Simeone"
}

def stiahni_realne_zapasy(vybrany_datum):
    url = f"https://api.football-data.org/v4/matches?dateFrom={vybrany_datum}&dateTo={vybrany_datum}"
    data = ziskaj_z_cache_alebo_api(url, f"zapasy_{vybrany_datum}", sekundy_platnosti=60)
    
    if not data: return []
    
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

        goals_list = [f"⚽ {g.get('minute')}' {g.get('player', {}).get('name')} ({g.get('team', {}).get('name')})" for g in z.get("goals", [])]
        if not goals_list: goals_list = ["Žiadne góly alebo API nedodalo detaily"]

        spracovane_zapasy.append({
            "id": z.get("id"),
            "homeTeam": {"id": z.get("homeTeam", {}).get("id"), "name": z.get("homeTeam", {}).get("name", "Neznámy")},
            "awayTeam": {"id": z.get("awayTeam", {}).get("id"), "name": z.get("awayTeam", {}).get("name", "Neznámy")},
            "score": {"home": z.get("score", {}).get("fullTime", {}).get("home"), "away": z.get("score", {}).get("fullTime", {}).get("away")},
            "status": nas_status, "minute": minuta, "league": z.get("competition", {}).get("name", "Ostatné ligy"),
            "details": {"venue": z.get("venue", "Neznámy štadión"), "referee": z.get("referees", [{}])[0].get("name", "Neznámy") if z.get("referees") else "Neznámy", "goals": goals_list}
        })
    return spracovane_zapasy

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
    z = ziskaj_z_cache_alebo_api(url, f"detail_{zapas_id}", sekundy_platnosti=600)
    if z:
        goals_list = [f"⚽ {g.get('minute')}' {g.get('player', {}).get('name')} ({g.get('team', {}).get('name')})" for g in z.get("goals", [])]
        return jsonify({"venue": z.get("venue", "Neznámy štadión"), "referee": z.get("referees", [{}])[0].get("name", "Neznámy") if z.get("referees") else "Neznámy", "goals": goals_list if goals_list else ["Zápas neskončil gólom alebo detaily nie sú dostupné."]})
    return jsonify({"venue": "Neznámy štadión", "referee": "Neznámy", "goals": ["Detaily momentálne nedostupné"]})

@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    url_team = f"https://api.football-data.org/v4/teams/{tim_id}"
    url_matches = f"https://api.football-data.org/v4/teams/{tim_id}/matches?limit=100"
    
    tim_data = ziskaj_z_cache_alebo_api(url_team, f"team_profil_{tim_id}", sekundy_platnosti=900)
    matches_data = ziskaj_z_cache_alebo_api(url_matches, f"team_matches_{tim_id}", sekundy_platnosti=900)

    if not tim_data:
        return "⚠️ API limit bol vyčerpaný. Počkajte 30 sekúnd a obnovte stránku (F5).", 429

    odohrane = []
    naplanovane = []
    nazov_klubu = tim_data.get("name", "")
    trofeje = TROFEJE_KLUBOV.get(nazov_klubu, "Klub má na konte domáce tituly a pohárové úspechy.")
    trener = TRENERI.get(tim_id, "Neznámy (Nedodané cez API)")

    # 🔥 INTELIGENTNÁ KONTROLA STRUKTÚRY: Prispôsobenie tvojmu novému formátu súpisiek
    if tim_id in RUČNÉ_SÚPISKY:
        data_supisky = RUČNÉ_SÚPISKY[tim_id]
        
        # Ak je súpiska slovník a obsahuje kľúč "players" (ako tvoj Manchester City)
        if isinstance(data_supisky, dict) and "players" in data_supisky:
            tim_data["squad"] = data_supisky["players"]
            # Ak si v súbore zadefinoval aj "manager", automaticky prepíšeme meno trénera
            if "manager" in data_supisky:
                trener = data_supisky["manager"].get("name", trener)
        else:
            # Ak je to rovno čistý zoznam hráčov (ako bol pôvodný Real Madrid)
            tim_data["squad"] = data_supisky

    if matches_data:
        vsetky_zapasy = matches_data.get("matches", [])
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
    
    data_standings = ziskaj_z_cache_alebo_api(url_standings, f"tabulka_{liga_kod}", sekundy_platnosti=600)
    stojisko = data_standings.get("standings", [{}])[0].get("table", []) if data_standings else []

    if liga_kod == "CL":
        url_matches = f"https://api.football-data.org/v4/competitions/CL/matches"
        data_cl = ziskaj_z_cache_alebo_api(url_matches, "cl_playoff_matches", sekundy_platnosti=600)
        vyradovacie_zapasy = []
        
        if data_cl:
            vsetky_cl_zapasy = data_cl.get("matches", [])
            fazy_playoff = ["PLAY_OFF_ROUND", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
            preklady_faz = {"PLAY_OFF_ROUND": "Play-off", "ROUND_OF_16": "Osemfinále", "QUARTER_FINALS": "Štvrťfinále", "SEMI_FINALS": "Semifinále", "FINAL": "🏆 FINÁLE"}
            for zm in vsetky_cl_zapasy:
                if zm.get("stage") in fazy_playoff:
                    vyradovacie_zapasy.append({
                        "id": zm.get("id"), "faza_sk": preklady_faz.get(zm.get("stage"), zm.get("stage")),
                        "homeTeam": {"id": zm.get("homeTeam", {}).get("id"), "name": zm.get("homeTeam", {}).get("name")},
                        "awayTeam": {"id": zm.get("awayTeam", {}).get("id"), "name": zm.get("awayTeam", {}).get("name")},
                        "score_home": zm.get("score", {}).get("fullTime", {}).get("home"), "score_away": zm.get("score", {}).get("fullTime", {}).get("away"), "status": zm.get("status")
                    })
        return render_template("liga_majstrov.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod, vyradovacie_zapasy=vyradovacie_zapasy)
        
    return render_template("tabulka.html", tabulka=stojisko, liga=NAZVY_LIG[liga_kod], aktualna_liga=liga_kod)

if __name__ == "__main__":
    app.run(debug=True)