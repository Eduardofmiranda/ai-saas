import pytest
from fastapi.testclient import TestClient

from app.models.conversation_transfer import ConversationTransfer


class TestTransferNode:
    @pytest.mark.asyncio
    async def test_transfer_to_agent_marks_conversation_pending(self, db_session, company, config, conversation):
        from app.services.nodes.context import NodeContext
        from app.services.nodes import registry

        ctx = NodeContext(
            db=db_session,
            company_id=company.id,
            execution_id=1,
            workflow_id=1,
            data={"conversation_id": conversation.id, "conversation": {"id": conversation.id}},
            config=config,
        )

        result = await registry.run_node(
            ctx, {"id": "n1", "type": "transfer_to_agent", "data": {}}
        )

        db_session.refresh(conversation)
        assert conversation.status == "pending_agent"
        assert result["outputs"]["transferred"] is True

        transfer = db_session.query(ConversationTransfer).one()
        assert transfer.conversation_id == conversation.id
        assert transfer.company_id == company.id
        assert transfer.actor_type == "workflow"
        assert transfer.action == "transfer_requested"

    @pytest.mark.asyncio
    async def test_transfer_to_agent_keeps_status_and_logs_when_already_pending(
        self, db_session, company, config, conversation,
    ):
        from app.services.nodes.context import NodeContext
        from app.services.nodes import registry

        conversation.status = "pending_agent"
        db_session.commit()

        ctx = NodeContext(
            db=db_session,
            company_id=company.id,
            execution_id=1,
            workflow_id=1,
            data={"conversation_id": conversation.id},
            config=config,
        )

        result = await registry.run_node(
            ctx, {"id": "n1", "type": "transfer_to_agent", "data": {}}
        )

        assert result["outputs"]["transferred"] is True
        assert db_session.query(ConversationTransfer).count() == 0

    @pytest.mark.asyncio
    async def test_transfer_to_agent_ignores_conversation_outside_company(
        self, db_session, company, config, conversation,
    ):
        from app.services.nodes.context import NodeContext
        from app.services.nodes import registry

        ctx = NodeContext(
            db=db_session,
            company_id=999,
            execution_id=1,
            workflow_id=1,
            data={"conversation_id": conversation.id},
            config=config,
        )

        result = await registry.run_node(
            ctx, {"id": "n1", "type": "transfer_to_agent", "data": {}}
        )

        assert result["outputs"]["transferred"] is False
        db_session.refresh(conversation)
        assert conversation.status == "open"
        assert db_session.query(ConversationTransfer).count() == 0


class TestReusePendingConversation:
    @pytest.mark.asyncio
    async def test_incoming_message_reuses_pending_agent_conversation(
        self, db_session, company, customer,
    ):
        from app.services.conversation_service import handle_incoming_workflow

        from app.models.conversation import Conversation

        conv = Conversation(company_id=company.id, customer_id=customer.id, status="pending_agent")
        db_session.add(conv)
        db_session.commit()

        result = await handle_incoming_workflow(
            db_session,
            company_id=company.id,
            phone=customer.phone,
            text="quero falar com alguem",
            wa_message_id="wamid_reuse",
        )

        assert result["status"] == "no_workflow"
        assert result["conversation_id"] == conv.id
        assert db_session.query(Conversation).count() == 1
        db_session.refresh(conv)
        assert conv.status == "pending_agent"


class TestTransferHistoryHttp:
    @pytest.fixture
    def db_session(self):
        import tempfile

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database.database import Base

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        db._engine = engine
        try:
            yield db
        finally:
            db.close()
            engine.dispose()

    @pytest.fixture
    def owner(self, db_session):
        from app.models.user import User

        u = User(company_id=1, name="Dono", email="owner@test.com", role="owner")
        u.set_password("senha123")
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u

    def _make(self, db_session, current_user):
        from app.database.session import get_db
        from app.main import app
        from app.services.deps import get_current_user

        def _get_db():
            yield db_session

        app.dependency_overrides[get_current_user] = lambda: current_user
        app.dependency_overrides[get_db] = _get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def _seed(self, db_session, *, status="open"):
        from app.models.conversation import Conversation
        from app.models.customer import Customer

        cust = Customer(company_id=1, phone="5511999999999", name="Cliente")
        db_session.add(cust)
        db_session.flush()
        conv = Conversation(company_id=1, customer_id=cust.id, status=status)
        db_session.add(conv)
        db_session.commit()
        return conv

    def test_patch_pending_to_open_records_assumed(self, db_session, owner):
        conv = self._seed(db_session, status="pending_agent")
        from app.models.conversation_transfer import ConversationTransfer

        for c in self._make(db_session, owner):
            res = c.patch(f"/conversations/{conv.id}", json={"status": "open"})
            assert res.status_code == 200
            assert res.json()["status"] == "open"

        transfer = db_session.query(ConversationTransfer).one()
        assert transfer.action == "assumed"
        assert transfer.actor_type == "user"
        assert transfer.user_name == "Dono"

    def test_patch_open_to_closed_records_closed(self, db_session, owner):
        conv = self._seed(db_session, status="open")

        for c in self._make(db_session, owner):
            res = c.patch(f"/conversations/{conv.id}", json={"status": "closed"})
            assert res.status_code == 200

        transfer = db_session.query(ConversationTransfer).one()
        assert transfer.action == "closed"

    def test_response_includes_transfers_list(self, db_session, owner):
        from app.models.conversation_transfer import ConversationTransfer

        conv = self._seed(db_session, status="pending_agent")
        db_session.add(
            ConversationTransfer(
                conversation_id=conv.id,
                company_id=1,
                actor_type="workflow",
                action="transfer_requested",
            )
        )
        db_session.commit()

        for c in self._make(db_session, owner):
            res = c.get("/conversations/")
            assert res.status_code == 200
            row = res.json()[0]
            assert row["status"] == "pending_agent"
            assert len(row["transfers"]) == 1
            assert row["transfers"][0]["action"] == "transfer_requested"

    def test_dashboard_counts_pending_conversations(self, db_session, owner):
        self._seed(db_session, status="open")
        self._seed(db_session, status="pending_agent")
        self._seed(db_session, status="closed")

        for c in self._make(db_session, owner):
            res = c.get("/dashboard/")
            assert res.status_code == 200
            data = res.json()
            assert data["pending_conversations"] == 1
            assert data["open_conversations"] == 1
            assert data["closed_conversations"] == 1