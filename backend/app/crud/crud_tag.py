"""
B25 - Tag Repository (CRUD)
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 2 (Data Access)

Implements all data-access operations for the `Tag` entity.

Key responsibilities
--------------------
* Look up tags by id, name, or slug (used when assigning tags to articles).
* Create new tags if they don't already exist.
* Retrieve all tags for admin/autocomplete endpoints.
* Resolve a mixed list of tag names → Tag ORM instances, creating any
  tags that are not yet in the database (upsert-style helper used by the
  Article repository's create/update path).

Design principles
-----------------
Same session-passed-in, never-commit philosophy as ArticleRepository.
"""

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import Tag


class TagRepository:
    """
    Stateless repository for Tag CRUD operations.
    """

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get(self, db: Session, tag_id: int) -> Optional[Tag]:
        """
        Fetch a single Tag by primary key.

        Returns None if no tag with the given id exists.
        """
        stmt = select(Tag).where(Tag.id == tag_id)
        return db.scalars(stmt).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Tag]:
        """
        Fetch a Tag by its human-readable name (case-sensitive).

        Used to check for duplicates before creating a new tag, and to
        resolve tag names supplied in article create/update payloads.

        Returns None if the name does not exist.
        """
        stmt = select(Tag).where(Tag.name == name)
        return db.scalars(stmt).first()

    def get_by_slug(self, db: Session, slug: str) -> Optional[Tag]:
        """
        Fetch a Tag by its URL-safe slug.

        Returns None if the slug does not exist.
        """
        stmt = select(Tag).where(Tag.slug == slug)
        return db.scalars(stmt).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Tag]:
        """
        Return a paginated list of all tags ordered alphabetically by name.

        Used for admin tag management and autocomplete suggestions.

        Parameters
        ----------
        skip  : Pagination offset (OFFSET).
        limit : Page size (LIMIT), capped at 200.
        """
        limit = min(limit, 200)
        stmt = (
            select(Tag)
            .order_by(Tag.name.asc())
            .offset(skip)
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def get_by_ids(self, db: Session, tag_ids: List[int]) -> Sequence[Tag]:
        """
        Fetch multiple tags by a list of primary keys in a single query.

        Used by the Article repository's create/update path when the API
        caller supplies tag IDs directly.

        Returns only the tags that actually exist; silently ignores
        non-existent IDs (the route handler should validate completeness
        if strict validation is required).
        """
        if not tag_ids:
            return []
        stmt = select(Tag).where(Tag.id.in_(tag_ids))
        return db.scalars(stmt).all()

    def get_by_names(self, db: Session, names: List[str]) -> Sequence[Tag]:
        """
        Fetch multiple tags by a list of names in a single query.

        Used as the first step of `get_or_create_many` to batch-fetch
        existing tags and determine which ones need to be inserted.
        """
        if not names:
            return []
        stmt = select(Tag).where(Tag.name.in_(names))
        return db.scalars(stmt).all()

    def name_exists(self, db: Session, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check whether a tag name is already taken.

        `exclude_id` allows the current tag's own name to be excluded
        during an update so unchanged names don't report false conflicts.

        Returns True if the name is taken, False otherwise.
        """
        stmt = select(Tag.id).where(Tag.name == name)
        if exclude_id is not None:
            stmt = stmt.where(Tag.id != exclude_id)
        return db.execute(stmt).first() is not None

    def slug_exists(self, db: Session, slug: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check whether a tag slug is already taken.

        Same exclude_id pattern as `name_exists` for update idempotency.

        Returns True if the slug is taken, False otherwise.
        """
        stmt = select(Tag.id).where(Tag.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Tag.id != exclude_id)
        return db.execute(stmt).first() is not None

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(self, db: Session, *, name: str, slug: str) -> Tag:
        """
        Persist a new Tag to the database.

        Parameters
        ----------
        name : Human-readable tag label. Must be unique (caller should
               check `name_exists` first or rely on the DB constraint).
        slug : URL-safe identifier. Must be unique.

        The tag is flushed (DB assigns `id`, `created_at`) but NOT committed.
        The caller commits.

        Returns the flushed Tag instance with `id` populated.
        """
        tag = Tag(name=name, slug=slug)
        db.add(tag)
        db.flush()
        db.refresh(tag)
        return tag

    # ------------------------------------------------------------------
    # GET-OR-CREATE  (most important helper for article tag management)
    # ------------------------------------------------------------------

    def get_or_create(self, db: Session, *, name: str, slug: str) -> tuple[Tag, bool]:
        """
        Return an existing Tag that matches `name`, or create a new one.

        Returns
        -------
        (tag, created)
            tag     : The Tag ORM instance (existing or newly created).
            created : True if the tag was just created, False if it existed.

        This is the safest single-tag upsert primitive – the route handler
        can decide whether to surface the `created` flag in the response.
        """
        existing = self.get_by_name(db, name)
        if existing is not None:
            return existing, False

        new_tag = self.create(db, name=name, slug=slug)
        return new_tag, True

    def get_or_create_many(
        self,
        db: Session,
        tag_inputs: List[dict],
    ) -> List[Tag]:
        """
        Resolve a list of tag payloads to Tag ORM instances, creating any
        tags that do not yet exist – all in as few queries as possible.

        Parameters
        ----------
        tag_inputs : List of dicts, each with keys:
                     - "name" (str, required)
                     - "slug" (str, required)

        Query strategy
        --------------
        1. One batch SELECT to fetch all tags whose names are in the input.
        2. For each name NOT found, one INSERT (via `create`).
        This means at most  1 + N_new  queries regardless of list size,
        instead of N individual get-or-create calls.

        Returns a list of Tag instances in the same order as `tag_inputs`.
        """
        if not tag_inputs:
            return []

        # Step 1: Batch-fetch all existing tags by name.
        names = [t["name"] for t in tag_inputs]
        existing_tags = {tag.name: tag for tag in self.get_by_names(db, names)}

        result: List[Tag] = []
        for payload in tag_inputs:
            name = payload["name"]
            slug = payload["slug"]
            if name in existing_tags:
                result.append(existing_tags[name])
            else:
                new_tag = self.create(db, name=name, slug=slug)
                existing_tags[name] = new_tag   # Prevent duplicate inserts
                result.append(new_tag)           # within the same call.

        return result

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, db: Session, *, tag: Tag) -> None:
        """
        Delete a Tag.

        The `ondelete="CASCADE"` on `article_tags.tag_id` ensures all
        join-table rows referencing this tag are removed automatically by
        the database – no manual cleanup needed.

        Flushed but NOT committed. The caller commits.
        """
        db.delete(tag)
        db.flush()
