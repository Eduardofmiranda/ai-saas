from app.database.database import engine, Base

from app.models.company import Company
from app.models.company_config import CompanyConfig
from app.models.user import User
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.workflow import Workflow
from app.models.execution import Execution
from app.models.pending_flow import PendingFlow
from app.models.knowledge import Knowledge, KnowledgeChunk

print(Base.metadata.tables.keys())

Base.metadata.create_all(bind=engine)

print("Tabelas criadas!")
