"""The optimisation on RunPod (PLT-12), on a fake job API and a fake volume.

The layout record goes up, the job is asked the recipe's optimisation, the run's files come back,
every other stage is local."""

import json

import pytest
from fixtures import write
from test_flow import FakeEngines

from zenryx.workflow import remote

FULL = {
    "ZENRYX_OPTIMISE_ON": "runpod",
    "RUNPOD_API_KEY": "k",
    "RUNPOD_ENDPOINT_ID": "e",
    "RUNPOD_VOLUME_ID": "v",
    "RUNPOD_DATACENTER": "EU-RO-1",
    "RUNPOD_S3_KEY": "a",
    "RUNPOD_S3_SECRET": "b",
    "ZENRYX_REF": "abc123",
}


class FakeVolume:
    def __init__(self, s):
        self.store: dict[str, bytes] = {}

    def upload(self, local, key):
        self.store[key] = local.read_bytes()

    def download(self, key, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(self.store[key])


class FakeJobs:
    """A worker that runs the optimisation by writing the run's files onto the volume."""

    def __init__(self, volume, status="COMPLETED"):
        self.volume, self.status_, self.inputs = volume, status, []

    def start(self, job_input):
        self.inputs.append(job_input)
        assert "fastcae-sim/data/first_loop/contract.json" in self.volume.store
        base = "fastcae-sim/data/first_loop"
        run = f"run_{job_input['design']}"
        self.volume.store[f"{base}/{run}.json"] = json.dumps(
            {"empty": True, "binary": {"worst": 0.9}}
        ).encode()
        self.volume.store[f"{base}/{run}.npz"] = b"field"
        self.volume.store[f"{base}/optimise_{job_input['design']}.log"] = b"[00:01] done in 1 s\n"
        return "job1"

    def wait(self, job, progress, every=15.0, stop=lambda: False):
        d = self.inputs[-1]["design"]
        out = {
            "exit": 0,
            "run": f"run_{d}",
            "settled": "settled at 9",
            "files": [f"run_{d}.json", f"run_{d}.npz", f"optimise_{d}.log"],
            "minutes": 3.0,
            "gpu": {"name": "RTX A4000", "peak_mb": 5000},
        }
        progress({"status": "IN_PROGRESS", "output": {"minutes": 1}})
        return {
            "status": self.status_,
            "output": out if self.status_ == "COMPLETED" else {"error": "boom"},
        }


def make(tmp_path, monkeypatch, status="COMPLETED"):
    monkeypatch.setattr(remote, "Volume", FakeVolume)
    s = remote.Settings.load(FULL)
    local = FakeEngines(tmp_path)
    eng = remote.RemoteOptimise(local, s, tmp_path)
    eng.jobs = FakeJobs(eng.volume, status)
    write(tmp_path, "contract.json", {"stem": "contract"})
    return eng, local


def test_the_optimisation_goes_to_runpod_and_its_files_come_back(tmp_path, monkeypatch) -> None:
    eng, local = make(tmp_path, monkeypatch)
    log = tmp_path / "optimise_d1.log"
    code, run, settled = eng.optimise(
        "d1", 7.73, 4, ["--least-width", "8"], {"LOOP_X": "1", "PATH": "/x"}, log
    )
    assert (code, run, settled) == (0, "run_d1", "settled at 9")
    sent = eng.jobs.inputs[0]
    assert (
        sent["mode"] == "optimise"
        and sent["ref"] == "abc123"
        and sent["args"] == ["--least-width", "8"]
    )
    assert sent["env"] == {"LOOP_X": "1"}  # only the loop's settings cross
    assert (tmp_path / "run_d1.npz").read_bytes() == b"field"
    assert "done in 1 s" in log.read_text() and "RTX A4000" in log.read_text()
    assert "optimise" not in local.calls  # the local optimiser never ran
    assert eng.draw("run_d1", "d1", {}, tmp_path / "b.log") == 0 and local.calls == ["draw"]


def test_a_failed_job_is_a_failed_optimisation(tmp_path, monkeypatch) -> None:
    eng, _ = make(tmp_path, monkeypatch, status="FAILED")
    log = tmp_path / "optimise_d1.log"
    assert eng.optimise("d1", 7.73, 4, [], {}, log) == (1, "", "")
    assert "FAILED" in log.read_text()


def test_the_setting_and_what_it_needs(tmp_path) -> None:
    local = FakeEngines(tmp_path)
    assert (
        remote.engines_for(local, tmp_path, remote.Settings.load({"ZENRYX_OPTIMISE_ON": "local"}))
        is local
    )
    assert (
        remote.engines_for(local, tmp_path, remote.Settings.load({"HOME": "/x"})) is local
    )  # local by default
    with pytest.raises(RuntimeError, match="RUNPOD_API_KEY"):
        remote.engines_for(local, tmp_path, remote.Settings.load({"ZENRYX_OPTIMISE_ON": "runpod"}))
    with pytest.raises(ValueError):
        remote.engines_for(local, tmp_path, remote.Settings.load({"ZENRYX_OPTIMISE_ON": "moon"}))
