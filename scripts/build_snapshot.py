#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import yaml


def load_current_state():
    """Load current state from Python engine."""
    prices_path = Path("data/prices.csv")
    if not prices_path.exists():
        raise FileNotFoundError("data/prices.csv not found. Run fetch_prices.py first.")

    # Load signals config to get expected version
    config_path = Path("signals.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Import and run the Python engine
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from python_mse.compute import compute_signals, load_signals_config, read_wide_csv

    config = load_signals_config()
    prices = read_wide_csv(prices_path)
    records = compute_signals(prices, config=config)

    return records[-1]  # Return the most recent record


def load_previous_state():
    """Attempt to load previous state using MCP or fallback methods."""

    # Try MCP approach first
    try:
        return load_previous_state_via_mcp()
    except Exception as e:
        print(f"MCP approach failed: {e}")
        print("Falling back to artifact-based approach")
        return load_previous_state_via_artifacts()


def load_previous_state_via_mcp():
    """Load previous state using available MCP tools."""
    # This is a placeholder for MCP integration
    # In a real implementation, this would use MCP to read the previous state.json
    # For now, we'll implement a simple file-based fallback

    # Check if there's a previous outputs/state.json
    prev_path = Path("outputs/state.json")
    if prev_path.exists():
        with open(prev_path, "r") as f:
            return json.load(f)

    return None


def load_previous_state_via_artifacts():
    """Load previous state from GitHub Actions artifacts (fallback)."""
    # This would use GitHub Actions API to fetch previous artifacts
    # For now, check local outputs directory
    prev_path = Path("outputs/state.json")
    if prev_path.exists():
        with open(prev_path, "r") as f:
            return json.load(f)

    return None


def compute_signal_diff(prev_signals, curr_signals):
    """Compute signal-only changes between states."""
    if prev_signals is None:
        return "Previous snapshot unavailable."

    changes = []
    for signal_name, current_value in curr_signals.items():
        prev_value = prev_signals.get(signal_name)
        if prev_value is None:
            changes.append(f"{signal_name}: NEW ({current_value})")
        elif prev_value != current_value:
            changes.append(f"{signal_name}: {prev_value} → {current_value}")

    if not changes:
        return "No signal changes."

    return "; ".join(changes)


def write_state_and_changelog(current_state, prev_state):
    """Write state.json and CHANGELOG.md."""
    # Ensure outputs directory exists
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Write current state
    state_path = outputs_dir / "state.json"
    with open(state_path, "w") as f:
        json.dump(current_state, f, indent=2)

    # Write changelog
    changelog_path = outputs_dir / "CHANGELOG.md"
    prev_signals = prev_state.get("signals", {}) if prev_state else {}
    curr_signals = current_state.get("signals", {})

    changelog_lines = [
        f"# Market State Engine Daily Changelog",
        f"**Date:** {current_state.get('date', 'Unknown')}",
        f"**Version:** {current_state.get('version', 'Unknown')}",
        "",
        "## Signal Changes",
        compute_signal_diff(prev_signals, curr_signals),
        "",
        "---",
        f"*Generated at {datetime.now().isoformat()}*",
    ]

    with open(changelog_path, "w") as f:
        f.write("\n".join(changelog_lines))

    print(f"State written to {state_path}")
    print(f"Changelog written to {changelog_path}")


def main():
    """Build snapshot and changelog."""
    print("Building daily snapshot and changelog...")

    try:
        current_state = load_current_state()
        print(f"Current state loaded for {current_state.get('date')}")

        prev_state = load_previous_state()
        if prev_state:
            print(f"Previous state loaded for {prev_state.get('date')}")
        else:
            print("No previous state found")

        write_state_and_changelog(current_state, prev_state)
        print("Snapshot and changelog generation complete.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
