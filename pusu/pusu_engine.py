"""
PUSU - Python Oyun Motoru
===========================
pusu_engine.js dosyasının birebir Python portu. Online (PVP) modu bu
modülü kullanır.
"""

import random

GRID_SIZE = 5
UNIT_TYPES = [1, 2, 3, 4, 5]
MAX_PER_UNIT = 3
MAX_PER_FRONT = 3
PUSU_PHASE1_COUNT = 2
PUSU_TOTAL_COUNT = 3


def empty_board():
    return [["-"] * GRID_SIZE for _ in range(GRID_SIZE)]


def new_game():
    return {
        "board": {"player1": empty_board(), "player2": empty_board()},
        "pusu": {"player1": [], "player2": []},
        "used_units": {
            "player1": {u: 0 for u in UNIT_TYPES},
            "player2": {u: 0 for u in UNIT_TYPES},
        },
        "front_progress": {"player1": [0] * GRID_SIZE, "player2": [0] * GRID_SIZE},
        "phase": "pusu",  # pusu -> battle -> final_pusu -> done
        "current_front": 0,
    }


def opponent_of(p):
    return "player2" if p == "player1" else "player1"


def pusu_quota(phase):
    if phase == "pusu":
        return PUSU_PHASE1_COUNT
    if phase == "final_pusu":
        return PUSU_TOTAL_COUNT
    return None


def commit_pusu(game, player, x, y):
    if game["phase"] not in ("pusu", "final_pusu"):
        return False, "Şu anda pusu kurma aşamasında değilsiniz."
    if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
        return False, "Geçersiz koordinat."

    quota = pusu_quota(game["phase"])
    my_pusu = game["pusu"][player]

    if (x, y) in my_pusu:
        return False, "Bu noktaya zaten tuzak kurdunuz."
    if len(my_pusu) >= quota:
        return False, "Bu aşamada kullanabileceğiniz tüm tuzakları kurdunuz."

    my_pusu.append((x, y))

    if game["phase"] == "pusu":
        if (len(game["pusu"]["player1"]) >= PUSU_PHASE1_COUNT and
                len(game["pusu"]["player2"]) >= PUSU_PHASE1_COUNT):
            game["phase"] = "battle"
    elif game["phase"] == "final_pusu":
        if (len(game["pusu"]["player1"]) >= PUSU_TOTAL_COUNT and
                len(game["pusu"]["player2"]) >= PUSU_TOTAL_COUNT):
            game["phase"] = "done"

    return True, None


def commit_unit(game, player, x, y, unit):
    if game["phase"] != "battle":
        return False, "Şu anda savaş aşamasında değilsiniz."
    if not (0 <= y < GRID_SIZE):
        return False, "Geçersiz koordinat."
    if unit not in UNIT_TYPES:
        return False, "Geçersiz birlik türü."
    if x != game["current_front"]:
        return False, f"Bu tur sadece {game['current_front'] + 1}. cepheye birlik gönderebilirsiniz."
    if game["board"][player][x][y] != "-":
        return False, "Bu kare zaten dolu."
    if game["used_units"][player][unit] >= MAX_PER_UNIT:
        return False, "Bu birlik türünü zaten 3 kez kullandınız."
    if game["front_progress"][player][x] >= MAX_PER_FRONT:
        return False, "Bu cepheye zaten 3 birlik gönderdiniz."

    game["board"][player][x][y] = str(unit)
    game["used_units"][player][unit] += 1
    game["front_progress"][player][x] += 1

    front = game["current_front"]
    if (game["front_progress"]["player1"][front] >= MAX_PER_FRONT and
            game["front_progress"]["player2"][front] >= MAX_PER_FRONT):
        game["current_front"] += 1
        if game["current_front"] >= GRID_SIZE:
            game["phase"] = "final_pusu"

    return True, None


def compute_results(game):
    scores = {"player1": [0] * GRID_SIZE, "player2": [0] * GRID_SIZE}
    for p in ("player1", "player2"):
        opp = opponent_of(p)
        trapped = set(game["pusu"][opp])
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                val = game["board"][p][x][y]
                if val != "-" and (x, y) not in trapped:
                    scores[p][x] += int(val)

    p1_wins = sum(1 for i in range(GRID_SIZE) if scores["player1"][i] > scores["player2"][i])
    p2_wins = sum(1 for i in range(GRID_SIZE) if scores["player2"][i] > scores["player1"][i])
    if p1_wins > p2_wins:
        winner = "player1"
    elif p2_wins > p1_wins:
        winner = "player2"
    else:
        winner = "draw"

    return scores, winner, p1_wins, p2_wins


def render_grid(game, viewer, owner):
    """owner==viewer: kendi tahtan, kartların değeri görünür.
    owner!=viewer: rakip tahtası - tam sis örtüsü. Sadece kendi
    kurduğun tuzaklar görünür; rakibin nereye birlik koyduğu (pozisyon
    dahil) HİÇ sızdırılmaz."""
    board = game["board"][owner]
    grid = []
    if owner == viewer:
        for x in range(GRID_SIZE):
            grid.append([f"unit:{board[x][y]}" if board[x][y] != "-" else "empty" for y in range(GRID_SIZE)])
    else:
        my_traps = set(game["pusu"][viewer])
        for x in range(GRID_SIZE):
            grid.append(["trap" if (x, y) in my_traps else "empty" for y in range(GRID_SIZE)])
    return grid


def used_units_remaining(game, player):
    return {str(u): MAX_PER_UNIT - game["used_units"][player][u] for u in UNIT_TYPES}


def pusu_list_json(pairs):
    return [[x, y] for (x, y) in pairs]
