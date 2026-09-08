"""
Utility functions for sending notifications.
"""
from django .utils import timezone 
from apps .notifications .models import Notification ,NotificationPreference 
from apps .audit .utils import log_security_event 


def send_notification (
recipient ,
notification_type ,
title ,
message ,
sender =None ,
priority ='MEDIUM',
data =None ,
related_object_type ='',
related_object_id ='',
send_email =True ,
):
    """
    Send a notification to a user.

    Args:
        recipient: User object
        notification_type: Notification.Type value
        title: Notification title
        message: Notification message
        sender: Optional sender User object
        priority: Notification.Priority value
        data: Dict with additional data
        related_object_type: Type of related object (e.g., 'channel')
        related_object_id: UUID of related object
        send_email: Whether to send email (default True, respects preferences)
    """
    # Check user preferences
    prefs =getattr (recipient ,'notification_preferences',None )

    # Create notification
    notification =Notification .objects .create (
    recipient =recipient ,
    sender =sender ,
    notification_type =notification_type ,
    priority =priority ,
    title =title ,
    message =message ,
    data =data or {},
    related_object_type =related_object_type ,
    related_object_id =related_object_id ,
    )

    # Check if email should be sent
    if send_email and prefs :
        if notification_type ==Notification .Type .SECURITY_ALERT :
            send_email =prefs .email_security_alerts 
        elif notification_type in [
        Notification .Type .CHANNEL_INVITATION ,
        Notification .Type .CHANNEL_UPDATE ,
        Notification .Type .CHANNEL_CLOSED ,
        ]:
            send_email =prefs .email_channel_updates 
        elif notification_type ==Notification .Type .NEW_MEDICAL_RECORD :
            send_email =prefs .email_medical_records 

            # Check quiet hours
        if prefs .quiet_hours_start and prefs .quiet_hours_end :
            now =timezone .now ().time ()
            if prefs .quiet_hours_start <=now <=prefs .quiet_hours_end :
                send_email =False # Don't send during quiet hours

    if send_email :
    # Real email delivery via the central email service (branded HTML,
    # SMTP in production / .eml files in dev). Fail-safe: delivery
    # problems are logged and reflected on the notification record.
        from utils .email_service import send_notification_email 
        try :
            delivered =send_notification_email (recipient ,notification )
        except Exception :# extra safety — never break the caller
            delivered =False 
        notification .is_email_sent =delivered 
        notification .email_sent_at =timezone .now ()if delivered else None 
        notification .save (update_fields =['is_email_sent','email_sent_at'])

    _dispatch_push (notification ,prefs )
    _dispatch_telegram_for_critical (notification )

    return notification 


def _dispatch_push (notification ,prefs ):
    """Best-effort FCM delivery for HIGH/CRITICAL notifications.

    CRITICAL always pushes; HIGH pushes except during the recipient's quiet
    hours (a phone vibrating at 3am for a routine channel update is exactly
    what quiet hours exist to prevent). Everything is guarded: a push outage
    must never fail the caller that created the notification.
    """
    try :
        if notification .priority not in ('HIGH','CRITICAL'):
            return 
        in_quiet_hours =(
        prefs .quiet_hours_start and prefs .quiet_hours_end 
        and prefs .quiet_hours_start <=timezone .now ().time ()<=prefs .quiet_hours_end 
        )
        if notification .priority =='HIGH'and in_quiet_hours :
            return 
        from apps .notifications .push import send_push_to_user 
        send_push_to_user (
        notification .recipient ,
        notification .title ,
        notification .message ,
        data ={
        'notification_id':str (notification .id ),
        'notification_type':notification .notification_type ,
        'priority':notification .priority ,
        },
        )
    except Exception :
        pass 


def _dispatch_telegram_for_critical (notification ):
    """Mirror CRITICAL notifications into the admin Telegram chat.

    Push reaches a phone that still has the app; Telegram reaches the admin
    channel even when nothing else is up. Guarded and silent on failure.
    """
    try :
        if notification .priority !='CRITICAL':
            return 
        from apps .security .telegram_service import send_critical_alert 
        send_critical_alert (
        notification .title ,
        [
        f"<b>الرسالة:</b> {notification .message }",
        f"<b>المستلم:</b> {notification .recipient .email }",
        ],
        )
    except Exception :
        pass 


def notify_channel_members (channel ,notification_type ,title ,message ,sender =None ,
exclude_sender =True ,**kwargs ):
    """
    Send notification to all members of a channel.
    """
    from apps .channels .models import ChannelMembership 
    notifications =[]

    memberships =channel .memberships .filter (is_active =True )
    if exclude_sender and sender :
        memberships =memberships .exclude (user =sender )

    for membership in memberships :
        notif =send_notification (
        recipient =membership .user ,
        notification_type =notification_type ,
        title =title ,
        message =message ,
        sender =sender ,
        data ={
        'channel_id':str (channel .id ),
        'channel_name':channel .name ,
        **kwargs .get ('data',{}),
        },
        related_object_type ='channel',
        related_object_id =str (channel .id ),
        priority =kwargs .get ('priority','MEDIUM'),
        )
        notifications .append (notif )

    return notifications 
