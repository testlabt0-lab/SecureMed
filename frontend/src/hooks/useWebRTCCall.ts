import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '../store/authStore';

/**
 * The missing half of telemedicine.
 *
 * `Telemedicine.tsx` called `getUserMedia` and rendered the result, which looks
 * like a video call and is not one: there was no `RTCPeerConnection` anywhere in
 * the frontend and nothing ever opened the signalling socket, so the two parties
 * each watched their own camera. The backend consumer for
 * `ws/video_call/<room_id>/` existed the whole time.
 *
 * Who offers is decided by arrival order, which the server reports: the consumer
 * broadcasts `peer_joined` to everyone *already* in the room, so the receiver of
 * that event is by definition the earlier peer and creates the offer. Deciding it
 * client-side instead — on role, or on a coin flip — is what produces the classic
 * glare bug where both sides offer at once and neither call connects.
 *
 * Media never passes through the server: it relays SDP and ICE only, so the audio
 * and video go peer to peer and the backend cannot record a consultation.
 */

/** Close codes from apps/telemedicine/consumers.py. */
const CLOSE_UNAUTHENTICATED = 4001;
const CLOSE_FORBIDDEN = 4003;
const CLOSE_ROOM_UNKNOWN = 4004;

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

export type CallState =
  | 'idle'
  | 'connecting'
  | 'waiting'
  | 'negotiating'
  | 'connected'
  | 'reconnecting'
  | 'denied'
  | 'ended';

/**
 * STUN discovers the public address of each peer; TURN relays media when a
 * symmetric NAT or a corporate firewall blocks the direct path. A deployment with
 * no TURN server loses roughly one call in five, and hospital networks are the
 * worst case for it — so the URLs are configuration, not constants.
 */
function buildIceServers(): RTCIceServer[] {
  const env = import.meta.env as Record<string, string | undefined>;
  const stun = (env.VITE_STUN_URLS || 'stun:stun.l.google.com:19302')
    .split(',')
    .map((url) => url.trim())
    .filter(Boolean);

  const servers: RTCIceServer[] = stun.length ? [{ urls: stun }] : [];

  const turnUrls = (env.VITE_TURN_URLS || '').split(',').map((u) => u.trim()).filter(Boolean);
  if (turnUrls.length) {
    servers.push({
      urls: turnUrls,
      username: env.VITE_TURN_USERNAME,
      credential: env.VITE_TURN_CREDENTIAL,
    });
  }
  return servers;
}

export interface UseWebRTCCallOptions {
  /** `Consultation.room_id`. Null while no session is open. */
  roomId?: string | null;
  /** Local camera/mic stream, or null until the user grants permission. */
  localStream: MediaStream | null;
  /** False tears the call down — used when the session panel closes. */
  enabled: boolean;
}

export interface UseWebRTCCall {
  state: CallState;
  remoteStream: MediaStream | null;
  /** True once the remote description has been applied in both directions. */
  isConnected: boolean;
  /** Human-readable Arabic status for the call banner. */
  statusText: string;
  /** Swap the outgoing video track — screen share on, and back off again. */
  replaceVideoTrack: (track: MediaStreamTrack | null) => Promise<void>;
  /** Send `bye` and close, without waiting for the socket to drop. */
  hangUp: () => void;
}

const STATUS_TEXT: Record<CallState, string> = {
  idle: '',
  connecting: 'جارٍ الاتصال بالخادم…',
  waiting: 'في انتظار انضمام الطرف الآخر…',
  negotiating: 'جارٍ تأسيس الاتصال المباشر…',
  connected: 'الاتصال مباشر ومشفَّر بين الطرفين',
  reconnecting: 'انقطع الاتصال، جارٍ إعادة المحاولة…',
  denied: 'لا تملك صلاحية الانضمام إلى هذه الجلسة',
  ended: 'انتهت الجلسة',
};

export function useWebRTCCall(options: UseWebRTCCallOptions): UseWebRTCCall {
  const { roomId, localStream, enabled } = options;
  const accessToken = useAuthStore((s) => s.accessToken);

  const [state, setState] = useState<CallState>('idle');
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const videoSenderRef = useRef<RTCRtpSender | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const retryRef = useRef(0);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  /** Queued ICE candidates that arrived before the remote description. */
  const pendingCandidatesRef = useRef<RTCIceCandidateInit[]>([]);

  localStreamRef.current = localStream;

  const send = useCallback((type: string, payload?: unknown) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type, payload }));
    }
  }, []);

  /** Drop the peer connection but keep the signalling socket open. */
  const closePeer = useCallback(() => {
    pcRef.current?.close();
    pcRef.current = null;
    videoSenderRef.current = null;
    pendingCandidatesRef.current = [];
    setRemoteStream(null);
  }, []);

  const replaceVideoTrack = useCallback(async (track: MediaStreamTrack | null) => {
    const sender =
      videoSenderRef.current ||
      pcRef.current?.getSenders().find((s) => s.track?.kind === 'video') ||
      null;
    if (!sender) return;
    // replaceTrack swaps the outgoing media without a new offer/answer round, so
    // starting or stopping a screen share does not interrupt the call.
    await sender.replaceTrack(track);
  }, []);

  const hangUp = useCallback(() => {
    send('bye');
    closePeer();
    const socket = socketRef.current;
    socketRef.current = null;
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
    if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
    setState('ended');
  }, [closePeer, send]);

  // A stream that arrives after the peer connection was built — the user granted
  // camera permission late, or switched device — has to be attached to the
  // existing senders. The connection effect below reads the stream through a ref
  // precisely so that granting permission does not tear down a live call.
  useEffect(() => {
    const pc = pcRef.current;
    if (!pc || !localStream) return;
    localStream.getTracks().forEach((track) => {
      const existing = pc.getSenders().find((s) => s.track?.kind === track.kind);
      if (existing) {
        existing.replaceTrack(track);
      } else {
        pc.addTrack(track, localStream);
        if (track.kind === 'video') videoSenderRef.current = pc.getSenders().slice(-1)[0];
      }
    });
  }, [localStream]);

  useEffect(() => {
    if (!enabled || !roomId || !accessToken) {
      setState('idle');
      return;
    }

    let disposed = false;

    const createPeer = () => {
      const pc = new RTCPeerConnection({ iceServers: buildIceServers() });
      pcRef.current = pc;

      pc.ontrack = (event) => {
        setRemoteStream(event.streams[0] || new MediaStream([event.track]));
      };

      pc.onicecandidate = (event) => {
        if (event.candidate) send('candidate', event.candidate.toJSON());
      };

      pc.onconnectionstatechange = () => {
        if (disposed) return;
        switch (pc.connectionState) {
          case 'connected':
            setState('connected');
            break;
          case 'disconnected':
            setState('reconnecting');
            break;
          case 'failed':
            // An ICE restart re-gathers candidates on the existing connection,
            // which recovers a call that lost its path (Wi-Fi to mobile data)
            // without dropping the session and renegotiating from scratch.
            setState('reconnecting');
            pc.restartIce?.();
            break;
          default:
            break;
        }
      };

      const stream = localStreamRef.current;
      if (stream) {
        stream.getTracks().forEach((track) => {
          const sender = pc.addTrack(track, stream);
          if (track.kind === 'video') videoSenderRef.current = sender;
        });
      }
      return pc;
    };

    const drainCandidates = async (pc: RTCPeerConnection) => {
      const queued = pendingCandidatesRef.current;
      pendingCandidatesRef.current = [];
      for (const candidate of queued) {
        try {
          await pc.addIceCandidate(candidate);
        } catch {
          /* a candidate for a closed transport is not an error worth surfacing */
        }
      }
    };

    /** We were already in the room, so we own the offer. */
    const makeOffer = async () => {
      const pc = pcRef.current || createPeer();
      setState('negotiating');
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      send('offer', { sdp: pc.localDescription });
    };

    const handleOffer = async (payload: any) => {
      if (!payload?.sdp) return;
      const pc = pcRef.current || createPeer();
      setState('negotiating');
      await pc.setRemoteDescription(new RTCSessionDescription(payload.sdp));
      await drainCandidates(pc);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      send('answer', { sdp: pc.localDescription });
    };

    const handleAnswer = async (payload: any) => {
      const pc = pcRef.current;
      if (!pc || !payload?.sdp || pc.signalingState === 'stable') return;
      await pc.setRemoteDescription(new RTCSessionDescription(payload.sdp));
      await drainCandidates(pc);
    };

    const handleCandidate = async (payload: any) => {
      if (!payload) return;
      const pc = pcRef.current;
      // Candidates routinely arrive before the offer they belong to; adding one
      // without a remote description throws and loses it, so queue instead.
      if (!pc || !pc.remoteDescription) {
        pendingCandidatesRef.current.push(payload);
        return;
      }
      try {
        await pc.addIceCandidate(payload);
      } catch {
        /* ignore: stale candidate */
      }
    };

    const connect = () => {
      if (disposed) return;

      const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      setState('connecting');

      let socket: WebSocket;
      try {
        socket = new WebSocket(
          `${scheme}//${window.location.host}/ws/video_call/${encodeURIComponent(roomId)}/`,
          ['access_token', accessToken],
        );
      } catch {
        setState('ended');
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        retryRef.current = 0;
        setState('waiting');
      };

      socket.onmessage = (event) => {
        let message: any;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        // Every handler is async; failures are logged rather than thrown, because
        // an unhandled rejection here would leave the UI showing "negotiating"
        // with no way back.
        const run = async () => {
          switch (message?.type) {
            case 'peer_joined':
              await makeOffer();
              break;
            case 'offer':
              await handleOffer(message.payload);
              break;
            case 'answer':
              await handleAnswer(message.payload);
              break;
            case 'candidate':
              await handleCandidate(message.payload);
              break;
            case 'peer_left':
            case 'bye':
              closePeer();
              setState('waiting');
              break;
            default:
              break;
          }
        };
        run().catch((error) => console.error('WebRTC signalling failed', error));
      };

      socket.onclose = (event) => {
        if (disposed) return;
        closePeer();

        // 4001/4003/4004 are verdicts, not transport failures: the token was
        // refused, the user is not a participant, or the consultation does not
        // exist or is already closed. Retrying any of them just repeats the same
        // rejected handshake.
        if (
          event.code === CLOSE_UNAUTHENTICATED ||
          event.code === CLOSE_FORBIDDEN ||
          event.code === CLOSE_ROOM_UNKNOWN
        ) {
          setState('denied');
          return;
        }

        setState('reconnecting');
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** retryRef.current, RECONNECT_MAX_MS);
        retryRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      closePeer();
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [enabled, roomId, accessToken, closePeer, send]);

  return {
    state,
    remoteStream,
    isConnected: state === 'connected',
    statusText: STATUS_TEXT[state],
    replaceVideoTrack,
    hangUp,
  };
}
