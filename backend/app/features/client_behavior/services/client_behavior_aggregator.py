from sqlalchemy.orm import Session


class ClientBehaviorAggregator:
    """Update hourly behavior rollups from DNS ingest batches."""

    def __init__(self, db: Session):
        self.db = db

    def process_queries(self, queries: list) -> None:
        """No-op: DNS ingest removed."""
