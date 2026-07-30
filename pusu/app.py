"""
PUSU - Online (PVP) Flask Backend
===================================
Tek kişilik AI modu tamamen sunucusuz çalışır (pusu_ai.html).
Bu dosya SADECE online (iki tarayıcı arasında) oynanan modu sağlar.
"""

import os
import random
import string

from flask import Flask, render_template, request, jsonify, session

import pusu_engine as engine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

rooms = {}  # oda kodu -> {"game": ..., "connected": {"player1": bool, "player2": bool}}


def generate_room_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in rooms:
            return code


def get_room_context():
    code = session.get("room")
    role = session.get("role")
    room = rooms.get(code) if code else None
    return room, role, code


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ai")
def ai_mode():
    return render_template("pusu_ai.html")


@app.route("/online")
def online_mode():
    return render_template("pusu_online.html")


@app.route("/create_room", methods=["POST"])
def create_room():
    code = generate_room_code()
    rooms[code] = {"game": engine.new_game(), "connected": {"player1": True, "player2": False}}
    session["room"] = code
    session["role"] = "player1"
    return jsonify({"status": "success", "room_code": code, "role": "player1"})


@app.route("/join_room", methods=["POST"])
def join_room():
    data = request.json or {}
    code = (data.get("room_code") or "").strip().upper()
    room = rooms.get(code)
    if not room:
        return jsonify({"status": "error", "message": "Oda bulunamadı."})
    if room["connected"]["player2"]:
        return jsonify({"status": "error", "message": "Bu oda dolu."})

    room["connected"]["player2"] = True
    session["room"] = code
    session["role"] = "player2"
    return jsonify({"status": "success", "room_code": code, "role": "player2"})


@app.route("/game_state", methods=["GET"])
def game_state():
    room, role, _ = get_room_context()
    if not room or not role:
        return jsonify({"status": "error", "message": "Bir odaya bağlı değilsiniz."})
    if not room["connected"]["player2"]:
        return jsonify({"status": "error", "message": "Rakip henüz odaya katılmadı."})

    game = room["game"]
    opp = engine.opponent_of(role)

    if game["phase"] in ("pusu", "final_pusu"):
        quota = engine.pusu_quota(game["phase"])
        is_my_turn = len(game["pusu"][role]) < quota
    elif game["phase"] == "battle":
        is_my_turn = game["front_progress"][role][game["current_front"]] < engine.MAX_PER_FRONT
    else:
        is_my_turn = False

    return jsonify({
        "status": "success",
        "phase": game["phase"],
        "current_front": game["current_front"],
        "is_my_turn": is_my_turn,
        "my_grid": engine.render_grid(game, role, role),
        "opponent_grid": engine.render_grid(game, role, opp),
        "my_used_units": engine.used_units_remaining(game, role),
    })


@app.route("/commit_pusu", methods=["POST"])
def commit_pusu_route():
    room, role, _ = get_room_context()
    if not room or not role:
        return jsonify({"status": "error", "message": "Bir odaya bağlı değilsiniz."})

    data = request.json or {}
    try:
        x, y = int(data["x"]), int(data["y"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"status": "error", "message": "Geçersiz veri."})

    ok, msg = engine.commit_pusu(room["game"], role, x, y)
    if not ok:
        return jsonify({"status": "error", "message": msg})
    return jsonify({"status": "success"})


@app.route("/commit_unit", methods=["POST"])
def commit_unit_route():
    room, role, _ = get_room_context()
    if not room or not role:
        return jsonify({"status": "error", "message": "Bir odaya bağlı değilsiniz."})

    data = request.json or {}
    try:
        x, y, unit = int(data["x"]), int(data["y"]), int(data["unit"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"status": "error", "message": "Geçersiz veri."})

    ok, msg = engine.commit_unit(room["game"], role, x, y, unit)
    if not ok:
        return jsonify({"status": "error", "message": msg})
    return jsonify({"status": "success"})


@app.route("/results", methods=["GET"])
def results():
    room, role, _ = get_room_context()
    if not room or not role:
        return jsonify({"status": "error", "message": "Bir odaya bağlı değilsiniz."})

    game = room["game"]
    if game["phase"] != "done":
        return jsonify({"status": "error", "message": "Oyun henüz tamamlanmadı."})

    scores, winner, p1w, p2w = engine.compute_results(game)
    return jsonify({
        "status": "success",
        "scores_p1": scores["player1"],
        "scores_p2": scores["player2"],
        "winner": winner,
        "player1_pusu": engine.pusu_list_json(game["pusu"]["player1"]),
        "player2_pusu": engine.pusu_list_json(game["pusu"]["player2"]),
    })


@app.route("/reset_room", methods=["POST"])
def reset_room():
    room, role, code = get_room_context()
    if not room or not role:
        return jsonify({"status": "error", "message": "Bir odaya bağlı değilsiniz."})

    connected = room["connected"]
    rooms[code] = {"game": engine.new_game(), "connected": connected}
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True)
