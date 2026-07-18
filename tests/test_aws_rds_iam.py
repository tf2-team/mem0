import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from mem0.utils.aws_rds_iam import generate_rds_iam_auth_token, rds_iam_auth_enabled
from mem0.vector_stores.pgvector import PGVector, _RdsIamConnectionPool


class TestRdsIamAuth(unittest.TestCase):
    def test_flag_defaults_to_disabled_and_accepts_true_values(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(rds_iam_auth_enabled())

        self.assertTrue(rds_iam_auth_enabled("true"))
        self.assertTrue(rds_iam_auth_enabled("1"))
        self.assertFalse(rds_iam_auth_enabled("false"))

    def test_token_uses_ambient_aws_credentials_and_explicit_region(self):
        client = MagicMock()
        client.generate_db_auth_token.return_value = "signed-rds-token"
        boto3 = MagicMock()
        boto3.client.return_value = client

        with patch.dict(sys.modules, {"boto3": boto3}):
            token = generate_rds_iam_auth_token("db.example", 5432, "mem0_app", "us-east-1")

        self.assertEqual(token, "signed-rds-token")
        boto3.client.assert_called_once_with("rds", region_name="us-east-1")
        client.generate_db_auth_token.assert_called_once_with(
            DBHostname="db.example",
            Port=5432,
            DBUsername="mem0_app",
            Region="us-east-1",
        )

    def test_pgvector_uses_ephemeral_pool_when_iam_auth_is_enabled(self):
        store = PGVector(
            dbname="mem0",
            collection_name="memories",
            embedding_model_dims=384,
            user="mem0_app",
            password="ignored",
            host="db.example",
            port=5432,
            diskann=False,
            hnsw=False,
            sslmode="require",
            use_aws_iam_auth=True,
            aws_region="us-east-1",
        )

        self.assertIsInstance(store.connection_pool, _RdsIamConnectionPool)
        self.assertNotIn("ignored", store.connection_pool._conninfo)
        self.assertIn("sslmode=require", store.connection_pool._conninfo)
