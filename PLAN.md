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

## Phase 3: Config, Key Validation & UI Foundation

- [x] Add `app/config.py` for basic environment variable loading.
- [x] Add `app/key.py` to write `MAKEMKV_KEY` and raise `MakeMKVKeyError` on expired/invalid output.
- [x] Catch `MakeMKVKeyError` in `app/main.py` and return HTTP 400 JSON response.
- [x] Verify key test scenarios in Dockge (valid, missing, invalid key).
- [x] Create minimal Single Page Application (`app/static/index.html`) served directly by FastAPI.
- [ ] Define HandBrake presets and options in `app/config.py`.
- [ ] Define MakeMKV presets and options in `app/config.py`.
- [ ] Add presets to SPA

## Phase 4: Transcoding Engine & Hardware Verification

- [ ] Add `app/ripper.py` for `makemkvcon` extraction and `HandBrakeCLI` processing.
- [ ] Verify QuickSync H.264 (`qsv_h264`) hardware acceleration on host GPU.
- [ ] Verify output directory creation.

## Phase 5: Real-time Progress & WebSockets

- [ ] Figure out if container can be booted regardless of whether drive device is available or not.
      Drive is of course needed to actually do ripping, but might not be to get the container running.
      Could then perhaps detect device added/removed and show in WebUI
- [ ] Stream real-time stdout progress parsing to the Web UI via WebSockets.
- [ ] Add browser audio chime triggers on completion/failure.
