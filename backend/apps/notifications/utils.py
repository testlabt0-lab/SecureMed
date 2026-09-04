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
    # Comment_217
    prefs =getattr (recipient ,'notification_preferences',None )

    # Comment_218
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

    # Comment_219
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

            # Comment_220
        if prefs .quiet_hours_start and prefs .quiet_hours_end :
            now =timezone .now ().time ()
            if prefs .quiet_hours_start <=now <=prefs .quiet_hours_end :
                send_email =False # Comment_221

    if send_email :
    # Comment_222
    # Comment_223
    # Comment_224
        from utils .email_service import send_notification_email 
        try :
            delivered =send_notification_email (recipient ,notification )
        except Exception :# Comment_225
            delivered =False 
        notification .is_email_sent =delivered 
        notification .email_sent_at =timezone .now ()if delivered else None 
        notification .save (update_fields =['is_email_sent','email_sent_at'])

    return notification 


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
