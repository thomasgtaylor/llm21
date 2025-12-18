import csv
from collections import Counter
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots


BENCHMARK_DIR = Path("benchmarks")

MODEL_NAMES = {
    "gpt-4o-mini-2024-07-18": "GPT-4o Mini",
    "gpt-5.2-2025-12-11": "GPT-5.2",
    "claude-opus-4-5-20251101": "Claude Opus 4.5",
    "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    "gemini-3-flash-preview": "Gemini 3 Flash",
}


def load_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def get_model_stats(records: list[dict]) -> dict:
    llm_records = [r for r in records if r["strategy"] == "llm"]
    mistakes = [r for r in llm_records if r["action"] != r["optimal_action"]]

    final_records = [r for r in llm_records if r["result"]]
    total_balance = sum(float(r["balance_change"]) for r in final_records)

    mistake_types = Counter((r["optimal_action"], r["action"]) for r in mistakes)

    by_value = Counter(int(r["player_value"]) for r in mistakes)

    return {
        "total_decisions": len(llm_records),
        "mistakes": len(mistakes),
        "accuracy": (1 - len(mistakes) / len(llm_records)) * 100 if llm_records else 0,
        "balance": total_balance,
        "mistake_types": mistake_types,
        "mistakes_by_value": by_value,
    }


def load_all_models() -> dict[str, dict]:
    models = {}
    for csv_path in BENCHMARK_DIR.rglob("*.csv"):
        model_id = csv_path.stem
        display_name = MODEL_NAMES.get(model_id, model_id)
        records = load_csv(csv_path)
        models[display_name] = get_model_stats(records)
    return models


def create_accuracy_chart(models: dict[str, dict]) -> go.Figure:
    sorted_models = sorted(models.items(), key=lambda x: x[1]["accuracy"], reverse=True)
    names = [m[0] for m in sorted_models]
    accuracies = [m[1]["accuracy"] for m in sorted_models]

    colors = [
        "#2ecc71" if a >= 95 else "#3498db" if a >= 85 else "#e74c3c"
        for a in accuracies
    ]

    fig = go.Figure(
        go.Bar(
            x=accuracies,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{a:.1f}%" for a in accuracies],
            textposition="outside",
        )
    )

    fig.update_layout(
        title="Decision Accuracy by Model",
        xaxis_title="Accuracy (%)",
        yaxis_title="",
        xaxis_range=[0, 105],
        height=400,
        template="plotly_dark",
    )

    return fig


def create_balance_chart(models: dict[str, dict]) -> go.Figure:
    sorted_models = sorted(models.items(), key=lambda x: x[1]["balance"], reverse=True)
    names = [m[0] for m in sorted_models]
    balances = [m[1]["balance"] for m in sorted_models]

    colors = ["#2ecc71" if b >= 0 else "#e74c3c" for b in balances]

    fig = go.Figure(
        go.Bar(
            x=balances,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{b:+.2f}" for b in balances],
            textposition="outside",
        )
    )

    fig.update_layout(
        title="Balance After 1000 Hands",
        xaxis_title="Balance (units)",
        yaxis_title="",
        height=400,
        template="plotly_dark",
    )

    return fig


def create_mistake_type_chart(models: dict[str, dict]) -> go.Figure:
    error_categories = {
        "Over-double": [("stand", "double"), ("hit", "double")],
        "Under-double": [("double", "hit"), ("double", "stand")],
        "Over-surrender": [("hit", "surrender"), ("stand", "surrender")],
        "Under-surrender": [("surrender", "hit"), ("surrender", "stand")],
        "Hit/Stand confusion": [("hit", "stand"), ("stand", "hit")],
        "Split errors": [
            ("split", "hit"),
            ("split", "stand"),
            ("hit", "split"),
            ("stand", "split"),
        ],
    }

    fig = go.Figure()

    for model_name, stats in models.items():
        category_counts = {}
        for cat_name, patterns in error_categories.items():
            count = sum(stats["mistake_types"].get(p, 0) for p in patterns)
            category_counts[cat_name] = count

        fig.add_trace(
            go.Bar(
                name=model_name,
                x=list(category_counts.keys()),
                y=list(category_counts.values()),
            )
        )

    fig.update_layout(
        title="Mistake Types by Model",
        xaxis_title="Error Category",
        yaxis_title="Count",
        barmode="group",
        height=500,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return fig


def create_mistakes_heatmap(models: dict[str, dict]) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=3,
        subplot_titles=list(models.keys())[:6],
        horizontal_spacing=0.08,
        vertical_spacing=0.15,
    )

    player_values = list(range(8, 21))

    for idx, (model_name, stats) in enumerate(models.items()):
        row = idx // 3 + 1
        col = idx % 3 + 1

        counts = [stats["mistakes_by_value"].get(v, 0) for v in player_values]

        fig.add_trace(
            go.Bar(x=player_values, y=counts, marker_color="#e74c3c", showlegend=False),
            row=row,
            col=col,
        )

    fig.update_layout(
        title="Mistakes by Player Hand Value",
        height=600,
        template="plotly_dark",
    )

    return fig


def create_personality_radar(models: dict[str, dict]) -> go.Figure:
    fig = go.Figure()

    categories = [
        "Over-double",
        "Under-double",
        "Over-surrender",
        "Under-surrender",
        "Hits too much",
        "Stands too much",
    ]

    patterns = {
        "Over-double": [("stand", "double"), ("hit", "double")],
        "Under-double": [("double", "hit"), ("double", "stand")],
        "Over-surrender": [("hit", "surrender"), ("stand", "surrender")],
        "Under-surrender": [("surrender", "hit"), ("surrender", "stand")],
        "Hits too much": [("stand", "hit")],
        "Stands too much": [("hit", "stand")],
    }

    for model_name, stats in models.items():
        values = []
        for cat in categories:
            count = sum(stats["mistake_types"].get(p, 0) for p in patterns[cat])
            values.append(count)

        values.append(values[0])

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                name=model_name,
                fill="toself",
                opacity=0.6,
            )
        )

    fig.update_layout(
        title="Model Personality: Error Tendencies",
        polar=dict(radialaxis=dict(visible=True)),
        height=600,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )

    return fig


def create_dashboard(models: dict[str, dict]) -> str:
    accuracy_chart = create_accuracy_chart(models)
    balance_chart = create_balance_chart(models)
    mistake_type_chart = create_mistake_type_chart(models)
    heatmap = create_mistakes_heatmap(models)
    radar = create_personality_radar(models)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Blackjack Benchmark Results</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #fff;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 1200px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .summary {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: #16213e;
            padding: 20px 40px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #888;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <h1>🃏 LLM Blackjack Benchmark</h1>
    <p class="subtitle">How well do language models play optimal blackjack strategy?</p>

    <div class="summary">
        <div class="stat-card">
            <div class="stat-value">{len(models)}</div>
            <div class="stat-label">Models Tested</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">1,000</div>
            <div class="stat-label">Hands per Model</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{max(m["accuracy"] for m in models.values()):.1f}%</div>
            <div class="stat-label">Best Accuracy</div>
        </div>
    </div>

    <div class="grid">
        <div class="chart-container">
            <div id="accuracy"></div>
        </div>
        <div class="chart-container">
            <div id="balance"></div>
        </div>
    </div>

    <div class="chart-container">
        <div id="mistake-types"></div>
    </div>

    <div class="chart-container">
        <div id="radar"></div>
    </div>

    <div class="chart-container">
        <div id="heatmap"></div>
    </div>

    <script>
        Plotly.newPlot('accuracy', {accuracy_chart.to_json()}.data, {accuracy_chart.to_json()}.layout);
        Plotly.newPlot('balance', {balance_chart.to_json()}.data, {balance_chart.to_json()}.layout);
        Plotly.newPlot('mistake-types', {mistake_type_chart.to_json()}.data, {mistake_type_chart.to_json()}.layout);
        Plotly.newPlot('radar', {radar.to_json()}.data, {radar.to_json()}.layout);
        Plotly.newPlot('heatmap', {heatmap.to_json()}.data, {heatmap.to_json()}.layout);
    </script>
</body>
</html>
"""
    return html


def main():
    models = load_all_models()
    html = create_dashboard(models)

    output_path = Path("dashboard.html")
    output_path.write_text(html)
    print(f"Dashboard saved to {output_path}")
    print(f"Open in browser: file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
