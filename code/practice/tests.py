from django.db import connection
from django.test import TestCase

from .models import Problem


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
