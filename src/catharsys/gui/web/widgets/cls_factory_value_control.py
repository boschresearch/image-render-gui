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

import re
from typing import Optional, Callable, Any
from anybase import config
from nicegui import events

from ..util import text
from .cls_value_control import CValueControl
from .cls_value_control_number import CValueControlNumber
from .cls_value_control_switch import CValueControlSwitch
from .cls_value_control_select import CValueControlSelect
from .cls_value_control_input import CValueControlInput


class CFactoryValueControl:
    def __init__(self):
        self._reVarStart = re.compile(r"^(?P<type>[a-z])[A-Z]")
        self._reVarNameEl = re.compile(r"([A-Z][a-z_\-0-9]+)")

        self._dicCtrlType: dict[str, CValueControl] = {
            "number": CValueControlNumber,
            "switch": CValueControlSwitch,
            "select": CValueControlSelect,
            "input": CValueControlInput,
        }

        self._dicCtrlDti: dict[str, str] = {
            "i": "/catharsys/gui/control/number/int:1.0",
            "f": "/catharsys/gui/control/number/float:1.0",
            "b": "/catharsys/gui/control/switch:1.0",
            "s": "/catharsys/gui/control/input:1.0",
        }

    # enddef

    # ###################################################################################
    def FromDict(
        self,
        _sName: str,
        _dicCtrl: dict,
        _xValue: Any = None,
        _dicData: Optional[dict] = None,
        _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments, dict, str, Any], bool]] = None,
    ) -> CValueControl:
        if not isinstance(_dicCtrl, dict):
            return None
        # endif

        bHasTypeDict: bool = False
        try:
            dicDti = config.CheckConfigType(_dicCtrl, "/catharsys/gui/control/*:*")
            bHasTypeDict = dicDti["bOK"]
        except Exception:
            pass
        # endtry

        if bHasTypeDict is False:
            # if no DTI is specified, deduce type from name
            return self.FromName(_sName=_sName, _xValue=_xValue, _dicData=_dicData, _funcOnChange=_funcOnChange)
        # endif

        lCtrlType = dicDti["lCfgType"][3:]
        if len(lCtrlType) == 0:
            return None
        # endif

        xClass = self._dicCtrlType.get(lCtrlType[0])
        if xClass is not None:
            return xClass(_sName, _dicCtrl, _xValue, _dicData, _funcOnChange)
        # endif

        return None

    # enddef

    # ###################################################################################
    def GetControlConfigFromName(self, _sName: str) -> dict:
        sLabel, sDti = text.ParseValueName(_sName, _dicType=self._dicCtrlDti)
        if sLabel is None or sDti is None:
            return None
        # endif

        dicCtrl = {
            "sDTI": sDti,
            "sLabel": sLabel,
            "sTooltip": sLabel,
        }
        return dicCtrl

    # enddef

    # ###################################################################################
    def FromName(
        self,
        _sName: str,
        _xValue: Any = None,
        _dicData: Optional[dict] = None,
        _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments, dict, str, Any], bool]] = None,
    ):
        dicCtrl = self.GetControlConfigFromName(_sName)
        return self.FromDict(_sName, dicCtrl, _xValue, _dicData, _funcOnChange)

    # enddef


# endclass
