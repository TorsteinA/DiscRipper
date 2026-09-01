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

## Phase 3: Config & Key Validation

- [x] Add `app/config.py` for basic environment variable loading.
- [x] Add `app/key.py` to write `MAKEMKV_KEY` and raise `MakeMKVKeyError` on expired/invalid output.
- [x] Test key validation behavior on startup and during drive scanning.

## Phase 4: Transcoding Engine Execution

- [ ] Add `app/ripper.py` for `makemkvcon` extraction and `HandBrakeCLI` processing.
- [ ] Verify QuickSync H.264 (`qsv_h264`) hardware acceleration on host GPU.
- [ ] Verify output directory creation.

## Phase 5: UI & Progress Updates

- [ ] Add WebSocket endpoint and manager (`websocket_manager.py`).
- [ ] Build minimal HTML/JS frontend (`index.html` + Tailwind).
- [ ] Stream real-time progress updates to UI.
