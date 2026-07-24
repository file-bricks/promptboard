"""Regression tests for the single-instance guard (U8).

A second start must be detected (so it can exit instead of spawning a second
window/tray) and must wake the primary instance via the activation callback.
"""
from __future__ import annotations

import uuid

from single_instance import SingleInstance


def _unique_name() -> str:
    return f"PromptBoard-test-{uuid.uuid4().hex}"


def test_reports_not_running_when_socket_is_free(qapp):
    guard = SingleInstance(_unique_name())
    assert guard.is_another_running() is False


def test_second_instance_is_detected_and_activates_primary(qapp):
    name = _unique_name()
    activations: list[int] = []

    primary = SingleInstance(name)
    assert primary.start_server(lambda: activations.append(1)) is True
    try:
        secondary = SingleInstance(name)
        assert secondary.is_another_running() is True

        # newConnection is delivered via the event loop.
        for _ in range(20):
            qapp.processEvents()
            if activations:
                break
        assert activations == [1]
    finally:
        primary.stop()


def test_primary_can_restart_after_stop(qapp):
    name = _unique_name()
    primary = SingleInstance(name)
    assert primary.start_server(lambda: None) is True
    primary.stop()

    # After stop the name is free again for a fresh primary.
    second = SingleInstance(name)
    assert second.start_server(lambda: None) is True
    second.stop()
