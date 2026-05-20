import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Opravené: Vložený tvoj pôvodný funkčný token priamo do kódu
API_KEY = "0353c89659b9409bbba986dc1555a1d7"
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

# Podporované ligy (Kódy pre football-data.org)
LEAGUES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League"
}

# Lokálna Cache pamäť, aby sme neprekročili limity API
cache = {}

def get_cached_data(cache_key, url, expiry_minutes=10):
    """Pomocná funkcia, ktorá ukladá odpovede z API do pamäte."""
    now = datetime.now()
    if cache_key in cache:
        data, timestamp = cache[cache_key]
        if now - timestamp < timedelta(minutes=expiry_minutes):
            return data
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache[cache_key] = (data, now)
            return data
    except Exception as e:
        print(f"Chyba pri volaní API: {e}")
    
    if cache_key in cache:
        return cache[cache_key][0]
    return None

def preloz_fazu_ucl(stage_en):
    """Prekladá anglické názvy kôl Ligy majstrov do slovenčiny bez emoji."""
    prevody = {
        "PRELIMINARY_ROUND": "Predkolo",
        "QUALIFYING_ROUND": "Kvalifikácia",
        "PLAYOFF_ROUND": "Play-off",
        "LEAGUE_STAGE": "Ligová fáza",
        "ROUND_OF_16": "Osemfinále",
        "QUARTER_FINALS": "Štvrťfinále",
        "SEMI_FINALS": "Semifinále",
        "FINAL": "Finále"
    }
    return prevody.get(stage_en, stage_en)

@app.route("/")
def index():
    """Hlavná stránka so zápasmi pre zvolený deň."""
    zvoleny_datum_str = request.args.get("date")
    dnes = datetime.now()
    
    if not zvoleny_datum_str:
        zvoleny_datum_str = dnes.strftime("%Y-%m-%d")
    
    # Generovanie menu 5 dní (včera, dnes, +3 dni dopredu)
    dni_menu = []
    start_den = dnes - timedelta(days=1)
    for i in range(5):
        den = start_den + timedelta(days=i)
        url_format = den.strftime("%Y-%m-%d")
        
        if url_format == dnes.strftime("%Y-%m-%d"):
            pekny_nazov = "Dnes"
        elif url_format == (dnes - timedelta(days=1)).strftime("%Y-%m-%d"):
            pekny_nazov = "Včera"
        elif url_format == (dnes + timedelta(days=1)).strftime("%Y-%m-%d"):
            pekny_nazov = "Zajtra"
        else:
            pekny_nazov = den.strftime("%d.%m.")
            
        dni_menu.append({"datum_url": url_format, "pekny_nazov": pekny_nazov})

    # Stiahnutie zápasov pre daný deň
    url = f"{BASE_URL}/matches?dateFrom={zvoleny_datum_str}&dateTo={zvoleny_datum_str}"
    cache_key = f"matches_{zvoleny_datum_str}"
    data = get_cached_data(cache_key, url, expiry_minutes=2)
    
    spracovane_zapasy = []
    if data and "matches" in data:
        for m in data["matches"]:
            kod_ligy = m.get("competition", {}).get("code")
            if kod_ligy in LEAGUES:
                status_raw = m.get("status")
                
                if status_raw in ["LIVE", "IN_PLAY", "PAUSED"]:
                    status = "LIVE"
                    minute = f"{m.get('minute', '??')}'"
                elif status_raw == "FINISHED":
                    status = "FINISHED"
                    minute = "Koniec"
                else:
                    status = "SCHEDULED"
                    utc_date_str = m.get("utcDate")
                    if utc_date_str:
                        try:
                            dt = datetime.strptime(utc_date_str, "%Y-%m-%dT%H:%M:%SZ")
                            dt_sk = dt + timedelta(hours=2)
                            minute = dt_sk.strftime("%H:%M")
                        except:
                            minute = utc_date_str[11:16]
                    else:
                        minute = "--:--"

                spracovane_zapasy.append({
                    "id": m.get("id"),
                    "league": LEAGUES[kod_ligy],
                    "homeTeam": {"name": m.get("homeTeam", {}).get("name", "Neznámy")},
                    "awayTeam": {"name": m.get("awayTeam", {}).get("name", "Neznámy")},
                    "score": {
                        "home": m.get("score", {}).get("fullTime", {}).get("home"),
                        "away": m.get("score", {}).get("fullTime", {}).get("away")
                    },
                    "status": status,
                    "minute": minute
                })

    try:
        obj_dat = datetime.strptime(zvoleny_datum_str, "%Y-%m-%d")
        povedz_datum = obj_dat.strftime("%d.%m.%Y")
    except:
        povedz_datum = zvoleny_datum_str

    return render_template(
        "index.html", 
        zapasy=spracovane_zapasy, 
        dni_menu=dni_menu, 
        aktualny_datum=zvoleny_datum_str,
        povedz_datum=povedz_datum
    )

@app.route("/tabulka/<liga_kod>")
def tabulka_ligy(liga_kod):
    """Zobrazenie ligovej tabuľky alebo pavúka / skupín pre Ligu Majstrov."""
    if liga_kod not in LEAGUES:
        return "Nepodporovaná liga", 404

    url = f"{BASE_URL}/competitions/{liga_kod}/standings"
    cache_key = f"standings_{liga_kod}"
    data = get_cached_data(cache_key, url, expiry_minutes=15)

    if liga_kod == "CL":
        tabulka_data = []
        if data and "standings" in data:
            for st in data["standings"]:
                if st.get("type") == "TOTAL":
                    tabulka_data = st.get("table", [])
                    break
        
        url_zapasy = f"{BASE_URL}/competitions/CL/matches"
        cache_key_zapasy = "ucl_all_matches"
        data_zapasy = get_cached_data(cache_key_zapasy, url_zapasy, expiry_minutes=15)
        
        vyradovacie = []
        if data_zapasy and "matches" in data_zapasy:
            for m in data_zapasy["matches"]:
                faza = m.get("stage")
                if faza and faza != "LEAGUE_STAGE":
                    vyradovacie.append({
                        "id": m.get("id"),
                        "faza_sk": preloz_fazu_ucl(faza),
                        "homeTeam": {"name": m.get("homeTeam", {}).get("name", "TBD")},
                        "awayTeam": {"name": m.get("awayTeam", {}).get("name", "TBD")},
                        "score_home": m.get("score", {}).get("fullTime", {}).get("home"),
                        "score_away": m.get("score", {}).get("fullTime", {}).get("away")
                    })
        
        return render_template("liga_majstrov.html", tabulka=tabulka_data, vyradovacie_zapasy=vyradovacie)
    
    else:
        tabulka_data = []
        if data and "standings" in data and len(data["standings"]) > 0:
            tabulka_data = data["standings"][0].get("table", [])
        
        return render_template("tabulka.html", liga=LEAGUES[liga_kod], tabulka=tabulka_data)

@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    """Zobrazenie profilu tímu, súpisky a posledných 5 zápasov (formy) vrátane ID."""
    url_tim = f"{BASE_URL}/teams/{tim_id}"
    cache_key_tim = f"team_prof_{tim_id}"
    tim_data = get_cached_data(cache_key_tim, url_tim, expiry_minutes=60)

    if not tim_data:
        return "Tím sa nepodarilo načítať. Skontrolujte limit API.", 404

    trener = "Neznámy"
    if "coach" in tim_data and tim_data["coach"].get("name"):
        trener = tim_data["coach"]["name"]

    trofeje_list = []
    if "runningCompetitions" in tim_data:
        for comp in tim_data["runningCompetitions"]:
            trofeje_list.append(comp.get("name"))
    trofeje_str = "Účastník súťaží: " + ", ".join(trofeje_list) if trofeje_list else "Informácie o súťažiach nedostupné"

    url_zapasy = f"{BASE_URL}/teams/{tim_id}/matches?status=FINISHED&limit=5"
    cache_key_zapasy = f"team_matches_{tim_id}"
    zapasy_data = get_cached_data(cache_key_zapasy, url_zapasy, expiry_minutes=15)

    posledne_zapasy = []
    if zapasy_data and "matches" in zapasy_data:
        for m in zapasy_data["matches"]:
            raw_date = m.get("utcDate", "")
            pekny_datum = raw_date[:10] if len(raw_date) >= 10 else raw_date
            
            posledne_zapasy.append({
                "id": m.get("id"),
                "datum": pekny_datum,
                "sutaz": m.get("competition", {}).get("name", "Súťaž"),
                "homeTeam": m.get("homeTeam", {}).get("name", "Neznámy"),
                "awayTeam": m.get("awayTeam", {}).get("name", "Neznámy"),
                "score_home": m.get("score", {}).get("fullTime", {}).get("home"),
                "score_away": m.get("score", {}).get("fullTime", {}).get("away")
            })

    return render_template(
        "tim.html", 
        tim=tim_data, 
        trener=trener, 
        trofeje=trofeje_str, 
        posledne_zapasy=posledne_zapasy
    )

@app.route("/api/zapas/<int:zapas_id>")
def api_detail_zapasu(zapas_id):
    """Endpoint, ktorý JavaScript volá na pozadí pre načítanie strelcov gólov."""
    url = f"{BASE_URL}/matches/{zapas_id}"
    cache_key = f"match_det_{zapas_id}"
    data = get_cached_data(cache_key, url, expiry_minutes=5)

    if not data or "match" not in data:
        return jsonify({
            "goals": ["Detaily gólov nie sú k dispozícii v bezplatnej verzii API."],
            "venue": "Neznámy štadión",
            "referee": "Neznámy rozhodca"
        })

    match_core = data["match"]
    zoznam_golov = []

    if "goals" in match_core and match_core["goals"]:
        for g in match_core["goals"]:
            minuta = g.get("minute", "?")
            strelec = g.get("scorer", {}).get("name", "Neznámy hráč")
            tim_golu = g.get("team", {}).get("name", "Tím")
            
            typ = g.get("type", "REGULAR")
            doplnok = ""
            if typ == "PENALTY":
                doplnok = " (penalta)"
            elif typ == "OWN":
                doplnok = " (vlastný gól)"

            zoznam_golov.append(f"{minuta}' [{tim_golu}] {strelec}{doplnok}")

    stadion = match_core.get("venue", "Neznámy")
    rozhodca = "Neznámy"
    if "referees" in match_core and len(match_core["referees"]) > 0:
        rozhodca = match_core["referees"][0].get("name", "Neznámy")

    return jsonify({
        "goals": zoznam_golov,
        "venue": stadion,
        "referee": rozhodca
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)