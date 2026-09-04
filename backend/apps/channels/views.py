"""
Views for channels app.

Implements:
- Security requirement #1: شروط الرؤية (only owner/member can view)
- Security requirement #2: منظومة الصلاحيات (grant, modify, revoke, remove)
"""
import logging 
from django .core .exceptions import PermissionDenied ,ValidationError 
from django .utils import timezone 
from django .utils .dateparse import parse_datetime 
from django .db import transaction 
from rest_framework import status ,viewsets ,permissions 
from rest_framework .decorators import action 
from rest_framework .response import Response 

from apps .channels .models import Channel ,ChannelMembership ,ChannelInvitation ,ChannelMessage 
from apps .channels .serializers import (
ChannelSerializer ,ChannelDetailSerializer ,
ChannelMembershipSerializer ,ChannelInvitationSerializer ,
ModifyRoleSerializer ,GrantPermissionSerializer ,RevokePermissionSerializer ,
ChannelMessageSerializer ,
)
from apps .security .permissions import IsAdmin 
from apps .audit .utils import log_security_event 
from apps .notifications .utils import send_notification 

logger =logging .getLogger ('security')


class ChannelViewSet (viewsets .ModelViewSet ):
    """
    Channel (Patient Case) ViewSet.

    Security:
    - Users can only see channels they own or are members of
    - Only channel owner or admin can manage (grant/revoke permissions)
    """

    queryset =Channel .objects .all ().order_by ('-created_at')

    def get_queryset (self ):
        """
        Security requirement #1: شروط الرؤية
        Only return channels the user can view (owner or member).
        Plus basin scoping (plan requirement: linkage by basin).
        """
        from django .db .models import Q 
        from apps .basins .utils import basin_scoped_queryset 
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            qs =Channel .objects .all ().order_by ('-created_at')
            return basin_scoped_queryset (qs ,user ,lookup ='basin_id')
        return Channel .objects .filter (
        Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
        ).distinct ().order_by ('-created_at')

    def get_serializer_class (self ):
        if self .action =='retrieve':
            return ChannelDetailSerializer 
        return ChannelSerializer 

    def list (self ,request ,*args ,**kwargs ):
        return super ().list (request ,*args ,**kwargs )

    def get_permissions (self ):
        if self .action in ['create','update','partial_update','destroy']:
            return [permissions .IsAuthenticated ()]
        return [permissions .IsAuthenticated ()]

    def perform_create (self ,serializer ):
        """Create channel - automatically set owner as the creator."""
        # Comment_186
        from apps .basins .utils import ensure_module_enabled ,basin_of 
        ensure_module_enabled (self .request .user ,'channels')

        # Comment_187
        basin =basin_of (self .request .user )
        if basin is None :
            patient =serializer .validated_data .get ('patient')
            basin =getattr (patient ,'basin',None )
        channel =serializer .save (owner =self .request .user ,basin =basin )
        # Comment_188
        ChannelMembership .objects .create (
        channel =channel ,
        user =self .request .user ,
        role =ChannelMembership .Role .OWNER ,
        granted_by =self .request .user ,
        )
        log_security_event (
        user =self .request .user ,
        event_type ='CHANNEL_CREATED',
        request =self .request ,
        details ={
        'channel_id':str (channel .id ),
        'channel_name':channel .name ,
        'basin':basin .name if basin else None ,
        }
        )

    def retrieve (self ,request ,*args ,**kwargs ):
        """Get channel detail - enforce visibility check."""
        channel =self .get_object ()
        if not channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بعرض هذه القناة')
        return super ().retrieve (request ,*args ,**kwargs )

    @action (detail =True ,methods =['get'])
    def members (self ,request ,pk =None ):
        """List all members of a channel (security requirement #1)."""
        channel =self .get_object ()
        if not channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بعرض أعضاء هذه القناة')

        memberships =channel .memberships .filter (is_active =True )
        serializer =ChannelMembershipSerializer (memberships ,many =True )
        return Response (serializer .data )

    @action (detail =True ,methods =['post'])
    def grant_permission (self ,request ,pk =None ):
        """
        Security requirement #2: منح صلاحية للقناة
        Grant a permission/role to a user in this channel.
        """
        channel =self .get_object ()
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة أو المدير يمكنه منح الصلاحيات')

        serializer =GrantPermissionSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )

        from apps .accounts .models import User 
        try :
            user =User .objects .get (email =serializer .validated_data ['user_email'])
        except User .DoesNotExist :
            return Response (
            {'detail':'المستخدم غير موجود'},
            status =status .HTTP_404_NOT_FOUND 
            )

            # Comment_189
        existing =ChannelMembership .objects .filter (
        channel =channel ,user =user ,is_active =True 
        ).first ()
        if existing :
            return Response (
            {'detail':f'المستخدم لديه بالفعل دور: {existing .get_role_display ()}'},
            status =status .HTTP_400_BAD_REQUEST 
            )

            # Comment_190
        membership ,created =ChannelMembership .objects .get_or_create (
        channel =channel ,user =user ,
        defaults ={
        'role':serializer .validated_data ['role'],
        'granted_by':request .user ,
        'notes':serializer .validated_data .get ('notes',''),
        'expires_at':serializer .validated_data .get ('expires_at'),
        'is_active':True ,
        }
        )
        if not created :
            membership .role =serializer .validated_data ['role']
            membership .granted_by =request .user 
            membership .is_active =True 
            membership .notes =serializer .validated_data .get ('notes','')
            membership .expires_at =serializer .validated_data .get ('expires_at')
            membership .save ()

        log_security_event (
        user =request .user ,
        event_type ='PERMISSION_GRANTED',
        request =request ,
        details ={
        'channel_id':str (channel .id ),
        'target_user':str (user .id ),
        'role':membership .role ,
        }
        )

        # Comment_191
        send_notification (
        recipient =user ,
        notification_type ='PERMISSION_GRANTED',
        title =f'تم منحك صلاحية في قناة {channel .name }',
        message =f'تم منحك دور {membership .get_role_display ()} في قناة "{channel .name }" بواسطة {request .user .full_name }',
        sender =request .user ,
        priority ='HIGH',
        data ={
        'channel_id':str (channel .id ),
        'channel_name':channel .name ,
        'role':membership .role ,
        },
        related_object_type ='channel',
        related_object_id =str (channel .id ),
        )

        return Response (
        ChannelMembershipSerializer (membership ).data ,
        status =status .HTTP_201_CREATED 
        )

    @action (detail =True ,methods =['post'])
    def modify_permission (self ,request ,pk =None ):
        """
        Security requirement #2: تعديل صلاحية عضو في قناة
        Modify an existing member's role.
        """
        channel =self .get_object ()
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة أو المدير يمكنه تعديل الصلاحيات')

        membership_id =request .data .get ('membership_id')
        try :
            membership =channel .memberships .get (id =membership_id )
        except ChannelMembership .DoesNotExist :
            return Response (
            {'detail':'العضوية غير موجودة'},
            status =status .HTTP_404_NOT_FOUND 
            )

        serializer =ModifyRoleSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )
        old_role =membership .role 
        membership .change_role (serializer .validated_data ['role'])
        membership .granted_by =request .user 
        membership .save ()

        log_security_event (
        user =request .user ,
        event_type ='PERMISSION_MODIFIED',
        request =request ,
        details ={
        'channel_id':str (channel .id ),
        'membership_id':str (membership .id ),
        'old_role':old_role ,
        'new_role':membership .role ,
        }
        )

        return Response (ChannelMembershipSerializer (membership ).data )

    @action (detail =True ,methods =['post'])
    def revoke_permission (self ,request ,pk =None ):
        """
        Security requirement #2: سحب الصلاحية
        Revoke a member's permission (deactivate but keep membership record).
        """
        channel =self .get_object ()
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة أو المدير يمكنه سحب الصلاحيات')

        membership_id =request .data .get ('membership_id')
        try :
            membership =channel .memberships .get (id =membership_id )
        except ChannelMembership .DoesNotExist :
            return Response (
            {'detail':'العضوية غير موجودة'},
            status =status .HTTP_404_NOT_FOUND 
            )

        if membership .role ==ChannelMembership .Role .OWNER :
            return Response (
            {'detail':'لا يمكن سحب صلاحية المالك'},
            status =status .HTTP_400_BAD_REQUEST 
            )

        membership .revoke ()
        log_security_event (
        user =request .user ,
        event_type ='PERMISSION_REVOKED',
        request =request ,
        details ={
        'channel_id':str (channel .id ),
        'membership_id':str (membership .id ),
        'reason':request .data .get ('reason',''),
        }
        )
        # Comment_192
        send_notification (
        recipient =membership .user ,
        notification_type ='PERMISSION_REVOKED',
        title =f'تم سحب صلاحيتك في قناة {channel .name }',
        message =f'تم سحب صلاحيتك في قناة "{channel .name }" بواسطة {request .user .full_name }',
        sender =request .user ,
        priority ='HIGH',
        data ={
        'channel_id':str (channel .id ),
        'channel_name':channel .name ,
        },
        related_object_type ='channel',
        related_object_id =str (channel .id ),
        )
        return Response ({'detail':'تم سحب الصلاحية'})

    @action (detail =True ,methods =['post'])
    def remove_member (self ,request ,pk =None ):
        """
        Security requirement #2: إلغاء العضوية
        Remove a member from the channel entirely.
        """
        channel =self .get_object ()
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة أو المدير يمكنه إزالة الأعضاء')

        membership_id =request .data .get ('membership_id')
        try :
            membership =channel .memberships .get (id =membership_id )
        except ChannelMembership .DoesNotExist :
            return Response (
            {'detail':'العضوية غير موجودة'},
            status =status .HTTP_404_NOT_FOUND 
            )

        if membership .role ==ChannelMembership .Role .OWNER :
            return Response (
            {'detail':'لا يمكن إزالة المالك'},
            status =status .HTTP_400_BAD_REQUEST 
            )

        user =membership .user 
        membership .delete ()

        log_security_event (
        user =request .user ,
        event_type ='MEMBERSHIP_CANCELLED',
        request =request ,
        details ={
        'channel_id':str (channel .id ),
        'removed_user':str (user .id ),
        'reason':request .data .get ('reason',''),
        }
        )

        return Response ({'detail':'تم إلغاء العضوية'})

    @action (detail =True ,methods =['get','post'])
    def messages (self ,request ,pk =None ):
        """
        In-channel secure chat (polling-based).
        GET  → list messages (optionally ?after=<iso> for incremental fetch)
        POST → send a new message (active members / owner / admins only)
        """
        channel =self .get_object ()
        if not channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بعرض محادثة هذه القناة')

        if request .method =='GET':
            qs =channel .messages .select_related ('sender').all ()
            after =request .query_params .get ('after')
            if after :
                parsed =parse_datetime (after )
                if parsed is not None :
                    if timezone .is_aware (parsed )is False :
                        parsed =timezone .make_aware (parsed )
                    qs =qs .filter (created_at__gt =parsed )
            limit =min (int (request .query_params .get ('limit',200 )or 200 ),500 )
            qs =qs .order_by ('-created_at')[:limit ]
            data =ChannelMessageSerializer (
            sorted (qs ,key =lambda m :m .created_at ),many =True 
            ).data 
            return Response (data )

            # Comment_193
        membership =channel .memberships .filter (
        user =request .user ,is_active =True 
        ).first ()
        is_admin =request .user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']
        if not is_admin and channel .owner_id !=request .user .id and membership is None :
            raise PermissionDenied ('فقط أعضاء القناة يمكنهم إرسال الرسائل')

        serializer =ChannelMessageSerializer (
        data =request .data ,context ={'request':request }
        )
        serializer .is_valid (raise_exception =True )
        message =serializer .save (channel =channel ,sender =request .user )

        log_security_event (
        user =request .user ,
        event_type ='CHANNEL_MESSAGE_SENT',
        request =request ,
        details ={'channel_id':str (channel .id ),'message_id':str (message .id )},
        )
        return Response (
        ChannelMessageSerializer (message ).data ,
        status =status .HTTP_201_CREATED ,
        )

    @action (detail =True ,methods =['post'])
    def close (self ,request ,pk =None ):
        """Close a channel."""
        channel =self .get_object ()
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة أو المدير يمكنه إغلاق القناة')

        channel .close ()
        log_security_event (
        user =request .user ,
        event_type ='CHANNEL_CLOSED',
        request =request ,
        details ={'channel_id':str (channel .id )}
        )
        return Response ({'detail':'تم إغلاق القناة'})


class ChannelInvitationViewSet (viewsets .ModelViewSet ):
    """Manage channel invitations."""

    serializer_class =ChannelInvitationSerializer 

    def get_queryset (self ):
        user =self .request .user 
        return ChannelInvitation .objects .filter (invitee =user ).order_by ('-created_at')

    def get_permissions (self ):
        if self .action in ['create']:
            return [permissions .IsAuthenticated ()]
        return [permissions .IsAuthenticated ()]

    def create (self ,request ,*args ,**kwargs ):
        """Create invitation - requires channel management permission."""
        serializer =self .get_serializer (data =request .data )
        serializer .is_valid (raise_exception =True )

        channel =serializer .validated_data ['channel']
        if not channel .can_manage (request .user ):
            raise PermissionDenied ('فقط مالك القناة يمكنه إرسال الدعوات')

        invitation =serializer .save ()
        log_security_event (
        user =request .user ,
        event_type ='INVITATION_SENT',
        request =request ,
        details ={
        'channel_id':str (channel .id ),
        'invitee':str (invitation .invitee .id ),
        }
        )
        return Response (
        ChannelInvitationSerializer (invitation ).data ,
        status =status .HTTP_201_CREATED 
        )

    @action (detail =True ,methods =['post'])
    def accept (self ,request ,pk =None ):
        """Accept an invitation."""
        invitation =self .get_object ()
        if invitation .invitee !=request .user :
            raise PermissionDenied ('غير مصرح لك بقبول هذه الدعوة')

        try :
            membership =invitation .accept ()
            log_security_event (
            user =request .user ,
            event_type ='INVITATION_ACCEPTED',
            request =request ,
            details ={
            'channel_id':str (invitation .channel .id ),
            'role':membership .role ,
            }
            )
            return Response ({
            'detail':'تم قبول الدعوة',
            'membership':ChannelMembershipSerializer (membership ).data 
            })
        except ValidationError as e :
            return Response (
            {'detail':str (e )},
            status =status .HTTP_400_BAD_REQUEST 
            )

    @action (detail =True ,methods =['post'])
    def reject (self ,request ,pk =None ):
        """Reject an invitation."""
        invitation =self .get_object ()
        if invitation .invitee !=request .user :
            raise PermissionDenied ('غير مصرح لك برفض هذه الدعوة')

        invitation .status =ChannelInvitation .Status .REJECTED 
        invitation .save ()
        log_security_event (
        user =request .user ,
        event_type ='INVITATION_REJECTED',
        request =request ,
        details ={'channel_id':str (invitation .channel .id )}
        )
        return Response ({'detail':'تم رفض الدعوة'})

