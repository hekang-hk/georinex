import importlib.resources as ir

import pytest
import xarray
from pytest import approx
from datetime import datetime
import georinex as gr


def test_fast_slow():
    fn = ir.files(f"{__package__}.data") / "minimal2.10o"
    fobs = gr.load(fn, fast=True)
    sobs = gr.load(fn, fast=False)

    assert fobs.equals(sobs)

    assert fobs.fast_processing
    assert not sobs.fast_processing


def test_meas_continuation():
    """
    tests OBS2 files with more than 10 types of observations
    """
    fn = ir.files(f"{__package__}.data") / "ab430140.18o.zip"
    obs = gr.load(fn, verbose=True)

    assert len(obs.data_vars) == 20
    for v in [
        "L1",
        "L2",
        "C1",
        "P2",
        "P1",
        "S1",
        "S2",
        "C2",
        "L5",
        "C5",
        "S5",
        "L6",
        "C6",
        "S6",
        "L7",
        "C7",
        "S7",
        "L8",
        "C8",
        "S8",
    ]:
        assert v in obs

    times = gr.to_datetime(obs.time)
    assert times.size == 9

    assert obs.fast_processing


def test_meas_one():
    """
    test specifying specific measurements (usually only a few of the thirty or so are needed)
    """
    fn = ir.files(f"{__package__}.data") / "demo.10o"
    obs = gr.load(fn)
    for v in ["L1", "L2", "P1", "P2", "C1", "S1", "S2"]:
        assert v in obs
    assert len(obs.data_vars) == 7

    sv = obs.sv.values
    assert len(sv) == 14
    for s in [
        "G13",
        "R19",
        "G32",
        "G07",
        "R23",
        "G31",
        "G20",
        "R11",
        "G12",
        "G26",
        "G09",
        "G21",
        "G15",
        "S24",
    ]:
        assert s in sv

    assert obs["C1"].sel(sv="G07").values == approx([22227666.76, 25342359.37])
    # %% one measurement
    obs = gr.load(fn, meas="C1")
    assert "L1" not in obs

    C1 = obs["C1"]
    assert C1.shape == (2, 14)  # two times, 14 SVs overall for all systems in this file
    assert C1.sel(sv="G07").values == approx([22227666.76, 25342359.37])

    assert obs.fast_processing


def test_meas_two():
    fn = ir.files(f"{__package__}.data") / "demo.10o"

    C1 = gr.load(fn, meas="C1")["C1"]
    # %% two NON-SEQUENTIAL measurements
    obs = gr.load(fn, meas=["L1", "S1"])
    assert "L2" not in obs

    L1 = obs["L1"]
    assert L1.shape == (2, 14)
    assert L1.sel(sv="G07").values == approx([118767195.32608, 133174968.81808])

    S1 = obs["S1"]
    assert S1.shape == (2, 14)

    assert (S1.sel(sv="R23") == approx([39.0, 79.0])).all()

    assert not C1.equals(L1)

    assert obs.fast_processing


def test_meas_miss():
    fn = ir.files(f"{__package__}.data") / "demo.10o"
    # %% measurement not in some systems
    obs = gr.load(fn, meas=["S2"])
    assert "L2" not in obs

    S2 = obs["S2"]
    assert S2.shape == (2, 10)  # all NaN SVs are dropped
    assert (S2.sel(sv="G13") == approx([40.0, 80.0])).all()

    with pytest.raises(KeyError):
        S2.sel(sv="R23")

    assert obs.fast_processing
    # %% measurement not in any system
    obs = gr.load(fn, meas="nonsense")
    assert len(obs) == 0
    # %% wildcard
    obs = gr.load(fn, meas="P")
    assert "L1" not in obs
    assert "P1" in obs and "P2" in obs
    assert len(obs.data_vars) == 2

    assert obs.fast_processing


def test_mangled_data():
    fn = ir.files(f"{__package__}.data") / "14601736.18o"

    obs = gr.load(fn)

    times = gr.to_datetime(obs.time)

    assert (
        times
        == (
            datetime(2018, 6, 22, 6, 17, 30),
            datetime(2018, 6, 22, 6, 17, 45),
            datetime(2018, 6, 22, 6, 18),
        )
    ).all()

    assert not obs.fast_processing


def test_mangled_times():
    fn = ir.files(f"{__package__}.data") / "badtime.10o"

    obs = gr.load(fn)

    times = gr.to_datetime(obs.time)

    assert times


def test_one_sv():
    obs = gr.load(ir.files(f"{__package__}.data") / "rinex2onesat.10o")

    assert len(obs.sv) == 1
    assert obs.sv.item() == "G13"

    times = gr.to_datetime(gr.gettime(ir.files(f"{__package__}.data") / "rinex2onesat.10o"))

    assert (times == [datetime(2010, 3, 5, 0, 0), datetime(2010, 3, 5, 0, 0, 30)]).all()

    assert obs.fast_processing


@pytest.mark.parametrize("use", (None, {"G", "R", "S"}))
def test_all_systems(tmp_path, use):
    """
    python -m georinex.read tests/demo.10o -o r2all.nc
    python -m georinex.read tests/demo.10n -o r2all.nc
    """
    pytest.importorskip("netCDF4")

    truth = xarray.open_dataset(ir.files(f"{__package__}.data") / "r2all.nc", group="OBS")
    # %% test reading all satellites
    obs = gr.load(ir.files(f"{__package__}.data") / "demo.10o", use=use)

    assert obs.equals(truth)
    assert obs.fast_processing

    assert obs.position == pytest.approx([4789028.4701, 176610.0133, 4195017.031])
    try:
        assert obs.position_geodetic == approx([41.38871005, 2.11199932, 166.25085213])
    except AttributeError:  # no pymap3d
        pass
    # %% test read .nc
    obs = gr.rinexobs(ir.files(f"{__package__}.data") / "r2all.nc")
    assert obs.equals(truth)
    # %% test write .nc
    outdir = tmp_path
    outfn = outdir / "testout.nc"
    gr.rinexobs(ir.files(f"{__package__}.data") / "demo.10o", outfn=outdir / "testout.nc")
    assert outfn.is_file() and 50000 > outfn.stat().st_size > 30000


@pytest.mark.parametrize("use", ("G", ["G"]))
def test_one_system(use):
    """python -m georinex.read tests/demo.10o -u G -o r2G.nc"""
    pytest.importorskip("netCDF4")

    truth = xarray.open_dataset(ir.files(f"{__package__}.data") / "r2G.nc", group="OBS")

    obs = gr.load(ir.files(f"{__package__}.data") / "demo.10o", use=use)
    assert obs.equals(truth)
    assert obs.fast_processing


def test_multi_system():
    """python -m georinex.read tests/demo.10o -u G R -o r2GR.nc"""
    pytest.importorskip("netCDF4")

    truth = xarray.open_dataset(ir.files(f"{__package__}.data") / "r2GR.nc", group="OBS")

    obs = gr.load(ir.files(f"{__package__}.data") / "demo.10o", use=("G", "R"))
    assert obs.equals(truth)
    assert obs.fast_processing


def test_all_indicators():
    """
    python -m georinex.read tests/demo.10o -useindicators  -o r2all_indicators.nc
    """
    pytest.importorskip("netCDF4")

    obs = gr.load(ir.files(f"{__package__}.data") / "demo.10o", useindicators=True)
    truth = gr.rinexobs(ir.files(f"{__package__}.data") / "r2all_indicators.nc", group="OBS")

    assert obs.equals(truth)
    assert obs.fast_processing


def test_meas_indicators():
    """
    python -m georinex.read tests/demo.10o -useindicators -m C1 -o r2_C1_indicators.nc
    """
    pytest.importorskip("netCDF4")

    obs = gr.load(ir.files(f"{__package__}.data") / "demo.10o", meas="C1", useindicators=True)
    truth = gr.rinexobs(ir.files(f"{__package__}.data") / "r2_C1_indicators.nc", group="OBS")

    assert obs.equals(truth)
    assert obs.fast_processing


def test_meas_onesys_indicators():
    obs = gr.load(
        ir.files(f"{__package__}.data") / "demo.10o", use="G", meas="C1", useindicators=True
    )

    C1 = obs["C1"]

    assert C1.sel(sv="G07").values == approx([22227666.76, 25342359.37])
    assert obs.fast_processing


@pytest.mark.parametrize("fn, tname", [("demo.10o", "GPS"), ("default_time_system2.10o", "GLO")])
def test_time_system(fn, tname):
    obs = gr.load(ir.files(f"{__package__}.data") / fn)
    assert obs.attrs["time_system"] == tname


def test_wrong_header_count():
    """
    tests wrong count for number of OBS2 types per @serioca #50
    """
    obs = gr.load(ir.files(f"{__package__}.data") / "wrong_obs2_count.10o")
    S2 = obs["S2"].dropna(dim="sv", how="all")

    assert S2.sel(sv="G31").item() == approx(63.0)
