"""
Notification System Feature
--------------------------
Provides SMS notifications for system events like user signups and message receipts.
"""

from .code import notification_manager, NotificationManager, NotificationEvent

__all__ = ['notification_manager', 'NotificationManager', 'NotificationEvent']
