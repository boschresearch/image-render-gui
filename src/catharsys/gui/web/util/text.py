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

from typing import Optional, Any
from . import defines


# ###################################################################################
def ParseValueName(_sName: str, *, _dicType: Optional[dict] = None) -> tuple[str, Any]:
    xMatch = defines.g_reVarStart.match(_sName)
    if xMatch is None:
        return None, None
    # endif

    xData = None
    if isinstance(_dicType, dict):
        xData = _dicType.get(xMatch.group("type"))
    # endif

    lNameParts = defines.g_reVarNameEl.findall(_sName[xMatch.end("type") :])
    lNameParts = ["".join(x) for x in lNameParts]
    sLabel = " ".join(lNameParts)

    return sLabel, xData


# enddef
