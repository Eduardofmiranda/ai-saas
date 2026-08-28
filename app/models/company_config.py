from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class CompanyConfig(Base):
    __tablename__ = "company_configs"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        unique=True,
    )

    # --- Inteligencia Artificial (configuravel por empresa) ---
    # Campos vazios = usa os defaults globais do .env (DEFAULT_AI_*)
    ai_provider = Column(String, nullable=False, default="")
    ai_model = Column(String, nullable=False, default="")
    ai_api_key = Column(String, default="")
    ai_base_url = Column(String, default="")
    system_prompt = Column(
        Text,
        default=(
            "Voce e um assistente virtual de atendimento ao cliente. "
            "Responda de forma educada, clara e objetiva em portugues do Brasil."
        ),
    )

    # --- WhatsApp / Evolution API (por empresa) ---
    evolution_base_url = Column(String, default="")
    evolution_api_key = Column(String, default="")
    evolution_instance = Column(String, default="")

    # --- Comportamento ---
    ai_on = Column(Boolean, nullable=False, default=True)

    company = relationship("Company")

    # Ajusta a chave API para nao vazar em respostas publicas ao omitir

    def public_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "ai_base_url": self.ai_base_url,
            "system_prompt": self.system_prompt,
            "evolution_base_url": self.evolution_base_url,
            "evolution_instance": self.evolution_instance,
            "ai_on": self.ai_on,
        }
