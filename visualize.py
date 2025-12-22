import csv
import json
from collections import Counter
from pathlib import Path


BENCHMARK_DIR = Path("benchmarks")

MODEL_INFO = {
    "gpt-4o-mini-2024-07-18": {"name": "GPT-4o Mini", "provider": "OpenAI"},
    "gpt-5.2-2025-12-11": {"name": "GPT-5.2", "provider": "OpenAI"},
    "claude-opus-4-5-20251101": {"name": "Claude Opus 4.5", "provider": "Anthropic"},
    "claude-sonnet-4-5-20250929": {"name": "Claude Sonnet 4.5", "provider": "Anthropic"},
    "gemini-3-flash-preview": {"name": "Gemini 3 Flash", "provider": "Google"},
    "gemini-3-pro-preview": {"name": "Gemini 3 Pro", "provider": "Google"},
}

PROVIDER_COLORS = {
    "OpenAI": "#10a37f",
    "Anthropic": "#d97706",
    "Google": "#4285f4",
}

ERROR_CATEGORIES = {
    "Over-double": [("stand", "double"), ("hit", "double")],
    "Under-double": [("double", "hit"), ("double", "stand")],
    "Over-surrender": [("hit", "surrender"), ("stand", "surrender")],
    "Under-surrender": [("surrender", "hit"), ("surrender", "stand")],
    "Hit/Stand": [("hit", "stand"), ("stand", "hit")],
    "Split": [("split", "hit"), ("split", "stand"), ("hit", "split"), ("stand", "split")],
}

TENDENCY_PATTERNS = {
    "Over-double": [("stand", "double"), ("hit", "double")],
    "Under-double": [("double", "hit"), ("double", "stand")],
    "Over-surrender": [("hit", "surrender"), ("stand", "surrender")],
    "Under-surrender": [("surrender", "hit"), ("surrender", "stand")],
    "Hits too much": [("stand", "hit")],
    "Stands too much": [("hit", "stand")],
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

    error_counts = {}
    for cat_name, patterns in ERROR_CATEGORIES.items():
        error_counts[cat_name] = sum(mistake_types.get(p, 0) for p in patterns)

    tendency_counts = {}
    for cat_name, patterns in TENDENCY_PATTERNS.items():
        tendency_counts[cat_name] = sum(mistake_types.get(p, 0) for p in patterns)

    mistakes_by_value = {v: by_value.get(v, 0) for v in range(8, 21)}

    return {
        "total_decisions": len(llm_records),
        "mistakes": len(mistakes),
        "accuracy": (1 - len(mistakes) / len(llm_records)) * 100 if llm_records else 0,
        "balance": total_balance,
        "error_counts": error_counts,
        "tendency_counts": tendency_counts,
        "mistakes_by_value": mistakes_by_value,
    }


def load_all_models() -> dict[str, dict]:
    models = {}
    for csv_path in BENCHMARK_DIR.rglob("*.csv"):
        model_id = csv_path.stem
        info = MODEL_INFO.get(model_id, {"name": model_id, "provider": "Unknown"})
        records = load_csv(csv_path)
        stats = get_model_stats(records)
        stats["provider"] = info["provider"]
        stats["model_id"] = model_id
        models[info["name"]] = stats
    return models


def create_leaderboard_table(models: dict[str, dict]) -> str:
    sorted_models = sorted(models.items(), key=lambda x: x[1]["accuracy"], reverse=True)

    rows = []
    for rank, (name, stats) in enumerate(sorted_models, 1):
        provider = stats["provider"]
        color = PROVIDER_COLORS.get(provider, "#6b7280")
        balance = stats["balance"]
        balance_color = "#10b981" if balance >= 0 else "#ef4444"
        balance_str = f"+{balance:.1f}" if balance >= 0 else f"{balance:.1f}"

        rows.append(f"""
            <tr data-model="{name}" data-rank="{rank}" data-provider="{provider}" data-accuracy="{stats["accuracy"]:.2f}" data-balance="{stats["balance"]:.2f}" data-mistakes="{stats["mistakes"]}">
                <td class="rank">{rank}</td>
                <td class="provider-cell" style="--accent-color: {color}">
                    <div class="provider-content">
                        <img src="assets/{provider.lower()}.svg" alt="{provider}" class="provider-icon" onerror="this.style.display='none'">
                        <span>{provider}</span>
                    </div>
                </td>
                <td class="model-cell">
                    <span class="model-name">{name}</span>
                </td>
                <td class="accuracy-cell">{stats["accuracy"]:.1f}%</td>
                <td class="balance-cell" style="color: {balance_color}">{balance_str}</td>
                <td class="mistakes-cell">{stats["mistakes"]}</td>
                <td class="details-cell">
                    <button class="details-btn" onclick="openModal('{name}')" aria-label="View details">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                    </button>
                </td>
            </tr>
        """)

    return "\n".join(rows)


def create_dashboard(models: dict[str, dict]) -> str:
    leaderboard_rows = create_leaderboard_table(models)

    models_json = json.dumps({
        name: {
            "provider": stats["provider"],
            "accuracy": stats["accuracy"],
            "balance": stats["balance"],
            "mistakes": stats["mistakes"],
            "error_counts": stats["error_counts"],
            "tendency_counts": stats["tendency_counts"],
            "mistakes_by_value": stats["mistakes_by_value"],
        }
        for name, stats in models.items()
    })

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Blackjack Benchmark</title>
    <link rel="icon" type="image/x-icon" href="/blackjack/favicon.ico">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg: #fafafa;
            --bg-card: #ffffff;
            --bg-hover: #f9fafb;
            --bg-header: #f9fafb;
            --border: #e5e7eb;
            --border-light: #f3f4f6;
            --text: #111827;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --accent: #6366f1;
            --green: #10b981;
            --red: #ef4444;
        }}
        [data-theme="dark"] {{
            --bg: #0f0f0f;
            --bg-card: #1a1a1a;
            --bg-hover: #222222;
            --bg-header: #141414;
            --border: #2a2a2a;
            --border-light: #222222;
            --text: #f0f0f0;
            --text-secondary: #a0a0a0;
            --text-muted: #707070;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            transition: background 0.2s, color 0.2s;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 48px 24px;
        }}
        header {{
            text-align: center;
            margin-bottom: 48px;
            position: relative;
        }}
        h1 {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 8px;
            letter-spacing: -0.025em;
        }}
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.05rem;
        }}
        .theme-toggle {{
            position: absolute;
            top: 0;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s;
        }}
        .theme-toggle:hover {{
            background: var(--bg-hover);
            color: var(--text);
        }}
        .sun-icon {{ display: none; }}
        .moon-icon {{ display: block; }}
        [data-theme="dark"] .sun-icon {{ display: block; }}
        [data-theme="dark"] .moon-icon {{ display: none; }}
        footer {{
            text-align: center;
            margin-top: 48px;
            padding-top: 24px;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        footer a:hover {{
            text-decoration: underline;
        }}
        .social-icons {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            margin-top: 16px;
        }}
        .social-icons a {{
            color: var(--text-muted);
            transition: color 0.2s;
            display: flex;
            align-items: center;
        }}
        .social-icons a:hover {{
            color: var(--text);
        }}
        .social-icons svg {{
            width: 20px;
            height: 20px;
        }}
        .leaderboard {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: background 0.2s, border-color 0.2s;
        }}
        .leaderboard table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .leaderboard th {{
            text-align: left;
            padding: 12px 16px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            background: var(--bg-header);
            border-bottom: 1px solid var(--border);
        }}
        .leaderboard th.sortable {{
            cursor: pointer;
            user-select: none;
            transition: color 0.15s;
            white-space: nowrap;
        }}
        .leaderboard th.sortable:hover {{
            color: var(--text);
        }}
        .leaderboard th .sort-icon {{
            display: inline-flex;
            align-items: center;
            margin-left: 4px;
            opacity: 0.4;
            transition: opacity 0.15s;
            vertical-align: middle;
            position: relative;
            top: -1.2px;
        }}
        .leaderboard th.sorted .sort-icon {{
            opacity: 1;
        }}
        .leaderboard th .sort-icon svg {{
            width: 12px;
            height: 12px;
        }}
        .leaderboard th.sorted {{
            color: var(--accent);
        }}
        .leaderboard th:last-child,
        .leaderboard td:last-child {{
            text-align: right;
        }}
        .leaderboard td {{
            padding: 16px;
            border-bottom: 1px solid var(--border-light);
            vertical-align: middle;
        }}
        .leaderboard tr:last-child td {{
            border-bottom: none;
        }}
        .leaderboard tr {{
            transition: background 0.15s;
        }}
        .leaderboard tbody tr:hover {{
            background: var(--bg-hover);
        }}
        .rank {{
            font-weight: 600;
            color: var(--text-muted);
            width: 48px;
        }}
        .provider-cell {{
            position: relative;
            padding-left: 20px !important;
        }}
        .provider-cell::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 8px;
            bottom: 8px;
            width: 3px;
            background: var(--accent-color);
            border-radius: 2px;
        }}
        .provider-content {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .provider-icon {{
            width: 20px;
            height: 20px;
        }}
        [data-theme="dark"] .provider-icon {{
            filter: brightness(1.2);
        }}
        .model-cell {{
            font-weight: 500;
        }}
        .model-name {{
            color: var(--text);
        }}
        .accuracy-cell {{
            font-weight: 600;
            color: var(--accent);
        }}
        .balance-cell {{
            font-weight: 500;
        }}
        .mistakes-cell {{
            color: var(--text-secondary);
        }}
        .details-cell {{
            width: 48px;
        }}
        .details-btn {{
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 8px;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .details-btn:hover {{
            background: var(--bg-hover);
            color: var(--accent);
            border-color: var(--accent);
        }}
        @media (max-width: 640px) {{
            .leaderboard {{
                overflow-x: auto;
            }}
            .leaderboard table {{
                min-width: 550px;
            }}
        }}

        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            background: var(--bg-card);
            z-index: 10;
        }}
        .modal-title-row {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .modal-provider-icon {{
            width: 28px;
            height: 28px;
        }}
        [data-theme="dark"] .modal-provider-icon {{
            filter: brightness(1.2);
        }}
        .modal-title {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        .modal-close {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            transition: all 0.15s;
        }}
        .modal-close:hover {{
            background: var(--bg-hover);
            color: var(--text);
        }}
        .modal-body {{
            padding: 24px;
        }}
        .modal-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--bg-header);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text);
        }}
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 4px;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }}
        .chart-container {{
            background: var(--bg-header);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .chart-container.full {{
            grid-column: 1 / -1;
        }}
        @media (max-width: 640px) {{
            .modal-stats {{
                grid-template-columns: 1fr;
            }}
            .chart-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>LLM Blackjack Benchmark</h1>
            <p class="subtitle">How well do language models play basic strategy? Results from 1,000 hands.</p>
            <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
                <svg class="sun-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
                <svg class="moon-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            </button>
        </header>

        <div class="leaderboard">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th class="sortable sorted" data-sort="accuracy" data-type="number" onclick="sortTable(this)">Accuracy<span class="sort-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg></span></th>
                        <th class="sortable" data-sort="balance" data-type="number" onclick="sortTable(this)">Balance<span class="sort-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 15l5 5 5-5M7 9l5-5 5 5"/></svg></span></th>
                        <th class="sortable" data-sort="mistakes" data-type="number" onclick="sortTable(this)">Mistakes<span class="sort-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 15l5 5 5-5M7 9l5-5 5 5"/></svg></span></th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {leaderboard_rows}
                </tbody>
            </table>
        </div>

        <footer>
            <div class="social-icons">
                <a href="https://thomasgtaylor.com" target="_blank" rel="noopener noreferrer" aria-label="Website">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="2" y1="12" x2="22" y2="12"></line>
                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                    </svg>
                </a>
                <a href="https://github.com/thomasgtaylor/llm21" target="_blank" rel="noopener noreferrer" aria-label="GitHub">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                </a>
                <a href="https://x.com/mrthomastaylor" target="_blank" rel="noopener noreferrer" aria-label="X">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                </a>
                <a href="https://youtube.com/@tgtaylor" target="_blank" rel="noopener noreferrer" aria-label="YouTube">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                    </svg>
                </a>
            </div>
        </footer>
    </div>

    <div class="modal-overlay" id="modal" onclick="closeModalOnOverlay(event)">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title-row">
                    <img src="" alt="" class="modal-provider-icon" id="modal-provider-icon" onerror="this.style.display='none'">
                    <h2 class="modal-title" id="modal-title">Model Details</h2>
                </div>
                <button class="modal-close" onclick="closeModal()" aria-label="Close">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
            </div>
            <div class="modal-body">
                <div class="modal-stats">
                    <div class="stat-card">
                        <div class="stat-value" id="stat-accuracy">-</div>
                        <div class="stat-label">Accuracy</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-balance">-</div>
                        <div class="stat-label">Balance</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-mistakes">-</div>
                        <div class="stat-label">Mistakes</div>
                    </div>
                </div>
                <div class="chart-grid">
                    <div class="chart-container">
                        <div id="chart-errors"></div>
                    </div>
                    <div class="chart-container">
                        <div id="chart-radar"></div>
                    </div>
                    <div class="chart-container full">
                        <div id="chart-by-value"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const modelsData = {models_json};

        function isDarkMode() {{
            return document.documentElement.getAttribute('data-theme') === 'dark';
        }}

        const providerColors = {{
            'OpenAI': '#10a37f',
            'Anthropic': '#d97706',
            'Google': '#4285f4'
        }};

        function getChartColors(provider) {{
            const dark = isDarkMode();
            return {{
                text: dark ? '#a0a0a0' : '#374151',
                grid: dark ? '#2a2a2a' : '#d1d5db',
                bg: 'rgba(0,0,0,0)',
                accent: providerColors[provider] || '#6366f1'
            }};
        }}

        function openModal(modelName) {{
            const data = modelsData[modelName];
            if (!data) return;

            document.getElementById('modal-title').textContent = modelName;
            const providerIcon = document.getElementById('modal-provider-icon');
            providerIcon.src = 'assets/' + data.provider.toLowerCase() + '.svg';
            providerIcon.alt = data.provider;
            providerIcon.style.display = '';
            document.getElementById('stat-accuracy').textContent = data.accuracy.toFixed(1) + '%';
            document.getElementById('stat-balance').textContent = (data.balance >= 0 ? '+' : '') + data.balance.toFixed(1);
            document.getElementById('stat-balance').style.color = data.balance >= 0 ? 'var(--green)' : 'var(--red)';
            document.getElementById('stat-mistakes').textContent = data.mistakes;

            document.getElementById('modal').classList.add('active');
            document.body.style.overflow = 'hidden';

            renderCharts(data, data.provider);
        }}

        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
            document.body.style.overflow = '';
        }}

        function closeModalOnOverlay(event) {{
            if (event.target.id === 'modal') {{
                closeModal();
            }}
        }}

        function renderCharts(data, provider) {{
            const colors = getChartColors(provider);
            const config = {{responsive: true, displayModeBar: false}};

            const layoutBase = {{
                font: {{family: 'Inter, system-ui, sans-serif', color: colors.text, size: 12}},
                paper_bgcolor: colors.bg,
                plot_bgcolor: colors.bg,
                margin: {{l: 40, r: 20, t: 40, b: 40}}
            }};

            const errorCategories = Object.keys(data.error_counts);
            const errorValues = Object.values(data.error_counts);

            Plotly.newPlot('chart-errors', [{{
                x: errorCategories,
                y: errorValues,
                type: 'bar',
                marker: {{color: colors.accent}}
            }}], {{
                ...layoutBase,
                title: {{text: 'Error Types', font: {{size: 14}}}},
                xaxis: {{showgrid: false, tickangle: -45}},
                yaxis: {{showgrid: true, gridcolor: colors.grid}},
                height: 280
            }}, config);

            const tendencyCategories = Object.keys(data.tendency_counts);
            const tendencyValues = Object.values(data.tendency_counts);

            const hexToRgba = (hex, alpha) => {{
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                return `rgba(${{r}}, ${{g}}, ${{b}}, ${{alpha}})`;
            }};

            Plotly.newPlot('chart-radar', [{{
                type: 'scatterpolar',
                r: [...tendencyValues, tendencyValues[0]],
                theta: [...tendencyCategories, tendencyCategories[0]],
                fill: 'toself',
                fillcolor: hexToRgba(colors.accent, 0.3),
                line: {{color: colors.accent}}
            }}], {{
                ...layoutBase,
                title: {{text: 'Error Tendencies', font: {{size: 14}}}},
                polar: {{
                    radialaxis: {{visible: true, showline: false, gridcolor: colors.grid}},
                    angularaxis: {{gridcolor: colors.grid}},
                    bgcolor: colors.bg
                }},
                height: 280,
                showlegend: false
            }}, config);

            const handValues = Object.keys(data.mistakes_by_value).map(Number);
            const mistakeCounts = Object.values(data.mistakes_by_value);

            Plotly.newPlot('chart-by-value', [{{
                x: handValues,
                y: mistakeCounts,
                type: 'bar',
                marker: {{color: colors.accent}}
            }}], {{
                ...layoutBase,
                title: {{text: 'Mistakes by Hand Value', font: {{size: 14}}}},
                xaxis: {{showgrid: false, dtick: 1, title: {{text: 'Player Hand Value', font: {{size: 11}}}}}},
                yaxis: {{showgrid: true, gridcolor: colors.grid, title: {{text: 'Mistakes', font: {{size: 11}}}}}},
                height: 250
            }}, config);
        }}

        function toggleTheme() {{
            const html = document.documentElement;
            const isDark = html.getAttribute('data-theme') === 'dark';
            html.setAttribute('data-theme', isDark ? 'light' : 'dark');
            localStorage.setItem('theme', isDark ? 'light' : 'dark');

            if (document.getElementById('modal').classList.contains('active')) {{
                const modelName = document.getElementById('modal-title').textContent;
                const data = modelsData[modelName];
                if (data) renderCharts(data, data.provider);
            }}
        }}

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});

        let currentSort = {{ column: 'accuracy', ascending: false }};

        function sortTable(th) {{
            const column = th.dataset.sort;
            const type = th.dataset.type;
            const tbody = document.querySelector('.leaderboard tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            if (currentSort.column === column) {{
                currentSort.ascending = !currentSort.ascending;
            }} else {{
                currentSort.column = column;
                currentSort.ascending = true;
            }}

            const upDownIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 15l5 5 5-5M7 9l5-5 5 5"/></svg>';
            const upIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
            const downIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>';

            document.querySelectorAll('.leaderboard th.sortable').forEach(h => {{
                h.classList.remove('sorted');
                h.querySelector('.sort-icon').innerHTML = upDownIcon;
            }});
            th.classList.add('sorted');
            th.querySelector('.sort-icon').innerHTML = currentSort.ascending ? upIcon : downIcon;

            rows.sort((a, b) => {{
                let aVal = a.dataset[column];
                let bVal = b.dataset[column];

                if (type === 'number') {{
                    aVal = parseFloat(aVal);
                    bVal = parseFloat(bVal);
                }} else {{
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }}

                if (aVal < bVal) return currentSort.ascending ? -1 : 1;
                if (aVal > bVal) return currentSort.ascending ? 1 : -1;
                return 0;
            }});

            rows.forEach(row => tbody.appendChild(row));
        }}

        (function() {{
            const saved = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = saved || (prefersDark ? 'dark' : 'light');
            if (theme === 'dark') {{
                document.documentElement.setAttribute('data-theme', 'dark');
            }}
        }})();
    </script>
</body>
</html>
"""
    return html


def main():
    models = load_all_models()
    html = create_dashboard(models)

    output_path = Path("index.html")
    output_path.write_text(html)
    print(f"Dashboard saved to {output_path}")


if __name__ == "__main__":
    main()
