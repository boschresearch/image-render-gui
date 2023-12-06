###
# Author: Christian Perwass (CR/ADI2.1)
# <LICENSE id="Apache-2.0">
#
#   Image-Render Automation Functions module
#   Copyright 2023 Robert Bosch GmbH and its subsidiaries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# </LICENSE>
###

import os
from pathlib import Path
from typing import Union, Any

from nicegui.element import Element
from nicegui import helpers

try:
    from nicegui import globals as ngcore
except Exception:
    from nicegui import core as ngcore
# endtry


# Need this image class to enable reloading files with same filename
# but different creation date
class CUiImage(Element, component="image.js"):
    def __init__(self, _pathImage: Path):
        super().__init__()

        if not _pathImage.exists():
            raise RuntimeError(f"Image file does not exist: {_pathImage}")
        # endif

        iTimeImage: int = int(os.path.getmtime(_pathImage.as_posix()))
        sUrl = f"/_nicegui/auto/static/{helpers.hash_file_path(_pathImage)}_{iTimeImage}/{_pathImage.name}"

        self.source = ngcore.app.add_static_file(local_file=_pathImage, url_path=sUrl)
        self._props["src"] = self.source

    # enddef


# endclass
