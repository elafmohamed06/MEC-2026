"""
AstroFit dashboard — run with:   streamlit run app.py
Demo logins:  lee / lee123   kim / kim123   ortiz / ortiz123   park / park123   doctor / doc123
"""
import hashlib
import json
import os

import plotly.graph_objects as go
import streamlit as st

from avatar import avatar_svg
from engine import (SCORES, LABELS, EXERCISES, DEFAULT_GOALS, MAX_DAILY_MIN,
                    daily_update, predict, adjust_plan, calibrate, validate_workout, status)

st.set_page_config(page_title="AstroFit", page_icon="🛰️", layout="wide")
MISSION_DAYS = 180
COLORS = {"green": "#34d399", "yellow": "#fbbf24", "red": "#f87171"}

# ---------------------------------------------------------------- security: hashed passwords + roles
SALT = "astrofit-mec-2026"
def h(pw): return hashlib.sha256((SALT + pw).encode()).hexdigest()
USERS = {   # passwords are never stored in plain text, only their hashes
    "lee":    {"hash": h("lee123"),   "role": "astronaut", "astronaut": "Cmdr. Lee"},
    "kim":    {"hash": h("kim123"),   "role": "astronaut", "astronaut": "Dr. Kim"},
    "ortiz":  {"hash": h("ortiz123"), "role": "astronaut", "astronaut": "Eng. Ortiz"},
    "park":   {"hash": h("park123"),  "role": "astronaut", "astronaut": "Spec. Park"},
    "doctor": {"hash": h("doc123"),   "role": "doctor",    "astronaut": None},
}

# ---------------------------------------------------------------- crew setup
LOOKS = {   # each avatar's appearance
    "Cmdr. Lee":  {"skin": "#e0ac69", "hair": "#1b1b1b", "style": "short"},
    "Dr. Kim":    {"skin": "#8d5524", "hair": "#1b1b1b", "style": "bun"},
    "Eng. Ortiz": {"skin": "#c68642", "hair": "#3b2416", "style": "short"},
    "Spec. Park": {"skin": "#f1c27d", "hair": "#8a5a33", "style": "bun"},
}

def new_crew():
    # true_factor = how fast their body REALLY loses strength (hidden; the app has to learn it)
    base = [("Cmdr. Lee", 1.0, {"bike": 40, "treadmill": 20}),
            ("Dr. Kim", 1.4, {"bike": 30, "treadmill": 30, "deadlifts": 20}),
            ("Eng. Ortiz", 0.8, {"treadmill": 40, "squats": 20}),
            ("Spec. Park", 1.2, {"bike": 60})]
    return {name: {"look": LOOKS[name], "scores": {s: 100.0 for s in SCORES}, "plan": plan, "model_factor": 1.0,
                   "true_factor": tf, "history": [{"day": 0, "scores": {s: 100.0 for s in SCORES}}],
                   "since_test": [], "log": []}
            for name, tf, plan in base}

if "crew" not in st.session_state:
    st.session_state.crew = new_crew()
    st.session_state.day = 0
    st.session_state.user = None

ss = st.session_state

# ---------------------------------------------------------------- simulation (stands in for real sensors)
def simulate_days(n, adherence, sleep_ok, food_ok):
    for _ in range(n):
        if ss.day >= MISSION_DAYS:
            break
        ss.day += 1
        for name, a in ss.crew.items():
            done = {ex: m * adherence for ex, m in a["plan"].items()}
            after = daily_update(a["scores"], done, a["true_factor"], sleep_ok, food_ok)
            a["since_test"].append(dict(scores_before=a["scores"], workout=done, sleep_ok=sleep_ok,
                                        food_ok=food_ok, scores_after=after))
            a["scores"] = after
            a["history"].append({"day": ss.day, "scores": after})

# ---------------------------------------------------------------- UI pieces
def chart(a, prediction, goals):
    fig = go.Figure()
    palette = ["#3498db", "#9b59b6", "#e67e22", "#e84393", "#fdcb6e", "#1abc9c"]
    hover = "<b>%{fullData.name}</b><br>Day %{x}: %{y:.1f}%<extra></extra>"
    for i, s in enumerate(SCORES):
        fig.add_trace(go.Scatter(x=[p["day"] for p in a["history"]], y=[p["scores"][s] for p in a["history"]],
                                 name=LABELS[s], legendgroup=s, line=dict(color=palette[i], width=2.5),
                                 hovertemplate=hover))
        fig.add_trace(go.Scatter(x=list(range(ss.day, MISSION_DAYS + 1)), y=[p[s] for p in prediction],
                                 name=f"{LABELS[s]} (predicted)", legendgroup=s, showlegend=False,
                                 line=dict(color=palette[i], dash="dot", width=2), hovertemplate=hover))
    # goal lines: labels sit OUTSIDE the plot on the right, so they never cover the data
    for g in sorted(set(goals.values())):
        fig.add_hline(y=g, line_dash="dash", line_color="#f87171", line_width=1)
        fig.add_annotation(x=1, xref="paper", xanchor="left", xshift=6, y=g, yref="y", showarrow=False,
                           text=f"goal {g:.0f}%", font=dict(size=11, color="#f87171"))
    # "today" marker: label sits ABOVE the plot
    fig.add_vline(x=ss.day, line_color="grey", line_width=1, line_dash="dot")
    fig.add_annotation(x=ss.day, xref="x", y=1, yref="paper", yanchor="bottom", yshift=4, showarrow=False,
                       text=f"today (day {ss.day})", font=dict(size=11, color="#bbb"))
    fig.update_layout(height=470, xaxis_title="Mission day", yaxis_title="Score (%)",
                      xaxis_range=[0, MISSION_DAYS], yaxis_range=[75, 102],
                      margin=dict(t=40, b=10, l=10, r=70),
                      hoverlabel=dict(namelength=-1, font_size=12),
                      legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=11)))
    return fig

def astronaut_panel(name):
    a = ss.crew[name]
    goals = DEFAULT_GOALS
    days_left = MISSION_DAYS - ss.day
    prediction = predict(a["scores"], a["plan"], days_left, a["model_factor"])
    landing = prediction[-1]

    st.subheader(f"👩‍🚀 {name} · Day {ss.day} of {MISSION_DAYS}")
    c1, c2 = st.columns([1, 3])
    with c1:
        sts = {s: status(landing[s], goals[s]) for s in SCORES}
        mood = "red" if "red" in sts.values() else "yellow" if "yellow" in sts.values() else "green"
        look = a.get("look") or LOOKS[name]
        colors = {s: COLORS[sts[s]] for s in SCORES}
        st.markdown(avatar_svg(colors, landing, look["skin"], look["hair"], mood), unsafe_allow_html=True)
    with c2:
        st.plotly_chart(chart(a, prediction, goals), width="stretch")

    # alerts
    problems = [s for s in SCORES if landing[s] < goals[s]]
    for s in problems:
        st.error(f"⚠️ {LABELS[s]} projected **{landing[s]:.1f}%** on landing (goal {goals[s]:.0f}%)")
    if not problems:
        st.success("✅ All scores on track for landing day")

    m = st.columns(3) + st.columns(3)
    for i, s in enumerate(SCORES):
        m[i].metric(LABELS[s], f"{a['scores'][s]:.1f}%", f"landing {landing[s]:.1f}%", delta_color="off")

    # plan
    st.markdown("#### 🏋️ Daily workout plan")
    total = sum(a["plan"].values())
    st.table({"Exercise": list(a["plan"]), "Minutes/day": list(a["plan"].values())})
    st.caption(f"Total {total} / {MAX_DAILY_MIN} min · personal loss rate (learned): {a['model_factor']:.2f}")

    b1, b2 = st.columns(2)
    if b1.button("🧠 Update plan", key=f"upd_{name}"):
        new_plan, changes = adjust_plan(a["scores"], a["plan"], days_left, goals, a["model_factor"])
        a["plan"] = new_plan
        a["log"].append(f"Day {ss.day}: " + ("; ".join(changes) if changes else "no change needed"))
        st.rerun()
    if b2.button("🧪 Weekly test (learn my body)", key=f"test_{name}"):
        f, msg = calibrate(a["since_test"], a["model_factor"])
        a["model_factor"] = f
        a["since_test"] = []
        a["log"].append(f"Day {ss.day}: {msg}")
        st.rerun()

    with st.expander("✍️ Log a workout manually"):
        cols = st.columns(3) + st.columns(3)
        entry = {ex: cols[i].number_input(ex.replace("_", " "), 0, 1000, 0, 10, key=f"log_{name}_{ex}")
                 for i, ex in enumerate(EXERCISES)}
        if st.button("Submit log", key=f"sub_{name}"):
            errors = validate_workout(entry)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.success("Logged ✅")
                a["log"].append(f"Day {ss.day}: logged {entry}")

    if a["log"]:
        st.markdown("#### 📜 Change log")
        for line in reversed(a["log"][-8:]):
            st.write("•", line)

def doctor_overview():
    st.subheader("🩺 Flight Doctor: Crew overview")
    rows = []
    for name, a in ss.crew.items():
        landing = predict(a["scores"], a["plan"], MISSION_DAYS - ss.day, a["model_factor"])[-1]
        worst = min(SCORES, key=lambda s: landing[s] - DEFAULT_GOALS[s])
        flag = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[status(landing[worst], DEFAULT_GOALS[worst])]
        rows.append({"Astronaut": name, "Status": flag, "Weakest area": LABELS[worst],
                     "Landing projection": f"{landing[worst]:.1f}%", "Exercise min/day": sum(a["plan"].values())})
    st.table(rows)
    if st.button("🧠 Update ALL plans"):
        for a in ss.crew.values():
            a["plan"], ch = adjust_plan(a["scores"], a["plan"], MISSION_DAYS - ss.day, DEFAULT_GOALS,
                                        a["model_factor"])
            a["log"].append(f"Day {ss.day} (doctor): " + ("; ".join(ch) if ch else "no change needed"))
        st.rerun()
    pick = st.selectbox("Open astronaut", list(ss.crew))
    astronaut_panel(pick)

# ---------------------------------------------------------------- login
st.title("🛰️ AstroFit")
st.caption("A digital twin of every astronaut's body, so they land strong enough to walk.")

if ss.user is None:
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            if u in USERS and USERS[u]["hash"] == h(p):
                ss.user = u
                st.rerun()
            else:
                st.error("Wrong username or password")
    st.caption("Demo: lee / lee123 · doctor / doc123")
    st.stop()

user = USERS[ss.user]

# ---------------------------------------------------------------- mission controls (sidebar)
with st.sidebar:
    st.write(f"Logged in as **{ss.user}** ({user['role']})")
    if st.button("Log out"):
        ss.user = None
        st.rerun()
    st.divider()
    st.header("🚀 Mission simulator")
    adherence = st.slider("How much of the plan the crew actually does", 0, 100, 100, 10) / 100
    sleep_ok = not st.checkbox("😴 Bad sleep")
    food_ok = not st.checkbox("🥫 Poor nutrition")
    c1, c2 = st.columns(2)
    if c1.button("⏩ +7 days"):
        simulate_days(7, adherence, sleep_ok, food_ok); st.rerun()
    if c2.button("⏩ +30 days"):
        simulate_days(30, adherence, sleep_ok, food_ok); st.rerun()

    st.divider()
    if user["role"] == "doctor":
        if st.button("💾 Save encrypted mission data"):
            try:
                from cryptography.fernet import Fernet
                if not os.path.exists("secret.key"):
                    open("secret.key", "wb").write(Fernet.generate_key())
                key = open("secret.key", "rb").read()
                data = json.dumps({"day": ss.day, "crew": ss.crew}).encode()
                open("mission_data.enc", "wb").write(Fernet(key).encrypt(data))
                st.success("Saved to mission_data.enc (encrypted)")
            except Exception as e:
                st.error(f"Save failed: {e}")
        if st.button("🔄 Restart mission"):
            ss.crew = new_crew(); ss.day = 0
            st.rerun()

# ---------------------------------------------------------------- main view (privacy: role-based)
if user["role"] == "doctor":
    doctor_overview()
else:
    astronaut_panel(user["astronaut"])   # astronauts can ONLY see their own data
