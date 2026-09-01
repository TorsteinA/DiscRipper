# Custom Optical Disc Ripper Plan

## Phase 1: Minimal Container Foundation

- [x] Multi-stage Dockerfile using `jlesage/makemkv:latest` (Path A) for `makemkvcon`.
- [x] Basic `requirements.txt` (FastAPI, Uvicorn, PyYAML).
- [x] Single `app/main.py` entrypoint.
- [x] Verify image builds cleanly locally with `docker build`.
- [x] Verify container runs locally and API returns healthcheck response.

## Phase 2: Host Hardware Access Verification

- [x] Add `disc.py` for non-mounting drive detection (`blkid` & `makemkvcon`).
- [x] Expose `/api/scan` endpoint.
- [x] Deploy to Dockge with host privileges (`privileged: true` and `/dev:/dev`).
- [x] Verify optical drive scan results against physical server drive.
- [x] Get a favicon to remove 404 error on accessing api
- [x] Improve isolation by removing need for privileged=true

## Phase 3: Transcoding Engine Execution

- [ ] Add `ripper.py` to wrap `makemkvcon` and `HandBrakeCLI` execution loops.
- [ ] Verify QuickSync H.264 (`qsv_h264`) hardware acceleration on host GPU.
- [ ] Verify Jellyfin directory output path creation.

## Phase 4: UI & Progress Updates

- [ ] Add WebSocket endpoint and manager (`websocket_manager.py`).
- [ ] Build minimal HTML/JS frontend (`index.html` + Tailwind).
- [ ] Stream real-time stdout parsing (percentages/stages) to UI.
- [ ] Add browser audio chime triggers on completion/failure.
