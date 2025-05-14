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
import base64
import hashlib
import shutil
import numpy as np
from typing import Union
from pathlib import Path
import catharsys.plugins.std.util.imgproc as imgproc

# need to enable OpenExr explicitly
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2


class CThumbnails:
    def __init__(
        self,
        *,
        _pathThumbnails: Path,
        _pathMain: Path,
        _iTrgWidth: int = 128,
        _iTrgHeight: int = 0,
        _sFileTypeExt: str = "jpg",
        _bNormalizeExr: bool = True,
    ):
        self._pathThumbnails: Path = _pathThumbnails
        self._pathMain: Path = _pathMain
        self._iTrgWidth: int = _iTrgWidth
        self._iTrgHeight: int = _iTrgHeight
        self._sFileTypeExt: str = _sFileTypeExt
        self._bNormalizeExr: bool = _bNormalizeExr

    # enddef

    @property
    def iTargetWidth(self) -> int:
        return self._iTrgWidth

    # enddef

    @iTargetWidth.setter
    def iTargetWidth(self, iValue: int):
        self._iTrgWidth = iValue

    # enddef

    @property
    def iTargetHeight(self) -> int:
        return self._iTrgHeight

    # enddef

    @iTargetHeight.setter
    def iTargetHeight(self, iValue: int):
        self._iTrgHeight = iValue

    # enddef

    # #########################################################################
    def GetRelativePath(self, _pathImage: Path) -> Path:
        return _pathImage.relative_to(self._pathMain)

    # enddef

    # #########################################################################
    def GetThumbnailNames(self, _pathImage: Path) -> tuple[str, str]:
        if _pathImage.exists():
            iTimeImage: int = int(os.path.getmtime(_pathImage.as_posix()))
        else:
            iTimeImage = 0
        # endif

        pathRel: Path
        try:
            pathRel = self.GetRelativePath(_pathImage)
        except Exception:
            pathRel = _pathImage
        # endtry
        sId: str = pathRel.as_posix()
        hashMD5 = hashlib.md5(sId.encode("utf8"))
        sName = base64.b32encode(hashMD5.digest()).decode()
        sFilename = f"{sName}-{iTimeImage}.{self._sFileTypeExt}"
        return sFilename, sName

    # enddef

    # #########################################################################
    def GetThumbnailPath(self):
        return self._pathThumbnails / f"{self._iTrgWidth}x{self._iTrgHeight}"

    # enddef

    # #########################################################################
    def CreateThumbnail(self, _pathImage: Path) -> Path:
        if not _pathImage.exists():
            raise RuntimeError(f"File does not exist: {(_pathImage.as_posix())}")
        # endif

        pathThumb: Path = self.GetThumbnailPath()
        pathThumb.mkdir(parents=True, exist_ok=True)
        sThumbFile, sThumbName = self.GetThumbnailNames(_pathImage)
        pathThumbFile = pathThumb / sThumbFile

        sExt: str = _pathImage.suffix
        aImage: np.ndarray = None

        if sExt == ".exr":
            aImage = imgproc.LoadImageExr(sFpImage=_pathImage.as_posix(), bAsUint=True, bNormalize=self._bNormalizeExr)
        else:
            aImage = cv2.imread(_pathImage.as_posix())
        # endif

        iW, iH = imgproc.UpdateWidthHeight(self._iTrgWidth, self._iTrgHeight, aImage)
        aImage = cv2.resize(aImage, (iW, iH), interpolation=cv2.INTER_AREA)

        cv2.imwrite(pathThumbFile.as_posix(), aImage)

        return pathThumbFile

    # enddef

    # #########################################################################
    def ProvideThumbnailPath(
        self, _pathImage: Union[str, Path], *, _bCreateOnDemand: bool = True, _bReturnString: bool = False
    ) -> Union[Path, str]:
        if isinstance(_pathImage, str):
            pathImage = Path(_pathImage)
        else:
            pathImage = _pathImage
        # endif

        if not pathImage.exists():
            raise RuntimeError(f"File does not exist: {(pathImage.as_posix())}")
        # endif
        pathThumbFile: Path = None
        pathThumb = self.GetThumbnailPath()
        if pathThumb.exists():
            sThumbFile, sThumbName = self.GetThumbnailNames(pathImage)
            pathThumbFile = pathThumb / sThumbFile
            if not pathThumbFile.exists():
                for pathFile in pathThumb.glob(f"{sThumbName}*.{self._sFileTypeExt}"):
                    pathFile.unlink()
                # endfor
                pathThumbFile = None
                if _bCreateOnDemand:
                    pathThumbFile = self.CreateThumbnail(pathImage)
                # endif
            # endif
        elif _bCreateOnDemand:
            pathThumbFile = self.CreateThumbnail(pathImage)
        # endif

        if _bReturnString:
            return pathThumbFile.as_posix()
        # endif
        return pathThumbFile

    # enddef


# endclass
