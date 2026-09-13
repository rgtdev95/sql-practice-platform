from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from .models import Problem
from .sandbox import QueryError, check_submission, validate_select_only


class ProblemSchemaProvisioningTests(TestCase):
    def make_problem(self, schema_sql):
        return Problem.objects.create(
            title="Add two numbers",
            slug="add-two-numbers",
            difficulty=Problem.Difficulty.EASY,
            schema_sql=schema_sql,
            solution_sql="SELECT * FROM nums",
        )

    def test_provision_schema_creates_tables_and_grants_practice_runner(self):
        problem = self.make_problem("CREATE TABLE nums (n integer);")

        problem.provision_schema()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                [problem.schema_name],
            )
            tables = [row[0] for row in cursor.fetchall()]
            self.assertEqual(tables, ["nums"])

            cursor.execute(
                "SELECT privilege_type FROM information_schema.role_table_grants "
                "WHERE table_schema = %s AND table_name = %s AND grantee = %s",
                [problem.schema_name, "nums", "practice_runner"],
            )
            privileges = [row[0] for row in cursor.fetchall()]
            self.assertIn("SELECT", privileges)

    def test_provision_schema_is_idempotent_on_resave(self):
        problem = self.make_problem("CREATE TABLE nums (n integer);")
        problem.provision_schema()

        problem.schema_sql = "CREATE TABLE letters (c text);"
        problem.provision_schema()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                [problem.schema_name],
            )
            tables = [row[0] for row in cursor.fetchall()]
            self.assertEqual(tables, ["letters"])

    def test_provision_schema_failure_leaves_nothing_behind(self):
        problem = self.make_problem("THIS IS NOT VALID SQL;")

        with self.assertRaises(Exception):
            problem.provision_schema()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [problem.schema_name],
            )
            self.assertIsNone(cursor.fetchone())


class ValidateSelectOnlyTests(SimpleTestCase):
    def test_accepts_plain_select(self):
        validate_select_only("SELECT 1")

    def test_accepts_cte(self):
        validate_select_only("WITH cte AS (SELECT 1 AS n) SELECT * FROM cte")

    def test_rejects_multiple_statements(self):
        with self.assertRaises(QueryError):
            validate_select_only("SELECT 1; SELECT 2;")

    def test_rejects_non_select(self):
        with self.assertRaises(QueryError):
            validate_select_only("DELETE FROM nums")


class SandboxExecutionTests(TransactionTestCase):
    """Uses TransactionTestCase, not TestCase: check_submission opens its
    own psycopg connection as practice_runner, a separate DB session from
    Django's ORM connection. TestCase wraps each test in an uncommitted
    transaction that a different connection can never see; TransactionTestCase
    actually commits, so the sandbox connection sees the same data."""

    def make_problem(self, schema_sql, solution_sql):
        problem = Problem.objects.create(
            title="Numbers",
            slug="numbers",
            difficulty=Problem.Difficulty.EASY,
            schema_sql=schema_sql,
            solution_sql=solution_sql,
        )
        problem.provision_schema()
        return problem

    def test_correct_submission(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer); INSERT INTO nums VALUES (1), (2), (3);",
            "SELECT n FROM nums ORDER BY n",
        )
        result = check_submission(problem, "SELECT n FROM nums ORDER BY n")
        self.assertEqual(result["status"], "correct")

    def test_correct_submission_ignores_order_when_solution_has_no_order_by(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer); INSERT INTO nums VALUES (1), (2), (3);",
            "SELECT n FROM nums",
        )
        result = check_submission(problem, "SELECT n FROM nums ORDER BY n DESC")
        self.assertEqual(result["status"], "correct")

    def test_incorrect_order_when_solution_requires_it(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer); INSERT INTO nums VALUES (1), (2), (3);",
            "SELECT n FROM nums ORDER BY n",
        )
        result = check_submission(problem, "SELECT n FROM nums ORDER BY n DESC")
        self.assertEqual(result["status"], "incorrect")

    def test_wrong_values_are_incorrect(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer); INSERT INTO nums VALUES (1), (2), (3);",
            "SELECT n FROM nums",
        )
        result = check_submission(problem, "SELECT n FROM nums WHERE n < 3")
        self.assertEqual(result["status"], "incorrect")

    def test_non_select_is_rejected_without_touching_data(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer); INSERT INTO nums VALUES (1);",
            "SELECT n FROM nums",
        )
        result = check_submission(problem, "DELETE FROM nums")
        self.assertEqual(result["status"], "error")

    def test_cannot_read_public_schema(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer);",
            "SELECT n FROM nums",
        )
        result = check_submission(problem, "SELECT * FROM public.auth_user")
        self.assertEqual(result["status"], "error")
        self.assertIn("permission denied", result["error"].lower())

    def test_long_running_query_times_out(self):
        problem = self.make_problem(
            "CREATE TABLE nums (n integer);",
            "SELECT n FROM nums",
        )
        result = check_submission(problem, "SELECT pg_sleep(10)")
        self.assertEqual(result["status"], "error")
        self.assertIn("too long", result["error"].lower())
