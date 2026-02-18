"""Business logic services for Neo Bloggy application."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from flask import (
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from neo_bloggy.auth import get_current_user
from neo_bloggy.caching import (
    POSTS_CACHE_VERSION_KEY,
    cache_storage,
    get_posts_cache_version,
)
from neo_bloggy.caching.cache_impl import (
    FileCache,
    delete_cache_key,
    get_cache_instance,
    get_cache_key,
)
from neo_bloggy.config import (
    CACHE_ENABLED,
    CACHE_TIMEOUT,
    MAX_POSTS_PER_PAGE,
    POSTS_PER_PAGE,
    config,
)
from neo_bloggy.database import (
    get_active_users,
    get_id_for_query,
    get_publisher_users,
)
from neo_bloggy.forms import CommentForm, CreatePostForm
from neo_bloggy.models import Comment, Post, User

logger = logging.getLogger(__name__)


class PostService:
    """Service class for post-related operations."""

    @staticmethod
    def _process_tags(tags_string: str) -> List[str]:
        """Process tags string into a clean list of tags."""
        if not tags_string:
            return []
        return [tag.strip() for tag in tags_string.split(",") if tag.strip()]

    @staticmethod
    def _build_pagination(
        page: int, per_page: int, total: int
    ) -> Dict[str, Any]:
        """Build pagination dictionary."""
        total_pages = (total + per_page - 1) // per_page
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    @staticmethod
    def _apply_cache_headers(
        response, cache: bool = True, prevent_cache: bool = False
    ):
        """Apply appropriate cache headers to response."""
        if prevent_cache:
            response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif cache:
            response.headers["Cache-Control"] = "public, max_age=300"
        return response

    @staticmethod
    def get_all_posts(page=1, per_page=POSTS_PER_PAGE):
        """Get all blog posts with pagination."""
        current_user = get_current_user()
        per_page = min(per_page, MAX_POSTS_PER_PAGE)
        cache = get_cache_instance(config, cache_timeout=CACHE_TIMEOUT)

        # Serve cached content for anonymous users
        if CACHE_ENABLED and not current_user:
            return PostService._get_cached_posts(
                page, per_page, current_user, cache
            )

        # Serve fresh content for logged-in users
        return PostService._get_fresh_posts(page, per_page, current_user)

    @staticmethod
    def _get_cached_posts(page, per_page, current_user, cache):
        """Get posts from cache or generate and cache them."""
        cache_version = get_posts_cache_version()
        cache_key_str = get_cache_key(
            f"get_all_posts_v{cache_version}_page_{page}_per_page_{per_page}"
        )
        current_time = time.time()

        # Check cache
        if isinstance(cache, FileCache):
            cached_result = cache.get(cache_key_str)
            if cached_result is not None:
                response = make_response(cached_result)
                return PostService._apply_cache_headers(response)
        elif cache_key_str in cache:
            result, timestamp = cache[cache_key_str]
            if current_time - timestamp < CACHE_TIMEOUT:
                response = make_response(result)
                return PostService._apply_cache_headers(response)

        # Generate and cache result
        from neo_bloggy.database import get_db

        db = get_db()
        publisher_users = get_publisher_users(db)
        skip = (page - 1) * per_page

        # Exclude drafts from public view
        posts = Post.find_many(
            {
                "author": {"$in": publisher_users},
                "status": {"$ne": Post.STATUS_DRAFT},
            },
            sort=("datetime", -1),
        )[skip : skip + per_page]
        total_posts = Post.count_documents(
            {
                "author": {"$in": publisher_users},
                "status": {"$ne": Post.STATUS_DRAFT},
            }
        )

        result = render_template(
            "index.html",
            all_posts=posts,
            pagination=PostService._build_pagination(
                page, per_page, total_posts
            ),
        )

        # Store in cache
        if isinstance(cache, FileCache):
            cache.set(cache_key_str, result)
        else:
            cache[cache_key_str] = (result, current_time)

        response = make_response(result)
        return PostService._apply_cache_headers(response)

    @staticmethod
    def _get_fresh_posts(page, per_page, current_user):
        """Get posts directly from database for logged-in users."""
        from neo_bloggy.database import get_db

        db = get_db()

        # Determine query based on user role
        if current_user and current_user.get("is_admin", False):
            # Admins see all posts (including drafts)
            query = {}
        else:
            active_users = get_active_users(db)
            # Exclude drafts from non-admin users
            query = {
                "author": {"$in": active_users},
                "status": {"$ne": Post.STATUS_DRAFT},
            }

        skip = (page - 1) * per_page
        posts = Post.find_many(query, sort=("datetime", -1))[
            skip : skip + per_page
        ]
        total_posts = Post.count_documents(query)

        response = make_response(
            render_template(
                "index.html",
                all_posts=posts,
                user=current_user,
                pagination=PostService._build_pagination(
                    page, per_page, total_posts
                ),
            )
        )

        # Prevent caching for logged-in users
        if current_user:
            return PostService._apply_cache_headers(
                response, prevent_cache=True
            )
        return response

    @staticmethod
    def create_post(current_user):
        """Create a new post."""
        form = CreatePostForm()
        if not form.validate_on_submit():
            return render_template("create_post.html", form=form)

        try:
            # Determine if saving as draft or publishing
            is_draft = form.save_draft.data

            # For published posts, img_url is required
            if not is_draft and not form.img_url.data:
                flash("Image URL is required for published posts.")
                return render_template("create_post.html", form=form)

            new_post = {
                "title": form.title.data,
                "subtitle": form.subtitle.data,
                "body": form.body.data,
                "img_url": form.img_url.data,
                "author": current_user["name"],
                "datetime": datetime.now().isoformat(),
                "tags": PostService._process_tags(form.tags.data),
                "status": (
                    Post.STATUS_DRAFT if is_draft else Post.STATUS_PUBLISHED
                ),
            }
            Post.create_post(new_post)

            if is_draft:
                flash("Draft saved successfully.")
            else:
                flash("Post Successfully Added")

            if CACHE_ENABLED:
                CacheService.increment_posts_cache_version()

            if is_draft:
                return redirect(
                    url_for("auth.profile", username=current_user["name"])
                )
            return redirect(url_for("posts.get_all_posts"))
        except Exception as err:
            flash(f"Failed to create post: {err}")
            return render_template("create_post.html", form=form)

    @staticmethod
    def edit_post(current_user, post_id):
        """Edit a post."""
        try:
            post = Post.find_one({"_id": post_id})
            if not post:
                flash("Post not found.")
                return redirect(url_for("posts.get_all_posts"))

            # Check authorization
            is_admin = current_user.get("is_admin", False)
            is_author = post["author"] == current_user["name"]

            if not is_admin and not is_author:
                flash("You can only edit your own posts.")
                return redirect(url_for("posts.get_all_posts"))

            if not is_admin and not current_user.get("is_active", True):
                flash("Your account has been disabled. You cannot edit posts.")
                return redirect(url_for("posts.get_all_posts"))

            # Populate form
            edit_form = CreatePostForm(
                title=post["title"],
                subtitle=post["subtitle"],
                img_url=post["img_url"],
                author=current_user["name"],
                body=post["body"],
                tags=", ".join(post.get("tags", [])),
            )

            if not edit_form.validate_on_submit():
                return render_template(
                    "create_post.html", form=edit_form, is_edit=True, post=post
                )

            # Determine if saving as draft or publishing
            is_draft = edit_form.save_draft.data

            # For published posts, img_url is required
            if not is_draft and not edit_form.img_url.data:
                flash("Image URL is required for published posts.")
                return render_template(
                    "create_post.html", form=edit_form, is_edit=True, post=post
                )

            # Update post
            update_data = {
                "title": edit_form.title.data,
                "subtitle": edit_form.subtitle.data,
                "img_url": edit_form.img_url.data,
                "body": edit_form.body.data,
                "tags": PostService._process_tags(edit_form.tags.data),
                "status": (
                    Post.STATUS_DRAFT
                    if is_draft
                    else post.get("status", Post.STATUS_PUBLISHED)
                ),
            }
            Post.update_post(post_id, update_data)

            # Clear cache
            if CACHE_ENABLED:
                cache_key = get_cache_key("get_post_with_comments", post_id)
                delete_cache_key(cache_storage, cache_key)
                if not is_draft:
                    CacheService.increment_posts_cache_version()

            if is_draft:
                flash("Draft updated successfully.")
                return redirect(
                    url_for("auth.profile", username=current_user["name"])
                )

            flash("Post Successfully Updated")
            return redirect(url_for("posts.show_post", post_id=post_id))

        except Exception as err:
            flash(f"Failed to edit post: {err}")
            return redirect(url_for("posts.get_all_posts"))

    @staticmethod
    def delete_post(current_user, post_id):
        """Delete a post."""
        try:
            post = Post.find_one({"_id": post_id})
            if not post:
                flash("Post not found.")
                return redirect(url_for("posts.get_all_posts"))

            # Check authorization
            is_admin = current_user.get("is_admin", False)
            is_author = post["author"] == current_user["name"]

            if not is_admin and not is_author:
                flash("You can only delete your own posts.")
                return redirect(url_for("posts.get_all_posts"))

            if not is_admin and not current_user.get("is_active", True):
                flash(
                    "Your account has been disabled. You cannot delete posts."
                )
                return redirect(url_for("posts.get_all_posts"))

            Post.delete_post(post_id)
            flash("Post Successfully Deleted")

            # Clear cache since we've deleted a post
            if CACHE_ENABLED:
                # Clear cache for this specific post
                cache_key = get_cache_key("get_post_with_comments", post_id)
                delete_cache_key(cache_storage, cache_key)
                # Also increment cache version to invalidate all paginated main posts list caches
                CacheService.increment_posts_cache_version()

            return redirect(url_for("posts.get_all_posts"))
        except Exception as e:
            flash(f"Failed to delete post: {str(e)}")
            return redirect(url_for("posts.get_all_posts"))

    @staticmethod
    def delete_draft(current_user, post_id):
        """Delete a draft post."""
        try:
            post = Post.find_one({"_id": post_id})
            if not post:
                flash("Draft not found.")
                return redirect(
                    url_for("auth.profile", username=current_user["name"])
                )

            # Check authorization - only author can delete their own drafts
            is_author = post["author"] == current_user["name"]
            is_admin = current_user.get("is_admin", False)

            if not is_admin and not is_author:
                flash("You can only delete your own drafts.")
                return redirect(
                    url_for("auth.profile", username=current_user["name"])
                )

            # Verify it's actually a draft
            if post.get("status") != Post.STATUS_DRAFT:
                flash("This is not a draft post.")
                return redirect(
                    url_for("auth.profile", username=current_user["name"])
                )

            Post.delete_post(post_id)
            flash("Draft deleted successfully.")

            return redirect(
                url_for("auth.profile", username=current_user["name"])
            )
        except Exception as e:
            flash(f"Failed to delete draft: {str(e)}")
            return redirect(
                url_for("auth.profile", username=current_user["name"])
            )

    @staticmethod
    def posts_by_tag(tag):
        """Get posts by tag."""
        current_user = get_current_user()
        from neo_bloggy.database import get_db

        db = get_db()

        # Build the search filter based on user status, excluding drafts
        tag_filter = {
            "tags": {"$elemMatch": tag},
            "status": {"$ne": Post.STATUS_DRAFT},
        }

        if current_user:
            if current_user.get("is_admin", False):
                # Admins can see all posts by tag (including drafts)
                search_filter = {"tags": {"$elemMatch": tag}}
            else:
                # Regular logged-in users can see posts from active users by tag
                active_users = get_active_users(db)
                search_filter = {
                    "$and": [tag_filter, {"author": {"$in": active_users}}]
                }
        else:
            # Anonymous users can only see posts from publisher users
            publisher_users = get_publisher_users(db)
            search_filter = {
                "$and": [tag_filter, {"author": {"$in": publisher_users}}]
            }

        # Find posts with the specified tag
        posts = Post.find_many(search_filter, sort=("datetime", -1))

        # Also get related tags for this tag to show related tags
        all_posts_with_tag = Post.find_many(
            search_filter, sort=("datetime", -1)
        )
        all_tags = set()
        for post in all_posts_with_tag:
            for post_tag in post.get("tags", []):
                if (
                    post_tag and post_tag.lower() != tag.lower()
                ):  # Exclude the current tag
                    all_tags.add(post_tag)

        related_tags = sorted(list(all_tags))[:10]  # Limit to 10 related tags

        response = make_response(
            render_template(
                "index.html",
                all_posts=posts,
                search_query=f"tag: {tag}",
                user=current_user,
                tag=tag,
                related_tags=related_tags,
            )
        )
        # Don't cache tag results as they may change frequently
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


class CommentService:
    """Service class for comment-related operations."""

    @staticmethod
    def show_post(post_id):
        """Show a post with its comments."""
        try:
            form = CommentForm()
            current_user = get_current_user()

            # For GET requests, we can use caching
            if request.method == "GET":
                from neo_bloggy.posts.helpers import get_post_with_comments

                requested_post, requested_post_comments = (
                    get_post_with_comments(post_id)
                )
            else:
                # For POST requests (comments), we need fresh data
                requested_post = Post.find_one({"_id": post_id})
                requested_post_comments = Comment.find_by_post_id(post_id)

            # Handle case where post is not found
            if not requested_post:
                flash("Post not found.")
                return redirect(url_for("posts.get_all_posts"))

            # Check if the post author is active (except for admins)
            post_author = User.find_by_name(requested_post["author"])
            if not post_author:
                flash("The requested post is not available.")
                return redirect(url_for("posts.get_all_posts"))

            # Non-admin users cannot view posts from inactive users
            is_admin = current_user and current_user.get("is_admin", False)
            if not is_admin and not post_author.get("is_active", True):
                flash("The requested post is not available.")
                return redirect(url_for("posts.get_all_posts"))

            # For anonymous users or non-admin users, check if the post author is a publisher
            # Non-publisher posts should only be visible to the author and admins
            if not is_admin and not post_author.get("is_publisher"):
                # Only the author of the post or admins can view non-publisher posts
                if (
                    not current_user
                    or current_user.get("name") != requested_post["author"]
                ):
                    flash("The requested post is not available.")
                    return redirect(url_for("posts.get_all_posts"))

            # Filter comments to only show those from active users
            from neo_bloggy.database import get_db

            db = get_db()
            active_users = get_active_users(db)
            if hasattr(requested_post_comments, "__iter__"):
                requested_post_comments = (
                    CommentService.filter_active_user_content(
                        requested_post_comments, active_users, "comment_author"
                    )
                )
            else:
                # If it's a cursor, convert to list and filter
                requested_post_comments = (
                    CommentService.filter_active_user_content(
                        list(requested_post_comments),
                        active_users,
                        "comment_author",
                    )
                )

            # commenting on a post
            if form.validate_on_submit():
                current_user = get_current_user()
                if not current_user:
                    flash("You need to login or register to comment.")
                    return redirect(url_for("auth.login"))

                new_comment = {
                    "text": form.comment_text.data,
                    "comment_author": current_user["name"],
                    "parent_post": get_id_for_query(post_id),
                    "datetime": datetime.now().isoformat(),
                }

                Comment.create_comment(new_comment)

                # Clear cache for this post since we've added a comment
                if CACHE_ENABLED:
                    cache_key = get_cache_key("get_post_with_comments", post_id)
                    delete_cache_key(cache_storage, cache_key)

                flash("Comment added successfully!")
                return redirect(url_for("posts.show_post", post_id=post_id))

            # Get author information to check if author is a publisher
            post_author_info = User.find_by_name(requested_post["author"])

            return render_template(
                "post.html",
                post=requested_post,
                comments=requested_post_comments,
                form=form,
                post_author_info=post_author_info,
                user=current_user,
            )
        except Exception as e:
            flash(f"Error loading post: {str(e)}")
            return redirect(url_for("posts.get_all_posts"))

    @staticmethod
    def filter_active_user_content(
        content_list, active_users, author_field="comment_author"
    ):
        """Filter content to only include items from active users."""
        return [
            item for item in content_list if item[author_field] in active_users
        ]

    @staticmethod
    def delete_comment(current_user, comment_id):
        """Delete a comment."""
        comment = Comment.find_one({"_id": comment_id})
        if not comment:
            flash("Comment not found.")
            post_id = request.args.get("post_id")
            return redirect(url_for("posts.show_post", post_id=post_id))

        # Check if user is admin or the comment author
        is_admin = current_user.get("is_admin", False)
        is_comment_author = comment["comment_author"] == current_user["name"]

        # If user is not admin and not the comment author, deny access
        if not is_admin and not is_comment_author:
            flash("You can only delete your own comments.")
            post_id = request.args.get("post_id")
            return redirect(url_for("posts.show_post", post_id=post_id))

        # If user is not admin but is the comment author, check if they're active
        if not is_admin and is_comment_author:
            if not current_user.get("is_active", True):
                flash(
                    "Your account has been disabled. You cannot delete comments."
                )
                post_id = request.args.get("post_id")
                return redirect(url_for("posts.show_post", post_id=post_id))

        Comment.delete_comment(comment_id)
        flash("Comment Successfully Deleted")
        post_id = request.args.get("post_id")

        # Clear cache for this post since we've deleted a comment
        if CACHE_ENABLED:
            cache_key = get_cache_key("get_post_with_comments", post_id)
            delete_cache_key(cache_storage, cache_key)

        return redirect(url_for("posts.show_post", post_id=post_id))


class UserService:
    """Service class for user-related operations."""

    @staticmethod
    def ensure_first_admin_is_publisher():
        """Ensure that if there's only one admin user in the system, they also have publisher status."""
        admin_users = User.find_admin_users()

        # If there's only one admin user, make sure they're also a publisher
        if len(admin_users) == 1:
            admin_user = admin_users[0]
            if not admin_user.get("is_publisher", False):
                # Update the admin user to also be a publisher
                try:
                    User.update_user_publisher_status(admin_user["_id"], True)
                    logger.info(
                        "Updated admin user '%s' to also have publisher status.",
                        admin_user["name"],
                    )
                except Exception as e:
                    logger.error(
                        "Failed to update admin user to publisher: %s", e
                    )


class CacheService:
    """Service class for cache-related operations."""

    @staticmethod
    def increment_posts_cache_version():
        """Increment the posts cache version in storage to invalidate all post-related caches."""
        if not CACHE_ENABLED:
            return
        from neo_bloggy.caching.cache_impl import FileCache

        current_version = get_posts_cache_version()
        new_version = current_version + 1

        cache_storage = get_cache_instance(config, cache_timeout=CACHE_TIMEOUT)
        if isinstance(cache_storage, FileCache):
            cache_storage.set(POSTS_CACHE_VERSION_KEY, new_version)
        else:
            # In-memory cache fallback
            cache_storage[POSTS_CACHE_VERSION_KEY] = (new_version, time.time())

    @staticmethod
    def get_posts_cache_version():
        """Get the current posts cache version from storage."""
        if not CACHE_ENABLED:
            return 0
        from neo_bloggy.caching.cache_impl import FileCache

        cache_storage = get_cache_instance(config, cache_timeout=CACHE_TIMEOUT)
        if isinstance(cache_storage, FileCache):
            version = cache_storage.get(POSTS_CACHE_VERSION_KEY)
            return version if version is not None else 0
        else:
            # In-memory cache fallback
            if POSTS_CACHE_VERSION_KEY in cache_storage:
                version, timestamp = cache_storage[POSTS_CACHE_VERSION_KEY]
                if time.time() - timestamp < CACHE_TIMEOUT:
                    return version
            return 0
