from .la_liga import LA_LIGA_SÚPISKY
from .premier_league import PREMIER_LEAGUE_SÚPISKY

# Tu Python automaticky spojí všetky slovníky do jedného veľkého pre backend
RUČNÉ_SÚPISKY = {}
RUČNÉ_SÚPISKY.update(LA_LIGA_SÚPISKY)
RUČNÉ_SÚPISKY.update(PREMIER_LEAGUE_SÚPISKY)

# Ak v budúcnosti vytvoríš napr. bundesliga.py, stačí ho tu hore importovať 
# a dole pridať: RUČNÉ_SÚPISKY.update(BUNDESLIGA_SÚPISKY)