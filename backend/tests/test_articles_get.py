"""
B28 - Backend Tests: Article Retrieval (GET /api/v1/articles/{id})
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 5 (Testing & Docs)

Tests the GET /api/v1/articles/{id} endpoint (B10) against the in-memory
SQLite database using the fixtures defined in conftest.py.

TEST COVERAGE
-------------
Happy path:
  ✅ 200 OK with full article body (id, title, slug, content, status, timestamps)
  ✅ Response structure matches ArticleResponseStub fields
  ✅ Tags list is present and empty for a tag-less article
  ✅ Category is None for an uncategorised article

Error paths:
  ✅ 404 Not Found for a non-existent article id
  ✅ Error response body matches the standard error envelope
  ✅ 422 Unprocessable Entity for an invalid (non-integer) id
  ✅ 422 Unprocessable Entity for id = 0 (violates ge=1 constraint)
"""

import pytest
from fastapi.testclient import TestClient

from app.models.article import ArticleStatus


# ---------------------------------------------------------------------------
# 200 OK — Happy path tests
# ---------------------------------------------------------------------------

class TestGetArticleSuccess:
    """Tests for successful article retrieval (HTTP 200)."""

    @pytest.mark.integration
    def test_get_existing_article_returns_200(self, client: TestClient, make_article):
        """
        GIVEN a published article exists in the database
        WHEN  GET /api/v1/articles/{id} is called with its id
        THEN  the response status code is 200 OK
        """
        article = make_article(title="SAP Password Reset", slug="sap-password-reset")

        response = client.get(f"/api/v1/articles/{article.id}")

        assert response.status_code == 200

    @pytest.mark.integration
    def test_get_article_response_contains_correct_id(self, client: TestClient, make_article):
        """
        GIVEN a published article exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body contains the correct article id
        """
        article = make_article(title="ServiceNow Onboarding", slug="servicenow-onboarding")

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["id"] == article.id

    @pytest.mark.integration
    def test_get_article_response_contains_correct_title(self, client: TestClient, make_article):
        """
        GIVEN a published article exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body contains the correct title
        """
        article = make_article(title="Apple MDM Enrollment", slug="apple-mdm-enrollment")

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["title"] == "Apple MDM Enrollment"

    @pytest.mark.integration
    def test_get_article_response_contains_correct_slug(self, client: TestClient, make_article):
        """
        GIVEN a published article with a specific slug
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body contains the exact slug
        """
        article = make_article(title="Test Slug Article", slug="test-slug-article-unique")

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["slug"] == "test-slug-article-unique"

    @pytest.mark.integration
    def test_get_article_response_contains_correct_status(self, client: TestClient, make_article):
        """
        GIVEN a DRAFT article exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body status field equals "draft"
        """
        article = make_article(
            title="Draft Article",
            slug="draft-article-status-test",
            status=ArticleStatus.DRAFT,
        )

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["status"] == "draft"

    @pytest.mark.integration
    def test_get_article_response_contains_timestamps(self, client: TestClient, make_article):
        """
        GIVEN an article exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body contains non-null created_at and updated_at fields
        """
        article = make_article(title="Timestamp Article", slug="timestamp-article-test")

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    @pytest.mark.integration
    def test_get_article_response_contains_empty_tags_list(self, client: TestClient, make_article):
        """
        GIVEN an article with no tags exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body has an empty tags list (not null/missing)
        """
        article = make_article(title="No Tags Article", slug="no-tags-article-test")

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert "tags" in data
        assert isinstance(data["tags"], list)
        assert len(data["tags"]) == 0

    @pytest.mark.integration
    def test_get_article_response_category_is_none_for_uncategorised(
        self, client: TestClient, make_article
    ):
        """
        GIVEN an uncategorised article (category_id is NULL) exists in the database
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body has category = null and category_id = null
        """
        article = make_article(
            title="Uncategorised Article",
            slug="uncategorised-article-test",
            category_id=None,
        )

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["category"] is None
        assert data["category_id"] is None

    @pytest.mark.integration
    def test_get_article_response_contains_content_field(self, client: TestClient, make_article):
        """
        GIVEN an article with specific content
        WHEN  GET /api/v1/articles/{id} is called
        THEN  the response body contains the full content string
        """
        content = "Step 1: Log in to SAP. Step 2: Navigate to settings."
        article = make_article(
            title="Content Check",
            slug="content-check-article",
            content=content,
        )

        response = client.get(f"/api/v1/articles/{article.id}")
        data = response.json()

        assert data["content"] == content


# ---------------------------------------------------------------------------
# 404 Not Found — Error path tests
# ---------------------------------------------------------------------------

class TestGetArticleNotFound:
    """Tests for the 404 Not Found error path."""

    @pytest.mark.integration
    def test_get_nonexistent_article_returns_404(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  GET /api/v1/articles/99999 is called
        THEN  the response status code is 404 Not Found
        """
        response = client.get("/api/v1/articles/99999")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_nonexistent_article_error_envelope_structure(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  GET /api/v1/articles/99999 is called
        THEN  the response body follows the standard error envelope:
              {"error": {"code": ..., "message": ..., "status": 404}}
        """
        response = client.get("/api/v1/articles/99999")
        data = response.json()

        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "status" in data["error"]

    @pytest.mark.integration
    def test_get_nonexistent_article_error_code_is_article_not_found(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  GET /api/v1/articles/99999 is called
        THEN  the error code in the response body is "ARTICLE_NOT_FOUND"
        """
        response = client.get("/api/v1/articles/99999")
        data = response.json()

        assert data["error"]["code"] == "ARTICLE_NOT_FOUND"

    @pytest.mark.integration
    def test_get_nonexistent_article_error_status_matches_http_status(self, client: TestClient):
        """
        GIVEN no article with id 99999 exists
        WHEN  GET /api/v1/articles/99999 is called
        THEN  the "status" field inside the error envelope equals 404
              (mirrors the HTTP status code for easy client handling)
        """
        response = client.get("/api/v1/articles/99999")
        data = response.json()

        assert data["error"]["status"] == 404

    @pytest.mark.integration
    def test_get_nonexistent_article_error_message_contains_id(self, client: TestClient):
        """
        GIVEN no article with id 12345 exists
        WHEN  GET /api/v1/articles/12345 is called
        THEN  the error message mentions the requested id so the client can
              display a meaningful error to the user
        """
        response = client.get("/api/v1/articles/12345")
        data = response.json()

        assert "12345" in data["error"]["message"]


# ---------------------------------------------------------------------------
# 422 Unprocessable Entity — Input validation tests
# ---------------------------------------------------------------------------

class TestGetArticleInputValidation:
    """Tests for FastAPI's path parameter validation (ge=1, type checks)."""

    @pytest.mark.integration
    def test_get_article_with_zero_id_returns_422(self, client: TestClient):
        """
        GIVEN id = 0 (violates ge=1 constraint in Path(..., ge=1))
        WHEN  GET /api/v1/articles/0 is called
        THEN  the response status code is 422 Unprocessable Entity
              (rejected by FastAPI's path validation before reaching the handler)
        """
        response = client.get("/api/v1/articles/0")

        assert response.status_code == 422

    @pytest.mark.integration
    def test_get_article_with_negative_id_returns_422(self, client: TestClient):
        """
        GIVEN id = -5 (also violates ge=1)
        WHEN  GET /api/v1/articles/-5 is called
        THEN  the response status code is 422 Unprocessable Entity
        """
        response = client.get("/api/v1/articles/-5")

        assert response.status_code == 422

    @pytest.mark.integration
    def test_get_article_with_string_id_returns_422(self, client: TestClient):
        """
        GIVEN id = "abc" (not a valid integer)
        WHEN  GET /api/v1/articles/abc is called
        THEN  the response status code is 422 Unprocessable Entity
        """
        response = client.get("/api/v1/articles/abc")

        assert response.status_code == 422
