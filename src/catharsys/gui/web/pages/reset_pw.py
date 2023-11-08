#!/usr/bin/env python3
# -*- coding:utf-8 -*-
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
import uuid
from typing import Optional

from pathlib import Path
from nicegui import ui, app
from fastapi.responses import RedirectResponse
from datetime import datetime
from catharsys.gui.web.util.cls_authenticate import CAuthenticate, EAuthResult
from catharsys.gui.web.util.cls_login import CLogin
from catharsys.gui.web.widgets.cls_message import CMessage, EMessageType


# ###########################################################################
# https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py


class CPageResetPw:
    def __init__(self, _xLogin: CLogin, _sUsername: str, _sId: str):
        self._xLogin: CLogin = _xLogin
        self._sUsername: str = _sUsername
        self._sId: str = _sId
        self._inPassword1: ui.input = None
        self._inPassword2: ui.input = None
        self._butApply: ui.button = None

    # enddef

    @staticmethod
    def Register(_xLogin: CLogin):
        @ui.page("/resetpw/{username}/{id}")
        def page_resetpw(username: str, id: str) -> Optional[RedirectResponse]:
            pageResetPw = CPageResetPw(_xLogin, username, id)
            pageResetPw.Create()

        # enddef

    # enddef

    # ###########################################################
    def Create(self):
        eResult: EAuthResult = self._xLogin.TestPublicLinkId(
            f"resetpw/{self._sUsername}",
            self._sId,
            _bRemoveIfValid=True,
        )

        if eResult == EAuthResult.VALID:
            with ui.card().tight().classes("absolute-center"):
                with ui.card_section():
                    ui.label(f"User: {self._sUsername}").classes("text-h6")
                    ui.label("Password must be at least 6 characters long")
                # endwith
                with ui.card_section():
                    self._inPassword1 = ui.input(
                        "Password", password=True, password_toggle_button=True, on_change=self._TestPw
                    )
                    self._inPassword2 = ui.input(
                        "Repeat Password", password=True, password_toggle_button=True, on_change=self._TestPw
                    )
                # endwith
                with ui.card_actions().props("align=center").classes("bg-white text-teal"):
                    self._butApply = ui.button("Apply", on_click=lambda: self.ApplyPassword()).props("flat")
                    self._butApply.set_enabled(False)
                # endwith
            # endwith

        else:
            sMsg: str = self._xLogin.GetAuthResultMessage(eResult)
            CMessage().ShowMessageScreen(_sText=sMsg, _sIcon="thunderstorm")
        # endif

    # enddef

    # ###########################################################
    def _TestPw(self):
        sPw1: str = str(self._inPassword1.value)
        sPw2: str = str(self._inPassword2.value)

        bValid = len(sPw1) >= 6 and sPw1 == sPw2

        self._butApply.set_enabled(bValid)

    # enddef

    # ###########################################################
    def ApplyPassword(self):
        sPw1: str = str(self._inPassword1.value)
        try:
            self._xLogin.SetUserPassword(self._sUsername, sPw1)
            ui.open("/login")
        except Exception as xEx:
            CMessage().ShowException("Error setting password", xEx)
        # endraise

    # enddef


# endclass
