# Disc Ripper

This is a pragmatic disc ripper project that does the bare minimum I need it to for my own personal ripping needs on my home server, afer having trouble getting ARM to work with a few Norwegian DVD's. For most people, I would expect ARM to be the better option.

I'm targeting a Jellyfin library, and will therefore let Jellyfin do the metadata and image collection. I will just rip the mkv file, compress it, and place it in a folder structure that fits the requirements of Jellyfin.

Building this tool has relied heavily on the use of AI; specifically Gemini. I do not need this tool to be production-ready, or enterprise-grade. I just need a simple tool that will produce the files I want it to.

There will be a lot of weird commits, as I'm developing on a machine that doesn't have the environment to run the code. Pushing, creating the image, and pulling the image, is how the code is manually tested.
