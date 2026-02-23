"""
Scenario Pool - Hardcoded templates with randomized parameters.
Generates unique engineering problems without AI API calls.
Each template defines the math and produces script_data compatible
with the existing diagram generation pipeline.
"""
import logging
import random
import math
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class ParamRange:
    """Defines a randomizable numeric parameter."""
    min_val: float
    max_val: float
    step: float = 1.0
    unit: str = ""

    def sample(self) -> float:
        steps = int((self.max_val - self.min_val) / self.step)
        return self.min_val + random.randint(0, steps) * self.step


@dataclass
class ChoiceParam:
    """A parameter that selects from a list of discrete options."""
    choices: list

    def sample(self):
        return random.choice(self.choices)


@dataclass
class ScenarioTemplate:
    """A template that generates unique problem variants."""
    id: str
    category: str
    tags: list[str]
    diagram_type: str  # "beam", "fbd", "stress", "stress_strain_curve", "infographic"
    params: dict[str, ParamRange | ChoiceParam]
    solve: Callable[[dict], dict]
    format_hook: Callable[[dict], str]
    format_diagram_desc: Callable[[dict], str]
    format_steps: Callable[[dict], list[dict]]
    format_options: Callable[[dict, dict], list[str]] | None = None  # None for infographics
    format_explanation: Callable[[dict, dict], str] = lambda p, s: ""
    engagement_format: str = "quiz_abcd"  # "quiz_abcd", "identify", "true_false", "infographic"
    format_key_facts: Callable[[dict, dict], list[str]] | None = None
    format_formula: Callable[[dict, dict], str] | None = None
    format_tweet: Callable[[dict, dict, str], str] | None = None  # (params, solved, eng_format) -> tweet text


# --- Tweet text pools (casual, engaging, varied) ---

_QUIZ_TWEETS = [
    "most engineers get this wrong on their first try",
    "this looks simple but watch out for the trick",
    "my professor used to put this on every exam",
    "how fast can you solve this one?",
    "if you get this right you're ready for your exam",
    "engineering students... can you get this?",
    "quick statics problem. go.",
    "pause and try this before scrolling",
    "this is the kind of problem that separates A students from B students",
    "you either see it instantly or you don't",
    "be honest... did you get it right?",
    "your statics professor is watching. no pressure.",
    "30 seconds. that's all you need.",
    "I failed this type of problem in my first year. don't be like me",
    "real talk... this one is tricky",
    "nobody gets D on this one",
    "comment your answer before checking",
    "tag someone who needs to practice this",
    "this comes up in every FE exam",
]

_TF_TWEETS = [
    "true or false? most people guess wrong on this one",
    "this trips up so many engineering students",
    "sounds right... but is it?",
    "your gut feeling might be wrong on this one",
    "one of the most common misconceptions in mechanics",
    "I bet half of you get this wrong",
    "think before you answer this one",
    "this shows up on exams more than you'd think",
]

_IDENTIFY_TWEETS = [
    "can you identify this point on the curve?",
    "name that point. engineering students should know this",
    "if you can't identify this you need to review your notes",
    "this comes up in every materials science exam",
    "stress-strain basics. do you know your stuff?",
    "how well do you actually know the stress-strain curve?",
]

_INFOGRAPHIC_TWEETS = [
    "save this for your next exam",
    "one of the most useful concepts in engineering",
    "if your professor didn't explain this well, here you go",
    "bookmark this. you'll need it later",
    "the concept that makes everything else click",
    "engineering fundamentals in one image",
    "I wish someone explained this to me this clearly in school",
    "this is the kind of stuff that shows up on the FE exam",
]


def _pick_tweet(pool: list[str]) -> str:
    """Pick a random tweet from a pool."""
    return random.choice(pool)


class ScenarioPool:
    """Manages all scenario templates and generates randomized problems."""

    def __init__(self):
        self.templates: list[ScenarioTemplate] = []
        self._register_all_templates()

    def _register_all_templates(self):
        self.templates.extend(_beam_templates())
        self.templates.extend(_fbd_templates())
        self.templates.extend(_stress_templates())
        self.templates.extend(_moment_templates())
        self.templates.extend(_stress_strain_templates())
        self.templates.extend(_concept_templates())
        logger.info("Registered %d templates", len(self.templates))

    def generate(self, topic: str = "", category: str = "", description: str = "",
                 recent_template_ids: list[str] | None = None) -> dict:
        """Select a template and generate a randomized problem.

        Args:
            recent_template_ids: Template IDs used recently. These will be
                deprioritized so content cycles through all templates before repeating.
        """
        candidates = self._match_templates(topic, category, description)
        if not candidates:
            candidates = self.templates

        template = self._pick_template(candidates, recent_template_ids or [])
        logger.info("Selected template: %s", template.id)

        sampled = {name: p.sample() for name, p in template.params.items()}
        logger.debug("Sampled params: %s", sampled)

        solved = template.solve(sampled)

        # Base result common to all formats
        result = {
            "type": template.engagement_format if template.engagement_format != "quiz_abcd" else "problem",
            "hook_text": template.format_hook(sampled),
            "diagram_description": template.format_diagram_desc(sampled),
            "content_steps": template.format_steps(sampled),
            "explanation": template.format_explanation(sampled, solved),
        }

        fmt = template.engagement_format

        if fmt in ("quiz_abcd", "identify"):
            # Standard 4-option quiz (identify is same format, different CTA)
            raw_options = template.format_options(sampled, solved)
            correct_text = raw_options[0]
            random.shuffle(raw_options)
            letters = ["A", "B", "C", "D"]
            correct_letter = letters[raw_options.index(correct_text)]
            result["answer_options"] = [f"{letters[i]}: {raw_options[i]}" for i in range(4)]
            result["correct_answer"] = correct_letter
            result["cta_text"] = "Comment your answer!" if fmt == "identify" else "Comment A, B, C, or D!"

        elif fmt == "true_false":
            options = template.format_options(sampled, solved)
            # options[0] = statement text, options[1] = "True" or "False"
            result["statement"] = options[0]
            result["correct_answer"] = options[1]
            result["answer_options"] = ["True", "False"]
            result["cta_text"] = "Comment TRUE or FALSE!"

        elif fmt == "infographic":
            result["key_facts"] = template.format_key_facts(sampled, solved) if template.format_key_facts else []
            result["formula"] = template.format_formula(sampled, solved) if template.format_formula else ""
            result["cta_text"] = "Save this for your exam!"

        # Generate casual tweet text (separate from diagram title)
        if template.format_tweet:
            result["tweet_text"] = template.format_tweet(sampled, solved, fmt)
        else:
            # Pick from pool based on format
            if fmt in ("quiz_abcd",):
                result["tweet_text"] = _pick_tweet(_QUIZ_TWEETS)
            elif fmt == "identify":
                result["tweet_text"] = _pick_tweet(_IDENTIFY_TWEETS)
            elif fmt == "true_false":
                result["tweet_text"] = _pick_tweet(_TF_TWEETS)
            elif fmt == "infographic":
                result["tweet_text"] = _pick_tweet(_INFOGRAPHIC_TWEETS)
            else:
                result["tweet_text"] = _pick_tweet(_QUIZ_TWEETS)

        result["template_id"] = template.id
        return result

    def _pick_template(
        self,
        candidates: list[ScenarioTemplate],
        recent_ids: list[str],
    ) -> ScenarioTemplate:
        """Pick a template, deprioritizing recently used ones.

        Templates not in the recent list are strongly preferred. If all
        candidates have been used recently, the least-recently-used one
        is chosen (LRU behaviour).
        """
        if not recent_ids:
            return random.choice(candidates)

        # Prefer candidates that haven't been used recently
        fresh = [t for t in candidates if t.id not in recent_ids]
        if fresh:
            return random.choice(fresh)

        # All candidates were used recently — pick the one used longest ago (LRU)
        id_to_recency = {tid: idx for idx, tid in enumerate(recent_ids)}
        candidates_sorted = sorted(
            candidates, key=lambda t: id_to_recency.get(t.id, -1)
        )
        return candidates_sorted[0]

    def _match_templates(self, topic: str, category: str, description: str) -> list[ScenarioTemplate]:
        search_text = f"{topic} {category} {description}".lower()
        scored = []
        for t in self.templates:
            score = sum(1 for tag in t.tags if tag in search_text)
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda x: -x[0])
        if scored:
            max_score = scored[0][0]
            return [t for s, t in scored if s == max_score]
        return []


# ============================================================
# BEAM REACTION TEMPLATES
# ============================================================

def _beam_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Simply supported, center load ---
    templates.append(ScenarioTemplate(
        id="beam_ss_center",
        category="beam_reactions",
        tags=["beam", "simply supported", "reaction", "center", "point load", "loading"],
        diagram_type="beam",
        params={
            "length": ParamRange(4, 12, step=2, unit="m"),
            "load": ParamRange(10, 50, step=5, unit="kN"),
        },
        solve=lambda p: {"ra": p["load"] / 2, "rb": p["load"] / 2},
        format_hook=lambda p: "Can you solve this Beam loading analysis problem?",
        format_diagram_desc=lambda p: (
            f"Simply supported beam, {p['length']:.0f}m length. "
            f"Pin support at left end (A), roller support at right end (B). "
            f"Point load of {p['load']:.0f} kN applied at center "
            f"({p['length']/2:.0f}m from each end)."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m beam with {p['load']:.0f} kN center load", "highlight": "load"},
            {"text": "Find: Reaction forces at A and B", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"Ra = {s['ra']:.0f} kN, Rb = {s['rb']:.0f} kN",
            f"Ra = {p['load']:.0f} kN, Rb = 0 kN",
            f"Ra = {s['ra']+2:.0f} kN, Rb = {s['rb']-2:.0f} kN",
            f"Ra = {s['ra']*2:.0f} kN, Rb = {s['rb']*2:.0f} kN",
        ],
        format_explanation=lambda p, s: (
            f"By symmetry, each support carries half the load: "
            f"{p['load']:.0f} / 2 = {s['ra']:.0f} kN each"
        ),
    ))

    # --- 2. Simply supported, off-center load ---
    templates.append(ScenarioTemplate(
        id="beam_ss_offset",
        category="beam_reactions",
        tags=["beam", "simply supported", "reaction", "offset", "point load", "loading", "asymmetric"],
        diagram_type="beam",
        params={
            "length": ParamRange(6, 12, step=2, unit="m"),
            "load": ParamRange(10, 40, step=5, unit="kN"),
            "dist_a": ParamRange(2, 4, step=1, unit="m"),  # distance from A
        },
        solve=lambda p: {
            "rb": round(p["load"] * p["dist_a"] / p["length"], 1),
            "ra": round(p["load"] * (p["length"] - p["dist_a"]) / p["length"], 1),
        },
        format_hook=lambda p: "Can you solve this Beam reaction problem?",
        format_diagram_desc=lambda p: (
            f"Simply supported beam, {p['length']:.0f}m length. "
            f"Pin support at left end (A), roller support at right end (B). "
            f"Point load of {p['load']:.0f} kN applied at {p['dist_a']:.0f}m from left end."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m beam, {p['load']:.0f} kN load at {p['dist_a']:.0f}m from A", "highlight": "load position"},
            {"text": "Find: Reaction forces Ra and Rb", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"Ra = {s['ra']:.1f} kN, Rb = {s['rb']:.1f} kN",
            # swapped — but if ra==rb use offset wrong answer
            f"Ra = {s['ra']+2:.1f} kN, Rb = {s['rb']-2:.1f} kN" if abs(s['ra'] - s['rb']) < 0.5
                else f"Ra = {s['rb']:.1f} kN, Rb = {s['ra']:.1f} kN",
            f"Ra = {p['load']:.1f} kN, Rb = 0 kN",  # all on one support
            f"Ra = {round(s['ra'] * 1.3, 1)} kN, Rb = {round(s['rb'] * 0.7, 1)} kN",  # factor error
        ],
        format_explanation=lambda p, s: (
            f"Taking moments about A: Rb = {p['load']:.0f} x {p['dist_a']:.0f} / {p['length']:.0f} = {s['rb']:.1f} kN. "
            f"Ra = {p['load']:.0f} - {s['rb']:.1f} = {s['ra']:.1f} kN"
        ),
    ))

    # --- 3. Simply supported, two point loads ---
    templates.append(ScenarioTemplate(
        id="beam_ss_two_loads",
        category="beam_reactions",
        tags=["beam", "simply supported", "reaction", "two loads", "point load", "loading", "multiple"],
        diagram_type="beam",
        params={
            "length": ParamRange(8, 12, step=2, unit="m"),
            "load1": ParamRange(10, 30, step=5, unit="kN"),
            "load2": ParamRange(10, 30, step=5, unit="kN"),
            "dist1": ParamRange(2, 3, step=1, unit="m"),
            "dist2": ParamRange(5, 7, step=1, unit="m"),
        },
        solve=lambda p: {
            "rb": round((p["load1"] * p["dist1"] + p["load2"] * p["dist2"]) / p["length"], 1),
            "ra": round(p["load1"] + p["load2"] - (p["load1"] * p["dist1"] + p["load2"] * p["dist2"]) / p["length"], 1),
        },
        format_hook=lambda p: "Can you find the beam reactions?",
        format_diagram_desc=lambda p: (
            f"Simply supported beam, {p['length']:.0f}m length. "
            f"Pin support at left end (A), roller support at right end (B). "
            f"Point load of {p['load1']:.0f} kN at {p['dist1']:.0f}m from A. "
            f"Point load of {p['load2']:.0f} kN at {p['dist2']:.0f}m from A."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m beam with {p['load1']:.0f} kN at {p['dist1']:.0f}m and {p['load2']:.0f} kN at {p['dist2']:.0f}m", "highlight": "loads"},
            {"text": "Find: Reaction forces at A and B", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"Ra = {s['ra']:.1f} kN, Rb = {s['rb']:.1f} kN",
            # swapped — but if ra≈rb, use offset instead
            f"Ra = {s['ra']+3:.1f} kN, Rb = {s['rb']-3:.1f} kN" if abs(s['ra'] - s['rb']) < 0.5
                else f"Ra = {s['rb']:.1f} kN, Rb = {s['ra']:.1f} kN",
            f"Ra = {p['load1']+p['load2']:.1f} kN, Rb = 0 kN",  # all on one support
            # "each takes one load" — guard against matching correct or swapped
            f"Ra = {s['ra']*1.3:.1f} kN, Rb = {s['rb']*0.7:.1f} kN"
                if (abs(s['ra'] - p['load1']) < 0.5 and abs(s['rb'] - p['load2']) < 0.5)
                or (abs(s['rb'] - p['load1']) < 0.5 and abs(s['ra'] - p['load2']) < 0.5)
                else f"Ra = {p['load1']:.1f} kN, Rb = {p['load2']:.1f} kN",
        ],
        format_explanation=lambda p, s: (
            f"Sum moments about A: Rb x {p['length']:.0f} = "
            f"{p['load1']:.0f} x {p['dist1']:.0f} + {p['load2']:.0f} x {p['dist2']:.0f}. "
            f"Rb = {s['rb']:.1f} kN, Ra = {s['ra']:.1f} kN"
        ),
    ))

    # --- 4. Cantilever, end load ---
    templates.append(ScenarioTemplate(
        id="beam_cantilever_end",
        category="beam_reactions",
        tags=["beam", "cantilever", "reaction", "end load", "fixed", "moment"],
        diagram_type="beam",
        params={
            "length": ParamRange(2, 8, step=1, unit="m"),
            "load": ParamRange(5, 40, step=5, unit="kN"),
        },
        solve=lambda p: {
            "reaction": p["load"],
            "moment": p["load"] * p["length"],
        },
        format_hook=lambda p: "Can you solve this cantilever beam problem?",
        format_diagram_desc=lambda p: (
            f"Cantilever beam, {p['length']:.0f}m length. "
            f"Fixed support at left end (A). "
            f"Point load of {p['load']:.0f} kN applied at the free right end."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m cantilever with {p['load']:.0f} kN end load", "highlight": "cantilever"},
            {"text": "Find: Reaction force and moment at A", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"R = {s['reaction']:.0f} kN, M = {s['moment']:.0f} kNm",
            f"R = {s['reaction']:.0f} kN, M = {s['moment']/2:.0f} kNm",  # half moment
            f"R = {s['reaction']/2:.0f} kN, M = {s['moment']:.0f} kNm",  # half reaction
            f"R = {s['reaction']:.0f} kN, M = {s['moment']*2:.0f} kNm",  # double moment
        ],
        format_explanation=lambda p, s: (
            f"For a cantilever: R = P = {s['reaction']:.0f} kN, "
            f"M = P x L = {p['load']:.0f} x {p['length']:.0f} = {s['moment']:.0f} kNm"
        ),
    ))

    # --- 5. Cantilever, mid load ---
    templates.append(ScenarioTemplate(
        id="beam_cantilever_mid",
        category="beam_reactions",
        tags=["beam", "cantilever", "reaction", "mid load", "fixed"],
        diagram_type="beam",
        params={
            "length": ParamRange(4, 8, step=1, unit="m"),
            "load": ParamRange(10, 40, step=5, unit="kN"),
            "dist": ParamRange(2, 3, step=1, unit="m"),  # distance from fixed end
        },
        solve=lambda p: {
            "reaction": p["load"],
            "moment": p["load"] * p["dist"],
        },
        format_hook=lambda p: "Can you solve this cantilever problem?",
        format_diagram_desc=lambda p: (
            f"Cantilever beam, {p['length']:.0f}m length. "
            f"Fixed support at left end (A). "
            f"Point load of {p['load']:.0f} kN applied at {p['dist']:.0f}m from the fixed end."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m cantilever, {p['load']:.0f} kN at {p['dist']:.0f}m from fixed end", "highlight": "load"},
            {"text": "Find: Reaction force and moment at fixed support", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"R = {s['reaction']:.0f} kN, M = {s['moment']:.0f} kNm",
            f"R = {s['reaction']:.0f} kN, M = {p['load'] * p['length']:.0f} kNm",  # used full length
            f"R = {s['reaction']/2:.0f} kN, M = {s['moment']:.0f} kNm",
            f"R = {s['reaction']:.0f} kN, M = {s['moment']/2:.0f} kNm",
        ],
        format_explanation=lambda p, s: (
            f"R = P = {s['reaction']:.0f} kN (equilibrium). "
            f"M = P x a = {p['load']:.0f} x {p['dist']:.0f} = {s['moment']:.0f} kNm"
        ),
    ))

    # --- 6. Simply supported, UDL ---
    templates.append(ScenarioTemplate(
        id="beam_ss_udl",
        category="beam_reactions",
        tags=["beam", "simply supported", "reaction", "distributed", "udl", "uniform", "loading"],
        diagram_type="beam",
        params={
            "length": ParamRange(4, 10, step=2, unit="m"),
            "w": ParamRange(2, 10, step=1, unit="kN/m"),
        },
        solve=lambda p: {
            "total_load": p["w"] * p["length"],
            "ra": p["w"] * p["length"] / 2,
            "rb": p["w"] * p["length"] / 2,
        },
        format_hook=lambda p: "Can you solve this distributed load problem?",
        format_diagram_desc=lambda p: (
            f"Simply supported beam, {p['length']:.0f}m length. "
            f"Pin support at left end (A), roller support at right end (B). "
            f"Uniformly distributed load of {p['w']:.0f} kN/m along entire beam. "
            f"Total load {p['w'] * p['length']:.0f} kN at center."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['length']:.0f}m beam with UDL of {p['w']:.0f} kN/m", "highlight": "distributed load"},
            {"text": "Find: Reaction forces at A and B", "highlight": "reactions"},
        ],
        format_options=lambda p, s: [
            f"Ra = {s['ra']:.0f} kN, Rb = {s['rb']:.0f} kN",
            f"Ra = {p['w']:.0f} kN, Rb = {p['w']:.0f} kN",  # forgot to multiply by length
            f"Ra = {s['total_load']:.0f} kN, Rb = 0 kN",  # all on one support
            f"Ra = {s['ra']+3:.0f} kN, Rb = {s['rb']-3:.0f} kN",  # unequal
        ],
        format_explanation=lambda p, s: (
            f"Total load = {p['w']:.0f} x {p['length']:.0f} = {s['total_load']:.0f} kN. "
            f"By symmetry: Ra = Rb = {s['total_load']:.0f} / 2 = {s['ra']:.0f} kN"
        ),
    ))

    return templates


# ============================================================
# FREE BODY DIAGRAM TEMPLATES
# ============================================================

def _fbd_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Two forces, find resultant ---
    templates.append(ScenarioTemplate(
        id="fbd_resultant",
        category="force_equilibrium",
        tags=["force", "resultant", "vector", "fbd", "free body", "addition", "rope"],
        diagram_type="fbd",
        params={
            "f1": ParamRange(20, 80, step=10, unit="N"),
            "f2": ParamRange(20, 80, step=10, unit="N"),
            "angle": ParamRange(45, 120, step=15, unit="deg"),
        },
        solve=lambda p: {
            "resultant": round(math.sqrt(
                p["f1"]**2 + p["f2"]**2 + 2 * p["f1"] * p["f2"] * math.cos(math.radians(p["angle"]))
            ), 1),
        },
        format_hook=lambda p: (
            f"Two ropes pull a ring bolt.\nFind the resultant force."
        ),
        format_diagram_desc=lambda p: (
            f"Free body diagram with forces. Find the resultant. "
            f"F1 = {p['f1']:.0f} N at 0 degrees. "
            f"F2 = {p['f2']:.0f} N at {p['angle']:.0f} degrees."
        ),
        format_steps=lambda p: [
            {"text": f"Given: F1 = {p['f1']:.0f} N, F2 = {p['f2']:.0f} N, angle = {p['angle']:.0f} deg", "highlight": "forces"},
            {"text": "Find: Magnitude of resultant force", "highlight": "resultant"},
        ],
        format_options=lambda p, s: [
            f"R = {s['resultant']:.1f} N",
            f"R = {p['f1'] + p['f2']:.0f} N",  # simple addition (wrong)
            f"R = {abs(p['f1'] - p['f2']):.0f} N",  # subtraction
            f"R = {round(s['resultant'] * 1.2, 1)} N",  # slightly off
        ],
        format_explanation=lambda p, s: (
            f"R = sqrt(F1² + F2² + 2·F1·F2·cosθ) = "
            f"sqrt({p['f1']:.0f}² + {p['f2']:.0f}² + 2·{p['f1']:.0f}·{p['f2']:.0f}·cos({p['angle']:.0f}°)) "
            f"= {s['resultant']:.1f} N"
        ),
    ))

    # --- 2. Hanging weight from two cables — find cable tension ---
    templates.append(ScenarioTemplate(
        id="fbd_cable_tension",
        category="force_equilibrium",
        tags=["force", "equilibrium", "cable", "tension", "hanging", "weight"],
        diagram_type="fbd_cables",
        params={
            "mass": ParamRange(10, 50, step=5, unit="kg"),
            "angle": ParamRange(30, 60, step=5, unit="deg"),
        },
        solve=lambda p: {
            "weight": round(p["mass"] * 9.81, 1),
            "tension": round(p["mass"] * 9.81 / (2 * math.sin(math.radians(p["angle"]))), 1),
        },
        format_hook=lambda p: (
            f"Find the cable tension\n({p['mass']:.0f} kg, θ = {p['angle']:.0f}°)"
        ),
        format_diagram_desc=lambda p: (
            f"Hanging weight from two cables. "
            f"mass = {p['mass']:.0f} kg, angle = {p['angle']:.0f} degrees from horizontal."
        ),
        format_steps=lambda p: [
            {"text": f"Given: mass = {p['mass']:.0f} kg, cable angle = {p['angle']:.0f}° from horizontal", "highlight": "cables"},
            {"text": "Find: Tension in each cable", "highlight": "tension"},
        ],
        format_options=lambda p, s: [
            f"T = {s['tension']:.1f} N",
            f"T = {round(s['weight'] / 2, 1)} N",  # divided by 2 but forgot sinθ
            f"T = {round(s['tension'] * 0.7, 1)} N",  # used cosθ instead of sinθ
            f"T = {round(s['tension'] * 1.4, 1)} N",  # slightly off
        ],
        format_explanation=lambda p, s: (
            f"Equilibrium: 2T·sin(θ) = W → T = W/(2·sinθ) = "
            f"{s['weight']:.1f}/(2·sin({p['angle']:.0f}°)) = {s['tension']:.1f} N"
        ),
    ))

    # --- 3. Inclined plane ---
    templates.append(ScenarioTemplate(
        id="fbd_inclined_plane",
        category="force_equilibrium",
        tags=["force", "incline", "plane", "friction", "fbd", "free body", "block", "slope"],
        diagram_type="fbd",
        params={
            "mass": ParamRange(5, 30, step=5, unit="kg"),
            "angle": ParamRange(15, 40, step=5, unit="deg"),  # max 40 to avoid cos=sin at 45
        },
        solve=lambda p: {
            "weight": round(p["mass"] * 9.81, 1),
            "normal": round(p["mass"] * 9.81 * math.cos(math.radians(p["angle"])), 1),
            "parallel": round(p["mass"] * 9.81 * math.sin(math.radians(p["angle"])), 1),
        },
        format_hook=lambda p: f"Find the normal force\n(m = {p['mass']:.0f} kg, θ = {p['angle']:.0f}°)",
        format_diagram_desc=lambda p: (
            f"Free body diagram with forces. "
            f"W = {p['mass'] * 9.81:.0f} N at 270 degrees. "
            f"Block on {p['angle']:.0f} deg incline. "
            f"Mass = {p['mass']:.0f} kg."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {p['mass']:.0f} kg block on {p['angle']:.0f} deg incline", "highlight": "incline"},
            {"text": "Find: Normal force (N) perpendicular to the slope", "highlight": "normal force"},
        ],
        format_options=lambda p, s: [
            f"N = {s['normal']:.1f} N",
            f"N = {s['weight']:.1f} N",  # forgot cos component (used full weight)
            f"N = {s['parallel']:.1f} N",  # used sin instead of cos
            f"N = {round(s['normal'] * 0.75, 1)} N",  # factor error
        ],
        format_explanation=lambda p, s: (
            f"N = mg x cos(θ) = {p['mass']:.0f} x 9.81 x cos({p['angle']:.0f}°) = {s['normal']:.1f} N"
        ),
    ))

    return templates


# ============================================================
# STRESS/STRAIN TEMPLATES
# ============================================================

def _stress_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Axial stress ---
    templates.append(ScenarioTemplate(
        id="stress_axial",
        category="stress_strain",
        tags=["stress", "axial", "rod", "bar", "tension", "compression", "cross section"],
        diagram_type="stress",
        params={
            "force": ParamRange(10, 100, step=10, unit="kN"),
            "diameter": ParamRange(20, 60, step=10, unit="mm"),
        },
        solve=lambda p: {
            "area": round(math.pi * (p["diameter"] / 2)**2, 1),  # mm^2
            "stress": round(p["force"] * 1000 / (math.pi * (p["diameter"] / 2)**2), 1),  # MPa
        },
        format_hook=lambda p: "Find the axial stress (σ)",
        format_diagram_desc=lambda p: (
            f"Axial stress in a circular rod. "
            f"Force of {p['force']:.0f} kN applied to a rod with "
            f"diameter {p['diameter']:.0f} mm."
        ),
        format_steps=lambda p: [
            {"text": f"Given: F = {p['force']:.0f} kN, diameter = {p['diameter']:.0f} mm", "highlight": "cross section"},
            {"text": "Find: Axial stress (MPa)", "highlight": "stress"},
        ],
        format_options=lambda p, s: [
            f"σ = {s['stress']:.1f} MPa",
            f"σ = {round(p['force'] * 1000 / (math.pi * p['diameter']**2), 1)} MPa",  # forgot /4 in area
            f"σ = {round(s['stress'] / 2, 1)} MPa",
            f"σ = {round(s['stress'] * 1.5, 1)} MPa",
        ],
        format_explanation=lambda p, s: (
            f"A = pi*d^2/4 = pi*{p['diameter']:.0f}^2/4 = {s['area']:.1f} mm^2. "
            f"sigma = F/A = {p['force']*1000:.0f}/{s['area']:.1f} = {s['stress']:.1f} MPa"
        ),
    ))

    # --- 2. Shear stress in bolt(s) connecting two plates ---
    templates.append(ScenarioTemplate(
        id="stress_shear",
        category="stress_strain",
        tags=["stress", "shear", "pin", "bolt", "connection"],
        diagram_type="shear",
        params={
            "force": ParamRange(10, 80, step=5, unit="kN"),
            "diameter": ParamRange(10, 25, step=5, unit="mm"),
            "bolts": ParamRange(1, 3, step=1, unit=""),
        },
        solve=lambda p: {
            "area_one": round(math.pi * (p["diameter"] / 2)**2, 1),
            "area_total": round(p["bolts"] * math.pi * (p["diameter"] / 2)**2, 1),
            "shear": round(p["force"] * 1000 / (p["bolts"] * math.pi * (p["diameter"] / 2)**2), 1),
        },
        format_hook=lambda p: (
            f"Find the shear stress (τ)\n({int(p['bolts'])} bolt{'s' if p['bolts'] > 1 else ''}, d = {p['diameter']:.0f} mm)"
        ),
        format_diagram_desc=lambda p: (
            f"Shear stress in a bolt connection. "
            f"Force of {p['force']:.0f} kN on {int(p['bolts'])} bolt{'s' if p['bolts'] > 1 else ''} with "
            f"diameter {p['diameter']:.0f} mm in single shear."
        ),
        format_steps=lambda p: [
            {"text": f"Given: F = {p['force']:.0f} kN, {int(p['bolts'])} bolt(s), d = {p['diameter']:.0f} mm", "highlight": "shear"},
            {"text": "Find: Shear stress in each bolt (MPa)", "highlight": "shear stress"},
        ],
        format_options=lambda p, s: [
            f"τ = {s['shear']:.1f} MPa",
            # "forgot to divide by bolt count" — only different when bolts > 1
            f"τ = {round(s['shear'] * p['bolts'], 1)} MPa" if p['bolts'] > 1
                else f"τ = {round(s['shear'] * 2, 1)} MPa",
            f"τ = {round(s['shear'] * 1.5, 1)} MPa",  # 1.5x factor error
            f"τ = {round(s['shear'] * 0.6, 1)} MPa",
        ],
        format_explanation=lambda p, s: (
            f"A_bolt = pi*d^2/4 = {s['area_one']:.1f} mm^2. "
            f"τ = F/(n*A) = {p['force']*1000:.0f}/({int(p['bolts'])}*{s['area_one']:.1f}) = {s['shear']:.1f} MPa"
        ),
    ))

    # --- 3. Bar elongation ---
    templates.append(ScenarioTemplate(
        id="strain_elongation",
        category="stress_strain",
        tags=["strain", "elongation", "deformation", "bar", "rod", "elastic", "young"],
        diagram_type="stress",
        params={
            "force": ParamRange(20, 100, step=10, unit="kN"),
            "length": ParamRange(1, 4, step=0.5, unit="m"),
            "diameter": ParamRange(20, 50, step=10, unit="mm"),
            "E": ParamRange(200, 200, step=1, unit="GPa"),  # steel, fixed
        },
        solve=lambda p: {
            "area": round(math.pi * (p["diameter"] / 2)**2, 2),
            "delta": round(
                (p["force"] * 1000 * p["length"] * 1000) /
                (math.pi * (p["diameter"] / 2)**2 * p["E"] * 1000), 2
            ),  # mm
        },
        format_hook=lambda p: "Find the elongation\nin the bar (δ)",
        format_diagram_desc=lambda p: (
            f"Axial elongation of a steel bar under tension. "
            f"Force of {p['force']:.0f} kN on a steel bar, length {p['length']:.1f} m, "
            f"diameter {p['diameter']:.0f} mm, modulus E = {p['E']:.0f} GPa."
        ),
        format_steps=lambda p: [
            {"text": f"Given: F={p['force']:.0f}kN, L={p['length']:.1f}m, d={p['diameter']:.0f}mm, E={p['E']:.0f}GPa", "highlight": "properties"},
            {"text": "Find: Elongation (mm)", "highlight": "deformation"},
        ],
        format_options=lambda p, s: [
            f"δ = {s['delta']:.2f} mm",
            f"δ = {round(s['delta'] * 2, 2)} mm",
            f"δ = {round(s['delta'] / 2, 2)} mm",
            f"δ = {round(s['delta'] * 1.5, 2)} mm",
        ],
        format_explanation=lambda p, s: (
            f"delta = PL/AE = ({p['force']*1000:.0f} x {p['length']*1000:.0f}) / "
            f"({s['area']:.1f} x {p['E']*1000:.0f}) = {s['delta']:.2f} mm"
        ),
    ))

    return templates


# ============================================================
# MOMENT TEMPLATES
# ============================================================

def _moment_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Moment of a force about a point ---
    templates.append(ScenarioTemplate(
        id="moment_force",
        category="moments",
        tags=["moment", "force", "torque", "point", "lever arm"],
        diagram_type="fbd",
        params={
            "force": ParamRange(10, 50, step=5, unit="kN"),
            "distance": ParamRange(2, 8, step=1, unit="m"),
            "angle": ParamRange(30, 75, step=15, unit="deg"),
        },
        solve=lambda p: {
            "moment": round(p["force"] * p["distance"] * math.sin(math.radians(p["angle"])), 1),
        },
        format_hook=lambda p: "Can you calculate the moment?",
        format_diagram_desc=lambda p: (
            f"Free body diagram with forces. Lever problem. "
            f"F = {p['force']:.0f} kN at {p['angle']:.0f} degrees. "
            f"Lever arm d = {p['distance']:.0f} m."
        ),
        format_steps=lambda p: [
            {"text": f"Given: F = {p['force']:.0f} kN, d = {p['distance']:.0f} m, angle = {p['angle']:.0f} deg", "highlight": "lever arm"},
            {"text": "Find: Moment about the pivot point", "highlight": "moment"},
        ],
        format_options=lambda p, s: [
            f"M = {s['moment']:.1f} kNm",
            f"M = {p['force'] * p['distance']:.0f} kNm",  # forgot sin
            f"M = {round(s['moment'] * 1.5, 1)} kNm",  # common factor error
            f"M = {round(s['moment'] / 2, 1)} kNm",
        ],
        format_explanation=lambda p, s: (
            f"M = F x d x sin(theta) = {p['force']:.0f} x {p['distance']:.0f} x sin({p['angle']:.0f}) "
            f"= {s['moment']:.1f} kNm"
        ),
    ))

    # --- 2. Couple moment ---
    templates.append(ScenarioTemplate(
        id="moment_couple",
        category="moments",
        tags=["moment", "couple", "torque", "pair"],
        diagram_type="fbd",
        params={
            "force": ParamRange(10, 40, step=5, unit="kN"),
            "arm": ParamRange(1, 6, step=0.5, unit="m"),
        },
        solve=lambda p: {
            "moment": round(p["force"] * p["arm"], 1),
        },
        format_hook=lambda p: "Can you find the couple moment?",
        format_diagram_desc=lambda p: (
            f"Free body diagram with forces. "
            f"Two equal and opposite forces of {p['force']:.0f} kN "
            f"separated by {p['arm']:.1f}m."
        ),
        format_steps=lambda p: [
            {"text": f"Given: Two forces of {p['force']:.0f} kN, arm = {p['arm']:.1f}m", "highlight": "couple"},
            {"text": "Find: Couple moment", "highlight": "moment"},
        ],
        format_options=lambda p, s: [
            f"M = {s['moment']:.1f} kNm",
            f"M = {round(2 * p['force'] * p['arm'], 1)} kNm",  # doubled
            f"M = {round(s['moment'] / 2, 1)} kNm",  # halved
            f"M = {round(s['moment'] * 0.7, 1)} kNm",  # factor error
        ],
        format_explanation=lambda p, s: (
            f"Couple moment = F x d = {p['force']:.0f} x {p['arm']:.1f} = {s['moment']:.1f} kNm"
        ),
    ))

    return templates


# ============================================================
# STRESS-STRAIN CURVE TEMPLATES
# ============================================================

# Material data for stress-strain curve generation
MATERIALS = {
    "steel": {
        "name": "Mild Steel",
        "yield": 250, "ultimate": 400, "fracture_strain": 0.25,
        "E": 200, "behavior": "ductile",
        "proportional_limit": 220,
    },
    "aluminum": {
        "name": "Aluminum 6061",
        "yield": 270, "ultimate": 310, "fracture_strain": 0.12,
        "E": 69, "behavior": "ductile",
        "proportional_limit": 240,
    },
    "cast_iron": {
        "name": "Cast Iron",
        "yield": 130, "ultimate": 200, "fracture_strain": 0.005,
        "E": 100, "behavior": "brittle",
        "proportional_limit": 120,
    },
}
MATERIAL_LIST = list(MATERIALS.keys())

CURVE_POINTS = ["Yield Strength", "Ultimate Tensile Strength", "Fracture", "Proportional Limit"]

# Points that actually exist on each material's curve
MATERIAL_POINTS = {
    "steel": ["Yield Strength", "Ultimate Tensile Strength", "Fracture", "Proportional Limit"],
    "aluminum": ["Yield Strength", "Ultimate Tensile Strength", "Fracture", "Proportional Limit"],
    "cast_iron": ["Ultimate Tensile Strength", "Fracture"],  # brittle: no yield plateau or proportional limit
}


def _valid_point(material_key: str, point_idx: int) -> str:
    """Return a valid point name for this material, wrapping if needed."""
    valid = MATERIAL_POINTS[material_key]
    return valid[int(point_idx) % len(valid)]


def _stress_strain_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Identify the highlighted point ---
    templates.append(ScenarioTemplate(
        id="ss_curve_identify",
        category="stress_strain_curve",
        tags=["stress", "strain", "curve", "yield", "ultimate", "fracture", "material", "interview"],
        diagram_type="stress_strain_curve",
        engagement_format="identify",
        params={
            "material_idx": ChoiceParam(list(range(len(MATERIAL_LIST)))),
            "point_idx": ChoiceParam(list(range(len(CURVE_POINTS)))),
        },
        solve=lambda p: {
            "material": MATERIAL_LIST[int(p["material_idx"])],
            "material_data": MATERIALS[MATERIAL_LIST[int(p["material_idx"])]],
            "highlighted_point": _valid_point(MATERIAL_LIST[int(p["material_idx"])], int(p["point_idx"])),
        },
        format_hook=lambda p: f"Can you identify\nthis point?",
        format_diagram_desc=lambda p: (
            f"Stress-strain curve for {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['name']}. "
            f"Highlight point: {_valid_point(MATERIAL_LIST[int(p['material_idx'])], int(p['point_idx']))}. "
            f"Behavior: {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['behavior']}."
        ),
        format_steps=lambda p: [
            {"text": f"Material: {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['name']}", "highlight": "material"},
            {"text": "Identify the highlighted point on the curve", "highlight": "point"},
        ],
        format_options=lambda p, s: [
            s["highlighted_point"],  # correct
            # wrong answers from the remaining points (use ALL points for good distractors)
            *[pt for pt in CURVE_POINTS if pt != s["highlighted_point"]]
        ],
        format_explanation=lambda p, s: (
            f"The highlighted point is the {s['highlighted_point']} on the "
            f"{s['material_data']['name']} stress-strain curve."
        ),
    ))

    # --- 2. True/False about material behavior ---
    # Statements bank: (statement, material_key, is_true)
    TF_STATEMENTS = [
        ("Mild steel shows a clear yield plateau before strain hardening", "steel", True),
        ("Cast iron exhibits significant necking before fracture", "cast_iron", False),
        ("Aluminum 6061 has a higher elastic modulus than mild steel", "aluminum", False),
        ("Cast iron fails with very little plastic deformation", "cast_iron", True),
        ("Mild steel has greater ductility than cast iron", "steel", True),
        ("The elastic modulus of aluminum is about 69 GPa", "aluminum", True),
    ]

    templates.append(ScenarioTemplate(
        id="ss_curve_true_false",
        category="stress_strain_curve",
        tags=["stress", "strain", "curve", "material", "true false", "interview", "concept"],
        diagram_type="stress_strain_curve",
        engagement_format="true_false",
        params={
            "stmt_idx": ChoiceParam(list(range(len(TF_STATEMENTS)))),
        },
        solve=lambda p: {
            "statement": TF_STATEMENTS[int(p["stmt_idx"])][0],
            "material": TF_STATEMENTS[int(p["stmt_idx"])][1],
            "is_true": TF_STATEMENTS[int(p["stmt_idx"])][2],
        },
        format_hook=lambda p: f"True or False?\n\"{TF_STATEMENTS[int(p['stmt_idx'])][0]}\"",
        format_diagram_desc=lambda p: (
            f"Stress-strain curve for {MATERIALS[TF_STATEMENTS[int(p['stmt_idx'])][1]]['name']}. "
            f"Behavior: {MATERIALS[TF_STATEMENTS[int(p['stmt_idx'])][1]]['behavior']}. "
            f"Show all labels."
        ),
        format_steps=lambda p: [
            {"text": TF_STATEMENTS[int(p["stmt_idx"])][0], "highlight": "statement"},
        ],
        format_options=lambda p, s: [
            s["statement"],
            "True" if s["is_true"] else "False",
        ],
        format_explanation=lambda p, s: (
            f"{'TRUE' if s['is_true'] else 'FALSE'}: {s['statement']}. "
            f"{s['material'].replace('_', ' ').title()} is a "
            f"{'ductile' if MATERIALS[s['material']]['behavior'] == 'ductile' else 'brittle'} material."
        ),
    ))

    # --- 3. What's missing? (identify the hidden label) ---
    templates.append(ScenarioTemplate(
        id="ss_curve_whats_missing",
        category="stress_strain_curve",
        tags=["stress", "strain", "curve", "material", "interview", "identify"],
        diagram_type="stress_strain_curve",
        engagement_format="identify",
        params={
            "material_idx": ChoiceParam(list(range(len(MATERIAL_LIST)))),
            "hidden_idx": ChoiceParam(list(range(len(CURVE_POINTS)))),
        },
        solve=lambda p: {
            "material": MATERIAL_LIST[int(p["material_idx"])],
            "material_data": MATERIALS[MATERIAL_LIST[int(p["material_idx"])]],
            "hidden_label": _valid_point(MATERIAL_LIST[int(p["material_idx"])], int(p["hidden_idx"])),
        },
        format_hook=lambda p: "What label\nis missing?",
        format_diagram_desc=lambda p: (
            f"Stress-strain curve for {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['name']}. "
            f"Hide label: {_valid_point(MATERIAL_LIST[int(p['material_idx'])], int(p['hidden_idx']))}. "
            f"Behavior: {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['behavior']}."
        ),
        format_steps=lambda p: [
            {"text": f"Material: {MATERIALS[MATERIAL_LIST[int(p['material_idx'])]]['name']}", "highlight": "material"},
            {"text": "One label has been replaced with '?' — identify it", "highlight": "missing"},
        ],
        format_options=lambda p, s: [
            s["hidden_label"],  # correct
            *[pt for pt in CURVE_POINTS if pt != s["hidden_label"]]
        ],
        format_explanation=lambda p, s: (
            f"The missing label is the {s['hidden_label']}."
        ),
    ))

    return templates


# ============================================================
# CONCEPT / INFOGRAPHIC TEMPLATES
# ============================================================

def _concept_templates() -> list[ScenarioTemplate]:
    templates = []

    # --- 1. Hooke's Law infographic ---
    templates.append(ScenarioTemplate(
        id="concept_hookes_law_info",
        category="concepts",
        tags=["hooke", "spring", "elasticity", "concept", "infographic", "law"],
        diagram_type="infographic",
        engagement_format="infographic",
        params={
            "k": ParamRange(50, 200, step=25, unit="N/m"),
            "x": ParamRange(0.1, 0.5, step=0.05, unit="m"),
        },
        solve=lambda p: {"force": round(p["k"] * p["x"], 1)},
        format_hook=lambda p: "Hooke's Law",
        format_diagram_desc=lambda p: (
            f"Infographic: Hooke's Law. Spring diagram. "
            f"k = {p['k']:.0f} N/m, x = {p['x']:.2f} m, F = {p['k'] * p['x']:.1f} N."
        ),
        format_steps=lambda p: [
            {"text": "F = kx", "highlight": "formula"},
            {"text": f"k = {p['k']:.0f} N/m, x = {p['x']:.2f} m", "highlight": "values"},
        ],
        format_explanation=lambda p, s: "Hooke's Law: Force is proportional to displacement in the elastic region.",
        format_key_facts=lambda p, s: [
            "F = kx (force = spring constant x displacement)",
            "Only valid in the elastic region",
            f"Example: k = {p['k']:.0f} N/m, x = {p['x']:.2f} m",
            f"F = {s['force']:.1f} N",
        ],
        format_formula=lambda p, s: "F = kx",
    ))

    # --- 2. Hooke's Law quiz ---
    templates.append(ScenarioTemplate(
        id="concept_hookes_law_quiz",
        category="concepts",
        tags=["hooke", "spring", "elasticity", "concept", "quiz"],
        diagram_type="infographic",
        engagement_format="quiz_abcd",
        params={
            "k": ParamRange(50, 200, step=25, unit="N/m"),
            "x": ParamRange(0.1, 0.5, step=0.05, unit="m"),
        },
        solve=lambda p: {"force": round(p["k"] * p["x"], 1)},
        format_hook=lambda p: f"Find the spring force\n(k = {p['k']:.0f} N/m)",
        format_diagram_desc=lambda p: (
            f"Infographic: Hooke's Law. Spring diagram. "
            f"k = {p['k']:.0f} N/m, x = {p['x']:.2f} m."
        ),
        format_steps=lambda p: [
            {"text": f"Given: k = {p['k']:.0f} N/m, x = {p['x']:.2f} m", "highlight": "spring"},
            {"text": "Find: Force F", "highlight": "force"},
        ],
        format_options=lambda p, s: [
            f"F = {s['force']:.1f} N",
            f"F = {round(s['force'] * 2, 1)} N",
            f"F = {round(s['force'] / 2, 1)} N",
            f"F = {round(p['k'] + p['x'], 1)} N",
        ],
        format_explanation=lambda p, s: f"F = kx = {p['k']:.0f} x {p['x']:.2f} = {s['force']:.1f} N",
    ))

    # --- 3. Pulley system infographic ---
    templates.append(ScenarioTemplate(
        id="concept_pulleys_info",
        category="concepts",
        tags=["pulley", "mechanical advantage", "concept", "infographic", "simple machine"],
        diagram_type="infographic",
        engagement_format="infographic",
        params={
            "n_pulleys": ParamRange(1, 4, step=1, unit=""),
            "load": ParamRange(50, 200, step=25, unit="kg"),
        },
        solve=lambda p: {
            "ma": int(p["n_pulleys"]),
            "effort": round(p["load"] * 9.81 / p["n_pulleys"], 1),
            "weight": round(p["load"] * 9.81, 1),
        },
        format_hook=lambda p: f"Pulley Systems",
        format_diagram_desc=lambda p: (
            f"Infographic: Pulley system. "
            f"{int(p['n_pulleys'])} pulley{'s' if p['n_pulleys'] > 1 else ''}, "
            f"load = {p['load']:.0f} kg."
        ),
        format_steps=lambda p: [
            {"text": "MA = number of supporting ropes", "highlight": "formula"},
            {"text": f"Effort = Weight / MA", "highlight": "calculation"},
        ],
        format_explanation=lambda p, s: (
            f"With {s['ma']} pulleys, MA = {s['ma']}. "
            f"Effort = {s['weight']:.0f} N / {s['ma']} = {s['effort']:.1f} N"
        ),
        format_key_facts=lambda p, s: [
            f"Mechanical Advantage (MA) = {s['ma']}",
            f"Weight = {p['load']:.0f} kg x 9.81 = {s['weight']:.0f} N",
            f"Effort = {s['weight']:.0f} / {s['ma']} = {s['effort']:.1f} N",
            "More pulleys = less effort, but more rope to pull",
        ],
        format_formula=lambda p, s: "Effort = Weight / MA",
    ))

    # --- 4. Pulley system quiz ---
    templates.append(ScenarioTemplate(
        id="concept_pulleys_quiz",
        category="concepts",
        tags=["pulley", "mechanical advantage", "concept", "quiz", "simple machine"],
        diagram_type="infographic",
        engagement_format="quiz_abcd",
        params={
            "n_pulleys": ParamRange(2, 4, step=1, unit=""),
            "load": ParamRange(50, 200, step=25, unit="kg"),
        },
        solve=lambda p: {
            "effort": round(p["load"] * 9.81 / p["n_pulleys"], 1),
            "weight": round(p["load"] * 9.81, 1),
        },
        format_hook=lambda p: f"Find the effort force\n({int(p['n_pulleys'])} pulleys, {p['load']:.0f} kg)",
        format_diagram_desc=lambda p: (
            f"Infographic: Pulley system. "
            f"{int(p['n_pulleys'])} pulleys, load = {p['load']:.0f} kg."
        ),
        format_steps=lambda p: [
            {"text": f"Given: {int(p['n_pulleys'])} pulleys, load = {p['load']:.0f} kg", "highlight": "pulleys"},
            {"text": "Find: Effort force", "highlight": "effort"},
        ],
        format_options=lambda p, s: [
            f"F = {s['effort']:.1f} N",
            f"F = {s['weight']:.0f} N",  # forgot to divide
            f"F = {round(s['effort'] * 2, 1)} N",
            f"F = {round(s['effort'] * 0.5, 1)} N",
        ],
        format_explanation=lambda p, s: (
            f"MA = {int(p['n_pulleys'])}. "
            f"Effort = {s['weight']:.0f} / {int(p['n_pulleys'])} = {s['effort']:.1f} N"
        ),
    ))

    # --- 5. Gear ratio infographic ---
    templates.append(ScenarioTemplate(
        id="concept_gears_info",
        category="concepts",
        tags=["gear", "ratio", "concept", "infographic", "simple machine", "transmission"],
        diagram_type="infographic",
        engagement_format="infographic",
        params={
            "driver_teeth": ParamRange(15, 30, step=5, unit="teeth"),
            "driven_teeth": ParamRange(40, 80, step=10, unit="teeth"),
        },
        solve=lambda p: {
            "ratio": round(p["driven_teeth"] / p["driver_teeth"], 2),
            "speed_mult": round(p["driver_teeth"] / p["driven_teeth"], 2),
        },
        format_hook=lambda p: "Gear Ratios",
        format_diagram_desc=lambda p: (
            f"Infographic: Gear ratio. "
            f"Driver gear {int(p['driver_teeth'])} teeth, driven gear {int(p['driven_teeth'])} teeth."
        ),
        format_steps=lambda p: [
            {"text": "Gear Ratio = Driven / Driver", "highlight": "formula"},
            {"text": f"{int(p['driven_teeth'])} / {int(p['driver_teeth'])} = {p['driven_teeth']/p['driver_teeth']:.2f}", "highlight": "calc"},
        ],
        format_explanation=lambda p, s: (
            f"Gear ratio = {int(p['driven_teeth'])} / {int(p['driver_teeth'])} = {s['ratio']:.2f}. "
            f"Output speed = {s['speed_mult']:.2f}x input speed, but torque is {s['ratio']:.2f}x higher."
        ),
        format_key_facts=lambda p, s: [
            f"Driver: {int(p['driver_teeth'])} teeth, Driven: {int(p['driven_teeth'])} teeth",
            f"Gear Ratio = {s['ratio']:.2f}:1",
            f"Speed reduction: output is {s['speed_mult']:.2f}x input speed",
            f"Torque multiplication: output is {s['ratio']:.2f}x input torque",
        ],
        format_formula=lambda p, s: "GR = N_driven / N_driver",
    ))

    # --- 6. Gear ratio quiz ---
    templates.append(ScenarioTemplate(
        id="concept_gears_quiz",
        category="concepts",
        tags=["gear", "ratio", "concept", "quiz", "simple machine"],
        diagram_type="infographic",
        engagement_format="quiz_abcd",
        params={
            "driver_teeth": ParamRange(15, 30, step=5, unit="teeth"),
            "driven_teeth": ParamRange(40, 80, step=10, unit="teeth"),
        },
        solve=lambda p: {
            "ratio": round(p["driven_teeth"] / p["driver_teeth"], 2),
        },
        format_hook=lambda p: f"Find the gear ratio",
        format_diagram_desc=lambda p: (
            f"Infographic: Gear ratio. "
            f"Driver gear {int(p['driver_teeth'])} teeth, driven gear {int(p['driven_teeth'])} teeth."
        ),
        format_steps=lambda p: [
            {"text": f"Driver: {int(p['driver_teeth'])} teeth, Driven: {int(p['driven_teeth'])} teeth", "highlight": "gears"},
            {"text": "Find: Gear ratio", "highlight": "ratio"},
        ],
        format_options=lambda p, s: [
            f"GR = {s['ratio']:.2f}:1",
            f"GR = {round(p['driver_teeth']/p['driven_teeth'], 2)}:1",  # inverted
            f"GR = {round(s['ratio'] * 2, 2)}:1",
            f"GR = {round(s['ratio'] / 2, 2)}:1",
        ],
        format_explanation=lambda p, s: (
            f"GR = Driven / Driver = {int(p['driven_teeth'])} / {int(p['driver_teeth'])} = {s['ratio']:.2f}:1"
        ),
    ))

    return templates


# Singleton instance
scenario_pool = ScenarioPool()
