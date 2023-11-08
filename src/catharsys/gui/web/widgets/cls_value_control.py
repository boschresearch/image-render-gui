###
# Author: Christian Perwass (CR/AEC5)
# <LICENSE id="Apache-2.0">
#
#   Image-Render Automation Functions module
#   Copyright 2022 Robert Bosch GmbH and its subsidiaries
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

import copy
from typing import Optional, Any
from nicegui import ui, events, app, Client
from anybase import convert, config

from ..util import text


class CValueControl:
    def __init__(self, _sName: str, _dicCtrl: dict):
        self._dicCtrl = copy.deepcopy(_dicCtrl)
        self._sName: str = _sName
        self._sDti: str = None
        self._lType: list[str] = None
        self._lVersion: list[int] = None
        self._sLabel: str = None
        self._sTooltip: str = None

        dicDti = config.CheckConfigType(_dicCtrl, "/catharsys/gui/control/*:*")
        if dicDti["bOK"] is False:
            sDti: str = dicDti.get("sCfgDti")
            raise RuntimeError(f"Unsupported DTI: {sDti}")
        # endif

        self._sDti = dicDti.get("sCfgDti")
        self._lType = dicDti["lCfgType"][3:]
        self._lVersion = dicDti["lCfgVer"]

        self._sLabel = self._dicCtrl.get("sLabel")
        if self._sLabel is None:
            self._sLabel, _ = text.ParseValueName(self._sName)
            if self._sLabel is None:
                self._sLabel = self._sName
            # endif
        # endif

        self._sTooltip = self._dicCtrl.get("sTooltip")
        if self._sTooltip is None:
            self._sTooltip = self._sLabel
        # endif

    # enddef


# endclass
