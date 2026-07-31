"""Unit tests for deterministic, alias-aware Nominatim query construction."""

import unittest

from app.services.geocoding import NominatimGeocodingClient


class _Settings:
    geocoding_locality_aliases = {
        "Appa Junction Peerancheru": "Peerancheru",
    }


class NominatimQueryCandidateTests(unittest.TestCase):
    """Verify aliases are normalized and fallbacks retain Hyderabad preference."""

    def test_alias_query_is_progressively_simplified(self) -> None:
        client = object.__new__(NominatimGeocodingClient)
        client._settings = _Settings()

        candidates = client._build_query_candidates("Appa Junction Peerancheru")

        self.assertEqual(
            candidates,
            (
                "Appa Junction Peerancheru, Hyderabad, Telangana, India",
                "Peerancheru, Hyderabad, Telangana, India",
                "Peerancheru",
                "Peerancheru, Telangana, India",
                "Peerancheru, India",
            ),
        )
