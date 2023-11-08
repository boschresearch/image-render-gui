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


# ###########################################################################
# https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py


class CPageLogin:
    def __init__(self, _xLogin: CLogin):
        self._xLogin: CLogin = _xLogin
        self._inUsername: ui.input = None
        self._inPassword: ui.input = None

    # enddef

    @staticmethod
    def Register(_xLogin: CLogin):
        @ui.page("/login")
        def page_login() -> Optional[RedirectResponse]:
            pageLogin = CPageLogin(_xLogin)
            return pageLogin.Create()

        # enddef

    # enddef

    # ###########################################################
    def Create(self) -> Optional[RedirectResponse]:
        if not self._xLogin.bNeedAuth:
            return RedirectResponse("/")
        # endif

        with ui.card().classes("absolute-center"):
            self._inUsername = ui.input("Username").on("keydown.enter", lambda: self.Login())
            self._inPassword = ui.input("Password", password=True, password_toggle_button=True).on(
                "keydown.enter", lambda: self.Login()
            )
            ui.button("Log in", on_click=lambda: self.Login())
        # endwith

        return None

    # enddef

    # ###########################################################
    def Login(self) -> None:
        eResult = self._xLogin.Login(self._inUsername.value, self._inPassword.value)
        self._inPassword.set_value("")
        if eResult == EAuthResult.VALID:
            ui.open("/")
        else:
            sMsg = self._xLogin.GetAuthResultMessage(eResult)
            ui.notify(sMsg, color="negative")
        # endif

    # endef

    # ###########################################################
    def Logout(self) -> None:
        if self._xLogin.Logout() is True:
            ui.open("/")
        # endif

    # enddef


# endclass
