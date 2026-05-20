from .la_liga import LA_LIGA_SÚPISKY
from .premier_league import PREMIER_LEAGUE_SÚPISKY
from .bundesliga import BUNDESLIGA_SÚPISKY
from .serie_a import SERIE_A_SÚPISKY
from .ligue_1 import LIGUE_1_SÚPISKY
# Tu Python automaticky spojí všetky slovníky do jedného veľkého pre backend
RUČNÉ_SÚPISKY = {}
RUČNÉ_SÚPISKY.update(LA_LIGA_SÚPISKY)
RUČNÉ_SÚPISKY.update(PREMIER_LEAGUE_SÚPISKY)
RUČNÉ_SÚPISKY.update(SERIE_A_SÚPISKY)
RUČNÉ_SÚPISKY.update(BUNDESLIGA_SÚPISKY)
RUČNÉ_SÚPISKY.update(LIGUE_1_SÚPISKY)
# Ak v budúcnosti vytvoríš napr. bundesliga.py, stačí ho tu hore importovať 
# a dole pridať: RUČNÉ_SÚPISKY.update(BUNDESLIGA_SÚPISKY)