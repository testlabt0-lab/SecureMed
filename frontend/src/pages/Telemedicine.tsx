import React, { useEffect, useRef, useState } from 'react';
import { Video, Mic, MicOff, VideoOff, PhoneOff, UserSquare2 } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const Telemedicine = () => {
  const { user } = useAuthStore();
  const [inCall, setInCall] = useState(false);
  const [roomId, setRoomId] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);

  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);

  const servers = {
    iceServers: [
      {
        urls: ['stun:stun1.l.google.com:19302', 'stun:stun2.l.google.com:19302'],
      },
    ],
  };

  const startCall = async () => {
    if (!roomId) {
      toast.error('يرجى إدخال رقم غرفة الاتصال (رقم الموعد)');
      return;
    }

    try {
      // 1. Get Local Media
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      
      setInCall(true);

      // 2. Initialize WebSocket Signaling
      wsRef.current = new WebSocket(`ws://localhost:8000/ws/webrtc/${roomId}/`);

      wsRef.current.onopen = () => {
        console.log('Connected to signaling server');
        wsRef.current?.send(JSON.stringify({ type: 'user_joined' }));
      };

      wsRef.current.onmessage = async (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'user_joined') {
          // Other user joined, we should create an offer
          createOffer();
        } else if (message.type === 'offer') {
          handleOffer(message.payload);
        } else if (message.type === 'answer') {
          handleAnswer(message.payload);
        } else if (message.type === 'ice_candidate') {
          handleNewICECandidateMsg(message.payload);
        } else if (message.type === 'user_left') {
          toast('المريض غادر المكالمة', { icon: 'ℹ️' });
          endCall();
        }
      };

    } catch (err) {
      console.error('Error accessing media devices.', err);
      toast.error('لا يمكن الوصول للكاميرا أو الميكروفون');
    }
  };

  const createPeerConnection = () => {
    const pc = new RTCPeerConnection(servers);
    
    // Add local stream tracks to PC
    localStreamRef.current?.getTracks().forEach((track) => {
      pc.addTrack(track, localStreamRef.current!);
    });

    // Handle remote stream
    pc.ontrack = (event) => {
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = event.streams[0];
      }
    };

    // Send ICE candidates to signaling server
    pc.onicecandidate = (event) => {
      if (event.candidate && wsRef.current) {
        wsRef.current.send(JSON.stringify({
          type: 'ice_candidate',
          payload: event.candidate,
        }));
      }
    };

    peerConnectionRef.current = pc;
    return pc;
  };

  const createOffer = async () => {
    const pc = createPeerConnection();
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    
    wsRef.current?.send(JSON.stringify({
      type: 'offer',
      payload: offer,
    }));
  };

  const handleOffer = async (offer: RTCSessionDescriptionInit) => {
    const pc = createPeerConnection();
    await pc.setRemoteDescription(new RTCSessionDescription(offer));
    
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    
    wsRef.current?.send(JSON.stringify({
      type: 'answer',
      payload: answer,
    }));
  };

  const handleAnswer = async (answer: RTCSessionDescriptionInit) => {
    if (peerConnectionRef.current) {
      await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(answer));
    }
  };

  const handleNewICECandidateMsg = async (incoming: RTCIceCandidateInit) => {
    if (peerConnectionRef.current) {
      const candidate = new RTCIceCandidate(incoming);
      await peerConnectionRef.current.addIceCandidate(candidate).catch(e => console.log(e));
    }
  };

  const toggleMute = () => {
    const audioTrack = localStreamRef.current?.getAudioTracks()[0];
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled;
      setIsMuted(!audioTrack.enabled);
    }
  };

  const toggleVideo = () => {
    const videoTrack = localStreamRef.current?.getVideoTracks()[0];
    if (videoTrack) {
      videoTrack.enabled = !videoTrack.enabled;
      setIsVideoOff(!videoTrack.enabled);
    }
  };

  const endCall = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'user_left' }));
      wsRef.current.close();
    }
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (localVideoRef.current) localVideoRef.current.srcObject = null;
    if (remoteVideoRef.current) remoteVideoRef.current.srcObject = null;
    
    setInCall(false);
  };

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (inCall) endCall();
    };
  }, [inCall]);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="العيادة الافتراضية" 
        subtitle="مكالمات مرئية مشفرة P2P" 
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-4 bg-slate-900 overflow-hidden relative min-h-[400px] flex items-center justify-center">
            {/* Remote Video (Main) */}
            <video 
              ref={remoteVideoRef} 
              autoPlay 
              playsInline 
              className={`w-full h-full object-cover rounded-xl ${!inCall ? 'hidden' : ''}`}
            ></video>
            
            {/* Placeholder if no remote video */}
            {!inCall && (
              <div className="text-center text-slate-500 flex flex-col items-center">
                <UserSquare2 className="w-20 h-20 mb-4 opacity-50" />
                <p className="text-lg">أدخل رقم الغرفة لبدء الاتصال</p>
              </div>
            )}

            {/* Local Video (PIP) */}
            <div className={`absolute bottom-6 right-6 w-48 h-36 bg-black rounded-lg overflow-hidden border-2 border-slate-700 shadow-xl ${!inCall ? 'hidden' : ''}`}>
              <video 
                ref={localVideoRef} 
                autoPlay 
                playsInline 
                muted
                className="w-full h-full object-cover"
              ></video>
            </div>

            {/* Controls overlay */}
            {inCall && (
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 bg-slate-900/80 backdrop-blur-sm px-6 py-3 rounded-full">
                <button onClick={toggleMute} className={`p-3 rounded-full transition-colors ${isMuted ? 'bg-red-500 text-white' : 'bg-slate-700 hover:bg-slate-600 text-white'}`}>
                  {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
                </button>
                <button onClick={toggleVideo} className={`p-3 rounded-full transition-colors ${isVideoOff ? 'bg-red-500 text-white' : 'bg-slate-700 hover:bg-slate-600 text-white'}`}>
                  {isVideoOff ? <VideoOff size={20} /> : <Video size={20} />}
                </button>
                <button onClick={endCall} className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors">
                  <PhoneOff size={20} />
                </button>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">إعدادات الاتصال</h3>
            {!inCall ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">رقم الغرفة الموحد</label>
                  <input
                    type="text"
                    value={roomId}
                    onChange={(e) => setRoomId(e.target.value)}
                    placeholder="مثال: APP-1234"
                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition-colors"
                  />
                </div>
                <button
                  onClick={startCall}
                  className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <Video size={18} />
                  انضمام للغرفة
                </button>
              </div>
            ) : (
              <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-lg">
                <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse mx-auto mb-2"></div>
                <p className="text-emerald-700 dark:text-emerald-400 font-medium">متصل بالغرفة: {roomId}</p>
                <p className="text-sm text-emerald-600/80 dark:text-emerald-400/80 mt-1">يتم التشفير بطريقة P2P</p>
              </div>
            )}
          </Card>
          
          <Card className="p-6">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">ملاحظات الطبيب</h3>
            <textarea 
              className="w-full h-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white resize-none"
              placeholder="اكتب ملاحظاتك أثناء الاستشارة هنا..."
            ></textarea>
            <button className="mt-3 w-full py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-medium rounded-lg transition-colors text-sm">
              حفظ في الملف الطبي
            </button>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Telemedicine;
