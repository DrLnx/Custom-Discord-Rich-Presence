"""Drives the real app through a headless terminal."""

from __future__ import annotations

import json

import pytest

CFG = {
    "active": "vscode",
    "profiles": {
        "vscode": {
            "client_id": "1234", "name": "Visual Studio Code",
            "activity_type": "playing", "status_display_type": "name",
            "details": "Developing", "state": "", "large_image": "",
            "large_text": "", "large_url": "", "small_image": "",
            "small_text": "", "small_url": "", "timer": True,
            "buttons": [{"label": "Site", "url": "https://example.com"}],
        },
        "music": {
            "client_id": "5678", "name": "Spotify", "activity_type": "listening",
            "status_display_type": "state", "details": "Bonobo", "state": "Kerala",
            "large_image": "", "large_text": "", "large_url": "", "small_image": "",
            "small_text": "", "small_url": "", "timer": False, "buttons": [],
        },
    },
}


@pytest.fixture
def app(sandbox):
    from drpc.tui.app import DrpcApp

    return DrpcApp(cfg=json.loads(json.dumps(CFG)))


async def test_it_mounts_and_shows_the_active_profile(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.profile_name == "vscode"
        assert app.row("name").value == "Visual Studio Code"
        assert app.row("b0_label").value == "Site"
        assert app.row("timer").value is True


async def test_empty_fields_show_their_placeholder(app):
    from textual.widgets import Static

    async with app.run_test() as pilot:
        await pilot.pause()
        rendered = app.row("small_text").query_one(".row-value", Static).render()
        assert "hover text" in rendered.plain


async def test_i_enters_a_field_and_escape_discards_the_edit(app):
    from textual.widgets import Input

    async with app.run_test() as pilot:
        await pilot.pause()
        row = app.row("details")
        row.focus()
        await pilot.press("i")
        assert row.editing
        assert isinstance(app.focused, Input)

        await pilot.press("!")
        await pilot.press("escape")
        assert not row.editing
        assert row.value == "Developing"  # discarded


async def test_enter_commits_the_edit_and_marks_the_form_dirty(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        row = app.row("details")
        row.focus()
        await pilot.press("i")
        for key in ("!", "!"):
            await pilot.press(key)
        await pilot.press("enter")
        assert row.value == "Developing!!"
        assert app.dirty


async def test_letters_stay_commands_while_a_row_is_focused(app):
    """The whole point of the modal design: `p` must not type a 'p'."""
    async with app.run_test() as pilot:
        await pilot.pause()
        app.row("details").focus()
        await pilot.press("p")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "Picker"
        assert app.row("details").value == "Developing"


async def test_the_picker_filters_and_switches_profile(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("p")
        await pilot.pause()
        for key in "mus":
            await pilot.press(key)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.profile_name == "music"
        assert app.row("name").value == "Spotify"
        assert app.row("timer").value is False


async def test_h_and_l_cycle_a_choice_row(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        row = app.row("activity_type")
        row.focus()
        await pilot.press("l")
        assert row.value == "listening"
        await pilot.press("h")
        assert row.value == "playing"


async def test_saving_writes_the_edited_profile_to_disk(app, sandbox):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.row("details").value = "Shipping"
        await pilot.press("s")
        await pilot.pause()
        assert not app.dirty
        saved = json.loads(sandbox.CONFIG.read_text())
        assert saved["profiles"]["vscode"]["details"] == "Shipping"
        assert saved["active"] == "vscode"


async def test_switching_profiles_keeps_edits_made_before_the_switch(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.row("details").value = "Kept"
        app._switch_profile("music")
        await pilot.pause()
        app._switch_profile("vscode")
        await pilot.pause()
        assert app.row("details").value == "Kept"


async def test_quitting_with_unsaved_edits_asks_first(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.row("details").value = "unsaved"
        await pilot.press("q")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "Confirm"
        await pilot.press("n")
        await pilot.pause()
        assert app.is_running


async def test_the_key_sheet_opens_and_closes(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "KeySheet"
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ != "KeySheet"


async def test_the_theme_toggle_flips_and_is_remembered_in_the_config(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        first = app.theme
        await pilot.press("T")
        assert app.theme != first
        assert app.cfg["theme"] == app.theme
