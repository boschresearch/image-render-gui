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


class CLogin:
    def __init__(self, _pathAuth: Path):
        self._xAuth: CAuthenticate = CAuthenticate(_pathAuth=_pathAuth)

    # enddef

    @property
    def bNeedAuth(self) -> bool:
        return self.bUserAuthEnabled is True and not self.bAuthenticated

    # enddef

    @property
    def bUserAuthEnabled(self) -> bool:
        return self._xAuth.bUserFileExists

    # enddef

    @property
    def bAuthenticated(self) -> bool:
        return app.storage.user.get("bAuthenticated", False)

    # enddef

    @property
    def bIsAdmin(self) -> bool:
        sUser: str = self.sUsername
        bIsAdmin: bool = False
        if self.bUserAuthEnabled and sUser is not None:
            try:
                bIsAdmin = "admin" in self.GetUserRights()
            except Exception:
                bIsAdmin = False
            # endtry
        # endif
        return bIsAdmin

    # endif

    @property
    def sUsername(self) -> str:
        if self.bNeedAuth:
            return None
        # endif

        if self.bUserAuthEnabled:
            return app.storage.user.get("sUsername")
        # endif

        return "public"

    # enddef

    def TestPublicLinkId(self, _sLink: str, _sId: str, *, _bRemoveIfValid: bool = False) -> EAuthResult:
        # if not self.bAuthenticated:
        #     return False
        # # endif

        return self._xAuth.TestPublicLinkId(_sLink=_sLink, _sId=_sId, _bRemoveIfValid=_bRemoveIfValid)

    # enddef

    def ProvidePublicLinkId(self, _sLink: str, _dtExpire: datetime) -> str:
        if not self.bAuthenticated:
            return None
        # endif

        return self._xAuth.ProvidePublicLinkId(_sUsername=self.sUsername, _sLink=_sLink, _dtExpire=_dtExpire)

    # enddef

    def TestAuthRedirect(self) -> RedirectResponse:
        if self.bNeedAuth is True:
            return RedirectResponse("/login")
        # endif
        return None

    # enddef

    def Login(self, _sUsername: str, _sPassword: str) -> EAuthResult:
        eResult = self._xAuth.TestUsernamePassword(_sUsername, _sPassword)
        if eResult == EAuthResult.VALID:
            app.storage.user.update({"sUsername": _sUsername, "bAuthenticated": True})
            return EAuthResult.VALID
        # endif
        return eResult

    # enddef

    def Logout(self) -> bool:
        bLoggedOut: bool = False
        if self.bUserAuthEnabled is True and self.bAuthenticated is True:
            sUsername: str = self.sUsername
            if sUsername != "public":
                app.storage.user.update({"sUsername": "", "bAuthenticated": False})
                bLoggedOut = True
            # endif
        # endif
        return bLoggedOut

    # enddef

    def AddUserTempPassword(self, _sUsername: str, *, _dtExpire: datetime, _lRights: list[str]):
        sPw: str = uuid.uuid4().hex
        self._xAuth.AddUser(_sUsername, sPw, _bForce=True, _dtExpire=_dtExpire, _lRights=_lRights)

    # enddef

    def SetUserPassword(self, _sUsername: str, _sPassword: str):
        self._xAuth.SetUserPassword(_sUsername=_sUsername, _sPassword=_sPassword)

    # enddef

    def GetUserRights(self) -> list[str]:
        return self._xAuth.GetUserRights(self.sUsername)

    # enddef

    def GetAuthResultMessage(self, _eResult: EAuthResult) -> str:
        return self._xAuth.GetAuthResultMessage(_eResult)

    # enddef


# endclass
