import importlib.resources as ir
import pytest
from pytest import approx
import xarray
from datetime import datetime
import georinex as gr


def test_contents():
    """
    test specifying specific measurements (usually only a few of the thirty or so are needed)
    """
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn)
    for v in ["L1C", "L2P", "C1P", "C2P", "C1C", "S1C", "S1P", "S2P"]:
        assert v in obs
    assert len(obs.data_vars) == 8


def test_meas_one():
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn, meas="C1C")
    assert "L1C" not in obs

    C1C = obs["C1C"]
    assert C1C.shape == (2, 14)  # two times, 14 SVs overall for all systems in this file

    assert (C1C.sel(sv="G07") == approx([22227666.76, 25342359.37])).all()


def test_meas_two():
    """two NON-SEQUENTIAL measurements"""
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn, meas=["L1C", "S1C"])
    assert "L2P" not in obs

    L1C = obs["L1C"].dropna(dim="sv", how="all")
    assert L1C.shape == (2, 14)
    assert (L1C.sel(sv="G07") == approx([118767195.32608, 133174968.81808])).all()

    S1C = obs["S1C"].dropna(dim="sv", how="all")
    assert S1C.shape == (2, 4)

    assert (S1C.sel(sv="R23") == approx([39.0, 79.0])).all()

    C1C = gr.load(fn, meas="C1C")
    assert not C1C.equals(L1C)


def test_meas_some_missing():
    """measurement not in some systems"""
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn, meas=["S2P"])
    assert "L2P" not in obs

    S2P = obs["S2P"].dropna(dim="sv", how="all")
    assert S2P.shape == (2, 10)
    assert (S2P.sel(sv="G13") == approx([40.0, 80.0])).all()

    assert "R23" not in S2P.sv


def test_meas_all_missing():
    """measurement not in any system"""
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn, meas="nonsense")
    assert "nonsense" not in obs

    assert len(obs.data_vars) == 0


def test_meas_wildcard():
    fn = ir.files(f"{__package__}.data") / "obs3.01gage.10o"
    obs = gr.load(fn, meas="C")
    assert "L1C" not in obs
    assert "C1P" in obs and "C2P" in obs and "C1C" in obs
    assert len(obs.data_vars) == 3


@pytest.mark.parametrize("fname", ["junk_time_obs3.10o"])
def test_junk_time(fname):
    """
    some RINEX 3 are observed to have unexpected non-time data

    fixes https://github.com/geospace-code/georinex/issues/77
    """

    times = gr.gettime(ir.files(f"{__package__}.data") / fname)
    assert times.tolist() == [datetime(2010, 3, 5, 0, 0, 30), datetime(2010, 3, 5, 0, 1, 30)]


@pytest.mark.parametrize("fname", ["ABMF00GLP_R_20181330000_01D_30S_MO.zip"])
def test_zip(fname):
    fn = ir.files(f"{__package__}.data") / fname
    obs = gr.load(fn)

    assert (
        obs.sv.values
        == [
            "E04",
            "E09",
            "E12",
            "E24",
            "G02",
            "G05",
            "G06",
            "G07",
            "G09",
            "G12",
            "G13",
            "G17",
            "G19",
            "G25",
            "G30",
            "R01",
            "R02",
            "R08",
            "R22",
            "R23",
            "R24",
            "S20",
            "S31",
            "S35",
            "S38",
        ]
    ).all()

    times = gr.gettime(fn)
    assert times.tolist() == [
        datetime(2018, 5, 13, 1, 30),
        datetime(2018, 5, 13, 1, 30, 30),
        datetime(2018, 5, 13, 1, 31),
    ]

    hdr = gr.rinexheader(fn)
    assert hdr["t0"] <= times[0]


def test_bad_system():
    """Z and Y are not currently used by RINEX"""
    with pytest.raises(KeyError):
        gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o", use="Z")

    with pytest.raises(KeyError):
        gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o", use=["Z", "Y"])


@pytest.mark.parametrize("use", ("G", ["G"]))
def test_one_system(use):
    """
    python -m georinex.read -q tests/obs3.01gage.10o  -u G -o r3G.nc
    """
    pytest.importorskip("netCDF4")

    truth = xarray.open_dataset(ir.files(f"{__package__}.data") / "r3G.nc", group="OBS")

    obs = gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o", use=use)
    assert obs.equals(truth)

    assert obs.position == approx([4789028.4701, 176610.0133, 4195017.031])
    try:
        assert obs.position_geodetic == approx([41.38871005, 2.11199932, 166.25085213])
    except AttributeError:  # no pymap3d
        pass


def test_multi_system():
    """
    python -m georinex.read -q tests/obs3.01gage.10o  -u G R -o r3GR.nc
    """
    pytest.importorskip("netCDF4")

    use = ("G", "R")

    obs = gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o", use=use)
    truth = xarray.open_dataset(ir.files(f"{__package__}.data") / "r3GR.nc", group="OBS")

    assert obs.equals(truth)


def test_all_system():
    """
    python -m georinex.read -q tests/obs3.01gage.10o -o r3all.nc
    """
    pytest.importorskip("netCDF4")

    obs = gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o")
    truth = gr.rinexobs(ir.files(f"{__package__}.data") / "r3all.nc", group="OBS")

    assert obs.equals(truth)


def tests_all_indicators():
    """
    python -m georinex.read -q tests/obs3.01gage.10o -useindicators -o r3all_indicators.nc
    """
    pytest.importorskip("netCDF4")

    obs = gr.load(ir.files(f"{__package__}.data") / "obs3.01gage.10o", useindicators=True)
    truth = gr.rinexobs(ir.files(f"{__package__}.data") / "r3all_indicators.nc", group="OBS")

    assert obs.equals(truth)


@pytest.mark.parametrize("fn, tname", [("obs3.01gage.10o", "GPS"), ("default_time_system3.10o", "GAL")])
def test_time_system(fn, tname):
    obs = gr.load(ir.files(f"{__package__}.data") / fn)
    assert obs.attrs["time_system"] == tname
