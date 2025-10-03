# Publisher Feature Documentation

## Overview
This feature adds publisher management capabilities to Neo Bloggy:

- All new registered users get a `publisher=False` flag by default
- All new registered users can write a blog right away even with `publisher=False`
- Blogs from non-publishers won't show on the homepage or search page until the user is marked as a publisher
- Admins can toggle the publisher flag on any user
- Admins can see all unpublished blogs with indicators showing the author's publisher status

## Implementation Details

### Database Changes
- Added `is_publisher` field to user documents, defaulting to `False`

### Routes Added
- `/admin/toggle_publisher/<user_id>` - POST route to toggle publisher status
- `/admin/unpublished-posts` - View all posts from non-publisher users

### Templates Modified
- `admin.html` - Added publisher toggle buttons and unpublished posts link
- `unpublished_posts.html` - New template to display unpublished posts
- `post.html` - Added indicator for non-publisher posts (visible to admins)
- `profile.html` - Added publisher status badge

## Usage

### For Admins
1. Navigate to the Admin Panel
2. Use the "Publish" or "Unpublish" buttons next to users to toggle their publisher status
3. Access "Unpublished Posts" section to view posts from non-publisher users

### For Users
1. New users can register and immediately start writing blogs
2. Their blogs will only appear on the main site once they are approved as publishers