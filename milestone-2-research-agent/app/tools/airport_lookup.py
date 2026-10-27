"""Airport lookup module using local bundled airport metadata."""

from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class AirportNotFoundError(Exception):
    """Raised when an airport cannot be found by IATA or ICAO code."""

    def __init__(self, code: str):
        super().__init__(f"Airport code '{code}' not recognized in database.")
        self.code = code


class Airport(BaseModel):
    """Airport metadata model."""

    iata: str = Field(..., min_length=3, max_length=3)
    icao: str = Field(..., min_length=4, max_length=4)
    name: str = Field(...)
    latitude: float = Field(...)
    longitude: float = Field(...)

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees.")
        return v


def _load_airports() -> dict[str, Airport]:
    json_path = Path(__file__).resolve().parent.parent / "data" / "airports.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    airport_index: dict[str, Airport] = {}
    for entry in data:
        airport = Airport(**entry)
        airport_index[airport.iata.upper()] = airport
        airport_index[airport.icao.upper()] = airport
    return airport_index


_AIRPORT_CACHE: dict[str, Airport] | None = None


def get_airport(code: str) -> Airport:
    """Retrieve airport details by IATA or ICAO code (case-insensitive).

    Raises:
        AirportNotFoundError: If code is not found in bundled dataset.
    """
    global _AIRPORT_CACHE
    if _AIRPORT_CACHE is None:
        _AIRPORT_CACHE = _load_airports()

    cleaned_code = code.strip().upper() if isinstance(code, str) else ""
    if cleaned_code in _AIRPORT_CACHE:
        return _AIRPORT_CACHE[cleaned_code]

    raise AirportNotFoundError(code)
