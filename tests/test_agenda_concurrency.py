"""Garantia transacional contra dupla reserva concorrente.

O teste real de concorrencia exige um banco Postgres descartavel (o SQLite nao
implementa advisory locks nem replica o READ COMMITTED do Postgres). Defina
`TEST_POSTGRES_URL` aponando para um banco vazio/discartavel para executa-lo:

    pytest tests/test_agenda_concurrency.py -k concurrency

Caso contrario, o teste e pulado (skip) e so o caminho SQLite do helper
(_serialize_booking ser no-op) e verificado.
"""
import os
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registra os models no Base.metadata)
from app.database.database import Base
from app.models.company import Company
from app.services import agenda as ag

TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL", "")

requires_postgres = pytest.mark.skipif(
    not TEST_POSTGRES_URL,
    reason="TEST_POSTGRES_URL (banco Postgres descartavel) nao definido",
)


@requires_postgres
def test_no_double_booking_under_concurrency():
    engine = create_engine(TEST_POSTGRES_URL, pool_size=10, max_overflow=5)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    try:
        setup = Session()
        company = Company(name="Agenda Concorrencia")
        setup.add(company)
        setup.commit()
        setup.refresh(company)
        setup.close()
        company_id = company.id

        n_workers = 4
        barrier = threading.Barrier(n_workers)
        successes: list[int] = []
        conflicts = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker(idx: int):
            db = Session()
            try:
                barrier.wait(timeout=30)
                appt = ag.add_appointment(
                    db,
                    company_id,
                    date="2099-09-21",
                    start_time="10:00",
                    end_time="10:30",
                    phone=f"55110000000{idx}",
                    origin="manual",
                )
                with lock:
                    successes.append(appt.id)
            except Exception as exc:  # noqa: BLE001 - coleta qualquer falha
                with lock:
                    if isinstance(exc, ag.AgendaError) and exc.code == "conflict":
                        conflicts.append(str(exc))
                    else:
                        errors.append(exc)
            finally:
                db.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert not errors, f"falhas inesperadas: {errors!r}"
        assert len(successes) == 1, f"esperado exatamente 1 insert, obtido {len(successes)}"
        assert len(conflicts) == n_workers - 1, conflict
    finally:
        engine.dispose()


def test_serialize_booking_is_noop_on_sqlite(db_session, company):
    # SQLite (dev/testes) nao tem advisory lock; o helper nao deve falhar.
    assert ag._serialize_booking(db_session, company.id, "2099-09-21") is None


def test_booking_flow_with_helper_present(db_session, company):
    # Garante que o novo passo de lock nao altera o fluxo normal no SQLite.
    appt = ag.add_appointment(
        db_session,
        company.id,
        date="2099-09-21",
        start_time="10:00",
        end_time="10:30",
        phone="5511000000000",
        origin="manual",
    )
    assert appt.id
    with pytest.raises(ag.AgendaError, match="ja esta ocupado"):
        ag.add_appointment(
            db_session,
            company.id,
            date="2099-09-21",
            start_time="10:00",
            end_time="10:30",
            phone="5511000000001",
            origin="manual",
        )