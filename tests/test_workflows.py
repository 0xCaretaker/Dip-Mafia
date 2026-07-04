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


def test_dip_mafia_triggers():
    on = _on(_load("dip-mafia.yml"))
    assert "schedule" in on and "workflow_dispatch" in on, "cron + manual kept"
    assert "workflow_call" not in on, "workflow_call dropped (no caller after run-bot removed)"


def test_dip_mafia_has_reuse_input():
    on = _on(_load("dip-mafia.yml"))
    inputs = (on.get("workflow_dispatch") or {}).get("inputs") or {}
    assert "reuse_if_unchanged" in inputs, "dip-mafia.yml must expose reuse_if_unchanged input"
    assert inputs["reuse_if_unchanged"].get("default") in (False, "false"), "default false"


def test_dip_mafia_reuse_cache_retired():
    # The scan reuse-cache was retired (2026-07-04): every run recomputes and
    # posts fresh. The actions/cache step and the REUSE_IF_UNCHANGED env are gone;
    # only the workflow_dispatch input shim remains (see test_dip_mafia_has_reuse_input).
    text = _text("dip-mafia.yml")
    for token in ("actions/cache", "REUSE_IF_UNCHANGED", "lastpost"):
        assert token not in text, f"dip-mafia.yml still references retired reuse-cache: {token!r}"


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


def test_regen_emits_changed_output():
    doc = _load("regen-stocks.yml")
    regen = doc["jobs"]["regen"]
    assert regen.get("outputs", {}).get("changed") == "${{ steps.commit.outputs.changed }}"
    text = _text("regen-stocks.yml")
    assert 'echo "changed=true" >> "$GITHUB_OUTPUT"' in text
    assert 'echo "changed=false" >> "$GITHUB_OUTPUT"' in text


def test_regen_no_longer_runs_bot():
    jobs = _load("regen-stocks.yml")["jobs"]
    assert "run-bot" not in jobs, "regen-stocks.yml must not fire the bot (web-scan dispatch is the sole post-after-scan trigger)"
    text = _text("regen-stocks.yml")
    assert "dip-mafia.yml" not in text, "regen-stocks.yml must not reference dip-mafia.yml"


if __name__ == "__main__":
    test_dip_mafia_triggers()
    test_dip_mafia_has_reuse_input()
    test_dip_mafia_reuse_cache_retired()
    test_dip_mafia_force_input_removed()
    test_dip_mafia_dedup_plumbing_gone()
    test_regen_emits_changed_output()
    test_regen_no_longer_runs_bot()
    print("✓ all workflow tests passed")
