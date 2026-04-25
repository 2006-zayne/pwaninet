# ============================================================================
# DEPRECATED - All views have been migrated to domain apps
# ============================================================================
#
# This file previously contained all Django views. Following domain-driven design
# principles, all views have been migrated to their respective domain apps:
#
# - users/views.py: register_view, profile_view, update_profile_view, toggle_follow, get_suggestions
# - posts/views.py: home_view, create_post_view, post_detail_view, add_comment, toggle_comment_like, toggle_like, post_likers_list, unit_posts_view, search_view
# - groups/views.py: groups_dashboard, groups_detail_view, create_group_view, toggle_group_membership, edit_group, invite_to_group, respond_to_invite
# - notifications/views.py: notifications_list, unread_notification_count, mark_notification_as_read, mark_all_as_read
# - courses/views.py: load_years
#
# The core app now only contains shared utilities (forms, signals, etc.)
# ============================================================================

