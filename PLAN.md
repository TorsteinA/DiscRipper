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
- [x] Ensure container can be booted regardless of whether drive device is available or not.

## Phase 3: Config, Key Validation & UI Foundation

- [x] Add `app/config.py` for basic environment variable loading.
- [x] Add `app/key.py` to write `MAKEMKV_KEY` and raise `MakeMKVKeyError` on expired/invalid output.
- [x] Catch `MakeMKVKeyError` in `app/main.py` and return HTTP 400 JSON response.
- [x] Verify key test scenarios in Dockge (valid, missing, invalid key).
- [x] Create minimal Single Page Application (`app/static/index.html`) served directly by FastAPI.
- [x] Make Result and Config typed objects, so I can check properties properly rather than by string matching.
- [x] Define MakeMKV presets and options in `app/config.py`.
- [x] Define HandBrake presets and options in `app/config.py`.
- [x] Add presets to SPA

## Phase 4: Transcoding Engine & Hardware Verification

- [x] Verify QuickSync H.264 (`qsv_h264`) hardware acceleration on host GPU.
- [x] System for storing ripping history and showing it in the WebUI
- [x] Fix proper paths for the things we want, from compose-yaml to the container.
      `compose.yaml` should probably forward the folders for Movies, Shows, and appdata.
- [ ] Get from Form input to the outputs we need. - Ensure we get correct file names and output paths. - Ensure we get correct CLI args for MakeMKV - Ensure we get correct CLI args for Handbrake - At this stage, just printing it is probably sufficient
- [ ] Add `app/ripper.py` for `makemkvcon` extraction
- [ ] Add `HandBrakeCLI` processing for compression
- [ ] Verify correct creation of output directory and file name.

## Phase 5: Real-time Progress & WebSockets

- [ ] Display whether drive is available and react to drive being connected/disconnected.
- [ ] Stream real-time stdout progress parsing to the Web UI via WebSockets.
      I think multiple progress bars makes sense,
      to show the whole pipeline and where within it we are currently at.
      We can probably safely assume that ie starting on step 3 means step 2 is finished and can be filled up, even if the last stdout wasn't a progress=1.0

## Phase 6: QoL improvements

- [ ] Add simple notification/chime on failure and completion.
- [ ] When disk is detected, look-up autofilled title to suggest year.
      Can we do fuzzy search for more/better suggestions?
      Or maybe we do a search on just fewer of the words if we have few hits - ie if "Harry Potter and the Philisopher's stone" gives few hits, just "Harry Potter" might get several.
- [ ] Before starting actual ripping process, do say ie "Expected time: 6-10 hours" with a rough estimate based on file size (if known) and preset.
