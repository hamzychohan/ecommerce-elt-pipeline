"""Data validation models for the extract pipeline."""

import logging
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ProductValidator(BaseModel):
    """Essential fields for a DummyJSON product."""
    id: int
    title: str
    price: float


class UserValidator(BaseModel):
    """Essential fields for a DummyJSON user."""
    id: int
    firstName: str
    lastName: str


class CartValidator(BaseModel):
    """Essential fields for a DummyJSON cart."""
    id: int
    total: float
    userId: int


def validate_records(entity: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate a batch of records, returning only those that pass."""
    validator_map = {
        "products": ProductValidator,
        "users": UserValidator,
        "carts": CartValidator,
    }

    model = validator_map.get(entity)
    if not model:
        logger.warning("No validator found for entity '%s'. Passing through raw records.", entity)
        return records

    valid_records = []
    errors = 0
    for record in records:
        try:
            # We don't overwrite the record because pydantic strips fields not defined in the model.
            # We just want to ensure it has the minimum required structure before passing it on.
            model(**record)
            valid_records.append(record)
        except ValidationError as e:
            errors += 1
            logger.debug("Validation failed for %s record: %s", entity, e)

    if errors > 0:
        logger.warning("Dropped %d invalid records for entity '%s'", errors, entity)

    return valid_records
