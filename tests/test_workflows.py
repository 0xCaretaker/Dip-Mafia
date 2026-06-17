"""Structural guards for the GitHub Actions wiring.

PyYAML parses a bare `on:` key as the boolean True (YAML 1.1), so read the
trigger map via _on(). Dependency: PyYAML (already installed). Run with:
    python3 tests/test_workflows.py
"""
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")


def _load(name):
    with open(os.path.join(WF, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _text(name):
    with open(os.path.join(WF, name), encoding="utf-8") as f:
        return f.read()


def _on(doc):
    # `on:` parses to the Python bool True under YAML 1.1
    return doc.get("on", doc.get(True))


def test_dip_mafia_is_callable():
    on = _on(_load("dip-mafia.yml"))
    assert "workflow_call" in on, "dip-mafia.yml must declare on: workflow_call"
    assert "schedule" in on and "workflow_dispatch" in on, "cron + manual kept"


def test_dip_mafia_force_input_removed():
    # The six7 "Run Dip Mafia" button dispatches with no inputs (github_dispatch
    # sends only {"ref": ...}), so the force input is dead once dedup is gone.
    on = _on(_load("dip-mafia.yml"))
    inputs = (on.get("workflow_dispatch") or {}).get("inputs") or {}
    assert "force" not in inputs, "force input should be removed (button sends no inputs)"


def test_dip_mafia_dedup_plumbing_gone():
    text = _text("dip-mafia.yml")
    for token in (".last_signal_hash", "DIP_MAFIA_FORCE",
                  "Restore signal cache", "Save signal cache"):
        assert token not in text, f"dip-mafia.yml still references: {token!r}"


if __name__ == "__main__":
    test_dip_mafia_is_callable()
    test_dip_mafia_force_input_removed()
    test_dip_mafia_dedup_plumbing_gone()
    print("✓ all workflow tests passed")
