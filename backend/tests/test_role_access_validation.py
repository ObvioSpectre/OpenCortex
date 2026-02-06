from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import AllowlistColumn, AllowlistTable, Base, Organization, OrganizationRole
from backend.models import DataSource
from backend.semantic.service import SemanticService


def _build_test_session() -> Session:
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_role_matrix_executive_finance_admin_for_revenue_metric():
    session = _build_test_session()

    org = Organization(id='org_demo', name='Demo Org', status='active')
    session.add(org)
    for role_key in ['admin', 'executive', 'finance', 'sales', 'senior_executive']:
        session.add(OrganizationRole(organization_id='org_demo', role_key=role_key, description='', is_active=True))

    ds = DataSource(id='default_mysql', organization_id='org_demo', name='Primary', mysql_uri='mysql+pymysql://x')
    session.add(ds)
    session.flush()

    t_orders = AllowlistTable(
        data_source_id='default_mysql',
        database_name='analytics',
        table_name='orders',
        approved=True,
        allowed_roles=['admin', 'executive', 'finance', 'sales', 'senior_executive'],
    )
    session.add(t_orders)
    session.flush()

    session.add_all([
        AllowlistColumn(allowlist_table_id=t_orders.id, column_name='order_date', approved=True, allowed_roles=['admin', 'executive', 'finance', 'sales', 'senior_executive']),
        AllowlistColumn(allowlist_table_id=t_orders.id, column_name='revenue', approved=True, allowed_roles=['admin', 'finance']),
        AllowlistColumn(allowlist_table_id=t_orders.id, column_name='quantity', approved=True, allowed_roles=['admin', 'executive', 'finance', 'sales', 'senior_executive']),
    ])

    session.commit()

    schema = {
        'databases': [
            {
                'database_name': 'analytics',
                'tables': [
                    {
                        'table_name': 'orders',
                        'columns': [
                            {'name': 'order_date', 'type': 'date'},
                            {'name': 'revenue', 'type': 'decimal(14,2)'},
                            {'name': 'quantity', 'type': 'int'},
                        ],
                        'primary_keys': ['order_id'],
                        'foreign_keys': [],
                        'date_time_columns': ['order_date'],
                    }
                ],
            }
        ]
    }

    allowlist = {'analytics.orders': {'order_date', 'revenue', 'quantity'}}
    semantic_service = SemanticService()
    semantic_service.build_semantic_model(session, 'org_demo', 'default_mysql', schema, allowlist)
    session.flush()

    exec_sem = semantic_service.get_role_aware_semantics(session, 'org_demo', 'default_mysql', role='executive')
    fin_sem = semantic_service.get_role_aware_semantics(session, 'org_demo', 'default_mysql', role='finance')
    admin_sem = semantic_service.get_role_aware_semantics(session, 'org_demo', 'default_mysql', role='admin')

    exec_metrics = {m['name'] for m in exec_sem['metrics']}
    fin_metrics = {m['name'] for m in fin_sem['metrics']}
    admin_metrics = {m['name'] for m in admin_sem['metrics']}

    assert 'orders_revenue_sum' not in exec_metrics
    assert 'orders_revenue_sum' in fin_metrics
    assert 'orders_revenue_sum' in admin_metrics

    assert exec_metrics.issubset(admin_metrics)
    assert fin_metrics.issubset(admin_metrics)
