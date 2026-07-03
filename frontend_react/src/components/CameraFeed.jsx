import { useEffect, useRef, useState } from "react";
import { detectFrame } from "../lib/api";

const DEMO_VIDEO_URL = "https://cdn.coverr.co/videos/coverr-walking-into-an-office-9013/1080p.mp4";

// How often we capture a frame from the visitor's webcam and send it
// to the backend for face recognition. Keeps bandwidth/inference load
// reasonable while still feeling live.
const CAPTURE_INTERVAL_MS = 1000;

/**
 * Live camera feed panel.
 *
 * Captures video from the VISITOR'S OWN webcam in the browser (via
 * getUserMedia) — not from any camera attached to the server — and
 * periodically posts a frame to POST /api/detect_frame, which runs
 * the exact same face-recognition + attendance pipeline the old
 * server-side MJPEG stream used, and returns the annotated JPEG back.
 * This is what makes the camera + face recognition actually work once
 * the backend is deployed to the cloud, since a cloud server has no
 * physical webcam of its own.
 *
 * Falls back to a looping demo video if the visitor denies camera
 * permission, has no webcam, or the backend can't be reached — so the
 * dashboard never shows a blank panel.
 */
export default function CameraFeed({ tall = false }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const objectUrlRef = useRef(null);
  const inFlightRef = useRef(false);

  const [mode, setMode] = useState("starting"); // starting | live | demo
  const [annotatedSrc, setAnnotatedSrc] = useState(null);
  const [timestamp, setTimestamp] = useState("");

  useEffect(() => {
    function tick() {
      const now = new Date();
      const dateStr = now.toLocaleDateString("en-GB").split("/").join("-");
      const timeStr = now.toLocaleTimeString("en-US", { hour12: true });
      setTimestamp(`${dateStr} ${timeStr}`);
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let captureTimer = null;

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setMode("demo");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setMode("live");
        captureTimer = setInterval(captureAndSend, CAPTURE_INTERVAL_MS);
      } catch (err) {
        // Permission denied, no camera device, insecure context, etc.
        setMode("demo");
      }
    }

    async function captureAndSend() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2 || inFlightRef.current) return;

      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        async (blob) => {
          if (!blob || cancelled) return;
          inFlightRef.current = true;
          try {
            const annotatedBlob = await detectFrame(blob);
            if (cancelled) return;
            const url = URL.createObjectURL(annotatedBlob);
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = url;
            setAnnotatedSrc(url);
          } catch (err) {
            // Backend unreachable for this frame — keep showing the
            // last good annotated frame and just retry next tick.
          } finally {
            inFlightRef.current = false;
          }
        },
        "image/jpeg",
        0.85
      );
    }

    start();

    return () => {
      cancelled = true;
      if (captureTimer) clearInterval(captureTimer);
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  const showDemo = mode !== "live";

  return (
    <div className={`video-panel-body${tall ? " tall" : ""}`}>
      {/* Hidden capture plumbing: the visitor's raw webcam feed and the
          canvas used to grab still frames from it. Not shown directly —
          the visible feed is the annotated frame the backend returns. */}
      <video ref={videoRef} muted playsInline style={{ display: "none" }} />
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {showDemo ? (
        <video src={DEMO_VIDEO_URL} autoPlay loop muted playsInline />
      ) : (
        <img src={annotatedSrc || undefined} alt="Live camera feed" />
      )}
      <span className="video-tag">CAM 01</span>
      <span className="video-timestamp">{timestamp}</span>
      <span className="video-location">MAIN ENTRANCE</span>
    </div>
  );
}
