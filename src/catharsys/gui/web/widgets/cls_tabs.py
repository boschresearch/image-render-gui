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

from nicegui import ui, events
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class CTabElement:
    xTab: ui.tab = None
    xPanel: ui.tab_panel = None


# endclass


class CTabs:
    def __init__(self, *, _funcOnChange: Optional[Callable[[events.ValueChangeEventArguments], None]] = None):
        self._dicTabs: dict[str, CTabElement] = dict()
        self._xTabs: ui.tabs = ui.tabs(on_change=_funcOnChange).props("inline-label")
        self._xPanels: ui.tab_panels = ui.tab_panels(self._xTabs)

    # enddef

    def __getitem__(self, _sKey: str) -> ui.tab_panel:
        return self._dicTabs[_sKey].xPanel

    # enddef

    def __contains__(self, _sKey: str) -> bool:
        return _sKey in self._dicTabs

    # enddef

    def __len__(self) -> int:
        return len(self._dicTabs)

    # enddef

    def __iter__(self) -> str:
        for sKey in self._dicTabs:
            yield sKey
        # endfor

    # enddef

    @property
    def lKeys(self) -> list[str]:
        return list(self._dicTabs.keys())

    # enddef

    @property
    def sSelected(self) -> str:
        return self._xTabs.value

    # enddef

    @property
    def uiTabs(self) -> ui.tabs:
        return self._xTabs

    # enddef

    @property
    def uiPanels(self) -> ui.tab_panels:
        return self._xPanels

    # enddef

    # ########################################################################################
    def GetPanel(self, _sName: set) -> ui.tab_panel:
        if _sName not in self:
            return None
        # endif
        return self[_sName]

    # enddef

    # ########################################################################################
    def Select(self, _sName: str):
        if _sName not in self._dicTabs:
            raise RuntimeError(f"Tab with name '{_sName}' does not exist")
        # endif
        self._xTabs.set_value(_sName)

    # enddef

    # ########################################################################################
    def SetIcon(self, _sName: str, _sIcon: str):
        if _sName not in self._dicTabs:
            raise RuntimeError(f"Tab with name '{_sName}' already present")
        # endif
        xTabEl: CTabElement = self._dicTabs[_sName]
        xTabEl.xTab.props(f"icon={_sIcon}")
        xTabEl.xTab.update()
        # self._xTabs.update()

    # enddef

    # ########################################################################################
    def Add(self, *, _sName: str, _sLabel: str, _sIcon: str = None) -> ui.tab_panel:
        if _sName in self._dicTabs:
            raise RuntimeError(f"Tab with name '{_sName}' already present")
        # endif
        xTabEl: CTabElement = CTabElement()
        with self._xTabs:
            xTabEl.xTab = ui.tab(_sName, label=_sLabel, icon=_sIcon)
        # endwith

        with self._xPanels:
            xTabEl.xPanel = ui.tab_panel(_sName)
        # endwith

        self._dicTabs[_sName] = xTabEl
        if len(self._dicTabs) == 1:
            self.Select(_sName)
        # endif

        return xTabEl.xPanel

    # enddef

    # ########################################################################################
    def Remove(self, _sName: str):
        if _sName not in self._dicTabs:
            raise RuntimeError(f"Tab with name '{_sName}' does not exist")
        # endif

        xTabEl = self._dicTabs[_sName]
        sSelTab: str = None
        if self._xTabs.value == _sName:
            sSelTab = next((x for x in self._dicTabs if x != _sName), None)
        # endif

        self._xTabs.remove(xTabEl.xTab)
        self._xPanels.remove(xTabEl.xPanel)
        del self._dicTabs[_sName]

        if sSelTab is not None:
            self._xTabs.set_value(sSelTab)
            self._xTabs.update()
        # endif

    # enddef

    # ########################################################################################
    def SetVisibility(self, _sName: str, _bVisible: bool):
        if _sName not in self._dicTabs:
            raise RuntimeError(f"Tab with name '{_sName}' does not exist")
        # endif

        xTabEl = self._dicTabs[_sName]
        sSelTab: str = None
        if _bVisible is False and self._xTabs.value == _sName:
            sSelTab = next((x for x in self._dicTabs if x != _sName), None)
        # endif

        xTabEl.xTab.set_visibility(_bVisible)
        xTabEl.xPanel.set_visibility(_bVisible)

        if sSelTab is not None:
            self._xTabs.set_value(sSelTab)
            self._xTabs.update()
        # endif

    # enddef


# endclass
