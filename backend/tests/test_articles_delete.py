"""
B30 - Backend Tests: Article Deletion (DELETE /api/v1/articles/{id})
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 5 (Testing & Docs)

Tests the DELETE /api/v1/articles/{id} endpoint (B13) against the in-memory
SQLite database using the fixtures defined in conftest.py.

TEST COVERAGE
-------------
Happy path:
  ✅ 204 No Content returned on successful deletion
  ✅ Response body is empty (RFC 9110 §15.3.5 compliance)
  ✅ Deleted article is no longer retrievable via GET (database persistence)
  ✅ Deleting one article does not affect other articles (isolation)

Error paths:
  ✅ 404 Not Found for a non-existent article id
  ✅ Error response body matches the standard error envelope
  ✅ Error code is "ARTICLE_NOT_FOUND"
  ✅ 404 returned when deleting an already-deleted article (idempotency check)
  ✅ 422 Unprocessable Entity for id = 0 and non-integer ids

IMPORTANT NOTE on 204 body
---------------------------
RFC 9110 mandates that a 204 response MUST NOT include a message body.
The test `test_delete_article_response_body_is_empty` asserts this by
checking that `response.content` is empty bytes (b"") — not that
`response.json()` is null, which would raise a JSONDecodeError on 204.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.article import ArticleStatus


# ---------------------------------------------------------------------------
# 204 No Content — Happy path tests
# ---------------------------------------------------------------------------

class TestDeleteArticleSuccess:
    """Tests for successful article deletion (HTTP 204)."""

    @pytest.mark.integration
    def test_delete_existing_article_returns_204(self, client: TestClient, make_article):
        """
        GIVEN a published article exists in the database
        WHEN  DELETE /api/v1/articles/{id} is called with its id
        THEN  the response status code is 204 No Content
        """
        article = make_article(title="Article To Delete", slug="article-to-delete")

        response = client.delete(f"/api/v1/articles/{article.id}")

        assert response.status_code == 204

    @pytest.mark.integration
    def test_delete_article_response_body_is_empty(self, client: TestClient, make_article):
        """
        GIVEN a published article exists in the database
        WHEN  DELETE /api/v1/articles/{id} is called
        THEN  the response body is completely empty (RFC 9110 §15.3.5 compliance)
              (assert on raw bytes, not json() — 204 has no JSON body)
        """
        article = make_article(
            title="No Body Article",
            slug="no-body-article-delete",
        )

        response = client.delete(f"/api/v1/articles/{article.id}")

        # b"" means strictly empty — no null, no {}, no whitespace.
        assert response.content == b""

    @pytest.mark.integration
    def test_deleted_article_is_no_longer_retrievable(self, client: TestClient, make_article):
        """
        GIVEN a published article is successfully deleted
        WHEN  GET /api/v1/articles/{id} is called for the same id
        THEN  the response status code is 404 Not Found
              (confirms the delete was actually persisted to the database)
        """
        article = make_article(
            title="Persistence Check Article",
            slug="persistence-check-article",
        )
        article_id = article.id

        # Delete it.
        delete_response = client.delete(f"/api/v1/articles/{article_id}")
        assert delete_response.status_code == 204

        # Try to fetch it — must be gone.
        get_response = client.get(f"/api/v1/articles/{article_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_draft_article_returns_204(self, client: TestClient, make_article):
        """
        GIVEN a DRAFT article exists in the database
        WHEN  DELETE /api/v1/articles/{id} is called
        THEN  the response status code is 204 (status does not block deletion)
        """
        article = make_article(
            title="Draft Article Delete",
            slug="draft-article-delete-test",
            status=ArticleStatus.DRAFT,
        )

        response = client.delete(f"/api/v1/articles/{article.id}")

        assert response.status_code == 204

    @pytest.mark.integration
    def test_delete_archived_article_returns_204(self, client: TestClient, make_article):
        """
        GIVEN an ARCHIVED article exists in the database
        WHEN  DELETE /api/v1/articles/{id} is called
        THEN  the response status code is 204 (archived articles can be deleted)
        """
        article = make_article(
            title="Archived Article Delete",
            slug="archived-article-delete-test",
            status=ArticleStatus.ARCHIVED,
        )

        response = client.delete(f"/api/v1/articles/{article.id}")

        assert response.status_code == 204

    @pytest.mark.integration
    def test_deleting_one_article_does_not_affect_others(
        self, client: TestClient, make_article
    ):
        """
        GIVEN two articles exist in the database
        WHEN  DELETE /api/v1/articles/{id} is called for the first article
        THEN  the second article is still retrievable via GET (isolation check)
        """
        article_a = make_article(title="Article A", slug="article-a-isolation")
        article_b = make_article(title="Article B", slug="article-b-isolation")

        # Delete only article A.
        delete_response = client.delete(f"/api/v1/articles/{article_a.id}")
        assert delete_response.status_code == 204

        # Article B must be unaffected.
        get_response = client.get(f"/api/v1/articles/{article_b.id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == article_b.id


# ---------------------------------------------------------------------------
# 404 Not Found — Error path tests
# ---------------------------------------------------------------------------

class TestDeleteArticleNotFound:
    """Tests for the 404 Not Found error path on deletion."""

    @pytest.mark.integration
    def test_delete_nonexistent_article_returns_404(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  DELETE /api/v1/articles/99999 is called
        THEN  the response status code is 404 Not Found
        """
        response = client.delete("/api/v1/articles/99999")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_delete_nonexistent_article_error_envelope_structure(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  DELETE /api/v1/articles/99999 is called
        THEN  the response body follows the standard error envelope:
              {"error": {"code": ..., "message": ..., "status": 404}}
        """
        response = client.delete("/api/v1/articles/99999")
        data = response.json()

        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "status" in data["error"]

    @pytest.mark.integration
    def test_delete_nonexistent_article_error_code_is_article_not_found(
        self, client: TestClient
    ):
        """
        GIVEN no article with id 99999 exists
        WHEN  DELETE /api/v1/articles/99999 is called
        THEN  the error code is "ARTICLE_NOT_FOUND"
        """
        response = client.delete("/api/v1/articles/99999")
        data = response.json()

        assert data["error"]["code"] == "ARTICLE_NOT_FOUND"

    @pytest.mark.integration
    def test_delete_nonexistent_article_error_status_is_404(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  DELETE /api/v1/articles/99999 is called
        THEN  the "status" field inside the error envelope equals 404
        """
        response = client.delete("/api/v1/articles/99999")
        data = response.json()

        assert data["error"]["status"] == 404

    @pytest.mark.integration
    def test_double_delete_returns_404_on_second_call(
        self, client: TestClient, make_article
    ):
        """
        GIVEN an article is successfully deleted on the first call
        WHEN  DELETE /api/v1/articles/{id} is called again for the same id
        THEN  the second call returns 404 Not Found
              (idempotency: the API behaves correctly on repeated delete attempts)
        """
        article = make_article(
            title="Double Delete Article",
            slug="double-delete-article-test",
        )
        article_id = article.id

        # First delete: should succeed.
        first_response = client.delete(f"/api/v1/articles/{article_id}")
        assert first_response.status_code == 204

        # Second delete: article is gone, must return 404.
        second_response = client.delete(f"/api/v1/articles/{article_id}")
        assert second_response.status_code == 404

    @pytest.mark.integration
    def test_delete_nonexistent_article_error_message_contains_id(self, client: TestClient):
        """
        GIVEN no article with id 55555 exists
        WHEN  DELETE /api/v1/articles/55555 is called
        THEN  the error message mentions the requested id
        """
        response = client.delete("/api/v1/articles/55555")
        data = response.json()

        assert "55555" in data["error"]["message"]


# ---------------------------------------------------------------------------
# 422 Unprocessable Entity — Input validation tests
# ---------------------------------------------------------------------------

class TestDeleteArticleInputValidation:
    """Tests for FastAPI path parameter validation on DELETE."""

    @pytest.mark.integration
    def test_delete_article_with_zero_id_returns_422(self, client: TestClient):
        """
        GIVEN id = 0 (violates ge=1 constraint in Path(..., ge=1))
        WHEN  DELETE /api/v1/articles/0 is called
        THEN  the response status code is 422 Unprocessable Entity
        """
        response = client.delete("/api/v1/articles/0")

        assert response.status_code == 422

    @pytest.mark.integration
    def test_delete_article_with_negative_id_returns_422(self, client: TestClient):
        """
        GIVEN id = -1 (violates ge=1)
        WHEN  DELETE /api/v1/articles/-1 is called
        THEN  the response status code is 422 Unprocessable Entity
        """
        response = client.delete("/api/v1/articles/-1")

        assert response.status_code == 422

    @pytest.mark.integration
    def test_delete_article_with_string_id_returns_422(self, client: TestClient):
        """
        GIVEN id = "invalid" (not a valid integer)
        WHEN  DELETE /api/v1/articles/invalid is called
        THEN  the response status code is 422 Unprocessable Entity
        """
        response = client.delete("/api/v1/articles/invalid")

        assert response.status_code == 422
