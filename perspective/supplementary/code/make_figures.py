#!/usr/bin/env python3
"""Regenerate Figures 2-4 of the Perspective and Figure S1 of the supplement.

Requires NumPy and Matplotlib. All plotted values come from cflibs_chain.py,
the constructed record in ../record/ and the CSV/JSON files written by
worked_examples.py, reconstruct_record.py and seeded_defects.py - run those
first (or simply run run_all.py).

Figure 1 (the quantification-chain schematic) is a TikZ drawing:
../../figures/fig1_chain.tex.

Output: ../../figures/fig{2,3,4}_*.pdf/.png (main text) and
        ../figures/figS1_boltzmann.pdf/.png (supplement)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import NullFormatter  # noqa: E402

import cflibs_chain as cf  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
REC = HERE.parent / "record"
FIG = HERE.parent.parent / "figures"       # figures of the main text
FIG_SUPP = HERE.parent / "figures"         # figures of the supplement

# ---- palette; series are also distinguished by marker shape or line style ----
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"


def setup() -> None:
    family = "DejaVu Sans"
    try:
        font_manager.findfont("Liberation Sans", fallback_to_default=False)
        family = "Liberation Sans"
    except Exception:  # font not installed: keep the Matplotlib default
        pass
    plt.rcParams.update({
        "font.family": family, "font.size": 7.5,
        "axes.labelsize": 8.0, "axes.titlesize": 8.0,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True, "xtick.major.size": 3, "ytick.major.size": 3,
        "xtick.minor.size": 0, "ytick.minor.size": 0,
        "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.dpi": 600, "figure.dpi": 150, "text.color": INK,
    })
    if family == "Liberation Sans":
        plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                             "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                             "mathtext.cal": "Liberation Sans:italic", "mathtext.sf": "Liberation Sans",
                             "mathtext.tt": "Liberation Mono"})


def save(fig, name: str, folder: Path = FIG) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(folder / f"{name}.png", bbox_inches="tight", pad_inches=0.02, dpi=600)
    plt.close(fig)
    print(f"wrote {folder.relative_to(HERE.parent.parent)}/{name}.pdf/.png")


def panel_label(ax, text: str) -> None:
    ax.text(-0.02, 1.06, text, transform=ax.transAxes, fontsize=8.5, fontweight="bold",
            ha="right", va="bottom", color=INK)


# ---------------------------------------------------------------- Figure 2
def figure2() -> None:
    record = json.loads((REC / "record.json").read_text())
    st = record["stark_line"]
    g_rec = st["instrument_gaussian_fwhm_nm"] / st["observed_fwhm_nm"]
    l_rec = cf.lorentz_from_voigt(1.0, g_rec)

    g = np.linspace(0.0, 0.97, 400)
    l_voigt = np.array([cf.lorentz_from_voigt(1.0, gi) for gi in g])
    l_quad = np.sqrt(1.0 - g**2)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.3, 2.45), gridspec_kw={"wspace": 0.46})

    # (a) share of the observed width that is Lorentzian
    ax1.plot(g, np.ones_like(g), color=MUTED, lw=1.5, ls=(0, (1, 1.6)))
    ax1.plot(g, l_quad, color=ORANGE, lw=1.6, ls=(0, (5, 2)))
    ax1.plot(g, l_voigt, color=BLUE, lw=1.6)
    ax1.plot([g_rec], [l_rec], "o", ms=5.5, mfc=BLUE, mec="white", mew=1.0, zorder=5)
    ax1.annotate("constructed\nrecord", (g_rec, l_rec), xytext=(0.19, 0.56), color=INK2,
                 ha="center", va="center", fontsize=7.0,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7, shrinkA=2, shrinkB=4))
    ax1.text(0.50, 1.03, "no correction", color=INK2, ha="center", va="bottom", fontsize=7.0)
    ax1.text(0.99, 0.80, "quadrature\nsubtraction", color=INK2, ha="right", va="center", fontsize=7.0)
    ax1.text(0.56, 0.27, "Voigt-consistent\nremoval", color=INK2, ha="right", va="center", fontsize=7.0)
    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.12)
    ax1.set_xlabel(r"Instrumental share of width, $G/W$")
    ax1.set_ylabel(r"Inferred Stark share, $\Delta\lambda_{\mathrm{S}}/W$")
    ax1.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    panel_label(ax1, "(a)")

    # (b) resulting overestimate of the electron density
    gb = g[g >= 0.08]
    lb = l_voigt[g >= 0.08]
    over_none = 100.0 * (1.0 / lb - 1.0)
    over_quad = 100.0 * (np.sqrt(1.0 - gb**2) / lb - 1.0)
    ax2.plot(gb, over_none, color=MUTED, lw=1.6, ls=(0, (1, 1.6)))
    ax2.plot(gb, over_quad, color=ORANGE, lw=1.6, ls=(0, (5, 2)))
    ax2.plot([g_rec], [100.0 * (1.0 / l_rec - 1.0)], "o", ms=5.5, mfc=MUTED, mec="white", mew=1.0, zorder=5)
    ax2.plot([g_rec], [100.0 * (np.sqrt(1 - g_rec**2) / l_rec - 1.0)], "o", ms=5.5, mfc=ORANGE, mec="white", mew=1.0, zorder=5)
    ax2.set_yscale("log")
    ax2.set_xlim(0, 1.0)
    ax2.set_ylim(1, 2000)
    ax2.set_yticks([1, 10, 100, 1000])
    ax2.set_yticklabels(["1", "10", "100", "1000"])
    ax2.text(0.40, 62, "no correction", color=INK2, ha="right", va="bottom", fontsize=7.0)
    ax2.text(0.60, 9.0, "quadrature\nsubtraction", color=INK2, ha="left", va="center", fontsize=7.0)
    ax2.set_xlabel(r"Instrumental share of width, $G/W$")
    ax2.set_ylabel(r"Overestimate of $N_{\mathrm{e}}$ (%)")
    panel_label(ax2, "(b)")
    save(fig, "fig2_linewidth")


# ---------------------------------------------------------------- Figure 3
def figure3() -> None:
    with open(OUT / "table_basis.csv", newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if not r["material"].startswith("Constructed")]
    record = json.loads((REC / "record.json").read_text())
    names = list(record["elements"])
    molar = [record["elements"][n]["molar_mass_g_mol"] for n in names]
    w_ref = [record["reference"]["values"][n] for n in names]
    x_ref = cf.mass_to_mole(w_ref, molar)
    mbar = cf.mean_molar_mass_from_mole(x_ref, molar)

    fig, ax = plt.subplots(figsize=(3.9, 3.0))
    xs = np.logspace(np.log10(0.2), np.log10(4.6), 200)
    ax.axhline(1.0, color=AXIS, lw=0.8, zorder=1)
    ax.axvline(1.0, color=AXIS, lw=0.8, zorder=1)
    ax.plot(xs, 1.0 / xs, color=MUTED, lw=1.4, zorder=2)

    px = [float(r["M_over_mean"]) for r in rows]
    py = [float(r["reported_over_true_if_unconverted"]) for r in rows]
    ax.plot(px, py, "o", ms=5.5, mfc=BLUE, mec="white", mew=1.0, zorder=4, label="nominal alloy compositions")
    rx = [m / mbar for m in molar]
    ry = [mbar / m for m in molar]
    ax.plot(rx, ry, "s", ms=5.2, mfc=ORANGE, mec="white", mew=1.0, zorder=5, label="constructed record")

    labels = {("Al-2.5Li (aluminum-lithium alloy)", "Li"): ("Li in Al–2.5Li", (9, 0), "left"),
              ("90W-7Ni-3Fe (tungsten heavy alloy)", "Fe"): ("Fe, Ni in 90W–7Ni–3Fe", (9, 4), "left"),
              ("Ti-6Al-4V (titanium alloy)", "Al"): ("Al in Ti–6Al–4V", (9, 3), "left"),
              ("63Sn-37Pb (solder)", "Sn"): ("Sn in 63Sn–37Pb", (-9, -3), "right"),
              ("90W-7Ni-3Fe (tungsten heavy alloy)", "W"): ("W", (7, 6), "left"),
              ("63Sn-37Pb (solder)", "Pb"): ("Pb", (7, 6), "left")}
    for r in rows:
        key = (r["material"], r["element"])
        if key in labels:
            text, off, ha = labels[key]
            ax.annotate(text, (float(r["M_over_mean"]), float(r["reported_over_true_if_unconverted"])),
                        xytext=off, textcoords="offset points", ha=ha, va="center", fontsize=7.0, color=INK2)
    for n, x0, y0, off in zip(names, rx, ry, [(-9, -3), (-2, -11), (-9, -3)]):
        if n == "Y":
            continue
        ax.annotate(n, (x0, y0), xytext=off, textcoords="offset points", ha="right", va="center",
                    fontsize=7.0, color=INK2)
    ax.annotate("elements near the\nmean molar mass", (1.045, 0.955), xytext=(0.40, 0.58), ha="left", va="center",
                fontsize=7.0, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7, shrinkA=1, shrinkB=6))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.2, 4.6)
    ax.set_ylim(0.21, 5.0)
    ax.set_xticks([0.25, 0.5, 1.0, 2.0, 4.0])
    ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"])
    ax.set_yticks([0.25, 0.5, 1.0, 2.0, 4.0])
    ax.set_yticklabels(["0.25", "0.5", "1", "2", "4"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel(r"Molar mass relative to the mean, $M_s/\bar{M}$")
    ax.set_ylabel(r"Mole fraction over mass fraction, $x_s/w_s$")
    ax.legend(loc="upper right", handletextpad=0.3, borderaxespad=0.2)
    save(fig, "fig3_basis")


# ---------------------------------------------------------------- Figure 4
SHORT = {"U1": r"U1  Temperature $+5\%$",
         "U2": r"U2  Stark parameter $+20\%$",
         "U3": r"U3  $A_{ki}$ of X I lines $+10\%$",
         "U4": r"U4  Spectral response tilted $+5\%$ per 100 nm",
         "C1": "C1  Instrumental width not removed",
         "C2": "C2  Quadrature subtraction on a Voigt profile",
         "C3": "C3  Half width used as a full width",
         "C4": "C4  Full width used as a half width",
         "C5": "C5  Reference density too high by a factor of 10",
         "C6": "C6  Reference density too low by a factor of 10",
         "C7": "C7  Energy-unit ordinate, photon-unit intensities",
         "C8": r"C8  Ground-level weights in place of $U$",
         "C9": "C9  Mole fractions reported as mass fractions"}


def figure4() -> None:
    res = json.loads((OUT / "seeded_defects.json").read_text())
    names = res["elements"]
    style = {"X": (BLUE, "o", 6.2), "Y": (ORANGE, "s", 5.6), "Z": (AQUA, "^", 6.6)}
    ref = json.loads((REC / "record.json").read_text())["reference"]["values"]
    legend = {"X": f"X, light minor constituent ({100 * ref['X']:.0f}%)",
              "Y": f"Y, major element ({100 * ref['Y']:.0f}%)",
              "Z": f"Z, heavy minor constituent ({100 * ref['Z']:.0f}%)"}

    unc = [r for r in res["scenarios"] if r["family"] == "uncertainty"]
    slips = [r for r in res["scenarios"] if r["family"] == "slip"]
    fig = plt.figure(figsize=(6.9, 5.6))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.34], wspace=0.03)
    ax = fig.add_subplot(grid[0])
    axm = fig.add_subplot(grid[1], sharey=ax)      # indicator matrix
    label_pad = 196
    ypos, ylabels = [], []
    y = 0.0

    def group_title(text: str, yy: float) -> None:
        ax.annotate(text, xy=(0.0, yy), xycoords=ax.get_yaxis_transform(), xytext=(-label_pad, 0),
                    textcoords="offset points", ha="left", va="center", fontsize=8.0, fontweight="bold",
                    color=INK, annotation_clip=False)

    def flags(r: dict, yy: float) -> None:
        marks = (r["flag_D"], r["flag_S"], r["flag_R"])
        for j, on in enumerate(marks):
            if on:
                axm.plot([j], [yy], "o", ms=6.4, mfc=INK2, mec=INK2, mew=0.9, zorder=4)
            else:
                axm.plot([j], [yy], "o", ms=6.4, mfc="white", mec=AXIS, mew=0.9, zorder=4)

    group_title("Input and parameter errors, for comparison", y)
    for j, text in enumerate(("density\nratio", "fit\nscatter", "reference\nvalue")):
        axm.text(j, y, text, ha="center", va="center", fontsize=7.0, color=INK2, linespacing=1.05)
    y -= 1.0
    # Monte Carlo 95% intervals of all assigned input uncertainties
    offs = {"X": 0.24, "Y": 0.0, "Z": -0.24}
    for n in names:
        lo, hi = res["monte_carlo_95_interval_ratio"][n]
        col, mk, ms = style[n]
        ax.plot([lo, hi], [y + offs[n], y + offs[n]], color=col, lw=2.6, solid_capstyle="round", zorder=3)
    ypos.append(y)
    ylabels.append("All assigned input uncertainties (95% interval)")
    y -= 1.0
    for r in unc + [None] + slips:
        if r is None:
            y -= 0.35
            group_title("Convention or reporting slips", y)
            y -= 1.0
            continue
        for n in names:
            v = r["ratio_to_baseline"][n]
            col, mk, ms = style[n]
            yy = y + offs[n]
            ax.plot([1.0, v], [yy, yy], color=AXIS, lw=1.0, zorder=2)
            ax.plot([v], [yy], mk, ms=ms, mfc=col, mec="white", mew=1.0, zorder=4)
        flags(r, y)
        ypos.append(y)
        ylabels.append(SHORT[r["id"]])
        y -= 1.0

    ax.axvline(1.0, color=MUTED, lw=0.9, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(0.15, 8.0)
    ax.set_xticks([0.2, 0.5, 1.0, 2.0, 5.0])
    ax.set_xticklabels(["×0.2", "×0.5", "×1", "×2", "×5"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_yticks(ypos)
    ax.set_yticklabels(ylabels, color=INK2, ha="left")
    ax.tick_params(axis="y", length=0, pad=label_pad)
    ax.set_ylim(y + 0.4, 0.6)
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Recovered mass fraction relative to the baseline reconstruction")
    handles = [plt.Line2D([], [], ls="", marker=style[n][1], ms=style[n][2], mfc=style[n][0], mec="white", mew=1.0,
                          label=legend[n]) for n in names]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.16, 1.0), ncol=3, columnspacing=1.2,
              handletextpad=0.2, borderaxespad=0.3)

    axm.set_xlim(-0.75, 2.75)
    axm.grid(False)
    for side in ("left", "bottom"):
        axm.spines[side].set_visible(False)
    axm.tick_params(axis="both", length=0, labelleft=False, labelbottom=False)
    axm.text(0.5, 1.012, "Flagged by", transform=axm.transAxes, ha="center", va="bottom", fontsize=8.0,
             fontweight="bold", color=INK)
    key = [plt.Line2D([], [], ls="", marker="o", ms=6.4, mfc=INK2, mec=INK2, mew=0.9, label="flagged"),
           plt.Line2D([], [], ls="", marker="o", ms=6.4, mfc="white", mec=AXIS, mew=0.9, label="not flagged")]
    axm.legend(handles=key, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, columnspacing=0.9,
               handletextpad=0.1, borderaxespad=0.9)
    save(fig, "fig4_sensitivity")


# --------------------------------------------------------------- Figure S1
def figure_s1() -> None:
    with open(OUT / "boltzmann_points_replicate1.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    summ = json.loads((OUT / "summary.json").read_text())
    slope = summ["A2"]["slope_per_eV_replicate_1"]
    inter = summ["A2"]["intercepts_replicate_1"]
    style = {"X I": (BLUE, "o"), "Y I": (ORANGE, "s"), "Y II": (AQUA, "^"), "Z II": (YELLOW, "D")}
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for sp, (col, mk) in style.items():
        pts = [(float(r["E_k_eV"]), float(r["ordinate_ln_I_over_gA"])) for r in rows if r["species"] == sp]
        e = np.array([p[0] for p in pts])
        ax.plot(e, inter[sp] + slope * e, color=col, lw=1.4, zorder=2)
        ax.plot(e, [p[1] for p in pts], mk, ms=6.0, mfc=col, mec="white", mew=1.1, zorder=4, label=sp)
        ax.annotate(sp, (e.max(), inter[sp] + slope * e.max()), xytext=(6, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(2.8, 8.6)
    ax.set_xlabel(r"Upper-level energy, $E_k$ (eV)")
    ax.set_ylabel(r"$\ln\,[I/(g_k A_{ki})]$")
    ax.legend(loc="lower left", ncol=2, columnspacing=1.2, handletextpad=0.2)
    save(fig, "figS1_boltzmann", FIG_SUPP)


def main() -> None:
    setup()
    figure2()
    figure3()
    figure4()
    figure_s1()


if __name__ == "__main__":
    main()
