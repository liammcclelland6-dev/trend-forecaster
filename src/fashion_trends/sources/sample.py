"""Synthetic sample signals for exercising the pipeline end to end."""

from datetime import date

from fashion_trends.models import Signal


class SampleSource:
    name = "sample"

    def fetch(self, observed_on: date) -> list[Signal]:
        examples = [
            ("search-001", "western belts", "https://example.invalid/search/western-belts", 0.8),
            ("pins-001", "cowboy buckle accessories", "https://example.invalid/pins/western", 0.7),
            ("video-001", "rhinestone rodeo belt styling", "https://example.invalid/video/rodeo", 0.6),
            ("editorial-001", "western influenced accessories", "https://example.invalid/editorial/runway", 0.7),
            ("search-002", "red ballet flats", "https://example.invalid/search/flats", 0.8),
        ]
        return [
            Signal(self.name, item_id, observed_on, text, url, confidence)
            for item_id, text, url, confidence in examples
        ]
