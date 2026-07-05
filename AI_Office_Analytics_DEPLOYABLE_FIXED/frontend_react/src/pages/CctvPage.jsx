import CameraFeed from "../components/CameraFeed";

export default function CctvPage({ cameraAvailable }) {
  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Live CCTV</h1>
          <p>Full screen live monitoring of the main entrance camera</p>
        </div>
      </div>

      <div className="panel cctv-full-panel">
        <div className="panel-header">
          <h3>Live CCTV Feed - Main Entrance</h3>
          <span className="live-tag">
            <span className="dot"></span>Live
          </span>
        </div>
        <CameraFeed cameraAvailable={cameraAvailable} tall />
      </div>
    </section>
  );
}
