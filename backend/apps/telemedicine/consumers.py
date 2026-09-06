"""WebRTC signalling for telemedicine consultations.

The server relays SDP offers/answers and ICE candidates and never sees decrypted
media — the peer connection is established directly between the two browsers.

Authorisation is the part that was missing. There used to be two copies of this
consumer; the routed one carried the comment *"In a real app, verify if the user has
access to this room"* and did no check at all, so any authenticated account that
knew or guessed a ``room_id`` joined the group and received the live signalling
traffic of somebody else's consultation. Room membership is now resolved against the
same access rule the REST layer uses (``apps.core.mixins``), so the doctor on the
consultation and the patient's care team can join and nobody else can.
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('webrtc')

CLOSE_UNAUTHENTICATED = 4001
CLOSE_FORBIDDEN = 4003
CLOSE_ROOM_UNKNOWN = 4004

# Only these reach the other peer. An open relay would forward anything, which
# turns the signalling channel into an unaudited chat between any two members of a
# room — including file: and data: payloads the client would happily render.
SIGNAL_TYPES = {'offer', 'answer', 'candidate', 'bye'}


@database_sync_to_async
def _authorise(room_name, user):
    """Return the consultation id when ``user`` may join ``room_name``, else None."""
    from apps.core.mixins import accessible_patients
    from apps.patients.models import Patient
    from apps.telemedicine.models import Consultation

    consultation = (
        Consultation.objects
        .filter(room_id=room_name)
        .exclude(status__in=(Consultation.Status.COMPLETED, Consultation.Status.CANCELLED))
        .only('id', 'doctor_id', 'patient_id')
        .first()
    )
    if consultation is None:
        return None, False

    if consultation.doctor_id == user.id:
        return consultation.id, True

    # The patient side. There is no Patient.user column in this schema — a patient
    # account reaches its own record through channel membership — so the same
    # queryset rule that scopes the patient index decides it here too.
    permitted = accessible_patients(
        Patient.objects.filter(pk=consultation.patient_id), user
    ).exists()
    return consultation.id, permitted


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = None
        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        consultation_id, permitted = await _authorise(self.room_name, self.user)
        if consultation_id is None:
            # Same code for "no such room" and "already finished": telling the
            # caller which one it is confirms the existence of a consultation to
            # someone with no right to know it exists.
            await self.close(code=CLOSE_ROOM_UNKNOWN)
            return
        if not permitted:
            logger.warning(
                'ws video_call denied: user %s is not a participant of room %s',
                self.user.id, self.room_name,
            )
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.room_group_name = f'video_call_{self.room_name}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept(subprotocol=self.scope.get('ws_subprotocol'))

        # Tells the joiner whether anyone is already waiting, which is what decides
        # who creates the offer. Without it both peers offer simultaneously and the
        # negotiation collapses.
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'peer_event',
            'event': 'peer_joined',
            'user_id': str(self.user.id),
            'sender_channel_name': self.channel_name,
        })
        logger.info('user %s joined video call room %s', self.user.id, self.room_name)

    async def disconnect(self, close_code):
        if not self.room_group_name:
            return
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'peer_event',
            'event': 'peer_left',
            'user_id': str(self.user.id),
            'sender_channel_name': self.channel_name,
        })
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        if not self.room_group_name:
            return
        try:
            payload = json.loads(text_data)
        except (TypeError, ValueError):
            return
        if not isinstance(payload, dict):
            return

        signal_type = payload.get('type')
        if signal_type not in SIGNAL_TYPES:
            logger.info('dropped unknown signal %r in room %s', signal_type, self.room_name)
            return

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'webrtc_signal',
            'message': {
                'type': signal_type,
                'payload': payload.get('payload'),
                'from': str(self.user.id),
            },
            'sender_channel_name': self.channel_name,
        })

    async def webrtc_signal(self, event):
        if self.channel_name == event.get('sender_channel_name'):
            return
        await self.send(text_data=json.dumps(event['message']))

    async def peer_event(self, event):
        if self.channel_name == event.get('sender_channel_name'):
            return
        await self.send(text_data=json.dumps({
            'type': event['event'],
            'from': event['user_id'],
        }))
