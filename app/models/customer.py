from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False
    )

    name = Column(String)

    phone = Column(
        String,
        nullable=False
    )

    email = Column(String, nullable=True)

    company = Column(String, nullable=True)

    city = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    company_rel = relationship("Company")