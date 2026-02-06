import pytest

from backend.agent.sql_validator import SQLValidationError, validate_sql


@pytest.fixture
def role_allowlist():
    return {
        "analytics.orders": {"order_date", "revenue", "customer_id", "quantity"},
    }


def test_validate_select_ok(role_allowlist):
    sql = (
        "SELECT DATE_FORMAT(`order_date`, '%Y-%m') AS period, SUM(`revenue`) AS metric_value "
        "FROM `analytics`.`orders` "
        "WHERE `order_date` >= DATE_SUB(CURRENT_DATE, INTERVAL 5 MONTH) "
        "GROUP BY DATE_FORMAT(`order_date`, '%Y-%m')"
    )
    validate_sql(sql, role_allowlist)


def test_validate_blocks_unapproved_column(role_allowlist):
    sql = "SELECT margin FROM analytics.orders"
    with pytest.raises(SQLValidationError, match="column outside role permissions"):
        validate_sql(sql, role_allowlist)


def test_validate_blocks_non_select(role_allowlist):
    sql = "DELETE FROM analytics.orders"
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql(sql, role_allowlist)


def test_validate_blocks_select_star(role_allowlist):
    sql = "SELECT * FROM analytics.orders"
    with pytest.raises(SQLValidationError, match=r"SELECT \* is not allowed"):
        validate_sql(sql, role_allowlist)


def test_validate_blocks_table_star(role_allowlist):
    sql = "SELECT o.* FROM analytics.orders o"
    with pytest.raises(SQLValidationError, match=r"SELECT \* is not allowed"):
        validate_sql(sql, role_allowlist)


def test_validate_blocks_subquery_select_star(role_allowlist):
    sql = "SELECT t.order_date FROM (SELECT * FROM analytics.orders) t"
    with pytest.raises(SQLValidationError, match=r"SELECT \* is not allowed"):
        validate_sql(sql, role_allowlist)


def test_validate_blocks_subquery_restricted_table(role_allowlist):
    sql = (
        "SELECT x.customer_id "
        "FROM (SELECT customer_id FROM analytics.customers) x"
    )
    with pytest.raises(SQLValidationError, match="table outside role permissions"):
        validate_sql(sql, role_allowlist)


def test_validate_allows_count_star(role_allowlist):
    sql = "SELECT COUNT(*) AS c FROM analytics.orders"
    validate_sql(sql, role_allowlist)
