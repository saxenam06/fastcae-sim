"""The API the Run button calls (PLT-5), on fake engines.

A run starts, reports its stages, ends with the workflow's state; one run at a time; a cancel
stops it; a stop during the optimisation finishes it, drawn and judged."""

import threading
import time

import pytest
from test_flow import FakeEngines

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from zenryx.api.server import create_app  # noqa: E402


def wait_until(client, run_id, done=("done", "failed", "cancelled"), most=20.0):
    t = time.time()
    while time.time() - t < most:
        s = client.get(f"/api/runs/{run_id}").json()
        if s["status"] in done:
            return s
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not end: {s}")


def test_a_run_from_the_button_to_its_outcome(tmp_path) -> None:
    out = tmp_path / "first_loop"
    out.mkdir()
    client = TestClient(create_app(lambda o: FakeEngines(o), out=out))
    before = client.get("/api/workflow").json()
    assert before["last"] is None and before["changed"]["contract"] and before["running"] is None
    started = client.post("/api/runs", json={"design": "d1"})
    assert started.status_code == 202
    assert {"stages_all", "stages", "log"} <= set(
        started.json()
    )  # what the Run panel reads at once
    s = wait_until(client, started.json()["id"])
    assert s["status"] == "done", s
    assert s["result"]["verdict"] == "passes every line" and s["result"]["design"] == "d1"
    assert [x["stage"] for x in s["stages"]][:4] == ["layout", "optimise", "draw", "oiltight"]
    after = client.get("/api/workflow").json()
    assert after["last"]["design"] == "d1" and not after["changed"]["contract"]
    assert client.get("/api/runs").json()[0]["id"] == s["id"]


class SlowEngines(FakeEngines):
    """The optimisation waits until released or cancelled."""

    def __init__(self, out):
        super().__init__(out)
        self.release = threading.Event()

    def optimise(self, *args):
        self.release.wait(10)
        return super().optimise(*args)

    def cancel(self):
        self.release.set()


def test_one_run_at_a_time_and_a_cancel(tmp_path) -> None:
    out = tmp_path / "first_loop"
    out.mkdir()
    made = []
    client = TestClient(create_app(lambda o: made.append(SlowEngines(o)) or made[-1], out=out))
    first = client.post("/api/runs", json={}).json()
    assert client.post("/api/runs", json={}).status_code == 409
    assert client.post(f"/api/runs/{first['id']}/cancel").json()["cancel"]
    s = wait_until(client, first["id"])
    assert s["status"] == "cancelled"
    assert "judge" not in [x["stage"] for x in s["stages"]]
    assert client.post("/api/runs/nope/cancel").status_code == 409


class FinishingEngines(SlowEngines):
    """A stop during the optimisation finishes it (`LocalEngines.cancel` says "finish")."""

    def cancel(self):
        self.release.set()
        return "finish"


def test_a_stop_during_the_optimisation_is_judged(tmp_path) -> None:
    out = tmp_path / "first_loop"
    out.mkdir()
    client = TestClient(create_app(lambda o: FinishingEngines(o), out=out))
    first = client.post("/api/runs", json={}).json()
    said = client.post(f"/api/runs/{first['id']}/cancel").json()
    assert said["finish"] and not said["cancel"]
    s = wait_until(client, first["id"])
    assert s["status"] == "done" and s["stopping"], s
    assert "judge" in [x["stage"] for x in s["stages"]]
