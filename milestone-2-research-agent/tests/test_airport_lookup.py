import pytest
from pydantic import ValidationError

from app.tools.airport_lookup import Airport, AirportNotFoundError, get_airport


def test_get_airport_iata():
    del_airport = get_airport("DEL")
    assert del_airport.iata == "DEL"
    assert del_airport.icao == "VIDP"
    assert "Indira Gandhi" in del_airport.name
    assert del_airport.latitude == pytest.approx(28.5665, 0.001)
    assert del_airport.longitude == pytest.approx(77.1031, 0.001)


def test_get_airport_icao():
    jfk_airport = get_airport("KJFK")
    assert jfk_airport.iata == "JFK"
    assert jfk_airport.icao == "KJFK"
    assert jfk_airport.name == "John F. Kennedy International Airport"


def test_get_airport_case_insensitive_and_whitespace():
    bom = get_airport(" bom ")
    assert bom.iata == "BOM"

    lhr = get_airport("egll")
    assert lhr.iata == "LHR"
    assert lhr.icao == "EGLL"


def test_get_airport_unknown_code():
    with pytest.raises(AirportNotFoundError) as exc_info:
        get_airport("ZZZ")
    assert "ZZZ" in str(exc_info.value)

    with pytest.raises(AirportNotFoundError):
        get_airport("INVALID")


def test_airport_coordinate_validation():
    # Valid airport
    a = Airport(
        iata="TST",
        icao="TEST",
        name="Test Airport",
        latitude=10.0,
        longitude=20.0,
    )
    assert a.latitude == 10.0

    # Invalid latitude
    with pytest.raises(ValidationError):
        Airport(
            iata="TST",
            icao="TEST",
            name="Test Airport",
            latitude=95.0,
            longitude=20.0,
        )

    # Invalid longitude
    with pytest.raises(ValidationError):
        Airport(
            iata="TST",
            icao="TEST",
            name="Test Airport",
            latitude=10.0,
            longitude=-185.0,
        )
