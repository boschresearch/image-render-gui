ToDo:
(ok) - main page with small title bar
(ok) - Wrap rows of grid, if many images of a single type are to be displayed, for example.
(ok) - Names and description for variants
(ok) - if too many images (> 100) are available in one dimension, then have two range sliders per value:
    one to set the starting position and one to set the number of images.
    Maybe need additional number input.

- copy trial variant settings when creating a new trial variant
- overwrite only gui settings from original option


Big ToDos:+
- action chain
- Scan artefacts via a separate process
- Have a thumbnail provider in separate process

Config Handling:
- Implement adding new config files/valus to trial dimensions per variant
    and editing them. For example, new camera names, or new meta configs.

Job Execution:
- Lock execution of BJOBS and ensure that it is not called too often.
- Check whether bjobs call was successfull
- Store generated jobs and associated LSF job numbers, to enable
    observing jobs again after closing webpage and restarting it.

Viewer:
- Give overview of which artefacts have been generated. Maybe simply as one pixel of a specific color per artefact.
- Export of view as PDF.
