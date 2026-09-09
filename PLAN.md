# Custom Optical Disc Ripper Plan

## Phase 1: Minimal Container Foundation

- [x] Multi-stage Dockerfile using `jlesage/makemkv:latest` (Path A) for `makemkvcon`.
- [x] Basic `requirements.txt` (FastAPI, Uvicorn, PyYAML).
- [x] Single `app/main.py` entrypoint.
- [x] Verify image builds cleanly locally with `docker build`.
- [x] Verify container runs locally and API returns healthcheck response.

## Phase 2: Host Hardware Access Verification

- [x] Add `disc.py` for non-mounting drive detection with `makemkvcon`.
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
- [x] Get from Form input to the outputs we need.
  - [x] Ensure we have permissions to write files.
  - Ensure we get correct CLI args for MakeMKV
  - Ensure we get correct CLI args for Handbrake
  - Ensure we get correct file names and output paths.
  - [x] for Movies
  - [x] for Movie Extras
  - [x] for Shows
  - At this stage, just printing it is probably sufficient
- [x] Stage 2: Add `app/ripper.py` for `makemkvcon` extraction
- [x] Stage 3: Add `HandBrakeCLI` processing for compression
- [x] Verify correct creation of output directory and file name.
- [x] Stage 4: delete temp folder if everything went well. These files are huge, so don't want to keep them around unnecessarily
- [x] Add real-time log streaming for `HandBrakeCLI` execution.
- [x] Add items to and edit them from history as they are being processed
- [x] Verify that compression works
- [x] Ensure compression does not overwrite main title.
- [ ] Verify full rip works
  - [x] for Movie
  - [x] For Movie Extras
  - [ ] For Show
- [x] Ensure cleanup and proper release so we can keep ripping while container is alive
- [x] Add MediaType to Ripping History elements and UI, to separate extra content from main film
  - Also make sure the status text looks okay on mobile.
- [x] Add ability to continue a failed job. If it failed at stage 3, we should be able to just redo stage 3.
  - Currently edits the last history item. Do I want to copy it and append instead?

## Phase 5: Real-time Progress & WebSockets

- [ ] Add a container version to the WebUI.
  - Can we display the commit sha or make a version string based on git tags, or in other ways version it nicely?
  - The important part is that it's clearly distinguishable when I'm making a change, even if I force push changes to overwrite a commit's content.
- [ ] Display whether drive is available and react to drive being connected/disconnected.
- [ ] Disable the Scan Drive button while the drive does the initial hardware read.
  - Starting scan before its ready locks it and it needs a power cycle.
- [ ] Design a V2 of the WebUI now that all main features are in place, to streamline the process.
  - On load, it should probably only include the "Drive Status" and "History" sections.
    - Can also include the section for trying unfinished jobs again (extraction finished, compression failed), but this section would show up only if there is a failed job that corresponds to a folder in /tmp.
  - Once "Scan Drive" is pressed and confirms data, The next section can replace it. We are then moved on to Configure Rip Job, and fill in our form.
  - Once every field on the form is filled in, the "Start Rip Job" button get activated.
  - Once we press "Start Rip Job", the section is again replaced, this time with the job progression section.
  - When the job progression reaches compression, we could re-enable a Drive Status section above it.
  - Consider all the below points in the plan as well when making this design.
- [ ] Add real-time log streaming for `makemkvcon` execution.
- [ ] Log streaming for both HandBrake and MakeMKV should probably reuse lines with `/r` instead of constantly pinging new lines?
  - Can this even be done when we want to stream with Websockets?
  - Other ways to avoid spamming the logs so much without sacrificing what we want in the WebUI?
- [ ] Make active History items in WebUI update when their status changes.
  - Would be great to know when it goes from EXTRACTING -> EXTRACTED -> COMPRESSING -> FINISHED on nice runs.
  - Would also be great to be able to see visually that it fails by having it go from ie EXTRACTING -> FAILED.
- [ ] Stream real-time stdout progress parsing to the Web UI via WebSockets.
  - I think multiple progress bars makes sense,
    to show the whole pipeline and where within it we are currently at.
  - We can probably safely assume that ie starting on step 3 means step 2 is finished and can be filled up, even if the last stdout wasn't a progress=1.0
  - Do I want separate progress bars for every title that gets extracted in step 2, for step 3, or do I just extend the one progress bar to cover all?
    - Maybe both?
    ```
        Stage 1:     |XXXXXXXXXXXXXXXXXXXXX|
        Stage 2:     |XXXXXXXXXXXXXXXXXXXXX|
            title 1:   |XXXXXXXXXXXXXXXXXXX|
            title 2:   |XXXXXXXXXXXXXXXXXXX|
            title 3:   |XXXXXXXXXXXXXXXXXXX|
        Stage 3:     |XXXXXXX--------------|
            title 1:   |XXXXXXXXXXXXXXXXX--|
            title 2:   |-------------------|
            title 3:   |-------------------|
    ```

## Phase 6: QoL improvements

- [ ] Can index.html be split into multiple files? It's become rather large by now
- [ ] When starting a job, empty the form so it's ready for next use.
- [ ] Add idiotproofing of user input data.
  - Title cannot contain weird characters. Should it be converted to Title Case on server?
  - Year must be a number between 1800 and today's year +5 (so we can don't crash if we were to want to rip an unreleased movie or extras relating to one)
  - season and episode must be a positive number
- [ ] Add a max length to the History section
  - Consider pagination instead, so we can avoid an ugly scrollbar?
- [ ] Add simple notification/chime on failure and completion.
- [ ] Add option to cancel ongoing job.
  - Could be cases where I realize after starting that the input was wrong
- [ ] Add a simple Queue system.
  - [ ] Disable Scan Drive and Action Buttons when there is an ongoing job using the drive. (Stage 2)
  - [ ] Instead of /api/rip starting a job directly, it adds to an Extraction Queue.
  - [ ] When done extracting, it doesn't start compression directly, it adds to a Compression Queue.
  - [ ] Updates to History should also probably be queued so that only one process tries to edit the file simultaneously.
- [ ] When disk is detected, look-up autofilled title to suggest year.
      Can we do fuzzy search for more/better suggestions?
      Or maybe we do a search on just fewer of the words if we have few hits - ie if "Harry Potter and the Philisopher's stone" gives few hits, just "Harry Potter" might get several.
- [ ] Before starting actual ripping process, do say ie "Expected time: 6-10 hours" with a rough estimate based on file size (if known) and preset.
