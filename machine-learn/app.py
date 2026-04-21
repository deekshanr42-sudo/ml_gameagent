from flask import Flask, jsonify, request, render_template
import random

app = Flask(__name__)

TOTAL_LEVELS = 10
LEVEL_SIZES = [5, 6, 7, 8, 9, 10, 11, 12, 13, 15]


def generate_maze(size):
    rows = cols = size
    gr = rows * 2 + 1
    gc = cols * 2 + 1
    grid = [[1] * gc for _ in range(gr)]
    vis = [[False] * cols for _ in range(rows)]
    grid[1][1] = 0
    stack = [(0, 0)]
    vis[0][0] = True
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    while stack:
        cr, cc = stack[-1]
        nb = []
        for dr, dc in dirs:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and not vis[nr][nc]:
                nb.append((nr, nc, dr, dc))
        if not nb:
            stack.pop()
        else:
            nr, nc, dr, dc = random.choice(nb)
            vis[nr][nc] = True
            r1, c1 = nr * 2 + 1, nc * 2 + 1
            r2, c2 = cr * 2 + 1, cc * 2 + 1
            grid[(r1 + r2) // 2][(c1 + c2) // 2] = 0
            grid[r1][c1] = 0
            stack.append((nr, nc))
    return {"grid": grid, "rows": gr, "cols": gc, "lr": rows, "lc": cols}


DATASET = [generate_maze(s) for s in LEVEL_SIZES]

G = {
    "lvl": 0, "pos": [1, 1], "vis": set(["1,1"]),
    "trail": [[1, 1]], "score": 0, "moves": 0,
    "ok": 0, "bad": 0, "rep": 0, "pen": 0,
    "active": False, "scores": []
}


def init_lvl(i):
    G["lvl"] = i
    G["pos"] = [1, 1]
    G["vis"] = set(["1,1"])
    G["trail"] = [[1, 1]]
    G["ok"] = G["bad"] = G["rep"] = G["pen"] = 0
    G["active"] = True


def stats():
    return {
        "ok": G["ok"], "bad": G["bad"], "rep": G["rep"],
        "pen": G["pen"], "moves": G["moves"],
        "seen": len(G["vis"]), "scores": G["scores"],
        "done": list(range(len(G["scores"])))
    }


def resp():
    m = DATASET[G["lvl"]]
    return {
        "level": G["lvl"], "total": TOTAL_LEVELS,
        "grid": m["grid"], "rows": m["rows"], "cols": m["cols"],
        "lr": m["lr"], "lc": m["lc"],
        "start": [1, 1], "goal": [m["rows"] - 2, m["cols"] - 2],
        "pos": list(G["pos"]), "vis": list(G["vis"]),
        "trail": [list(t) for t in G["trail"]],
        "score": G["score"], "active": G["active"], "stats": stats()
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "levels": TOTAL_LEVELS})


@app.route("/api/maze")
def maze():
    return jsonify(resp())


@app.route("/api/move", methods=["POST"])
def move():
    if not G["active"]:
        return jsonify({"error": "not active"}), 400
    d = request.get_json(force=True)
    dr = d.get("direction", "")
    if dr not in ("up", "down", "left", "right"):
        return jsonify({"error": "bad dir"}), 400
    m = DATASET[G["lvl"]]
    r, c = G["pos"]
    nr, nc = r, c
    if dr == "up": nr -= 1
    elif dr == "down": nr += 1
    elif dr == "left": nc -= 1
    elif dr == "right": nc += 1
    G["moves"] += 1
    sc = 0
    mt = "invalid"
    msg = ""
    if nr < 0 or nr >= m["rows"] or nc < 0 or nc >= m["cols"]:
        G["bad"] += 1; G["pen"] += 1; sc = -20; mt = "invalid"; msg = "bounds"
    elif m["grid"][nr][nc] == 1:
        G["bad"] += 1; G["pen"] += 1; sc = -20; mt = "invalid"; msg = "wall"
    else:
        k = str(nr) + "," + str(nc)
        if k in G["vis"]:
            G["rep"] += 1; G["pen"] += 1; sc = -5; mt = "repeat"; msg = "repeat"
        else:
            G["ok"] += 1; sc = 10; mt = "valid"; msg = "ok"; G["vis"].add(k)
        G["pos"] = [nr, nc]; G["trail"].append([nr, nc])
    G["score"] += sc
    done = False
    all_done = False
    ls = 0
    if mt in ("valid", "repeat") and nr == m["rows"] - 2 and nc == m["cols"] - 2:
        done = True; G["active"] = False
        ls = 10 * G["ok"] - 20 * G["bad"] - 5 * G["rep"] + 50
        G["score"] += 50; G["scores"].append(ls)
        if G["lvl"] >= TOTAL_LEVELS - 1:
            all_done = True
    return jsonify({
        "valid": mt in ("valid", "repeat"), "type": mt, "msg": msg,
        "sc": sc, "score": G["score"], "pos": list(G["pos"]),
        "done": done, "all_done": all_done, "ls": ls if done else 0,
        "stats": stats()
    })


@app.route("/api/next", methods=["POST"])
def nxt():
    n = G["lvl"] + 1
    if n >= TOTAL_LEVELS:
        return jsonify({"error": "all done"}), 400
    init_lvl(n)
    return jsonify(resp())


@app.route("/api/reset", methods=["POST"])
def reset():
    global DATASET
    DATASET = [generate_maze(s) for s in LEVEL_SIZES]
    G["score"] = G["moves"] = 0; G["scores"] = []; init_lvl(0)
    return jsonify(resp())


if __name__ == "__main__":
    init_lvl(0)
    print("RL Maze Agent -> http://127.0.0.1:5000")
    app.run(debug=True, port=5000)