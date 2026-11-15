# MEC-2026
AstroFit 🛰️

A digital twin of each astronaut's body that predicts bone/muscle/heart loss in microgravity and automatically adjusts their workout plan so they land strong enough to walk.

Run it
pip install -r requirements.txt
streamlit run app.py

Logins: lee/lee123, kim/kim123, ortiz/ortiz123, park/park123 (astronauts), doctor/doc123 (flight doctor)

Files
engine.py: the model (daily_update, predict, adjust_plan, calibrate, validate_workout). Run python engine.py to test.
app.py: Streamlit dashboard, login/roles, simulator, NOAA space weather, encrypted save.

Numbers are a simplified model for the competition, not medical data.
