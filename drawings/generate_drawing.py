"""
Reconstructs the hand-drawn framing plan as a parametric CAD drawing.

Outputs an AutoCAD-compatible DXF (R2018). DXF opens natively in AutoCAD and
every major CAD program and can be re-saved as .dwg there.

All dimensions are in millimetres. Every value below is a parameter so the
geometry can be corrected to match the source sketch exactly.
"""
import ezdxf
from ezdxf.enums import TextEntityAlignment

# ---------------------------------------------------------------------------
# PARAMETERS (mm) -- edit these to match the sketch precisely
# ---------------------------------------------------------------------------
MW = 100          # frame member width (drawn as the "double line" thickness)

HEIGHT      = 3760   # overall bay height (outer)
GAP         = 200    # gap between the two bays (centre joint)

# Left bay
L_WIDTH     = 3960   # overall width (outer)
L_STRIP     = 1090   # left side-strip width (vertical divider position)
# Right bay
R_WIDTH     = 3800   # overall width (outer)
R_STRIP     = 900    # left side-strip width (vertical divider position)

MAIN_PANEL  = 2810   # main panel width (reference dim from sketch)
BAND        = 1090   # height of the bottom band that holds the V-brace

# ---------------------------------------------------------------------------
doc = ezdxf.new("R2018", setup=True)
doc.units = ezdxf.units.MM
msp = doc.modelspace()

# layers
doc.layers.add("FRAME",  color=7)    # white/black members
doc.layers.add("BRACE",  color=1)    # red diagonal braces
doc.layers.add("TEXT",   color=3)    # green panel labels
doc.layers.add("DIMS",   color=5)    # blue dimensions

DIMSTYLE = "STD"
ds = doc.dimstyles.get("Standard")
ds.dxf.dimtxt = 120
ds.dxf.dimexe = 40
ds.dxf.dimexo = 40
ds.dxf.dimasz = 80
ds.dxf.dimgap = 30


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def member(x, y, w, h):
    """A frame member drawn as a filled-look closed rectangle (double line)."""
    msp.add_lwpolyline(rect(x, y, w, h), close=True, dxfattribs={"layer": "FRAME"})


def label(txt, x, y, h=200):
    msp.add_text(
        txt, height=h, dxfattribs={"layer": "TEXT"}
    ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)


def lindim(p1, p2, base, angle=0):
    d = msp.add_linear_dim(
        base=base, p1=p1, p2=p2, angle=angle,
        dxfattribs={"layer": "DIMS"},
    )
    d.render()


def draw_bay(x0, width, strip):
    """Draw one bay with its lower-left outer corner at (x0, 0)."""
    H = HEIGHT
    # perimeter members
    member(x0, 0, width, MW)                    # bottom
    member(x0, H - MW, width, MW)               # top
    member(x0, 0, MW, H)                        # left
    member(x0 + width - MW, 0, MW, H)           # right
    # vertical divider (side strip)
    dx = x0 + strip
    member(dx, MW, MW, H - 2 * MW)
    # bottom band horizontal member across the full inner width
    by = BAND
    member(x0 + MW, by, width - 2 * MW, MW)
    bx0 = dx + MW            # main-panel inner left
    bx1 = x0 + width - MW    # main-panel inner right
    # V-brace inside the band (apex at bottom-centre on the bottom member)
    apex_x = (bx0 + bx1) / 2.0
    msp.add_line((bx0, by), (apex_x, MW), dxfattribs={"layer": "BRACE"})
    msp.add_line((bx1, by), (apex_x, MW), dxfattribs={"layer": "BRACE"})
    # panel labels (F)
    label("F", x0 + strip / 2.0, H * 0.6)                      # side strip
    label("F", (bx0 + bx1) / 2.0, (by + H - MW) / 2.0)         # main upper
    label("F", x0 + strip / 2.0, (MW + by) / 2.0)              # lower-left band
    return dict(x0=x0, width=width, strip=strip, dx=dx, by=by,
                bx0=bx0, bx1=bx1)


# place the two bays side by side
left  = draw_bay(0, L_WIDTH, L_STRIP)
right = draw_bay(L_WIDTH + GAP, R_WIDTH, R_STRIP)

# ---------------------------------------------------------------------------
# dimensions
# ---------------------------------------------------------------------------
# left bay top width
lindim((0, HEIGHT), (L_WIDTH, HEIGHT), base=(0, HEIGHT + 350))
# right bay top width
lindim((L_WIDTH + GAP, HEIGHT), (L_WIDTH + GAP + R_WIDTH, HEIGHT),
       base=(0, HEIGHT + 350))
# gap
lindim((L_WIDTH, HEIGHT), (L_WIDTH + GAP, HEIGHT), base=(0, HEIGHT + 600))
# overall height (right side)
lindim((L_WIDTH + GAP + R_WIDTH, 0), (L_WIDTH + GAP + R_WIDTH, HEIGHT),
       base=(L_WIDTH + GAP + R_WIDTH + 400, 0), angle=90)
# left bay bottom: strip + main
lindim((0, 0), (L_STRIP, 0), base=(0, -400))
lindim((L_STRIP, 0), (L_WIDTH, 0), base=(0, -400))
# band height (left)
lindim((0, 0), (0, BAND), base=(-400, 0), angle=90)

# ---------------------------------------------------------------------------
doc.saveas("drawings/frame_plan.dxf")
print("wrote drawings/frame_plan.dxf")

# optional preview render (skipped if matplotlib is unavailable)
try:
    import matplotlib
    matplotlib.use("Agg")
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    ctx.current_layout_properties.set_colors(bg="#FFFFFF")
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    fig.savefig("drawings/frame_plan_preview.png", dpi=110, facecolor="white")
    print("wrote drawings/frame_plan_preview.png")
except Exception as exc:  # noqa: BLE001
    print("preview skipped:", exc)
