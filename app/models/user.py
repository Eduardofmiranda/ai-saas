from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
    )

    name = Column(String, nullable=False)

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = Column(String, nullable=False)

    role = Column(String, nullable=False, default="agent")

    company = relationship("Company")

    def set_password(self, raw_password: str) -> None:
        from app.services.security import hash_password

        self.password_hash = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        from app.services.security import verify_password

        return verify_password(raw_password, self.password_hash)
