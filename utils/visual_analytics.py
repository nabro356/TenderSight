"""
Visual Analytics — Charts and visualizations for evaluation reports.
Uses matplotlib to generate charts as base64 images for Streamlit.
"""
import io
import base64
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="#ffffff", edgecolor="none")
    buf.seek(0)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_radar_chart(evaluations: dict, criteria: list) -> str:
    """Generate a radar chart comparing all bidders across criterion types."""
    import matplotlib.pyplot as plt
    import numpy as np

    # Group criteria by type
    type_scores = {}  # {bidder: {type: avg_score}}
    types_set = set()

    for name, ev in evaluations.items():
        type_scores[name] = {}
        for v in ev.get("verdicts", []):
            ctype = v.get("criterion_type", "General")
            types_set.add(ctype)
            score = 1.0 if v.get("status") == "ELIGIBLE" else (0.5 if v.get("status") == "MANUAL_REVIEW" else 0.0)
            if ctype not in type_scores[name]:
                type_scores[name][ctype] = []
            type_scores[name][ctype].append(score)

    # Average scores per type
    categories = sorted(types_set)
    if len(categories) < 3:
        categories = categories + ["Overall"]  # Need at least 3 for radar

    for name in type_scores:
        for ctype in categories:
            if ctype in type_scores[name]:
                type_scores[name][ctype] = sum(type_scores[name][ctype]) / len(type_scores[name][ctype])
            elif ctype == "Overall":
                all_scores = [s for scores in type_scores[name].values() for s in (scores if isinstance(scores, list) else [scores])]
                type_scores[name][ctype] = sum(all_scores) / max(len(all_scores), 1) if all_scores else 0
            else:
                type_scores[name][ctype] = 0

    # Create radar
    N = len(categories)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")

    colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

    for idx, (name, scores) in enumerate(type_scores.items()):
        values = [scores.get(cat, 0) for cat in categories]
        values += values[:1]
        color = colors[idx % len(colors)]
        ax.plot(angles, values, 'o-', linewidth=2, label=name[:20], color=color, markersize=6)
        ax.fill(angles, values, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=10, fontweight="bold", color="#334155")
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], size=8, color="#94a3b8")
    ax.spines['polar'].set_color('#e2e8f0')
    ax.grid(color='#e2e8f0', linewidth=0.5)

    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9,
              frameon=True, facecolor='white', edgecolor='#e2e8f0')
    ax.set_title("Bidder Comparison by Criterion Type", pad=20,
                 fontsize=14, fontweight="bold", color="#1e293b")

    return _fig_to_base64(fig)


def generate_heatmap(evaluations: dict, criteria: list) -> str:
    """Generate a bidder × criteria heatmap matrix."""
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap

    bidder_names = list(evaluations.keys())
    crit_ids = [c.get("id", f"C{i}") for i, c in enumerate(criteria)]

    if not bidder_names or not crit_ids:
        return ""

    # Build matrix: 1=eligible, 0.5=review, 0=not_eligible
    matrix = []
    for name in bidder_names:
        row = []
        verdicts_map = {
            v.get("criterion_id"): v.get("status", "MANUAL_REVIEW")
            for v in evaluations[name].get("verdicts", [])
        }
        for cid in crit_ids:
            status = verdicts_map.get(cid, "MANUAL_REVIEW")
            row.append(1.0 if status == "ELIGIBLE" else (0.5 if status == "MANUAL_REVIEW" else 0.0))
        matrix.append(row)

    matrix = np.array(matrix)

    fig, ax = plt.subplots(figsize=(max(8, len(crit_ids) * 1.2), max(3, len(bidder_names) * 0.8)))
    fig.patch.set_facecolor("#ffffff")

    cmap = ListedColormap(["#fee2e2", "#fef3c7", "#dcfce7"])
    im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=1)

    ax.set_xticks(range(len(crit_ids)))
    ax.set_xticklabels(crit_ids, rotation=45, ha='right', fontsize=9, fontweight='bold', color='#334155')
    ax.set_yticks(range(len(bidder_names)))
    ax.set_yticklabels([n[:25] for n in bidder_names], fontsize=10, color='#334155')

    # Add text annotations
    status_labels = {1.0: "✅", 0.5: "⚠️", 0.0: "❌"}
    for i in range(len(bidder_names)):
        for j in range(len(crit_ids)):
            label = status_labels.get(matrix[i, j], "?")
            ax.text(j, i, label, ha='center', va='center', fontsize=14)

    # Grid lines
    for i in range(len(bidder_names) + 1):
        ax.axhline(i - 0.5, color='white', linewidth=2)
    for j in range(len(crit_ids) + 1):
        ax.axvline(j - 0.5, color='white', linewidth=2)

    ax.set_title("Eligibility Heatmap", fontsize=14, fontweight="bold",
                 color="#1e293b", pad=15)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    plt.tight_layout()
    return _fig_to_base64(fig)


def generate_confidence_chart(evaluations: dict) -> str:
    """Generate horizontal bar chart of confidence per bidder."""
    import matplotlib.pyplot as plt
    import numpy as np

    bidder_names = list(evaluations.keys())
    if not bidder_names:
        return ""

    confidences = []
    colors_list = []
    for name in bidder_names:
        verdicts = evaluations[name].get("verdicts", [])
        avg_conf = sum(v.get("confidence", 0.5) for v in verdicts) / max(len(verdicts), 1)
        confidences.append(avg_conf)
        status = evaluations[name].get("overall_status", "MANUAL_REVIEW")
        colors_list.append("#16a34a" if status == "ELIGIBLE" else "#dc2626" if status == "NOT_ELIGIBLE" else "#d97706")

    fig, ax = plt.subplots(figsize=(8, max(2.5, len(bidder_names) * 0.7)))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")

    y_pos = np.arange(len(bidder_names))
    bars = ax.barh(y_pos, confidences, height=0.5, color=colors_list, edgecolor='white', linewidth=1)

    for i, (bar, conf) in enumerate(zip(bars, confidences)):
        ax.text(conf + 0.02, i, f"{conf:.0%}", va='center', fontsize=10,
                fontweight='bold', color='#334155')

    ax.set_yticks(y_pos)
    ax.set_yticklabels([n[:25] for n in bidder_names], fontsize=10, color='#334155')
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("Average Confidence", fontsize=10, color='#64748b')
    ax.set_title("Evaluation Confidence by Bidder", fontsize=14,
                 fontweight="bold", color="#1e293b", pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(colors='#94a3b8')

    plt.tight_layout()
    return _fig_to_base64(fig)


def generate_pass_method_chart(evaluations: dict) -> str:
    """Pie chart showing deterministic vs LLM resolution breakdown."""
    import matplotlib.pyplot as plt

    deterministic = 0
    llm = 0
    for ev in evaluations.values():
        for v in ev.get("verdicts", []):
            if v.get("pass_used") == "deterministic":
                deterministic += 1
            else:
                llm += 1

    if deterministic + llm == 0:
        return ""

    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor("#ffffff")

    sizes = [deterministic, llm]
    labels = [f"Deterministic\n({deterministic})", f"LLM Reasoning\n({llm})"]
    colors = ["#3b82f6", "#8b5cf6"]
    explode = (0.05, 0.05)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 10, "color": "#334155"},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_color("white")

    ax.set_title("Resolution Method", fontsize=14, fontweight="bold",
                 color="#1e293b", pad=15)

    plt.tight_layout()
    return _fig_to_base64(fig)
