import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
import uuid

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Phone screen dimensions (9:16 aspect ratio)
PHONE_WIDTH = 1080 / 180  # 6 inches at 180 DPI = 1080px
PHONE_HEIGHT = 1920 / 180  # 10.67 inches at 180 DPI = 1920px
PHONE_DPI = 180  # Higher DPI for crisp phone display

# ── Layout constants (shared across all diagram types) ──────────────────
# Title
TITLE_Y = 0.97
TITLE_FONTSIZE = 18

# Answer option boxes (2x2 grid)
OPTION_Y_TOP = 0.20        # Top row y-position
OPTION_Y_BOTTOM = 0.04     # Bottom row y-position
OPTION_HEIGHT = 0.11
OPTION_WIDTH = 0.40
OPTION_LEFT_X = 0.06
OPTION_RIGHT_X = 0.54      # 0.06 + 0.40 = 0.46, gap = 0.08 to 0.54
OPTION_FONTSIZE = 13

# Colors
COLOR_BG = "#1a1a2e"
COLOR_TEAL = "#4ecca3"      # supports, option borders, blocks
COLOR_RED = "#e94560"       # applied loads / forces
COLOR_CYAN = "#00d9ff"      # reaction forces
COLOR_YELLOW = "#ffd93d"    # pivots, angles, moments
COLOR_PURPLE = "#6c5ce7"    # extra forces

# Force arrow colors (cycled for multi-force diagrams)
FORCE_COLORS = [COLOR_RED, COLOR_CYAN, COLOR_YELLOW, COLOR_PURPLE]

# Font sizes
FONT_LABEL = 14             # force labels, R/M labels
FONT_SUPPORT = 16           # support labels (A, B)
FONT_DIMENSION = 15         # dimension text (L = X m, d = X m)

logger.debug("Module loaded - Phone dimensions: %sx%s inches", PHONE_WIDTH, PHONE_HEIGHT)


class DiagramGenerator:
    """
    Generates engineering diagrams using Matplotlib.
    Optimized for phone screens (9:16 vertical aspect ratio).
    """

    def __init__(self):
        self.output_dir = Path(settings.output_dir) / "diagrams"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set dark theme for better video appearance
        plt.style.use("dark_background")

        # Colors
        self.bg_color = COLOR_BG
        self.option_border_color = COLOR_TEAL

    def _save_and_upload(self) -> str:
        """
        Save the current figure to a local file.
        If S3 is configured, upload and return the S3 key.
        Otherwise return the local file path.
        """
        output_path = self.output_dir / f"{uuid.uuid4()}.png"
        plt.savefig(output_path, dpi=PHONE_DPI, facecolor=self.bg_color)
        plt.close()

        if settings.use_s3:
            from app.services.s3_service import s3_service
            s3_key = s3_service.upload_file(str(output_path))
            return s3_key

        # Store relative path (e.g. "output/diagrams/abc.png") for /output static mount
        try:
            base = Path(settings.output_dir).resolve().parent
            return str(output_path.resolve().relative_to(base)).replace("\\", "/")
        except ValueError:
            return str(output_path)

    def _draw_answer_options(
        self,
        ax,
        options: list[str] | None,
        correct_answer: str | None = None,
    ):
        """
        Draw answer options at the bottom of the diagram.
        Options are displayed in a 2x2 grid without highlighting the correct answer.
        Uses data coordinates (not axes transforms) to ensure they're included in the saved image.
        """
        if not options:
            return

        positions = [
            (OPTION_LEFT_X, OPTION_Y_TOP),     # A - top left
            (OPTION_RIGHT_X, OPTION_Y_TOP),    # B - top right
            (OPTION_LEFT_X, OPTION_Y_BOTTOM),  # C - bottom left
            (OPTION_RIGHT_X, OPTION_Y_BOTTOM), # D - bottom right
        ]

        for i, (opt, (x, y)) in enumerate(zip(options[:4], positions)):
            # Draw option box - consistent color for all
            rect = patches.FancyBboxPatch(
                (x, y), OPTION_WIDTH, OPTION_HEIGHT,
                boxstyle="round,pad=0.015,rounding_size=0.02",
                facecolor="#2d3436",
                edgecolor=self.option_border_color,
                linewidth=3,
            )
            ax.add_patch(rect)

            # Format text with each value on its own line
            # e.g., "A: Ra = 6 kN, Rb = 6 kN" -> "A:\nRa = 6 kN\nRb = 6 kN"
            import textwrap
            text = opt
            if ": " in opt:
                prefix, rest = opt.split(": ", 1)
                # Split on comma first, then wrap long lines
                values = [v.strip() for v in rest.split(",")]
                if len(values) > 1:
                    text = f"{prefix}:\n" + "\n".join(values)
                else:
                    # Single value — wrap if too long for box (~14 chars)
                    wrapped = textwrap.fill(rest, width=14)
                    text = f"{prefix}:\n{wrapped}"

            # Draw option text — shrink font if many lines
            n_lines = text.count("\n") + 1
            fs = OPTION_FONTSIZE if n_lines <= 2 else 11

            ax.text(
                x + OPTION_WIDTH / 2, y + OPTION_HEIGHT / 2,
                text,
                ha="center", va="center",
                fontsize=fs, color="white", fontweight="bold",
                linespacing=1.3,
            )

    async def generate_beam_diagram(
        self,
        title: str = "Simply Supported Beam",
        load_position: float = 0.5,  # 0-1, position along beam
        load_value: float = 10,  # kN
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate a beam loading diagram optimized for phone screens."""
        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        # Adjust diagram position to leave room for answer options at bottom
        diagram_y_offset = 0.15 if answer_options else 0
        beam_y = 0.45 + diagram_y_offset

        # Beam
        ax.plot([0.1, 0.9], [beam_y, beam_y], "w-", linewidth=8)

        # Supports (triangles)
        support_size = 0.04
        left_support = patches.Polygon(
            [[0.1, beam_y], [0.1 - support_size, beam_y - support_size * 2],
             [0.1 + support_size, beam_y - support_size * 2]],
            closed=True, facecolor=COLOR_TEAL, edgecolor="white"
        )
        right_support = patches.Polygon(
            [[0.9, beam_y], [0.9 - support_size, beam_y - support_size * 2],
             [0.9 + support_size, beam_y - support_size * 2]],
            closed=True, facecolor=COLOR_TEAL, edgecolor="white"
        )
        ax.add_patch(left_support)
        ax.add_patch(right_support)

        # Load arrow
        load_x = 0.1 + load_position * 0.8
        ax.annotate(
            "", xy=(load_x, beam_y + 0.02),
            xytext=(load_x, beam_y + 0.15),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=3, mutation_scale=15)
        )
        ax.text(
            load_x, beam_y + 0.18, f"{load_value} kN",
            ha="center", fontsize=14, color=COLOR_RED, fontweight="bold"
        )

        # Labels
        ax.text(0.5, beam_y - 0.12, "L", ha="center", fontsize=12, color="white")
        ax.annotate(
            "", xy=(0.1, beam_y - 0.08), xytext=(0.9, beam_y - 0.08),
            arrowprops=dict(arrowstyle="<->", color="white", lw=1)
        )

        # Title at top - use full top area
        ax.text(0.5, TITLE_Y, title, ha="center", va="top",
                fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                transform=ax.transAxes, wrap=True)

        # Draw answer options at bottom
        self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    async def generate_free_body_diagram(
        self,
        title: str = "Free Body Diagram",
        forces: list[dict] | None = None,
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
        body_type: str = "particle",
        description: str = "",
    ) -> str:
        """
        Generate a free body diagram optimized for phone screens.

        forces: list of dicts with keys: magnitude, angle (degrees), label
        body_type: "particle" (circle), "bar" (horizontal beam), "block_incline" (block on slope)
        """
        if not forces:
            forces = [
                {"magnitude": 50, "angle": 0, "label": "F1 = 50N"},
                {"magnitude": 30, "angle": 90, "label": "F2 = 30N"},
                {"magnitude": 40, "angle": 225, "label": "F3 = 40N"},
            ]

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        # Adjust diagram position for answer options
        diagram_y_offset = 0.15 if answer_options else 0
        center_y = 0.55 + diagram_y_offset

        if body_type == "cables":
            # Hanging weight from two cables
            self._draw_hanging_cables(ax, center_y, description)
        elif body_type == "bar":
            # Horizontal bar for couple/moment problems
            self._draw_fbd_bar(ax, center_y, forces)
        elif body_type == "block_incline":
            # Block on inclined plane
            self._draw_fbd_incline(ax, center_y, forces, description)
        else:
            # Default: particle (circle) with force arrows
            self._draw_fbd_particle(ax, center_y, forces, description)

        # Title at top - use full top area
        import textwrap
        wrapped_title = "\n".join(textwrap.wrap(title, width=25))
        ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                transform=ax.transAxes, linespacing=1.2)

        # Draw answer options at bottom
        self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    def _draw_fbd_particle(self, ax, center_y: float, forces: list[dict],
                           description: str = ""):
        """Draw a particle (circle) with force arrows radiating out."""
        # Aspect-corrected circle: use Ellipse to appear circular on 9:16
        aspect = 6.0 / 10.6667
        r = 0.04
        is_resultant = "resultant" in description.lower()

        if is_resultant:
            # Draw ring bolt: ring + bolt shaft + base plate (scaled up)
            ring_r = 0.05
            # Ring (unfilled circle)
            ring = patches.Ellipse(
                (0.5, center_y + ring_r * aspect * 0.5), ring_r * 2,
                ring_r * 2 * aspect,
                facecolor="none", edgecolor=COLOR_TEAL, linewidth=4,
            )
            ax.add_patch(ring)
            # Bolt shaft (short vertical line below ring)
            shaft_top = center_y + ring_r * aspect * 0.5 - ring_r * aspect
            shaft_bottom = shaft_top - 0.04
            ax.plot([0.5, 0.5], [shaft_top, shaft_bottom],
                    color="#aaaaaa", linewidth=4, solid_capstyle="round")
            # Base plate (small horizontal rectangle)
            plate_w = 0.12
            plate_h = 0.015 * aspect
            plate = patches.FancyBboxPatch(
                (0.5 - plate_w / 2, shaft_bottom - plate_h),
                plate_w, plate_h,
                boxstyle="round,pad=0.003",
                facecolor="#555555", edgecolor="#888888", linewidth=2,
            )
            ax.add_patch(plate)
            # Surface hatching below plate
            for x in np.linspace(0.5 - plate_w / 2 + 0.01, 0.5 + plate_w / 2 - 0.01, 6):
                ax.plot([x, x - 0.015],
                        [shaft_bottom - plate_h, shaft_bottom - plate_h - 0.02 * aspect],
                        color="#666666", linewidth=1.2)
        else:
            circle = patches.Ellipse(
                (0.5, center_y), r * 2, r * 2 * aspect,
                facecolor=COLOR_TEAL, edgecolor="white", linewidth=2,
            )
            ax.add_patch(circle)

        colors = FORCE_COLORS
        arrow_len = 0.22 if is_resultant else 0.15

        known_forces = [f for f in forces if "?" not in f.get("label", "")]

        # Arrow origin: ring center for ring bolt, particle center otherwise
        if is_resultant:
            origin_x = 0.5
            origin_y = center_y + ring_r * aspect * 0.5  # ring center
        else:
            origin_x = 0.5
            origin_y = center_y

        for i, force in enumerate(forces):
            angle_rad = np.radians(force["angle"])
            is_unknown = "?" in force.get("label", "")

            dx = arrow_len * np.cos(angle_rad)
            dy = arrow_len * np.sin(angle_rad) * aspect

            arrow_style = dict(
                arrowstyle="-|>", color=colors[i % len(colors)],
                lw=3, mutation_scale=15,
            )
            if is_unknown:
                arrow_style["linestyle"] = "dashed"
                arrow_style["lw"] = 2.5

            ax.annotate(
                "", xy=(origin_x + dx, origin_y + dy),
                xytext=(origin_x, origin_y),
                arrowprops=arrow_style,
            )

            # Smart label placement based on arrow direction
            label = force["label"]
            tip_x = origin_x + dx
            tip_y = origin_y + dy
            cos_a = np.cos(angle_rad)
            sin_a = np.sin(angle_rad)

            # Offset label beyond the arrow tip
            lbl_x = tip_x + 0.04 * cos_a
            lbl_y = tip_y + 0.04 * sin_a * aspect

            # Adjust ha/va based on quadrant
            if abs(cos_a) > 0.7:  # mostly horizontal
                ha = "left" if cos_a > 0 else "right"
                va = "center"
            elif abs(sin_a) > 0.7:  # mostly vertical
                ha = "center"
                va = "bottom" if sin_a > 0 else "top"
            else:  # diagonal
                ha = "left" if cos_a > 0 else "right"
                va = "bottom" if sin_a > 0 else "top"

            ax.text(
                lbl_x, lbl_y, label,
                ha=ha, va=va, fontsize=13,
                color=colors[i % len(colors)], fontweight="bold",
            )

        # Draw resultant arrow (dashed) for resultant problems
        if is_resultant and len(known_forces) >= 2:
            # Sum force components
            rx = sum(f["magnitude"] * np.cos(np.radians(f["angle"])) for f in known_forces)
            ry = sum(f["magnitude"] * np.sin(np.radians(f["angle"])) for f in known_forces)
            r_angle = np.arctan2(ry, rx)

            r_dx = arrow_len * 1.2 * np.cos(r_angle)
            r_dy = arrow_len * 1.2 * np.sin(r_angle) * aspect

            ax.annotate(
                "", xy=(origin_x + r_dx, origin_y + r_dy),
                xytext=(origin_x, origin_y),
                arrowprops=dict(
                    arrowstyle="-|>", color=COLOR_YELLOW,
                    lw=3, mutation_scale=15, linestyle="dashed",
                ),
            )
            # Label — offset more to avoid overlapping force labels
            cos_r = np.cos(r_angle)
            sin_r = np.sin(r_angle)
            rl_x = origin_x + r_dx + 0.06 * cos_r
            rl_y = origin_y + r_dy + 0.06 * sin_r * aspect
            ha_r = "left" if cos_r > 0 else "right"
            va_r = "bottom" if sin_r > 0 else "top"
            ax.text(rl_x, rl_y, "R = ?",
                    ha=ha_r, va=va_r, fontsize=14,
                    color=COLOR_YELLOW, fontweight="bold")

        # Draw angle arc between first two known forces
        if len(known_forces) >= 2:
            from matplotlib.patches import Arc
            a1 = known_forces[0]["angle"]
            a2 = known_forces[1]["angle"]
            # Draw arc from smaller to larger angle
            arc_start = min(a1, a2)
            arc_end = max(a1, a2)
            arc_r = 0.10 if is_resultant else 0.08
            arc = Arc((origin_x, origin_y), arc_r * 2, arc_r * 2 * aspect,
                      angle=0, theta1=arc_start, theta2=arc_end,
                      color="white", lw=1.5, linestyle="--")
            ax.add_patch(arc)

            # Place angle label outside the arc to avoid the resultant arrow
            if is_resultant:
                # Resultant bisects the arc — place label OUTSIDE the angle,
                # just below the F1 arrow (below arc_start)
                lbl_angle = np.radians(arc_start - 15)
                label_r = arc_r + 0.02
                ha_arc = "left"
                va_arc = "top"
            else:
                lbl_angle = np.radians((arc_start + arc_end) / 2)
                label_r = arc_r + 0.03
                ha_arc = "center"
                va_arc = "center"

            ax.text(origin_x + label_r * np.cos(lbl_angle),
                    origin_y + label_r * np.sin(lbl_angle) * aspect,
                    f"{arc_end - arc_start:.0f}°",
                    ha=ha_arc, va=va_arc, fontsize=13,
                    color="white", fontweight="bold")

    def _draw_hanging_cables(self, ax, center_y: float, description: str = ""):
        """Draw a weight hanging from two symmetric cables attached to a ceiling.
        Used for cable tension problems: T = W/(2·sinθ)."""
        import re
        aspect = PHONE_WIDTH / PHONE_HEIGHT  # ~0.5625

        # Parse mass and angle from description
        mass_match = re.search(r"mass\s*=\s*(\d+)", description)
        angle_match = re.search(r"angle\s*=\s*(\d+)", description)
        mass = int(mass_match.group(1)) if mass_match else 20
        angle_deg = int(angle_match.group(1)) if angle_match else 45

        # Layout positions
        ceiling_y = center_y + 0.18
        junction_y = center_y - 0.02
        cable_len_y = ceiling_y - junction_y  # vertical drop
        cable_len_x = cable_len_y * aspect / np.tan(np.radians(angle_deg))

        junction_x = 0.5
        left_anchor = (junction_x - cable_len_x, ceiling_y)
        right_anchor = (junction_x + cable_len_x, ceiling_y)

        # Ceiling bar with hatching
        ceil_left = min(left_anchor[0], 0.15) - 0.05
        ceil_right = max(right_anchor[0], 0.85) + 0.05
        ceil_left = max(ceil_left, 0.08)
        ceil_right = min(ceil_right, 0.92)
        ax.plot([ceil_left, ceil_right], [ceiling_y, ceiling_y], "w-", linewidth=5)
        for x in np.linspace(ceil_left + 0.02, ceil_right - 0.02, 8):
            ax.plot([x, x - 0.015], [ceiling_y, ceiling_y + 0.02 * aspect],
                    "w-", linewidth=1.5)

        # Cables (two lines from ceiling anchors to junction)
        cable_color = COLOR_TEAL
        ax.plot([left_anchor[0], junction_x], [left_anchor[1], junction_y],
                color=cable_color, linewidth=3, solid_capstyle="round")
        ax.plot([right_anchor[0], junction_x], [right_anchor[1], junction_y],
                color=cable_color, linewidth=3, solid_capstyle="round")

        # Junction point (small filled circle)
        junction_r = 0.008
        ax.plot(junction_x, junction_y, "o", color="white",
                markersize=8, zorder=5)

        # Weight block hanging below junction
        block_w = 0.12
        block_h = 0.08 * aspect
        rope_len = 0.04
        block_top = junction_y - rope_len
        block_bottom = block_top - block_h

        # Rope from junction to block
        ax.plot([junction_x, junction_x], [junction_y, block_top],
                "w-", linewidth=2.5)

        # Weight block
        block = patches.FancyBboxPatch(
            (junction_x - block_w / 2, block_bottom), block_w, block_h,
            boxstyle="round,pad=0.008",
            facecolor=COLOR_RED, edgecolor="white", linewidth=2,
        )
        ax.add_patch(block)
        ax.text(junction_x, block_bottom + block_h / 2,
                f"{mass} kg", ha="center", va="center",
                fontsize=14, color="white", fontweight="bold")

        # Weight arrow (downward from block)
        arrow_len = 0.06
        ax.annotate(
            "", xy=(junction_x, block_bottom - arrow_len),
            xytext=(junction_x, block_bottom),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_YELLOW, lw=2.5, mutation_scale=14),
        )
        ax.text(junction_x + 0.06, block_bottom - arrow_len / 2,
                f"W = {mass}×9.81", ha="left", va="center",
                fontsize=11, color=COLOR_YELLOW, fontweight="bold")

        # T labels on cables (25% from ceiling anchor, offset outward)
        for anchor, label_side in [(left_anchor, "left"), (right_anchor, "right")]:
            t_x = anchor[0] + (junction_x - anchor[0]) * 0.25
            t_y = anchor[1] + (junction_y - anchor[1]) * 0.25
            if label_side == "left":
                lbl_x = t_x - 0.05
                ha = "right"
            else:
                lbl_x = t_x + 0.05
                ha = "left"
            ax.text(lbl_x, t_y, "T", ha=ha, va="center", fontsize=16,
                    color=COLOR_CYAN, fontweight="bold")

        # Angle arcs at junction point (angle between cable and horizontal)
        from matplotlib.patches import Arc
        # Scale arc radius to cable spread (smaller for steep angles)
        arc_r = min(0.09, cable_len_x * 0.6)
        # Draw horizontal reference line through junction
        ax.plot([junction_x - 0.15, junction_x + 0.15],
                [junction_y, junction_y],
                color="#888888", linewidth=1.2, linestyle="--")

        # Left cable angle arc: from horizontal-left (180°) to cable direction
        left_cable_angle = np.degrees(np.arctan2(
            left_anchor[1] - junction_y, left_anchor[0] - junction_x))
        arc_start_l = min(left_cable_angle, 180)
        arc_end_l = max(left_cable_angle, 180)
        arc_l = Arc((junction_x, junction_y),
                    arc_r * 2, arc_r * 2 * (PHONE_HEIGHT / PHONE_WIDTH),
                    angle=0, theta1=arc_start_l, theta2=arc_end_l,
                    color="white", lw=1.8)
        ax.add_patch(arc_l)
        # Label on left side
        mid_a_l = np.radians((arc_start_l + arc_end_l) / 2)
        lbl_r = arc_r + 0.04
        ax.text(junction_x + lbl_r * np.cos(mid_a_l) - 0.01,
                junction_y + lbl_r * np.sin(mid_a_l) * (PHONE_HEIGHT / PHONE_WIDTH),
                f"θ={angle_deg}°",
                ha="right", va="center", fontsize=12,
                color="white", fontweight="bold")

        # Right cable angle arc: from cable direction to 0° (horizontal right)
        right_cable_angle = np.degrees(np.arctan2(
            right_anchor[1] - junction_y, right_anchor[0] - junction_x))
        arc_start_r = min(0, right_cable_angle)
        arc_end_r = max(0, right_cable_angle)
        arc_r2 = Arc((junction_x, junction_y),
                     arc_r * 2, arc_r * 2 * (PHONE_HEIGHT / PHONE_WIDTH),
                     angle=0, theta1=arc_start_r, theta2=arc_end_r,
                     color="white", lw=1.8)
        ax.add_patch(arc_r2)
        # Label on right side
        mid_a_r = np.radians((arc_start_r + arc_end_r) / 2)
        ax.text(junction_x + lbl_r * np.cos(mid_a_r) + 0.01,
                junction_y + lbl_r * np.sin(mid_a_r) * (PHONE_HEIGHT / PHONE_WIDTH),
                f"θ={angle_deg}°",
                ha="left", va="center", fontsize=12,
                color="white", fontweight="bold")

    def _draw_fbd_bar(self, ax, center_y: float, forces: list[dict]):
        """Draw a horizontal bar with pivot, force arrow, and distance label.
        Used for moment and couple problems."""
        import re

        bar_left = 0.15
        bar_right = 0.85
        bar_width = bar_right - bar_left
        bar_height = 0.02

        # Draw the bar
        bar = patches.FancyBboxPatch(
            (bar_left, center_y - bar_height / 2), bar_width, bar_height,
            boxstyle="round,pad=0.005",
            facecolor=COLOR_TEAL, edgecolor="white", linewidth=2.5,
        )
        ax.add_patch(bar)

        colors = FORCE_COLORS

        # Check if this is a couple (two opposite forces) or a moment (one force + pivot)
        real_forces = [f for f in forces if f["angle"] != 270]  # exclude dimension markers
        dim_forces = [f for f in forces if f["angle"] == 270]  # dimension markers

        if len(real_forces) == 2 and abs(real_forces[0]["angle"] - real_forces[1]["angle"]) > 90:
            # COUPLE: two opposite forces at each end of bar
            # Left end: upward force
            left_x = bar_left + 0.05
            right_x = bar_right - 0.05

            # Force 1 at left end (pointing up) - starts flush from bar top
            arrow_len = 0.17
            bar_top = center_y + bar_height / 2
            bar_bot = center_y - bar_height / 2
            ax.annotate(
                "", xy=(left_x, bar_top + arrow_len), xytext=(left_x, bar_top),
                arrowprops=dict(arrowstyle="-|>", color=colors[0], lw=5, mutation_scale=22)
            )
            ax.text(
                left_x, bar_top + arrow_len + 0.03, real_forces[0]["label"],
                ha="center", va="bottom", fontsize=14,
                color=colors[0], fontweight="bold"
            )

            # Force 2 at right end (pointing down) - starts flush from bar bottom
            ax.annotate(
                "", xy=(right_x, bar_bot - arrow_len), xytext=(right_x, bar_bot),
                arrowprops=dict(arrowstyle="-|>", color=colors[1], lw=5, mutation_scale=22)
            )
            ax.text(
                right_x, bar_bot - arrow_len - 0.03, real_forces[1]["label"],
                ha="center", va="top", fontsize=14,
                color=colors[1], fontweight="bold"
            )

        elif len(real_forces) >= 1:
            # MOMENT: force at one end, pivot at other end
            pivot_x = bar_left + 0.02
            force_x = bar_right - 0.05

            # Draw pivot (triangle support) - positioned below bar with clear spacing
            support_size = 0.03
            pivot_tri = patches.Polygon(
                [[pivot_x, center_y - bar_height / 2],
                 [pivot_x - support_size, center_y - bar_height / 2 - support_size * 2],
                 [pivot_x + support_size, center_y - bar_height / 2 - support_size * 2]],
                closed=True, facecolor=COLOR_YELLOW, edgecolor="white", linewidth=2
            )
            ax.add_patch(pivot_tri)
            ax.text(pivot_x - support_size - 0.04, center_y - bar_height / 2 - support_size, "Pivot",
                    ha="center", fontsize=12, color=COLOR_YELLOW, fontweight="bold")

            # Force arrow at the other end - starts flush from bar top surface
            force = real_forces[0]
            angle_rad = np.radians(force["angle"])
            bar_top = center_y + bar_height / 2
            arrow_len = 0.18
            dx = arrow_len * np.cos(angle_rad)
            dy = arrow_len * np.sin(angle_rad)

            ax.annotate(
                "", xy=(force_x + dx, bar_top + dy), xytext=(force_x, bar_top),
                arrowprops=dict(arrowstyle="-|>", color=colors[0], lw=4, mutation_scale=18)
            )
            # Force label near arrow tip
            ax.text(
                force_x + dx * 1.3, bar_top + dy * 1.3 + 0.02, force["label"],
                ha="center", va="bottom", fontsize=14,
                color=colors[0], fontweight="bold"
            )

            # Angle label near the force arrow base
            angle_deg = force["angle"]
            if angle_deg != 90:  # Only show angle if not perpendicular (obvious)
                # Draw a small arc to indicate angle from horizontal
                arc_radius = 0.07
                arc_angles = np.linspace(0, np.radians(angle_deg), 20)
                arc_x = force_x + arc_radius * np.cos(arc_angles)
                arc_y = bar_top + arc_radius * np.sin(arc_angles)
                ax.plot(arc_x, arc_y, color="white", linewidth=1.5)
                # Label to the left of the arc
                mid_angle = np.radians(angle_deg / 2)
                label_r = arc_radius + 0.05
                ax.text(
                    force_x - 0.08, bar_top + label_r * np.sin(mid_angle) + 0.02,
                    f"θ = {angle_deg:.0f}°",
                    ha="center", va="center", fontsize=12,
                    color="white", fontweight="bold"
                )

        # Distance dimension below bar — align with force positions
        dim_y = center_y - 0.1
        # Use force x-positions if this is a couple, otherwise bar edges
        dim_left = bar_left + 0.05 if len(real_forces) == 2 else bar_left + 0.02
        dim_right = bar_right - 0.05 if len(real_forces) == 2 else bar_right - 0.02
        ax.annotate(
            "", xy=(dim_left, dim_y), xytext=(dim_right, dim_y),
            arrowprops=dict(arrowstyle="<->", color="white", lw=2)
        )
        # Use dimension label from forces if available, otherwise generic
        dim_label = dim_forces[0]["label"] if dim_forces else "d"
        ax.text(
            0.5, dim_y - 0.04, dim_label,
            ha="center", va="center", fontsize=15,
            color="white", fontweight="bold"
        )

    def _draw_fbd_incline(self, ax, center_y: float, forces: list[dict], description: str = ""):
        """Draw a block on an inclined plane with force vectors.

        Textbook-style: ramp triangle, upright rectangular block sitting on
        the slope, angle arc between ground and slope at bottom-left.
        The block is NOT rotated — it's drawn as a simple upright rectangle
        whose bottom-center rests on the slope surface.
        """
        import re

        # Extract incline angle from description
        angle_match = re.search(r'(\d+)\s*deg\s*incline', description.lower())
        if not angle_match:
            angle_match = re.search(r'block\s*on\s*(\d+)', description.lower())
        incline_angle = float(angle_match.group(1)) if angle_match else 30
        angle_rad = np.radians(incline_angle)

        # Extract mass from description
        mass_match = re.search(r'[Mm]ass\s*=?\s*(\d+\.?\d*)\s*kg', description)
        mass_kg = mass_match.group(1) if mass_match else None

        # --- Ramp geometry ---
        ramp_width = 0.55
        ramp_h = ramp_width * np.tan(angle_rad)
        if ramp_h > 0.28:
            ramp_h = 0.28
            ramp_width = ramp_h / np.tan(angle_rad)

        base_y = center_y - 0.05
        ramp_left = 0.5 - ramp_width / 2
        ramp_right = ramp_left + ramp_width

        # Ground line with hatching
        ax.plot([0.05, 0.95], [base_y, base_y], "w-", linewidth=2.5)
        for hx in np.linspace(0.08, 0.92, 12):
            ax.plot([hx, hx - 0.02], [base_y, base_y - 0.012],
                    color="gray", linewidth=1, alpha=0.6)

        # Ramp triangle (bottom-left, bottom-right, top-right)
        ramp = patches.Polygon(
            [[ramp_left, base_y],
             [ramp_right, base_y],
             [ramp_right, base_y + ramp_h]],
            closed=True, facecolor="#2d3436", edgecolor="white", linewidth=2.5
        )
        ax.add_patch(ramp)

        # --- Angle arc at bottom-left corner ---
        # Place in the open space between ground and slope
        arc_r = 0.09
        arc_angles = np.linspace(0, angle_rad, 30)
        arc_x = ramp_left + arc_r * np.cos(arc_angles)
        arc_y = base_y + arc_r * np.sin(arc_angles)
        ax.plot(arc_x, arc_y, color=COLOR_YELLOW, linewidth=2.5)
        # Angle label below the ramp, in the open ground area to the left
        ax.text(
            ramp_left - 0.03, base_y + 0.04,
            f"θ = {incline_angle:.0f}°",
            ha="right", va="center", fontsize=14,
            color=COLOR_YELLOW, fontweight="bold"
        )

        # --- Block on the slope (rotated to sit flush/tangent) ---
        # Position at 55% up the slope
        slope_frac = 0.45
        contact_x = ramp_left + slope_frac * ramp_width
        contact_y = base_y + slope_frac * ramp_h

        block_size = 0.12  # visual size in data coords

        # Slope direction in data coords — matches the actual ramp line exactly
        sx, sy = np.cos(angle_rad), np.sin(angle_rad)

        # Normal direction: must LOOK perpendicular on screen (aspect ratio 6:10.67)
        # Screen coords: x_screen = x_data * W, y_screen = y_data * H
        # Screen slope dir: (W*cosθ, H*sinθ), rotate 90° CCW: (-H*sinθ, W*cosθ)
        # Back to data coords: divide by W, H → (-H/W * sinθ, W/H * cosθ)
        ar = 10.6667 / 6.0  # height/width
        nx, ny = -ar * np.sin(angle_rad), (1.0 / ar) * np.cos(angle_rad)

        # Four corners: bottom-left, bottom-right, top-right, top-left
        # Bottom edge sits ON the slope line, block extends upward along normal
        corners = [
            (contact_x - sx * block_size / 2,                   contact_y - sy * block_size / 2),
            (contact_x + sx * block_size / 2,                   contact_y + sy * block_size / 2),
            (contact_x + sx * block_size / 2 + nx * block_size, contact_y + sy * block_size / 2 + ny * block_size),
            (contact_x - sx * block_size / 2 + nx * block_size, contact_y - sy * block_size / 2 + ny * block_size),
        ]
        block = patches.Polygon(
            corners, closed=True,
            facecolor=COLOR_TEAL, edgecolor="white", linewidth=2.5
        )
        ax.add_patch(block)

        # Block center for force arrows and label
        block_cx = contact_x + nx * block_size / 2
        block_cy = contact_y + ny * block_size / 2

        # "m" label centered in upper portion of block, clear of the weight arrow
        label_offset = 0.25
        label_x = block_cx + nx * block_size * label_offset
        label_y = block_cy + ny * block_size * label_offset
        ax.text(label_x, label_y, "m", ha="center", va="center",
                fontsize=14, color="white", fontweight="bold")

        # --- Force arrows from block center ---
        colors = FORCE_COLORS
        for i, force in enumerate(forces):
            f_angle_rad = np.radians(force["angle"])
            arrow_len = 0.10
            dx = arrow_len * np.cos(f_angle_rad)
            dy = arrow_len * np.sin(f_angle_rad)

            ax.annotate(
                "", xy=(block_cx + dx, block_cy + dy), xytext=(block_cx, block_cy),
                arrowprops=dict(arrowstyle="-|>", color=colors[i % len(colors)],
                                lw=4, mutation_scale=20)
            )
            # Label offset from arrow tip — put weight label to the side, not below
            label_x = block_cx + dx * 1.8
            label_y = block_cy + dy * 1.8
            # If pointing down (weight), offset label to the right to avoid ground overlap
            if force["angle"] == 270:
                label_x = block_cx + 0.18
                label_y = block_cy + dy * 0.5
                # Ensure label doesn't go off-screen
                if label_x + 0.10 > 0.95:
                    label_x = 0.85
            ax.text(
                label_x, label_y, force["label"],
                ha="center", va="center", fontsize=13,
                color=colors[i % len(colors)], fontweight="bold"
            )

    async def generate_stress_diagram(
        self,
        title: str = "Stress Distribution",
        description: str = "",
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate an axial rod/bar stress diagram optimized for phone screens.
        Shows a horizontal rod with fixed wall on left and applied force on right,
        with given parameters labeled (F, d/L, A/diameter).
        """
        import re

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        # Diagram center (raised to reduce gap from title)
        center_y = 0.68
        rod_left = 0.12
        rod_right = 0.62
        rod_height = 0.07

        # Fixed wall on left (hatching)
        wall_x = rod_left
        ax.plot([wall_x, wall_x], [center_y - 0.12, center_y + 0.12],
                "w-", linewidth=5)
        for y_h in np.linspace(center_y - 0.11, center_y + 0.11, 7):
            ax.plot([wall_x - 0.03, wall_x], [y_h - 0.02, y_h], "w-", linewidth=2)

        # Rod body
        rod = patches.FancyBboxPatch(
            (rod_left, center_y - rod_height / 2), rod_right - rod_left, rod_height,
            boxstyle="round,pad=0.005",
            facecolor=COLOR_TEAL, edgecolor="white", linewidth=2,
        )
        ax.add_patch(rod)

        # Parse force and dimensions from description
        force_val = ""
        diameter_val = ""
        length_val = ""
        area_val = ""
        modulus_val = ""

        f_match = re.search(r'(?:force|load|F)\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(kN|N)', description, re.IGNORECASE)
        if f_match:
            force_val = f"{f_match.group(1)} {f_match.group(2)}"

        d_match = re.search(r'diameter\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)', description, re.IGNORECASE)
        if d_match:
            diameter_val = f"d = {d_match.group(1)} {d_match.group(2)}"

        l_match = re.search(r'length\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)', description, re.IGNORECASE)
        if l_match:
            length_val = f"L = {l_match.group(1)} {l_match.group(2)}"

        a_match = re.search(r'area\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)', description, re.IGNORECASE)
        if a_match:
            area_val = f"A = {a_match.group(1)} {a_match.group(2)}"

        e_match = re.search(r'(?:modulus|E)\s*(?:of\s+)?(?:E\s*)?=?\s*(\d+(?:\.\d+)?)\s*(GPa|MPa)', description, re.IGNORECASE)
        if e_match:
            modulus_val = f"E = {e_match.group(1)} {e_match.group(2)}"

        # Applied force arrow on right end (pulling right = tension)
        arrow_len = 0.12
        ax.annotate(
            "", xy=(rod_right + arrow_len, center_y),
            xytext=(rod_right, center_y),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=4, mutation_scale=20)
        )
        if force_val:
            ax.text(rod_right + arrow_len + 0.02, center_y, f"F = {force_val}",
                    ha="left", va="center", fontsize=FONT_LABEL, color=COLOR_RED, fontweight="bold")

        # Dimension labels below rod (exclude length if shown as dimension line)
        info_y = center_y - rod_height / 2 - 0.06
        info_items = [s for s in [diameter_val, area_val, modulus_val] if s]
        if info_items:
            info_text = ",  ".join(info_items)
            ax.text(0.5, info_y, info_text,
                    ha="center", va="top", fontsize=12, color="white", fontweight="bold")

        # Length dimension line
        if length_val:
            dim_y = center_y - rod_height / 2 - 0.12
            ax.annotate(
                "", xy=(rod_left, dim_y), xytext=(rod_right, dim_y),
                arrowprops=dict(arrowstyle="<->", color="white", lw=2)
            )
            ax.text((rod_left + rod_right) / 2, dim_y - 0.03, length_val,
                    ha="center", fontsize=FONT_DIMENSION, color="white", fontweight="bold")

        # Title at top
        import textwrap
        wrapped_title = "\n".join(textwrap.wrap(title, width=25))
        ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                transform=ax.transAxes, linespacing=1.2)

        # Draw answer options at bottom
        self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    async def generate_shear_diagram(
        self,
        title: str = "Shear Stress",
        description: str = "",
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate a shear bolt/pin diagram: two plates overlapping with bolt(s)."""
        import re

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        center_y = 0.68

        # Parse parameters from description
        f_match = re.search(r'(?:force|F)\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(kN|N)', description, re.IGNORECASE)
        force_val = f"{f_match.group(1)} {f_match.group(2)}" if f_match else ""

        d_match = re.search(r'diameter\s*(?:of\s+)?=?\s*(\d+(?:\.\d+)?)\s*(mm)', description, re.IGNORECASE)
        diameter_val = f"d = {d_match.group(1)} {d_match.group(2)}" if d_match else ""

        bolt_match = re.search(r'(\d+)\s*bolt', description, re.IGNORECASE)
        n_bolts = int(bolt_match.group(1)) if bolt_match else 1

        # --- Plate geometry ---
        plate_h = 0.04   # height of each plate
        overlap = 0.22   # how much the plates overlap in the middle
        plate_len = 0.28

        # Center the whole assembly horizontally
        total_w = plate_len + overlap + plate_len
        assembly_left = (1.0 - total_w) / 2

        # Bottom plate: extends from left into overlap
        bot_left = assembly_left
        bot_right = bot_left + plate_len + overlap
        bot_y = center_y - plate_h  # bottom plate sits below center

        # Top plate: extends from overlap to right
        top_left = bot_right - overlap
        top_right = top_left + plate_len + overlap
        top_y = center_y  # top plate sits above center

        # Draw bottom plate
        bot_plate = patches.FancyBboxPatch(
            (bot_left, bot_y), bot_right - bot_left, plate_h,
            boxstyle="round,pad=0.003",
            facecolor="#3d5a80", edgecolor="white", linewidth=2,
        )
        ax.add_patch(bot_plate)

        # Draw top plate
        top_plate = patches.FancyBboxPatch(
            (top_left, top_y), top_right - top_left, plate_h,
            boxstyle="round,pad=0.003",
            facecolor="#3d5a80", edgecolor="white", linewidth=2,
        )
        ax.add_patch(top_plate)

        # --- Bolt(s) through the overlap region ---
        overlap_cx = (top_left + bot_right) / 2
        bolt_r = 0.015
        bolt_spacing = 0.10

        if n_bolts == 1:
            bolt_xs = [overlap_cx]
        elif n_bolts == 2:
            bolt_xs = [overlap_cx - bolt_spacing / 2, overlap_cx + bolt_spacing / 2]
        else:
            bolt_xs = [overlap_cx - bolt_spacing, overlap_cx, overlap_cx + bolt_spacing]

        for bx in bolt_xs:
            # Bolt shaft (vertical line through both plates)
            ax.plot([bx, bx], [bot_y - 0.01, top_y + plate_h + 0.01],
                    color=COLOR_YELLOW, linewidth=3, zorder=5)
            # Bolt head (circle on top)
            head = patches.Circle((bx, top_y + plate_h + 0.01), bolt_r,
                                  facecolor=COLOR_YELLOW, edgecolor="white",
                                  linewidth=1.5, zorder=6)
            ax.add_patch(head)
            # Bolt nut (small rectangle on bottom)
            nut_w = bolt_r * 1.6
            nut_h = 0.008
            nut = patches.FancyBboxPatch(
                (bx - nut_w / 2, bot_y - 0.01 - nut_h), nut_w, nut_h,
                boxstyle="round,pad=0.002",
                facecolor=COLOR_YELLOW, edgecolor="white", linewidth=1, zorder=6,
            )
            ax.add_patch(nut)

        # --- Force arrows (opposing on each plate) ---
        arrow_len = 0.10

        # Left arrow: pulling bottom plate to the left
        left_arrow_y = center_y - plate_h / 2
        ax.annotate(
            "", xy=(bot_left - arrow_len, left_arrow_y),
            xytext=(bot_left, left_arrow_y),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=4, mutation_scale=20)
        )
        ax.text(bot_left - arrow_len / 2, left_arrow_y - 0.04, "F",
                ha="center", va="top", fontsize=FONT_LABEL, color=COLOR_RED, fontweight="bold")

        # Right arrow: pulling top plate to the right
        right_arrow_y = center_y + plate_h / 2
        ax.annotate(
            "", xy=(top_right + arrow_len, right_arrow_y),
            xytext=(top_right, right_arrow_y),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=4, mutation_scale=20)
        )
        if force_val:
            ax.text(top_right + arrow_len / 2, right_arrow_y + 0.04, f"F = {force_val}",
                    ha="center", va="bottom", fontsize=FONT_LABEL, color=COLOR_RED, fontweight="bold")

        # --- Labels ---
        # Bolt diameter label below the assembly
        info_y = bot_y - 0.06
        if diameter_val:
            ax.text(0.5, info_y, diameter_val,
                    ha="center", va="top", fontsize=12, color="white", fontweight="bold")

        # Title at top
        import textwrap
        wrapped_title = "\n".join(textwrap.wrap(title, width=25))
        ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                transform=ax.transAxes, linespacing=1.2)

        # Draw answer options at bottom
        self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    def _parse_beam_description(self, description: str) -> dict:
        """Extract beam parameters from description text."""
        import re

        params = {
            "length": 6.0,
            "load_position": 0.5,
            "load_value": 10.0,
            "load_distance": None,  # actual distance in meters from left
            "left_support": "pin",
            "right_support": "roller",
            "loads": [],  # list of {value, position, distance} for multi-load
            "is_udl": False,
            "udl_w": 0.0,  # kN/m for distributed loads
        }

        desc_lower = description.lower()

        # Extract length (e.g., "6m length", "10 m beam")
        length_match = re.search(r"(\d+(?:\.\d+)?)\s*m(?:eter)?s?\s*(?:length|long|beam)?", desc_lower)
        if length_match:
            params["length"] = float(length_match.group(1))

        # Check for uniformly distributed load (UDL)
        udl_match = re.search(r"(\d+(?:\.\d+)?)\s*kn/m", desc_lower)
        if udl_match and "distribut" in desc_lower:
            params["is_udl"] = True
            params["udl_w"] = float(udl_match.group(1))
            # Extract total load for reference
            total_match = re.search(r"total\s+load\s+(\d+(?:\.\d+)?)\s*kn", desc_lower)
            if total_match:
                params["load_value"] = float(total_match.group(1))
            else:
                params["load_value"] = params["udl_w"] * params["length"]
            params["load_position"] = 0.5
            params["loads"] = [{
                "value": params["load_value"],
                "position": 0.5,
                "distance": params["length"] / 2,
            }]
            # Support types (still need to parse these)
            if "fixed" in desc_lower and "left" in desc_lower:
                params["left_support"] = "fixed"
            if "fixed" in desc_lower and "right" in desc_lower:
                params["right_support"] = "fixed"
            if "cantilever" in desc_lower:
                params["left_support"] = "fixed"
                params["right_support"] = "none"
            return params

        # Try to find multiple "point load of X kN at Ym from A" patterns
        multi_load = re.findall(
            r"(?:point\s+)?load\s+of\s+(\d+(?:\.\d+)?)\s*kn\s+(?:applied\s+)?at\s+(\d+(?:\.\d+)?)\s*m\s*from\s*(?:left|end\s*a|a)",
            desc_lower
        )

        if multi_load and params["length"] > 0:
            for val_str, dist_str in multi_load:
                val = float(val_str)
                dist = float(dist_str)
                params["loads"].append({
                    "value": val,
                    "position": dist / params["length"],
                    "distance": dist,
                })
            # Set primary load to first one for backward compat
            params["load_value"] = params["loads"][0]["value"]
            params["load_position"] = params["loads"][0]["position"]
            params["load_distance"] = params["loads"][0]["distance"]
        else:
            # Single load parsing
            load_match = re.search(r"(\d+(?:\.\d+)?)\s*kn", desc_lower)
            if load_match:
                params["load_value"] = float(load_match.group(1))

            # Determine load position from description
            if "center" in desc_lower or "middle" in desc_lower:
                params["load_position"] = 0.5
                params["load_distance"] = params["length"] / 2
            elif "free right end" in desc_lower or "free end" in desc_lower:
                params["load_position"] = 1.0
                params["load_distance"] = params["length"]
            else:
                # Check for position like "3m from"
                pos_match = re.search(r"(\d+(?:\.\d+)?)\s*m\s*from\s*(?:left|end\s*a|each|the fixed)", desc_lower)
                if pos_match and params["length"] > 0:
                    pos = float(pos_match.group(1))
                    params["load_position"] = pos / params["length"]
                    params["load_distance"] = pos

            params["loads"] = [{
                "value": params["load_value"],
                "position": params["load_position"],
                "distance": params["load_distance"],
            }]

        # Support types
        if "fixed" in desc_lower and "left" in desc_lower:
            params["left_support"] = "fixed"
        if "fixed" in desc_lower and "right" in desc_lower:
            params["right_support"] = "fixed"
        if "cantilever" in desc_lower:
            params["left_support"] = "fixed"
            params["right_support"] = "none"

        return params

    async def generate_beam_from_description(
        self,
        title: str,
        description: str,
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate a beam diagram by parsing the description, optimized for phone screens."""
        params = self._parse_beam_description(description)

        logger.debug("Creating figure: %sx%s inches (9:16 vertical)", PHONE_WIDTH, PHONE_HEIGHT)
        logger.debug("Answer options to draw: %s", answer_options)

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        # Adjust diagram position for answer options at bottom
        # With options: diagram in middle area, options at bottom, title at top
        diagram_y_offset = 0.12 if answer_options else 0
        beam_y = 0.48 + diagram_y_offset  # Lowered to avoid title overlap
        beam_left = 0.08
        beam_right = 0.92
        beam_width = beam_right - beam_left

        # Draw beam - thicker for visibility
        ax.plot([beam_left, beam_right], [beam_y, beam_y], "w-", linewidth=12)

        # Draw supports - larger
        support_size = 0.045

        # Left support
        if params["left_support"] == "pin":
            triangle = patches.Polygon(
                [[beam_left, beam_y],
                 [beam_left - support_size, beam_y - support_size * 2],
                 [beam_left + support_size, beam_y - support_size * 2]],
                closed=True, facecolor=COLOR_TEAL, edgecolor="white", linewidth=2.5
            )
            ax.add_patch(triangle)
            ax.text(beam_left, beam_y - support_size * 3, "A", ha="center",
                    fontsize=16, color="white", fontweight="bold")
        elif params["left_support"] == "fixed":
            ax.plot([beam_left, beam_left], [beam_y - 0.08, beam_y + 0.08],
                    "w-", linewidth=5)
            for y in np.linspace(beam_y - 0.07, beam_y + 0.07, 5):
                ax.plot([beam_left - 0.03, beam_left], [y - 0.02, y], "w-", linewidth=2.5)

            # Reaction force R — below beam pointing up, same length as load arrow
            r_arrow_len = 0.12  # match red load arrow length
            r_x = beam_left + 0.05  # shifted right to avoid overlap with support line
            r_base = beam_y - 0.02 - r_arrow_len  # start below beam (with gap for beam thickness)
            r_tip = beam_y - 0.02  # tip at bottom edge of beam
            ax.annotate(
                "", xy=(r_x, r_tip),
                xytext=(r_x, r_base),
                arrowprops=dict(arrowstyle="-|>", color=COLOR_CYAN, lw=4, mutation_scale=20)
            )
            ax.text(r_x + 0.04, r_base + r_arrow_len * 0.3, "R",
                    ha="center", fontsize=14, color=COLOR_CYAN, fontweight="bold")

            # Reaction moment M (curved arrow, 270° CCW arc = 3/4 circle)
            # Position arc to the left of the fixed hatching, at beam level
            arc_r = 0.035
            arc_cx = beam_left - 0.065
            arc_cy = beam_y
            # Draw full arc from 0° to 260° (leave room for arrowhead triangle)
            arc_angles = np.linspace(np.radians(0), np.radians(255), 60)
            arc_x = arc_cx + arc_r * np.cos(arc_angles)
            arc_y_pts = arc_cy + arc_r * np.sin(arc_angles)
            ax.plot(arc_x, arc_y_pts, color=COLOR_YELLOW, linewidth=3, clip_on=False)
            # Manual triangle arrowhead at 270° pointing along CCW tangent (rightward)
            tip_angle = np.radians(270)
            tip_x = arc_cx + arc_r * np.cos(tip_angle)
            tip_y = arc_cy + arc_r * np.sin(tip_angle)
            arrow_size = 0.012
            # Triangle: tip points right (tangent at 270° CCW), two base points behind
            tri = patches.Polygon(
                [[tip_x + arrow_size, tip_y],
                 [tip_x - arrow_size * 0.5, tip_y + arrow_size * 0.7],
                 [tip_x - arrow_size * 0.5, tip_y - arrow_size * 0.7]],
                closed=True, facecolor=COLOR_YELLOW, edgecolor=COLOR_YELLOW,
                clip_on=False,
            )
            ax.add_patch(tri)
            ax.text(arc_cx, arc_cy + arc_r + 0.03, "M",
                    ha="center", fontsize=14, color=COLOR_YELLOW, fontweight="bold",
                    clip_on=False)

        # Right support
        if params["right_support"] == "roller":
            triangle = patches.Polygon(
                [[beam_right, beam_y],
                 [beam_right - support_size, beam_y - support_size * 2],
                 [beam_right + support_size, beam_y - support_size * 2]],
                closed=True, facecolor=COLOR_TEAL, edgecolor="white", linewidth=2.5
            )
            ax.add_patch(triangle)
            # Roller circle - positioned below triangle
            circle = plt.Circle((beam_right, beam_y - support_size * 2.6),
                                 support_size * 0.5, color=COLOR_TEAL, ec="white", lw=2.5)
            ax.add_patch(circle)
            # B label - to the right of the roller, same height as A
            ax.text(beam_right + support_size * 1.5, beam_y - support_size * 3, "B", ha="center",
                    fontsize=16, color="white", fontweight="bold")
        elif params["right_support"] == "pin":
            triangle = patches.Polygon(
                [[beam_right, beam_y],
                 [beam_right - support_size, beam_y - support_size * 2],
                 [beam_right + support_size, beam_y - support_size * 2]],
                closed=True, facecolor=COLOR_TEAL, edgecolor="white", linewidth=2.5
            )
            ax.add_patch(triangle)
            ax.text(beam_right, beam_y - support_size * 3, "B", ha="center",
                    fontsize=16, color="white", fontweight="bold")

        # Draw load arrows
        if params["is_udl"]:
            # Uniformly distributed load: multiple arrows spanning the beam
            arrow_top = beam_y + 0.12
            n_arrows = 7  # number of arrows across the beam
            # Horizontal line connecting arrow tops
            ax.plot([beam_left, beam_right], [arrow_top, arrow_top],
                    color=COLOR_RED, linewidth=3)
            # Draw evenly spaced arrows
            for i in range(n_arrows):
                ax_x = beam_left + (i / (n_arrows - 1)) * beam_width
                ax.annotate(
                    "", xy=(ax_x, beam_y + 0.02),
                    xytext=(ax_x, arrow_top),
                    arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=2.5,
                                    mutation_scale=15)
                )
            # Label: "w = X kN/m" above the line
            ax.text(
                0.5, arrow_top + 0.03, f"w = {params['udl_w']:.0f} kN/m",
                ha="center", fontsize=16, color=COLOR_RED, fontweight="bold"
            )
        else:
            # Point loads
            for load in params["loads"]:
                load_x = beam_left + load["position"] * beam_width
                arrow_top = beam_y + 0.12
                ax.annotate(
                    "", xy=(load_x, beam_y + 0.02),
                    xytext=(load_x, arrow_top),
                    arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=4,
                                    mutation_scale=20)
                )
                ax.text(
                    load_x, arrow_top + 0.03, f"{load['value']:.0f} kN",
                    ha="center", fontsize=18, color=COLOR_RED, fontweight="bold"
                )

        # Dimension lines
        dim_y = beam_y - 0.16
        num_loads = len(params["loads"])
        has_positioned_loads = any(
            ld["distance"] is not None and abs(ld["position"] - 0.5) > 0.01
            for ld in params["loads"]
        )

        if has_positioned_loads and num_loads <= 2:
            # Show load position dimensions instead of just total length
            # Draw segmented dimensions from A to each load, and last load to B
            positions = sorted(params["loads"], key=lambda ld: ld["position"])
            dim_points = [0.0]  # start at A
            dim_labels = []
            for ld in positions:
                dim_points.append(ld["distance"])
            dim_points.append(params["length"])  # end at B

            for i in range(len(dim_points) - 1):
                seg_start = dim_points[i]
                seg_end = dim_points[i + 1]
                seg_len = seg_end - seg_start
                if seg_len < 0.1:
                    continue
                # Convert to x coords
                x_start = beam_left + (seg_start / params["length"]) * beam_width
                x_end = beam_left + (seg_end / params["length"]) * beam_width
                ax.annotate(
                    "", xy=(x_start, dim_y), xytext=(x_end, dim_y),
                    arrowprops=dict(arrowstyle="<->", color="white", lw=2)
                )
                ax.text(
                    (x_start + x_end) / 2, dim_y - 0.04,
                    f"{seg_len:.0f} m",
                    ha="center", fontsize=14, color="white", fontweight="bold"
                )
        else:
            # Simple total length dimension (center load or cantilever)
            ax.annotate(
                "", xy=(beam_left, dim_y), xytext=(beam_right, dim_y),
                arrowprops=dict(arrowstyle="<->", color="white", lw=2)
            )
            ax.text(
                (beam_left + beam_right) / 2, dim_y - 0.04,
                f"L = {params['length']:.0f} m",
                ha="center", fontsize=16, color="white", fontweight="bold"
            )

        # Title at top - with text wrapping
        # Wrap long titles manually
        import textwrap
        wrapped_title = "\n".join(textwrap.wrap(title, width=25))
        ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                transform=ax.transAxes, linespacing=1.2)

        # Draw answer options at bottom
        self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    def _parse_forces_description(self, description: str) -> list[dict] | None:
        """Parse force data from description text for FBD diagrams."""
        import re

        forces = []

        # Pattern: "F1 = 50 N at 0 degrees" or "F1 = 50N acting at 45 deg"
        force_pattern = re.findall(
            r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*(?:kN|N)\s*(?:at|acting at)?\s*(\d+(?:\.\d+)?)\s*(?:deg|degrees)',
            description, re.IGNORECASE
        )
        for label_name, magnitude, angle in force_pattern:
            mag = float(magnitude)
            unit = "kN" if "kn" in description.lower() else "N"
            forces.append({
                "magnitude": mag,
                "angle": float(angle),
                "label": f"{label_name} = {mag:.0f}{unit}",
            })

        # Pattern: "F3 = ? N at 233 degrees" — unknown force (draw as dashed)
        unknown_pattern = re.findall(
            r'(\w+)\s*=\s*\?\s*(?:kN|N)\s*(?:at|acting at)?\s*(\d+(?:\.\d+)?)\s*(?:deg|degrees)',
            description, re.IGNORECASE
        )
        for label_name, angle in unknown_pattern:
            forces.append({
                "magnitude": 0,
                "angle": float(angle),
                "label": f"{label_name} = ?",
            })

        # Pattern: "Lever arm d = X m" or "arm d = X m" - add as dimension marker
        if forces:
            lever_match = re.search(
                r'(?:lever\s+)?arm\s+\w?\s*=\s*(\d+(?:\.\d+)?)\s*m',
                description, re.IGNORECASE
            )
            if lever_match:
                arm = float(lever_match.group(1))
                forces.append({
                    "magnitude": arm,
                    "angle": 270,
                    "label": f"d = {arm:.0f} m",
                })

        # Pattern: "force of X kN acting horizontally/vertically/at angle"
        if not forces:
            # Look for simpler patterns
            simple_pattern = re.findall(
                r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*(kN|N)\s+acting\s+(horizontally|vertically|upward|downward)',
                description, re.IGNORECASE
            )
            angle_map = {
                "horizontally": 0, "vertically": 90,
                "upward": 90, "downward": 270,
                "right": 0, "left": 180,
            }
            for label_name, magnitude, unit, direction in simple_pattern:
                mag = float(magnitude)
                forces.append({
                    "magnitude": mag,
                    "angle": angle_map.get(direction.lower(), 0),
                    "label": f"{label_name} = {mag:.0f} {unit}",
                })

        # Pattern for couples: "Two equal and opposite forces of X kN separated by Ym"
        if not forces:
            couple_match = re.search(
                r'(?:two|2)\s+(?:equal\s+)?(?:and\s+)?opposite\s+forces?\s+of\s+(\d+(?:\.\d+)?)\s*(kN|N)',
                description, re.IGNORECASE
            )
            if couple_match:
                mag = float(couple_match.group(1))
                unit = couple_match.group(2)
                forces = [
                    {"magnitude": mag, "angle": 0, "label": f"F = {mag:.0f} {unit}"},
                    {"magnitude": mag, "angle": 180, "label": f"F = {mag:.0f} {unit}"},
                ]

                # Also check for arm distance
                arm_match = re.search(r'separated\s+by\s+(\d+(?:\.\d+)?)\s*m', description, re.IGNORECASE)
                if arm_match:
                    arm = float(arm_match.group(1))
                    forces[0]["label"] = f"F = {mag:.0f} {unit}"
                    forces[1]["label"] = f"F = {mag:.0f} {unit}"
                    # Add a dimension label as a third "force" pointing down
                    forces.append({
                        "magnitude": arm,
                        "angle": 270,
                        "label": f"d = {arm:.1f} m",
                    })

        return forces if forces else None

    # ── Stress-Strain Curve ─────────────────────────────────────────────
    async def generate_stress_strain_curve(
        self,
        title: str,
        description: str,
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate a stress-strain curve diagram with labeled points/regions.

        Reference style: ductile steel curve with dashed vertical region
        separators, region labels, Young's modulus Rise/Run annotation,
        and clearly labeled key points (Yield, Ultimate, Fracture).
        """
        import re
        import textwrap
        from scipy.interpolate import PchipInterpolator

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        desc_lower = description.lower()

        # Determine material behavior
        is_brittle = "brittle" in desc_lower or "cast iron" in desc_lower

        # Detect True/False statement in title (quoted text on second line)
        _title_lines = title.split("\n", 1)
        has_statement = len(_title_lines) > 1 and _title_lines[1].strip().startswith('"')

        # Parse which point to highlight or hide
        highlight_point = None
        hide_label = None
        highlight_match = re.search(r"highlight point:\s*(.+?)\.", description, re.IGNORECASE)
        if highlight_match:
            highlight_point = highlight_match.group(1).strip()
        hide_match = re.search(r"hide label:\s*(.+?)\.", description, re.IGNORECASE)
        if hide_match:
            hide_label = hide_match.group(1).strip()

        # ── Chart area ───────────────────────────────────────────────────
        chart_left = 0.14
        chart_right = 0.92
        chart_bottom = 0.38 if answer_options else 0.15
        # Lower chart top when there's a statement (True/False) to avoid overlap
        chart_top = 0.75 if has_statement else 0.82
        chart_w = chart_right - chart_left
        chart_h = chart_top - chart_bottom

        # Subtle rounded background
        chart_bg = patches.FancyBboxPatch(
            (chart_left - 0.02, chart_bottom - 0.02),
            chart_w + 0.04, chart_h + 0.04,
            boxstyle="round,pad=0.01",
            facecolor="#0d0d1a", edgecolor="#333355", linewidth=1.5,
        )
        ax.add_patch(chart_bg)

        # ── Determine material type ──────────────────────────────────────
        is_aluminum = "aluminum" in desc_lower
        # Note: all strain values are educational/exaggerated so the elastic
        # region is clearly visible (real elastic strains ~0.002 would be
        # invisible at this scale).

        # ── Curve data ───────────────────────────────────────────────────
        if is_brittle:
            # Gray cast iron: smooth concave-down curve from origin,
            # gradually flattening, then abrupt fracture at the peak.
            # UTS and fracture are essentially the same point — it just snaps.
            strain_max = 0.12
            stress_max = 280

            n_pts = 200
            frac_strain = 0.08
            frac_stress = 230

            # Concave-down curve (power < 1 gives that shape)
            s = np.linspace(0, frac_strain, n_pts)
            st = frac_stress * (s / frac_strain) ** 0.45

            strain = s
            stress = st

            points = {
                "Ultimate Tensile Strength": (frac_strain, frac_stress),
                "Fracture": (frac_strain, frac_stress),
            }
            region_boundaries = []
            region_labels = ["Elastic"]
            region_colors = [COLOR_TEAL]

        elif is_aluminum:
            # Aluminum: linear elastic → gradual curve (no sharp yield)
            # Reference (b): smooth transition, 0.2% offset to find σ_y
            strain_max = 0.35
            stress_max = 380

            # Linear elastic segment
            n_elastic = 100
            elastic_end = 0.04
            yield_stress = 270
            e_strain = np.linspace(0, elastic_end, n_elastic)
            e_stress = yield_stress * (e_strain / elastic_end)  # linear

            # Gradual curve past elastic — no sharp yield
            curve_ctrl_s =  [0.04, 0.06, 0.10, 0.16, 0.22, 0.28, 0.32]
            curve_ctrl_st = [270,  295,  315,  325,  320,  300,  270]
            spl_a = PchipInterpolator(curve_ctrl_s, curve_ctrl_st)
            c_strain = np.linspace(0.04, 0.32, 250)
            c_stress = spl_a(c_strain)

            strain = np.concatenate([e_strain, c_strain[1:]])
            stress = np.concatenate([e_stress, c_stress[1:]])
            stress = np.maximum(stress, 0)

            points = {
                "Yield Strength": (0.06, 295),
                "Ultimate Tensile Strength": (0.16, 325),
                "Fracture": (0.32, 270),
            }
            region_boundaries = [0.06, 0.22]
            region_labels = ["Elastic", "Strain\nhardening", "Necking"]
            region_colors = [COLOR_TEAL, "#ff9f43", COLOR_RED]

        else:
            # Low carbon steel: linear → sharp yield → drop → plateau
            # → strain hardening → ultimate → necking → fracture
            # Reference (a): visible elastic ramp, sharp yield point, dip
            strain_max = 0.35
            stress_max = 470

            # Linear elastic (exaggerated to ~12% of x-axis)
            n_elastic = 100
            elastic_end = 0.04
            yield_stress = 300
            e_strain = np.linspace(0, elastic_end, n_elastic)
            e_stress = yield_stress * (e_strain / elastic_end)  # linear

            # Post-yield: sharp yield → small drop → plateau → hardening
            # → ultimate → necking → fracture
            post_ctrl_s =  [0.04, 0.045, 0.05, 0.10, 0.16, 0.22, 0.27, 0.32]
            post_ctrl_st = [300,  275,    275,  280,  350,  420,  395,  330]
            spl_s = PchipInterpolator(post_ctrl_s, post_ctrl_st)
            p_strain = np.linspace(0.04, 0.32, 300)
            p_stress = spl_s(p_strain)

            strain = np.concatenate([e_strain, p_strain[1:]])
            stress = np.concatenate([e_stress, p_stress[1:]])
            stress = np.maximum(stress, 0)

            points = {
                "Yield Strength": (0.04, 300),
                "Ultimate Tensile Strength": (0.22, 420),
                "Fracture": (0.32, 330),
            }
            # Dashed separators: after yield plateau, after hardening
            region_boundaries = [0.04, 0.10, 0.22]
            region_labels = ["Elastic", "Yield", "Strain\nhardening", "Necking"]
            region_colors = [COLOR_TEAL, COLOR_YELLOW, "#ff9f43", COLOR_RED]

        # ── Coordinate mapping ───────────────────────────────────────────
        def to_chart(s_val, st_val):
            x = chart_left + (s_val / (strain_max * 1.05)) * chart_w
            y = chart_bottom + (st_val / (stress_max * 1.05)) * chart_h
            return x, y

        # ── Draw colored region fills (ductile only) ─────────────────────
        if not is_brittle:
            # Define strain ranges for each region
            region_edges = [0] + region_boundaries + [strain[-1]]
            for i in range(len(region_edges) - 1):
                mask = (strain >= region_edges[i]) & (strain <= region_edges[i + 1])
                rx = [to_chart(s, st)[0] for s, st in zip(strain[mask], stress[mask])]
                ry = [to_chart(s, st)[1] for s, st in zip(strain[mask], stress[mask])]
                if rx:
                    c = region_colors[i] if i < len(region_colors) else COLOR_RED
                    ax.fill_between(rx, chart_bottom, ry, alpha=0.08, color=c)

        # ── Draw the curve ───────────────────────────────────────────────
        curve_x = [to_chart(s, st)[0] for s, st in zip(strain, stress)]
        curve_y = [to_chart(s, st)[1] for s, st in zip(strain, stress)]
        ax.plot(curve_x, curve_y, color=COLOR_TEAL, linewidth=3.5, zorder=5)

        # ── Draw axes with arrows ────────────────────────────────────────
        arrow_props = dict(color="white", linewidth=2)
        # X axis
        ax.annotate("", xy=(chart_right + 0.02, chart_bottom),
                     xytext=(chart_left, chart_bottom),
                     arrowprops=dict(arrowstyle="-|>", color="white", lw=2))
        # Y axis
        ax.annotate("", xy=(chart_left, chart_top + 0.02),
                     xytext=(chart_left, chart_bottom),
                     arrowprops=dict(arrowstyle="-|>", color="white", lw=2))
        # Axis labels
        ax.text(chart_left + chart_w / 2, chart_bottom - 0.035, "Strain, ε",
                ha="center", fontsize=14, color="white", fontstyle="italic")
        ax.text(chart_left + 0.01, chart_top + 0.025, "Stress, σ",
                ha="left", va="bottom", fontsize=14, color="white",
                fontstyle="italic")

        # ── Dashed vertical region separators (no labels) ────────────────
        if not is_brittle:
            for boundary in region_boundaries:
                bx, _ = to_chart(boundary, 0)
                ax.plot([bx, bx], [chart_bottom, chart_top],
                        color="#555577", linewidth=1.2, linestyle="--", zorder=3)

        # ── Young's modulus Rise/Run annotation ──────────────────────────
        if not is_brittle:
            # Rise/Run triangle on the elastic line itself
            # Now elastic region is wide enough to draw directly on it
            tri_color = "#aaaacc"
            e_low = elastic_end * 0.25
            e_high = elastic_end * 0.70
            s_low = yield_stress * (e_low / elastic_end)
            s_high = yield_stress * (e_high / elastic_end)

            x1, y1 = to_chart(e_low, s_low)
            x2, y2 = to_chart(e_high, s_high)
            x_corner = x2
            y_corner = y1

            # Run (horizontal) and Rise (vertical)
            ax.plot([x1, x_corner], [y1, y_corner], color=tri_color,
                    linewidth=1.2, linestyle="--", zorder=6)
            ax.plot([x_corner, x2], [y_corner, y2], color=tri_color,
                    linewidth=1.2, linestyle="--", zorder=6)

            ax.text((x1 + x_corner) / 2, y_corner - 0.015, "Run",
                    ha="center", va="top", fontsize=9,
                    color=tri_color, fontstyle="italic")
            ax.text(x_corner + 0.015, (y_corner + y2) / 2, "Rise",
                    ha="left", va="center", fontsize=9,
                    color=tri_color, fontstyle="italic")

            # E = Slope label
            ax.text(x_corner + 0.025, y2 + 0.01,
                    "E = Rise / Run",
                    ha="left", va="bottom", fontsize=9,
                    color=COLOR_CYAN, fontweight="bold", zorder=10)

        # ── Key points and labels ────────────────────────────────────────
        point_colors = {
            "Yield Strength": COLOR_YELLOW,
            "Ultimate Tensile Strength": COLOR_RED,
            "Fracture": "#ff6b6b",
        }
        # Label positioning offsets: (dx, dy, ha, va)
        # Offset labels well above the curve so they don't overlap it
        label_offsets = {
            "Yield Strength": (0.04, 0.045, "left", "bottom"),
            "Ultimate Tensile Strength": (0.0, 0.045, "center", "bottom"),
            "Fracture": (0.04, 0.025, "left", "bottom"),
        }
        # For brittle materials, UTS and Fracture share the same point —
        # offset Fracture label below to avoid overlap
        if is_brittle and "Ultimate Tensile Strength" in points and "Fracture" in points:
            uts_pos = points["Ultimate Tensile Strength"]
            frac_pos = points["Fracture"]
            if abs(uts_pos[0] - frac_pos[0]) < 0.01 and abs(uts_pos[1] - frac_pos[1]) < 10:
                label_offsets["Fracture"] = (0.04, -0.045, "left", "top")
        display_names = {}
        if is_aluminum:
            # Move yield label below the curve to avoid overlapping UTS
            label_offsets["Yield Strength"] = (0.04, -0.035, "left", "top")

        # When a point is highlighted or hidden, only show "?" on that
        # point — all other points get dots only (no labels). This reduces
        # clutter and makes the quiz more challenging.
        quiz_mode = bool(highlight_point or hide_label)

        for name, (s_val, st_val) in points.items():
            px, py = to_chart(s_val, st_val)
            color = point_colors.get(name, "white")
            is_highlighted = (highlight_point and name == highlight_point)
            is_hidden = (hide_label and name == hide_label)

            if is_highlighted:
                # Glowing "?" marker
                glow = plt.Circle((px, py), 0.025, color=color, alpha=0.3, zorder=8)
                ax.add_patch(glow)
                circle = plt.Circle((px, py), 0.012, color=color, ec="white", lw=2, zorder=9)
                ax.add_patch(circle)
                dx, dy, ha, va = label_offsets.get(name, (0, 0.025, "center", "bottom"))
                ax.text(px + dx, py + dy, "?",
                        ha=ha, va=va, fontsize=20, color="white",
                        fontweight="bold", zorder=10)
            elif is_hidden:
                # Smaller "?" marker
                circle = plt.Circle((px, py), 0.008, color=color, ec="white", lw=1.5, zorder=9)
                ax.add_patch(circle)
                dx, dy, ha, va = label_offsets.get(name, (0, 0.025, "center", "bottom"))
                ax.text(px + dx, py + dy, "?",
                        ha=ha, va=va, fontsize=16, color="#aaaaaa",
                        fontweight="bold", zorder=10)
            elif quiz_mode:
                # In quiz mode: show labels on non-target points too
                circle = plt.Circle((px, py), 0.008, color=color, ec="white", lw=1.5, zorder=9)
                ax.add_patch(circle)
                label_text = display_names.get(name, name)
                dx, dy, ha, va = label_offsets.get(name, (0, 0.045, "center", "bottom"))
                ax.text(px + dx, py + dy, label_text,
                        ha=ha, va=va, fontsize=10, color=color,
                        fontweight="bold", zorder=10)
            else:
                # Full label mode (show all point labels)
                circle = plt.Circle((px, py), 0.008, color=color, ec="white", lw=1.5, zorder=9)
                ax.add_patch(circle)
                label_text = display_names.get(name, name)
                dx, dy, ha, va = label_offsets.get(name, (0, 0.025, "center", "bottom"))
                ax.plot([px, px + dx], [py, py + dy * 0.5],
                        color=color, linewidth=0.8, linestyle=":", alpha=0.6, zorder=7)
                ax.text(px + dx, py + dy, label_text,
                        ha=ha, va=va, fontsize=11, color=color,
                        fontweight="bold", zorder=10)

        # ── Horizontal dashed lines from key points to Y-axis ────────────
        if not quiz_mode:
            for name, (s_val, st_val) in points.items():
                if name == "Fracture":
                    continue
                px, py = to_chart(s_val, st_val)
                ax.plot([chart_left, px], [py, py],
                        color="#444466", linewidth=0.8, linestyle=":", zorder=2)

        # ── Title ────────────────────────────────────────────────────────
        # Check if title has a quoted True/False statement (starts with ")
        title_lines = title.split("\n", 1)
        has_statement = len(title_lines) > 1 and title_lines[1].strip().startswith('"')

        if has_statement:
            # Render header and statement separately with good spacing
            header = title_lines[0]
            wrapped_header = "\n".join(textwrap.wrap(header, width=25))
            ax.text(0.5, TITLE_Y, wrapped_header, ha="center", va="top",
                    fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                    transform=ax.transAxes, linespacing=1.2)

            statement = title_lines[1].strip().strip('"')
            wrapped_stmt = "\n".join(textwrap.wrap(statement, width=30))
            n_header_lines = wrapped_header.count("\n") + 1
            stmt_y = TITLE_Y - n_header_lines * 0.045 - 0.015
            ax.text(0.5, stmt_y, wrapped_stmt, ha="center", va="top",
                    fontsize=15, color="#ffcc66", fontstyle="italic",
                    transform=ax.transAxes, linespacing=1.4)
        else:
            # Regular title (may contain newlines for wrapping)
            wrapped_title = "\n".join(textwrap.wrap(title, width=25))
            ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                    fontsize=TITLE_FONTSIZE, color="white", fontweight="bold",
                    transform=ax.transAxes, linespacing=1.2)

        # Material subtitle (between title and chart top) — skip if statement
        # already provides context (True/False templates)
        if not has_statement:
            material_match = re.search(r"for\s+(.+?)\.", description, re.IGNORECASE)
            if material_match:
                mat_name = material_match.group(1)
                subtitle_y = chart_top + 0.06
                ax.text(0.5, subtitle_y, mat_name, ha="center",
                        fontsize=14, color="#aaaaaa", fontstyle="italic")

        # ── Answer options at bottom ─────────────────────────────────────
        if answer_options:
            self._draw_answer_options(ax, answer_options, correct_answer)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    # ── Infographic ─────────────────────────────────────────────────────
    async def generate_infographic(
        self,
        title: str,
        description: str,
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Generate an educational infographic with diagram, formula, and key facts."""
        import re

        fig, ax = plt.subplots(figsize=(PHONE_WIDTH, PHONE_HEIGHT), facecolor=self.bg_color)
        ax.set_facecolor(self.bg_color)

        desc_lower = description.lower()
        has_options = answer_options and len(answer_options) > 0

        # Title at top
        import textwrap
        wrapped_title = "\n".join(textwrap.wrap(title, width=25))
        ax.text(0.5, TITLE_Y, wrapped_title, ha="center", va="top",
                fontsize=22, color="white", fontweight="bold",
                transform=ax.transAxes, linespacing=1.2)

        # Determine which visual to draw
        if "spring" in desc_lower or "hooke" in desc_lower:
            self._draw_spring_infographic(ax, description, has_options=has_options)
        elif "pulley" in desc_lower:
            self._draw_pulley_infographic(ax, description, has_options=has_options)
        elif "gear" in desc_lower:
            self._draw_gear_infographic(ax, description, has_options=has_options)

        # Answer options OR CTA at bottom
        if has_options:
            self._draw_answer_options(ax, answer_options, correct_answer)
        else:
            # Draw CTA bar at bottom
            ax.text(0.5, 0.12, "Save this for your exam!",
                    ha="center", fontsize=16, color=COLOR_TEAL, fontweight="bold",
                    fontstyle="italic")

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        return self._save_and_upload()

    def _draw_spring_infographic(self, ax, description: str, has_options: bool = False):
        """Draw a spring diagram with Hooke's law formula and values."""
        import re

        # Parse values
        k_match = re.search(r"k\s*=\s*(\d+(?:\.\d+)?)", description)
        x_match = re.search(r"x\s*=\s*(\d+(?:\.\d+)?)", description)
        f_match = re.search(r"F\s*=\s*(\d+(?:\.\d+)?)", description)
        k_val = float(k_match.group(1)) if k_match else 100
        x_val = float(x_match.group(1)) if x_match else 0.2
        f_val = float(f_match.group(1)) if f_match else k_val * x_val

        # Spring visual: wall on left, coils, block on right
        center_y = 0.72
        wall_x = 0.15
        block_x = 0.72
        spring_y_top = center_y + 0.04
        spring_y_bot = center_y - 0.04

        # Wall (hatched)
        ax.plot([wall_x, wall_x], [center_y - 0.08, center_y + 0.08], "w-", linewidth=4)
        for y in np.linspace(center_y - 0.07, center_y + 0.07, 5):
            ax.plot([wall_x - 0.03, wall_x], [y - 0.02, y], "w-", linewidth=2)

        # Spring coils (zigzag)
        n_coils = 8
        coil_xs = np.linspace(wall_x + 0.02, block_x - 0.04, n_coils * 2 + 1)
        coil_ys = []
        for i, cx in enumerate(coil_xs):
            if i % 2 == 0:
                coil_ys.append(center_y)
            else:
                coil_ys.append(spring_y_top if (i // 2) % 2 == 0 else spring_y_bot)
        ax.plot(coil_xs, coil_ys, color=COLOR_TEAL, linewidth=3)

        # Block
        block_w = 0.10
        block_h = 0.10
        block = patches.FancyBboxPatch(
            (block_x - 0.02, center_y - block_h / 2), block_w, block_h,
            boxstyle="round,pad=0.005", facecolor=COLOR_TEAL, alpha=0.6,
            edgecolor="white", linewidth=2,
        )
        ax.add_patch(block)

        # Force arrow
        arrow_start = block_x + block_w + 0.02
        ax.annotate(
            "", xy=(arrow_start + 0.10, center_y),
            xytext=(arrow_start, center_y),
            arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=4, mutation_scale=20)
        )
        ax.text(arrow_start + 0.05, center_y + 0.04, "F",
                ha="center", fontsize=16, color=COLOR_RED, fontweight="bold")

        # Displacement dimension below spring
        dim_y = center_y - 0.15
        ax.annotate(
            "", xy=(wall_x, dim_y), xytext=(block_x, dim_y),
            arrowprops=dict(arrowstyle="<->", color="white", lw=2)
        )
        ax.text((wall_x + block_x) / 2, dim_y - 0.035, f"x = {x_val:.2f} m",
                ha="center", fontsize=14, color="white", fontweight="bold")

        # Formula box — consistent spacing above options
        formula_y = 0.44 if has_options else 0.40
        formula_box = patches.FancyBboxPatch(
            (0.15, formula_y - 0.04), 0.70, 0.07,
            boxstyle="round,pad=0.015", facecolor="#1e1e3a",
            edgecolor=COLOR_TEAL, linewidth=2,
        )
        ax.add_patch(formula_box)
        ax.text(0.5, formula_y, "F = kx", ha="center", va="center",
                fontsize=22, color=COLOR_TEAL, fontweight="bold")

        # Values below formula — hide F answer for quiz mode
        values_y = formula_y - 0.10
        if has_options:
            ax.text(0.5, values_y, f"k = {k_val:.0f} N/m    x = {x_val:.2f} m    F = ?",
                    ha="center", fontsize=13, color="#cccccc")
        else:
            ax.text(0.5, values_y, f"k = {k_val:.0f} N/m    x = {x_val:.2f} m    F = {f_val:.1f} N",
                    ha="center", fontsize=13, color="#cccccc")

    def _draw_pulley_infographic(self, ax, description: str, has_options: bool = False):
        """Draw a pulley system diagram with dynamic layout."""
        import re

        n_match = re.search(r"(\d+)\s*pulley", description)
        load_match = re.search(r"load\s*=\s*(\d+(?:\.\d+)?)\s*kg", description)
        n_pulleys = int(n_match.group(1)) if n_match else 2
        load_kg = float(load_match.group(1)) if load_match else 100

        center_x = 0.5
        pulley_r = 0.04
        aspect = PHONE_HEIGHT / PHONE_WIDTH  # ~1.778, for making circles round

        # --- Dynamic layout ---
        load_block_h = 0.06
        formula_box_h = 0.07

        if has_options:
            # Quiz: generous spacing, use full canvas
            formula_gap = 0.12   # gap between load block bottom and formula center
            subtitle_gap = 0.06  # gap from formula center to MA subtitle
            values_gap = 0.12    # gap from formula center to values text
            top_y = 0.80         # leave gap below 2-line title bottom (~0.87)
            bot_limit = 0.33     # just above option box tops (0.20 + 0.11)

            # Scale pulley size and offsets based on count
            if n_pulleys <= 2:
                pulley_r = 0.04
                first_pulley_offset = 0.04
                load_rope = 0.06
            elif n_pulleys == 3:
                pulley_r = 0.035
                first_pulley_offset = 0.03
                load_rope = 0.05
            else:  # 4 pulleys
                pulley_r = 0.03
                first_pulley_offset = 0.03
                load_rope = 0.04

            # Compute pulley gap from available space (no hard minimum)
            avail = top_y - bot_limit
            fixed = (first_pulley_offset + load_rope + load_block_h
                     + formula_gap + values_gap)
            remaining = avail - fixed
            if n_pulleys > 1:
                pulley_gap = min(0.10, remaining / (n_pulleys - 1))
            else:
                pulley_gap = 0
        else:
            # Infographic: tighter gaps, center content vertically
            formula_gap = 0.10
            subtitle_gap = 0.05
            values_gap = 0.10
            first_pulley_offset = 0.04
            load_rope = 0.06
            pulley_gap = min(0.10, 0.10) if n_pulleys > 1 else 0
            # Total content height
            diagram_h = (0.04 + first_pulley_offset
                         + (max(n_pulleys - 1, 0) * pulley_gap)
                         + load_rope + load_block_h)
            content_h = diagram_h + formula_gap + formula_box_h / 2 + values_gap
            top_bound = 0.84
            bot_bound = 0.18
            available = top_bound - bot_bound
            top_y = bot_bound + available / 2 + content_h / 2
            top_y = min(top_y, top_bound)

        # Ceiling bar
        ax.plot([0.2, 0.8], [top_y + 0.02, top_y + 0.02], "w-", linewidth=5)
        for x in np.linspace(0.22, 0.78, 8):
            ax.plot([x, x - 0.02], [top_y + 0.02, top_y + 0.05], "w-", linewidth=1.5)

        # Draw pulleys vertically (use Ellipse to compensate for 9:16 aspect)
        from matplotlib.patches import Ellipse
        pulley_positions = []
        for i in range(n_pulleys):
            py = top_y - first_pulley_offset - i * pulley_gap
            ellipse = Ellipse((center_x, py),
                              width=pulley_r * 2,
                              height=pulley_r * 2 / aspect,
                              facecolor=COLOR_TEAL, edgecolor="white", lw=2, zorder=5)
            ax.add_patch(ellipse)
            dot = Ellipse((center_x, py),
                          width=0.01, height=0.01 / aspect,
                          facecolor="white", edgecolor="white", zorder=6)
            ax.add_patch(dot)
            pulley_positions.append((center_x, py))

        # Rope
        if pulley_positions:
            # Pulley visual radius in Y (aspect-corrected)
            pr_y = pulley_r / aspect

            # Top attachment to ceiling
            ax.plot([center_x, center_x], [top_y + 0.02, pulley_positions[0][1] + pr_y],
                    color="#aaaaaa", linewidth=2)
            # Between pulleys
            for i in range(len(pulley_positions) - 1):
                ax.plot([center_x + pulley_r, center_x + pulley_r],
                        [pulley_positions[i][1], pulley_positions[i+1][1]],
                        color="#aaaaaa", linewidth=2)
            # From last pulley down to load
            last_y = pulley_positions[-1][1]
            load_y = last_y - load_rope
            ax.plot([center_x, center_x], [last_y - pr_y, load_y + 0.02],
                    color="#aaaaaa", linewidth=2)

            # Effort rope on side — ends below last pulley with arrow, not into load
            effort_x = center_x - pulley_r
            effort_top = pulley_positions[0][1]
            effort_bot = load_y + load_block_h * 0.5  # stop well above load block
            ax.plot([effort_x, effort_x],
                    [effort_top, effort_bot],
                    color=COLOR_RED, linewidth=2.5)
            # Arrow tip pointing down
            arrow_sz = 0.015
            ax.plot([effort_x - arrow_sz, effort_x, effort_x + arrow_sz],
                    [effort_bot + arrow_sz * 1.5, effort_bot, effort_bot + arrow_sz * 1.5],
                    color=COLOR_RED, linewidth=2.5, solid_capstyle="round")
            ax.text(effort_x - 0.06, (effort_top + effort_bot) / 2,
                    "Effort", ha="center", fontsize=11, color=COLOR_RED,
                    fontweight="bold", rotation=90)

            # Load block (wider for readable text)
            load_w = 0.16
            load_block = patches.FancyBboxPatch(
                (center_x - load_w / 2, load_y - load_block_h), load_w, load_block_h,
                boxstyle="round,pad=0.008", facecolor="#333366",
                edgecolor="white", linewidth=2,
            )
            ax.add_patch(load_block)
            ax.text(center_x, load_y - load_block_h * 0.3, "Mass",
                    ha="center", va="center", fontsize=10, color="#aaaaaa")
            ax.text(center_x, load_y - load_block_h * 0.7, f"{load_kg:.0f} kg",
                    ha="center", va="center", fontsize=14, color="white", fontweight="bold")

            diagram_bottom = load_y - load_block_h
        else:
            diagram_bottom = diagram_bot

        # --- Formula box positioned below diagram ---
        weight = load_kg * 9.81
        effort = weight / n_pulleys

        formula_y = diagram_bottom - formula_gap
        if has_options:
            formula_y = max(formula_y, 0.48)

        formula_box = patches.FancyBboxPatch(
            (0.12, formula_y - 0.04), 0.76, 0.07,
            boxstyle="round,pad=0.015", facecolor="#1e1e3a",
            edgecolor=COLOR_TEAL, linewidth=2,
        )
        ax.add_patch(formula_box)
        ax.text(0.5, formula_y, "Effort = Weight / MA", ha="center", va="center",
                fontsize=18, color=COLOR_TEAL, fontweight="bold")
        # Subtitle explaining MA — positioned below the formula box bottom
        box_bottom = formula_y - 0.04
        ax.text(0.5, box_bottom - 0.035, "MA = Mechanical Advantage (number of pulleys)",
                ha="center", va="top", fontsize=12, color="#888888", style="italic")
        values_y = box_bottom - 0.08
        if has_options:
            ax.text(0.5, values_y,
                    f"MA = {n_pulleys}    Weight = {weight:.0f} N    Effort = ?",
                    ha="center", fontsize=13, color="#cccccc")
        else:
            ax.text(0.5, values_y,
                    f"MA = {n_pulleys}    Weight = {weight:.0f} N    Effort = {effort:.1f} N",
                    ha="center", fontsize=13, color="#cccccc")

    @staticmethod
    def _gear_polygon(cx, cy, r_pitch, n_teeth, aspect, rotation=0.0):
        """Build a gear outline polygon with proper tooth profiles.

        Returns list of (x, y) vertices for a closed polygon.
        """
        addendum = r_pitch * 0.12   # tooth height above pitch circle
        dedendum = r_pitch * 0.14   # tooth depth below pitch circle
        r_outer = r_pitch + addendum
        r_root = r_pitch - dedendum

        tooth_angle = 2 * np.pi / n_teeth
        tip_half = tooth_angle * 0.22   # tooth tip arc half-width
        flank = tooth_angle * 0.05      # transition width

        verts = []
        for i in range(n_teeth):
            base_angle = rotation + i * tooth_angle
            angles_radii = [
                (base_angle, r_root),
                (base_angle + tooth_angle * 0.5 - tip_half - flank, r_root),
                (base_angle + tooth_angle * 0.5 - tip_half, r_outer),
                (base_angle + tooth_angle * 0.5 + tip_half, r_outer),
                (base_angle + tooth_angle * 0.5 + tip_half + flank, r_root),
                (base_angle + tooth_angle, r_root),
            ]
            for a, r in angles_radii:
                verts.append((cx + r * np.cos(a), cy + r * np.sin(a) / aspect))

        verts.append(verts[0])  # close
        return verts

    def _draw_gear_infographic(self, ax, description: str, has_options: bool = False):
        """Draw meshing gears with ratio information."""
        import re
        from matplotlib.patches import Polygon, Ellipse

        driver_match = re.search(r"driver.*?(\d+)\s*teeth", description, re.IGNORECASE)
        driven_match = re.search(r"driven.*?(\d+)\s*teeth", description, re.IGNORECASE)
        n_driver = int(driver_match.group(1)) if driver_match else 20
        n_driven = int(driven_match.group(1)) if driven_match else 60
        ratio = n_driven / n_driver

        aspect = PHONE_HEIGHT / PHONE_WIDTH

        # Pitch radii — scale so both fit nicely, with minimum driver size
        driver_r = 0.10
        driven_r = driver_r * ratio
        if driven_r > 0.22:
            driven_r = 0.22
            driver_r = driven_r / ratio
        if driver_r < 0.06:
            driver_r = 0.06
            driven_r = driver_r * ratio
            if driven_r > 0.22:
                driven_r = 0.22

        # Vertically center gears in available space
        # For quiz: gears sit between title (~0.85) and formula (~0.52)
        # For infographic: gears sit between title (~0.85) and lower area
        max_r = max(driver_r, driven_r)
        gear_visual_height = (max_r * 1.15) / aspect + 0.08  # gear radius + labels
        if has_options:
            # Center gears between title bottom and formula top
            top_bound = 0.84
            bot_bound = 0.52
            center_y = (top_bound + bot_bound) / 2 + gear_visual_height * 0.2
        else:
            center_y = 0.72
        # Center both gears horizontally
        total_w = driver_r + driven_r + 0.01
        mid_x = 0.50
        driver_cx = mid_x - total_w / 2
        driven_cx = mid_x + total_w / 2

        # Rotation offset so teeth mesh at the contact point
        driven_tooth_angle = 2 * np.pi / n_driven
        driven_rot = np.pi - driven_tooth_angle * 0.5

        for cx, r, n_teeth, color, label, rot in [
            (driver_cx, driver_r, n_driver, COLOR_RED, f"Driver\n{n_driver}T", 0.0),
            (driven_cx, driven_r, n_driven, COLOR_TEAL, f"Driven\n{n_driven}T", driven_rot),
        ]:
            # Gear body polygon with teeth
            verts = self._gear_polygon(cx, center_y, r, n_teeth, aspect, rotation=rot)
            gear_poly = Polygon(verts, closed=True,
                                facecolor=color, alpha=0.25,
                                edgecolor=color, linewidth=2, zorder=3)
            ax.add_patch(gear_poly)

            # Hub circle (ellipse for aspect correction)
            hub_r = r * 0.25
            hub = Ellipse((cx, center_y), hub_r * 2, hub_r * 2 / aspect,
                          facecolor=self.bg_color, ec=color, lw=2, zorder=4)
            ax.add_patch(hub)

            # Axle dot
            dot = Ellipse((cx, center_y), 0.012, 0.012 / aspect,
                          facecolor="white", zorder=5)
            ax.add_patch(dot)

            # Label below gear
            gear_bottom = center_y - (r * 1.15) / aspect
            ax.text(cx, gear_bottom - 0.02, label,
                    ha="center", va="top", fontsize=12, color=color,
                    fontweight="bold", linespacing=1.3)

        # Rotation arrow on driver
        arr_y = center_y + (driver_r + 0.02) / aspect
        ax.annotate("", xy=(driver_cx + 0.03, arr_y),
                    xytext=(driver_cx - 0.03, arr_y),
                    arrowprops=dict(arrowstyle="-|>", color=COLOR_RED, lw=2))

        # Formula box — position relative to gear bottom for consistent spacing
        # Driven gear label bottom ≈ center_y - (r*1.15)/aspect - 0.02 - 0.06 (two text lines)
        max_r = max(driver_r, driven_r)
        gear_labels_bottom = center_y - (max_r * 1.15) / aspect - 0.08
        # Place formula box with consistent gap below gear labels
        formula_y = gear_labels_bottom - 0.06
        # But clamp so it doesn't overlap answer options
        if has_options:
            formula_y = max(formula_y, 0.44)
        else:
            formula_y = max(formula_y, 0.26)
        formula_box = patches.FancyBboxPatch(
            (0.10, formula_y - 0.04), 0.80, 0.07,
            boxstyle="round,pad=0.015", facecolor="#1e1e3a",
            edgecolor=COLOR_TEAL, linewidth=2,
        )
        ax.add_patch(formula_box)
        ax.text(0.5, formula_y, "GR = N_driven / N_driver",
                ha="center", va="center", fontsize=18, color=COLOR_TEAL, fontweight="bold")

        # Values — hide answer for quiz mode
        values_y = formula_y - 0.10
        if has_options:
            ax.text(0.5, values_y,
                    f"N_driven = {n_driven}    N_driver = {n_driver}    GR = ?",
                    ha="center", fontsize=13, color="#cccccc")
        else:
            ax.text(0.5, values_y,
                    f"GR = {n_driven} / {n_driver} = {ratio:.2f}:1",
                    ha="center", fontsize=14, color="#cccccc")
            ax.text(0.5, values_y - 0.04,
                    f"Output torque is {ratio:.1f}x higher, speed is {1/ratio:.2f}x",
                    ha="center", fontsize=11, color="#999999")

    async def generate_from_description(
        self,
        title: str,
        description: str,
        answer_options: list[str] | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """
        Smart diagram generation based on description analysis.
        Parses the description to determine diagram type and parameters.
        Optimized for phone screens (9:16 aspect ratio) with answer options at bottom.
        """
        logger.info("generate_from_description called - Title: %s", title)
        logger.debug("Answer options: %s", answer_options)
        description_lower = description.lower()

        # Determine diagram type and generate
        if "stress-strain curve" in description_lower or "stress strain curve" in description_lower:
            return await self.generate_stress_strain_curve(
                title=title, description=description,
                answer_options=answer_options, correct_answer=correct_answer
            )
        elif "infographic" in description_lower:
            return await self.generate_infographic(
                title=title, description=description,
                answer_options=answer_options, correct_answer=correct_answer
            )
        elif "beam" in description_lower or "support" in description_lower:
            return await self.generate_beam_from_description(
                title, description, answer_options, correct_answer
            )
        elif "hanging weight" in description_lower and "cable" in description_lower:
            return await self.generate_free_body_diagram(
                title=title, forces=[], answer_options=answer_options,
                correct_answer=correct_answer, body_type="cables", description=description
            )
        elif "free body" in description_lower or "forces" in description_lower:
            forces = self._parse_forces_description(description)
            # Detect body type from description
            if "incline" in description_lower or "slope" in description_lower:
                body_type = "block_incline"
            elif "opposite" in description_lower or "couple" in description_lower or "lever" in description_lower or "separated" in description_lower:
                body_type = "bar"
            else:
                body_type = "particle"
            return await self.generate_free_body_diagram(
                title=title, forces=forces, answer_options=answer_options,
                correct_answer=correct_answer, body_type=body_type, description=description
            )
        elif "shear" in description_lower and "bolt" in description_lower:
            return await self.generate_shear_diagram(
                title=title, description=description,
                answer_options=answer_options, correct_answer=correct_answer
            )
        elif "stress" in description_lower or "elongation" in description_lower or "axial" in description_lower:
            return await self.generate_stress_diagram(
                title=title, description=description,
                answer_options=answer_options, correct_answer=correct_answer
            )
        else:
            # Default to beam diagram
            return await self.generate_beam_from_description(
                title, description, answer_options, correct_answer
            )


# Singleton instance
diagram_generator = DiagramGenerator()
