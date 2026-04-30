let localStream = null;
let remoteStream = null;
let peerConnection = null;
let signalingSocket = null;
let currentCallId = null;
let isCallActive = false;

const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { 
            urls: 'turn:openrelay.metered.ca:80',
            username: 'openrelayproject',
            credential: 'openrelayproject'
        }
    ]
};

async function startVideoCall() {
    if (!currentConversation || !currentConversation.otherParticipant) return;
    
    currentCallId = generateCallId();
    
    // Show modal
    document.getElementById('videoCallModal').style.display = 'flex';
    
    // Get local media
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        document.getElementById('localVideo').srcObject = localStream;
        
        // Create peer connection
        createPeerConnection();
        
        // Add local tracks
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
        
        // Create offer
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        // Connect signaling
        connectSignaling();
        
        // Send offer
        setTimeout(() => {
            if (signalingSocket && signalingSocket.readyState === WebSocket.OPEN) {
                signalingSocket.send(JSON.stringify({
                    type: 'offer',
                    offer: offer
                }));
            }
        }, 1000);
        
    } catch (error) {
        console.error('Error accessing media devices:', error);
        alert('Could not access camera/microphone');
    }
}

function createPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);
    
    peerConnection.ontrack = (event) => {
        if (!remoteStream) {
            remoteStream = new MediaStream();
            document.getElementById('remoteVideo').srcObject = remoteStream;
        }
        remoteStream.addTrack(event.track);
    };
    
    peerConnection.onicecandidate = (event) => {
        if (event.candidate && signalingSocket) {
            signalingSocket.send(JSON.stringify({
                type: 'ice_candidate',
                candidate: event.candidate
            }));
        }
    };
    
    peerConnection.oniceconnectionstatechange = () => {
        if (peerConnection.iceConnectionState === 'disconnected') {
            endCall();
        }
    };
}

function connectSignaling() {
    const token = localStorage.getItem('access_token');
    signalingSocket = new WebSocket(`ws://localhost:8000/ws/call/${currentCallId}/?token=${token}`);
    
    signalingSocket.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'offer':
                await handleOffer(data);
                break;
            case 'answer':
                await handleAnswer(data);
                break;
            case 'ice_candidate':
                await handleIceCandidate(data);
                break;
            case 'user_joined':
                console.log('User joined:', data.user_name);
                break;
            case 'user_left':
                console.log('User left:', data.user_name);
                if (isCallActive) {
                    endCall();
                }
                break;
            case 'call_ended':
                endCall();
                break;
        }
    };
}

async function handleOffer(data) {
    if (!peerConnection) {
        createPeerConnection();
        
        // Get local stream
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        document.getElementById('localVideo').srcObject = localStream;
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }
    
    const offer = new RTCSessionDescription(data.offer);
    await peerConnection.setRemoteDescription(offer);
    
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    
    signalingSocket.send(JSON.stringify({
        type: 'answer',
        answer: answer
    }));
}

async function handleAnswer(data) {
    const answer = new RTCSessionDescription(data.answer);
    await peerConnection.setRemoteDescription(answer);
}

async function handleIceCandidate(data) {
    if (peerConnection) {
        const candidate = new RTCIceCandidate(data.candidate);
        await peerConnection.addIceCandidate(candidate);
    }
}

function startAudioCall() {
    // Similar to video call but without video track
    startCall('audio');
}

function endCall() {
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    
    if (signalingSocket) {
        signalingSocket.send(JSON.stringify({ type: 'end_call', duration: getCallDuration() }));
        signalingSocket.close();
        signalingSocket = null;
    }
    
    isCallActive = false;
    document.getElementById('videoCallModal').style.display = 'none';
}

function generateCallId() {
    return `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function getCallDuration() {
    // Calculate call duration
    return 0;
}

// Toggle controls
document.getElementById('toggleMic')?.addEventListener('click', () => {
    if (localStream) {
        const audioTrack = localStream.getAudioTracks()[0];
        audioTrack.enabled = !audioTrack.enabled;
        document.getElementById('toggleMic').style.opacity = audioTrack.enabled ? '1' : '0.5';
    }
});

document.getElementById('toggleVideo')?.addEventListener('click', () => {
    if (localStream) {
        const videoTrack = localStream.getVideoTracks()[0];
        videoTrack.enabled = !videoTrack.enabled;
        document.getElementById('toggleVideo').style.opacity = videoTrack.enabled ? '1' : '0.5';
    }
});

document.getElementById('screenShare')?.addEventListener('click', async () => {
    try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const videoTrack = screenStream.getVideoTracks()[0];
        
        const sender = peerConnection.getSenders().find(s => s.track.kind === 'video');
        if (sender) {
            sender.replaceTrack(videoTrack);
        }
        
        videoTrack.onended = () => {
            // Restore camera track
            const cameraTrack = localStream.getVideoTracks()[0];
            sender.replaceTrack(cameraTrack);
        };
    } catch (error) {
        console.error('Error sharing screen:', error);
    }
});