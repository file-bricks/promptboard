"""Hermetic regression tests for Bugsweep Iteration on PromptBoard (2026-11-16).

Area: Lokale Bibliotheks-Persistenz, Markdown/TXT-Materialisierung,
Pfad-/Gerätenamen-Sanitization, Single-Instance-IPC & Inline-Variablen-/Such-Resilienz
(src/storage.py, src/materializer.py, src/models.py, src/library_query.py,
src/single_instance.py, src/inline_variables.py, src/profiprompt_adapter.py,
src/explorerpro_adapter.py, src/promptboard.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
import getpass
import json
import os
import stat
from types import SimpleNamespace
import uuid

import pytest
from PySide6 import QtNetwork, QtWidgets

from explorerpro_adapter import load_explorerpro_items
from inline_variables import extract_inline_variables, resolve_inline_variables
from library_query import _parse_iso_datetime, item_matches_search
from materializer import build_markdown, materialize_item, materialize_items
from models import ItemType, LibraryItem, sanitize_filename
import promptboard as pb_module
from profiprompt_adapter import load_profiprompt_items
import single_instance as si_module
from single_instance import SingleInstance
from storage import Storage, atomic_write_json


def test_storage_load_items_tolerates_utf8_bom_null_items_and_null_entries(tmp_path):
    store = Storage(tmp_path)
    bom_payload = {
        "items": [
            None,
            {
                "id": "bom-1",
                "item_type": "PROMPT",
                "name": "Mit BOM",
                "content": "Inhalt mit Umlauten äöüß",
            },
        ]
    }
    store.library_file.write_text(
        json.dumps(bom_payload, ensure_ascii=False),
        encoding="utf-8-sig",
    )

    loaded = store.load_items()
    assert len(loaded) == 1
    assert loaded[0].id == "bom-1"
    assert loaded[0].name == "MIT BOM"

    # Explicit null items list must return empty list instead of TypeError
    store.library_file.write_text('{"items": null}', encoding="utf-8")
    assert store.load_items() == []


def test_storage_load_items_rejects_invalid_root_or_items_type_without_data_loss(tmp_path):
    store = Storage(tmp_path)
    raw_invalid = '"unexpected-scalar-json"'
    store.library_file.write_text(raw_invalid, encoding="utf-8")

    with pytest.raises(ValueError):
        store.load_items()

    # upsert_item must NOT overwrite unrecognized library.json structure
    with pytest.raises(ValueError):
        store.upsert_item(
            LibraryItem(id="x1", item_type=ItemType.PROMPT, name="Neu", content="Text")
        )
    assert store.library_file.read_text(encoding="utf-8") == raw_invalid

    raw_bad_items = '{"items": "not-a-list"}'
    store.library_file.write_text(raw_bad_items, encoding="utf-8")
    with pytest.raises(ValueError):
        store.load_items()
    assert store.library_file.read_text(encoding="utf-8") == raw_bad_items


def test_seed_initial_item_skips_corrupt_library_without_crashing_or_overwriting(tmp_path):
    store = Storage(tmp_path)
    corrupt_raw = "{broken json --- do not overwrite"
    store.library_file.write_text(corrupt_raw, encoding="utf-8")

    created_calls: list[int] = []
    fake_window = SimpleNamespace(create_item=lambda: created_calls.append(1))

    seed_fn = getattr(pb_module, "_seed_initial_item_if_empty", None)
    assert callable(seed_fn), "_seed_initial_item_if_empty helper missing in promptboard.py"

    result = seed_fn(store, fake_window)
    assert result is False
    assert created_calls == []
    assert store.library_file.read_text(encoding="utf-8") == corrupt_raw


def test_atomic_write_json_rejects_directory_target_without_temp_leak_and_overwrites_readonly(
    tmp_path,
):
    work_dir = tmp_path / "atomic_case"
    work_dir.mkdir()
    dir_target = work_dir / "already_a_dir.json"
    dir_target.mkdir()

    with pytest.raises(IsADirectoryError):
        atomic_write_json(dir_target, {"hello": "world"})

    leftovers = [p for p in work_dir.iterdir() if p != dir_target]
    assert leftovers == [], f"Temp files leaked after IsADirectoryError: {leftovers}"

    ro_file = work_dir / "readonly.json"
    ro_file.write_text('{"old": 1}', encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)
    try:
        atomic_write_json(ro_file, {"new": 2})
        assert json.loads(ro_file.read_text(encoding="utf-8")) == {"new": 2}
        assert [p for p in work_dir.iterdir() if p.name.endswith(".tmp")] == []
    finally:
        os.chmod(ro_file, stat.S_IWRITE | stat.S_IREAD)


def test_sanitize_filename_neutralizes_windows_reserved_devices_and_caps_overlong_names(tmp_path):
    for reserved in ("CON", "nul", "PRN", "AUX.v1", "COM1", "LPT9", "CLOCK$", "COM\u00b9"):
        safe = sanitize_filename(reserved)
        stem_head = safe.split(".", 1)[0].upper().translate(
            str.maketrans({"\u00b9": "1", "\u00b2": "2", "\u00b3": "3"})
        )
        assert stem_head not in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "CLOCK$",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }, f"Reserved device name escaped sanitization: {reserved!r} -> {safe!r}"

    overlong_name = "SEHR LANGER PROMPT NAME " * 20  # 480 chars
    safe_long = sanitize_filename(overlong_name)
    assert 1 <= len(safe_long) <= 120
    assert not safe_long.endswith((" ", "."))

    # End-to-end materialization on Windows for NUL and overlong name
    nul_item = LibraryItem(id="n1", item_type=ItemType.PROMPT, name="NUL", content="Safe")
    long_item = LibraryItem(
        id="l1", item_type=ItemType.PROMPT, name=overlong_name, content="Long Safe"
    )
    nul_path = materialize_item(nul_item, tmp_path)
    long_path = materialize_item(long_item, tmp_path)
    assert nul_path.is_file()
    assert long_path.is_file()
    assert "Safe" in nul_path.read_text(encoding="utf-8")
    assert "Long Safe" in long_path.read_text(encoding="utf-8")


def test_materializer_escapes_html_comment_breakout_in_origin_marker():
    injected = LibraryItem(
        id='id" -->\n# INJECTED',
        item_type=ItemType.PROMPT,
        name="Marker Test",
        content="Echter Inhalt",
        updated_at="2026-05-01T10:00:00Z --> EVIL",
    )
    md = build_markdown(injected)
    first_line = md.splitlines()[0]
    assert first_line.startswith("<!-- promptboard:item ")
    assert first_line.endswith(" -->")
    # Must contain only the closing '-->' at the very end, no premature comment close
    assert first_line[:-4].count("-->") == 0
    assert "# INJECTED" not in md.splitlines()[1]


def test_materialize_items_disambiguates_colliding_stems_within_batch_and_guards_dirs(
    tmp_path, monkeypatch
):
    first = LibraryItem(
        id="c1", item_type=ItemType.PROMPT, name="Code Review", content="Inhalt Eins"
    )
    second = LibraryItem(
        id="c2", item_type=ItemType.SKILL, name="Code Review", content="Inhalt Zwei"
    )
    third = LibraryItem(
        id="c3", item_type=ItemType.AGENT, name="Code Review", content="Inhalt Drei"
    )

    targets = materialize_items([first, second, third], tmp_path)
    assert len(targets) == 3
    assert len(set(targets)) == 3
    assert targets[0] == tmp_path / "CODE REVIEW.md"
    assert "Inhalt Eins" in targets[0].read_text(encoding="utf-8")
    assert "Inhalt Zwei" in targets[1].read_text(encoding="utf-8")
    assert "Inhalt Drei" in targets[2].read_text(encoding="utf-8")

    # Single-item re-materialization still overwrites by default (CLAUDE.md Hard Rule)
    first_updated = LibraryItem(
        id="c1", item_type=ItemType.PROMPT, name="Code Review", content="Inhalt Eins Aktualisiert"
    )
    single_target = materialize_item(first_updated, tmp_path)
    assert single_target == tmp_path / "CODE REVIEW.md"
    assert "Inhalt Eins Aktualisiert" in single_target.read_text(encoding="utf-8")

    # Directory collision at target file path raises IsADirectoryError cleanly
    blocking_dir = tmp_path / "BLOCKIERTER PFAD.md"
    blocking_dir.mkdir()
    blocked_item = LibraryItem(
        id="b1", item_type=ItemType.PROMPT, name="Blockierter Pfad", content="X"
    )
    with pytest.raises(IsADirectoryError):
        materialize_item(blocked_item, tmp_path)

    # MainWindow._materialize_items with confirm_overwrite=True and StandardButton.No
    # must protect existing CODE REVIEW.md and NOT let the second item shift into it.
    ui_dir = tmp_path / "ui_batch"
    ui_dir.mkdir()
    protected_file = ui_dir / "CODE REVIEW.md"
    protected_file.write_text("PROTECTED ORIGINAL", encoding="utf-8")
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.No,
    )
    fake_self = SimpleNamespace(
        settings=SimpleNamespace(
            get_materialize_path=lambda: ui_dir,
            get_materialize_format=lambda: "markdown",
            get_confirm_overwrite=lambda: True,
        ),
        status_label=SimpleNamespace(setText=lambda _msg: None),
        _show_error=lambda *args: (_ for _ in ()).throw(AssertionError(args)),
    )
    pb_module.MainWindow._materialize_items(fake_self, [first, second])
    assert protected_file.read_text(encoding="utf-8") == "PROTECTED ORIGINAL"
    assert (ui_dir / "CODE REVIEW (2).md").is_file()
    assert "Inhalt Zwei" in (ui_dir / "CODE REVIEW (2).md").read_text(encoding="utf-8")


def test_parse_iso_datetime_handles_z_suffix_whitespace_non_strings_and_timezone_chronology(
    tmp_path,
):
    epoch_min = datetime.min.replace(tzinfo=timezone.utc)
    assert _parse_iso_datetime(None) == epoch_min  # type: ignore[arg-type]
    assert _parse_iso_datetime(12345) == epoch_min  # type: ignore[arg-type]
    assert _parse_iso_datetime("   ") == epoch_min

    parsed_z = _parse_iso_datetime("  2026-05-01T10:00:00Z  ")
    assert parsed_z == datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Chronological comparison across timezones:
    # 2026-05-01T23:30:00+00:00 (23:30 UTC) is NEWER than 2026-05-02T00:15:00+02:00 (22:15 UTC)!
    profi_dir = tmp_path / "profi"
    profi_dir.mkdir()
    (profi_dir / "prompts.json").write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": "older_local_midnight",
                        "title": "Older",
                        "text": "A",
                        "created_at": "2026-05-01T20:00:00+00:00",
                        "updated_at": "2026-05-02T00:15:00+02:00",  # 22:15 UTC
                    },
                    {
                        "id": "newer_utc",
                        "title": "Newer",
                        "text": "B",
                        "created_at": "2026-05-01T20:00:00+00:00",
                        "updated_at": "2026-05-01T23:30:00+00:00",  # 23:30 UTC
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    profi_items = load_profiprompt_items(profi_dir)
    assert [it.id for it in profi_items] == [
        "profiprompt:prompt:newer_utc",
        "profiprompt:prompt:older_local_midnight",
    ]

    exp_dir = tmp_path / "exp"
    exp_dir.mkdir()
    (exp_dir / "prompts.json").write_text(
        json.dumps(
            [
                {
                    "id": "older_exp",
                    "title": "Older",
                    "content": "A",
                    "created": "2026-05-01T20:00:00+00:00",
                    "modified": "2026-05-02T00:15:00+02:00",
                },
                {
                    "id": "newer_exp",
                    "title": "Newer",
                    "content": "B",
                    "created": "2026-05-01T20:00:00+00:00",
                    "modified": "2026-05-01T23:30:00+00:00",
                },
            ]
        ),
        encoding="utf-8",
    )
    exp_items = load_explorerpro_items(exp_dir)
    assert [it.id for it in exp_items] == [
        "explorerpro:prompt:newer_exp",
        "explorerpro:prompt:older_exp",
    ]


def test_single_instance_sanitizes_domain_username_and_drains_burst_connections(
    qapp, monkeypatch
):
    monkeypatch.setattr(getpass, "getuser", lambda: r"CORP\Jane Doe / Admin@" + ("x" * 80))
    server_name = si_module._default_server_name()
    assert "\\" not in server_name
    assert "/" not in server_name
    assert " " not in server_name
    assert len(server_name) <= 80

    # Burst drain: queue two pending client connections before _handle_new_connection runs
    unique_name = f"PromptBoard-burst-{uuid.uuid4().hex[:12]}"
    activations: list[int] = []
    primary = SingleInstance(unique_name)
    assert primary.start_server(lambda: activations.append(1)) is True
    try:
        # Block automatic signal dispatch briefly by disconnecting newConnection, connect 2 clients,
        # then invoke _handle_new_connection() once to verify full pending-queue drain.
        primary._server.newConnection.disconnect(primary._handle_new_connection)
        s1 = QtNetwork.QLocalSocket()
        s2 = QtNetwork.QLocalSocket()
        s1.connectToServer(unique_name)
        s2.connectToServer(unique_name)
        assert s1.waitForConnected(500)
        assert s2.waitForConnected(500)
        s1.write(b"activate")
        s2.write(b"activate")
        s1.waitForBytesWritten(300)
        s2.waitForBytesWritten(300)
        primary._server.waitForNewConnection(100)
        primary._server.waitForNewConnection(100)

        primary._handle_new_connection()
        assert primary._server.hasPendingConnections() is False
        assert len(activations) >= 1
        s1.disconnectFromServer()
        s2.disconnectFromServer()
        s1.deleteLater()
        s2.deleteLater()
        qapp.processEvents()
    finally:
        primary.stop()
        qapp.processEvents()


def test_inline_variables_and_search_handle_non_string_inputs_gracefully():
    assert extract_inline_variables(None) == []  # type: ignore[arg-type]
    assert extract_inline_variables(12345) == []  # type: ignore[arg-type]
    assert resolve_inline_variables(None, lambda _n: ("x", True)) == ""  # type: ignore[arg-type]
    assert resolve_inline_variables(12345, lambda _n: ("x", True)) == ""  # type: ignore[arg-type]

    sample = LibraryItem(
        id="s1", item_type=ItemType.PROMPT, name="Beispiel", content="Hallo Welt"
    )
    assert item_matches_search(sample, None) is True  # type: ignore[arg-type]
    assert item_matches_search(sample, 12345) is True  # type: ignore[arg-type]
