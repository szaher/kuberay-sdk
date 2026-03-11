"""Unit tests for state color scheme (T007)."""

from __future__ import annotations

import pytest

from kuberay_sdk.display._colors import STATE_COLORS, get_state_color


class TestStateColorScheme:
    """Tests for StateColorScheme and get_state_color()."""

    @pytest.mark.parametrize(
        "state",
        ["RUNNING", "READY", "SUCCEEDED", "COMPLETE"],
    )
    def test_success_states_are_green(self, state: str) -> None:
        assert get_state_color(state) == "green"

    @pytest.mark.parametrize(
        "state",
        ["CREATING", "PENDING", "SCALING", "INITIALIZING", "SUBMITTING"],
    )
    def test_transitional_states_are_yellow(self, state: str) -> None:
        assert get_state_color(state) == "yellow"

    @pytest.mark.parametrize(
        "state",
        ["FAILED", "ERROR", "CRASHED", "TIMEOUT", "UNKNOWN"],
    )
    def test_failure_states_are_red(self, state: str) -> None:
        assert get_state_color(state) == "red"

    def test_unknown_state_defaults_to_yellow(self) -> None:
        assert get_state_color("SOME_NEW_STATE") == "yellow"

    def test_case_insensitive_lookup(self) -> None:
        assert get_state_color("running") == "green"
        assert get_state_color("Failed") == "red"

    def test_returns_valid_color_string(self) -> None:
        valid_colors = {"green", "yellow", "red"}
        for color in STATE_COLORS.values():
            assert color in valid_colors

    def test_state_colors_is_immutable(self) -> None:
        with pytest.raises(TypeError):
            STATE_COLORS["NEW"] = "blue"  # type: ignore[index]
