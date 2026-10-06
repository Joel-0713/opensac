import pytest
from unittest.mock import MagicMock, patch
from seed_rag import seed_database

@patch("seed_rag.ConnectionPool")
@patch("seed_rag.GoogleGenerativeAIEmbeddings")
def test_seed_database(mock_embeddings_cls, mock_pool_cls, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query.return_value = [0.1] * 768
    mock_embeddings_cls.return_value = mock_embeddings
    
    mock_pool = MagicMock()
    mock_pool_cls.return_value.__enter__.return_value = mock_pool
    mock_conn = MagicMock()
    mock_pool.connection.return_value.__enter__.return_value = mock_conn
    
    seed_database()
    
    assert mock_embeddings.embed_query.call_count == 3
    assert mock_conn.execute.call_count == 3
    mock_conn.commit.assert_called_once()
