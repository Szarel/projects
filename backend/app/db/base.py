"""Base imports for Alembic autogeneration."""

from app.db.session import Base
from app.models.property import Property  # noqa: F401
from app.models.person import Person  # noqa: F401
from app.models.contract import LeaseContract  # noqa: F401
from app.models.charge import Charge, PaymentDetail  # noqa: F401
from app.models.property_state import PropertyStateHistory  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.user import User  # noqa: F401
