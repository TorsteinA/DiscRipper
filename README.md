# Disc Ripper

This is a pragmatic disc ripper project that does the bare minimum I need it to for my own personal ripping needs on my home server, afer having trouble getting ARM to work with a few Norwegian DVD's. For most people, I would expect ARM to be the better option.

I'm targeting a Jellyfin library, and will therefore let Jellyfin do the metadata and image collection. I will just rip the mkv file, compress it, and place it in a folder structure that fits the requirements of Jellyfin.

While Gemini has been heavily involved when writing this tool, I have done most of the work myself. I simply do not think Gemini produces code of sufficient quality itself to get through a project like this without producing a bunch of weird bugs. I have constantly needed to babysit the outputs and verify every tiny step to make something that I trust to work even just for myself.

There will be a lot of weird commits, as I'm developing on a machine that doesn't have the environment to run the code. Pushing, creating the image, and pulling the image, is how the code is manually tested.

# Example `compose.yaml`

```yaml
services:
  disc-ripper:
    image: ghcr.io/torsteina/discripper:latest
    container_name: disc-ripper
    restart: unless-stopped
    privileged: true
    ports:
      - 8095:8000
    environment:
      - MAKEMKV_KEY=[key-id]
    devices:
      - /dev/sr0:/dev/sr0
      - /dev/sg1:/dev/sg1
      - /dev/dri:/dev/dri
    volumes:
      # Storage mapping
      - /appdata/discripper/data:/data # peristent storage
      - /srv/dev-disk-by-uuid-[id]/JellyfinMedia/Movies:/media/movies
      - /srv/dev-disk-by-uuid-[id]/JellyfinMedia/Shows:/media/shows
    group_add:
      - "24" # host cdrom group
      - "44" # host render/video group
```
