"""Simple 2D astronaut drawn with SVG. Each body part is coloured by its predicted landing-day status."""

MOUTHS = {"green": "M88 62 Q100 72 112 62",   # smile
          "yellow": "M88 66 L112 66",         # flat
          "red": "M88 70 Q100 60 112 70"}     # frown


def avatar_svg(colors, scores, skin="#f1c27d", hair="#4a2c16", mood="green"):
    """colors / scores: dicts keyed by score name (leg_bone, spine_bone, leg_muscle, upper_muscle, core_muscle, heart)."""
    def part(shape, key, label):
        # <title> gives a hover tooltip with the part's name and score
        return f'<g><title>{label}: {scores[key]:.1f}% on landing</title>{shape.format(c=colors[key])}</g>'

    def bone(x, y1, y2, w):
        # dark border line underneath so the bone shows even on a body part of the same colour
        line = f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke-linecap="round" '
        return line + f'stroke="#1a1a1a" stroke-width="{w + 4}"/>' + line + 'stroke="{c}" stroke-width="' + str(w) + '"/>'

    return f'''
<svg viewBox="0 0 200 300" width="220">
  {part('<rect x="40" y="95" width="22" height="90" rx="11" fill="{c}"/>', "upper_muscle", "Left arm")}
  {part('<rect x="138" y="95" width="22" height="90" rx="11" fill="{c}"/>', "upper_muscle", "Right arm")}
  {part('<rect x="65" y="90" width="70" height="95" rx="18" fill="{c}"/>', "core_muscle", "Core")}
  {part(bone(100, 98, 178, 6), "spine_bone", "Spine")}
  {part('<circle cx="112" cy="118" r="8" fill="{c}" stroke="#1a1a1a" stroke-width="2"/>', "heart", "Heart")}
  {part('<rect x="68" y="188" width="28" height="95" rx="12" fill="{c}"/>', "leg_muscle", "Left leg")}
  {part('<rect x="104" y="188" width="28" height="95" rx="12" fill="{c}"/>', "leg_muscle", "Right leg")}
  {part(bone(82, 195, 275, 5), "leg_bone", "Left leg bone")}
  {part(bone(118, 195, 275, 5), "leg_bone", "Right leg bone")}
  <circle cx="100" cy="50" r="34" fill="{skin}"/>
  <path d="M66 46 Q100 0 134 46 Q100 30 66 46 Z" fill="{hair}"/>
  <circle cx="88" cy="50" r="4" fill="#222"/><circle cx="112" cy="50" r="4" fill="#222"/>
  <path d="{MOUTHS[mood]}" stroke="#222" stroke-width="3" fill="none" stroke-linecap="round"/>
</svg>
<div style="font-size:12px;color:#aaa">Arms = upper body, torso = core, legs = leg muscle<br>
center line = spine, dot = heart, inner leg lines = leg bones</div>'''
