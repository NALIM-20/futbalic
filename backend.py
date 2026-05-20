import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import requests
# Uisti sa, že máš priečinok 'supisky' a v ňom '__init__.py' a v ňom definované RUČNÉ_SÚPISKY
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
        print(f"DEBUG: Volám {url} -> Status: {response.status_code}") # TOTO TI UKÁŽE CHYBU V TERMINÁLE
        
        if response.status_code == 200:
            data = response.json()
            cache[cache_key] = (data, datetime.now())
            return data
        else:
            print(f"API CHYBA: {response.text}") # Tu uvidíš, či máš vyčerpaný limit
    except Exception as e:
        print(f"EXCEPTION: {e}")
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
                    "score": m["score"]["fullTime"], "status": m["status"]
                })
    return render_template("index.html", zápasy=zápasy, aktualny_datum=datum)

@app.route("/tabulka/<liga_kod>")
def tabulka_ligy(liga_kod):
    url = f"{BASE_URL}/competitions/{liga_kod}/standings"
    data = get_cached_data(f"standings_{liga_kod}", url)
    
    # Bezpečná kontrola dát
    tabulka = []
    if data and "standings" in data and len(data["standings"]) > 0:
        tabulka = data["standings"][0].get("table", [])
    
    if liga_kod == "CL":
        matches = get_cached_data("matches_CL", f"{BASE_URL}/competitions/CL/matches")
        vyradovacie = []
        if matches and "matches" in matches:
            vyradovacie = [{"id": m["id"], "faza_sk": preloz_fazu_ucl(m["stage"]), "homeTeam": m["homeTeam"], "awayTeam": m["awayTeam"], "score_home": m["score"]["fullTime"].get("home"), "score_away": m["score"]["fullTime"].get("away")} for m in matches["matches"] if m["stage"] != "LEAGUE_STAGE"]
        return render_template("liga_majstrov.html", tabulka=tabulka, vyradovacie_zapasy=vyradovacie)
    
    return render_template("tabulka.html", liga=LEAGUES.get(liga_kod, liga_kod), tabulka=tabulka)

@app.route("/tabulka/tim/<int:tim_id>")
def profil_timu(tim_id):
    tim_data = get_cached_data(f"team_{tim_id}", f"{BASE_URL}/teams/{tim_id}") or {}
    trener = "Neznámy"
    if tim_id in RUČNÉ_SÚPISKY:
        tim_data["squad"] = RUČNÉ_SÚPISKY[tim_id].get("players", [])
        trener = RUČNÉ_SÚPISKY[tim_id].get("coach", {}).get("name", "Neznámy")
    
    return render_template("tim.html", tim=tim_data, trener=trener, posledne_zapasy=[], trofeje="Dáta z API")

if __name__ == "__main__":
    app.run(debug=True)