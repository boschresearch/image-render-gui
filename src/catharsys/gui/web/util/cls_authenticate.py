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
import enum
import hashlib
import base64
import uuid
from typing import Optional
from pathlib import Path
from datetime import datetime

from anybase.cls_any_error import CAnyError_Message
from anybase import config as anycfg

# import catharsys.api as capi
from getpass import getpass


class EAuthResult(enum.Enum):
    VALID = enum.auto()
    NO_FILE = enum.auto()
    CORRUPT_DB = enum.auto()
    INVALID_LINK = enum.auto()
    INVALID_ID = enum.auto()
    INVALID_USER = enum.auto()
    EXPIRED = enum.auto()


# endclass


class CAuthenticate:
    def __init__(self, *, _pathAuth: Optional[Path] = None):
        self._sDTI = "/catharsys/gui/web/user:1.0"
        self._pathAuth = _pathAuth
        self._sUserFileBasename = "gui-web-user"
        self._iKeyLen = 64
        self._iIterations = 100000

    # enddef

    @property
    def pathUserFile(self) -> Path:
        return self._pathAuth / f"{self._sUserFileBasename}.json"

    # enddef

    @property
    def bUserFileExists(self) -> bool:
        return self.pathUserFile.exists()

    # enddef

    @property
    def iTimestampNow(self) -> int:
        return int(datetime.utcnow().timestamp())

    # enddef

    ####################################################################
    def GetTimestamp(self, _dtX: datetime) -> int:
        return int(_dtX.timestamp())

    # enddef

    ####################################################################
    def GetPasswordFromConsole(self, _sUsername: Optional[str] = None) -> str:
        if _sUsername is not None:
            sPrompt = f"Please enter password for user '{_sUsername}': "
        else:
            sPrompt = "Please enter the user password: "
        # endif

        sPw1: str = getpass(sPrompt)
        sPw2: str = getpass("Repeat password: ")

        if sPw1 != sPw2:
            raise RuntimeError("The two passwords are not identical")
        # endif

        return sPw1

    # enddef

    ####################################################################
    def AddUser(
        self,
        _sUsername: str,
        _sPassword: str,
        _bForce: bool = False,
        *,
        _dtExpire: Optional[datetime] = None,
        _lRights: Optional[list[str]] = [],
    ) -> None:
        dicUserData: dict = None
        pathUserFile = self.pathUserFile

        if not pathUserFile.exists():
            dicUserData = {"sDTI": self._sDTI, "mUser": {}}
        else:
            dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        # endif

        dicUser = dicUserData.get("mUser")
        if dicUser is None:
            dicUser = dicUserData["mUser"] = {}
        # endif

        if _sUsername in dicUser and _bForce is False:
            raise RuntimeError(
                f"Password NOT updated because username '{_sUsername}' already present in file: {(pathUserFile.as_posix())}"
            )
        # endif

        iTimestampExpire: int = 0
        if _dtExpire is not None:
            iTimestampExpire = self.GetTimestamp(_dtExpire)
        # endif

        sKey, sSalt = self.HashPassword(_sPassword)
        dicUser[_sUsername] = {
            "sUser": _sUsername,
            "sKey": sKey,
            "sSalt": sSalt,
            "iExpire": iTimestampExpire,
            "lRights": _lRights,
        }

        anycfg.Save(pathUserFile, dicUserData, sDTI=self._sDTI)

    # enddef

    ####################################################################
    def SetUserPassword(self, *, _sUsername: str, _sPassword: str):
        dicUserData: dict = None
        pathUserFile = self.pathUserFile
        if not pathUserFile.exists():
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.NO_FILE))
        # endif

        dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        dicUsers: dict = dicUserData.get("mUser")
        if not isinstance(dicUsers, dict):
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.CORRUPT_DB))
        # endif

        dicUser: dict = dicUsers.get(_sUsername)
        if not isinstance(dicUser, dict):
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.INVALID_ID))
        # endif

        sKey, sSalt = self.HashPassword(_sPassword)
        dicUser["sKey"] = sKey
        dicUser["sSalt"] = sSalt

        anycfg.Save(pathUserFile, dicUserData, sDTI=self._sDTI)

        return EAuthResult.VALID

    # enddef

    ####################################################################
    def ProvidePublicLinkId(self, *, _sUsername: str, _sLink: str, _dtExpire: datetime) -> str:
        dicUserData: dict = None
        pathUserFile = self.pathUserFile

        if not pathUserFile.exists():
            dicUserData = {"sDTI": self._sDTI, "mUser": {}, "mPublicLinks": {}}
        else:
            dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        # endif

        dicUsers: dict = dicUserData.get("mUser")
        if dicUsers is None:
            # raise RuntimeError(f"Invalid User '{_sUsername}'")
            return None
        # endif

        if _sUsername not in dicUsers:
            return None
        # endif

        dicPublicLinks: dict[str, dict] = dicUserData.get("mPublicLinks")
        if dicPublicLinks is None:
            dicPublicLinks = dicUserData["mPublicLinks"] = {}
        # endif

        dicLinkIds: dict = dicPublicLinks.get(_sLink)
        if dicLinkIds is None:
            dicPublicLinks[_sLink] = dict()
            dicLinkIds = dicPublicLinks[_sLink]
        # endif

        uidUser = uuid.uuid4()
        sId: str = uidUser.hex

        iTimeStampExpire: int = self.GetTimestamp(_dtExpire)
        iTimeStampCreated: int = self.iTimestampNow

        dicLinkIds[sId] = {
            "sId": sId,
            "sLink": _sLink,
            "sUsername": _sUsername,
            "iCreated": iTimeStampCreated,
            "iExpire": iTimeStampExpire,
        }

        anycfg.Save(pathUserFile, dicUserData, sDTI=self._sDTI)
        return sId

    # enddef

    ####################################################################
    def TestPublicLinkId(self, _sLink: str, _sId: str, *, _bRemoveIfValid: bool = False) -> EAuthResult:
        dicUserData: dict = None
        pathUserFile = self.pathUserFile
        if not pathUserFile.exists():
            return EAuthResult.NO_FILE
        # endif

        dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        dicPublicLinks: dict = dicUserData.get("mPublicLinks")
        if not isinstance(dicPublicLinks, dict):
            # print("mPublicLinks not found")
            return EAuthResult.CORRUPT_DB
        # endif

        dicLinkIds: dict = dicPublicLinks.get(_sLink)
        if dicLinkIds is None:
            # print(f"Ref not found: {_sLink}")
            return EAuthResult.INVALID_LINK
        # endif

        dicLinkData: dict = dicLinkIds.get(_sId)
        if dicLinkData is None:
            return EAuthResult.INVALID_ID
        # endif

        iTimeStampExpire: int = dicLinkData["iExpire"]
        iTimeStampNow: int = self.iTimestampNow

        # dtNow = datetime.fromtimestamp(iTimeStampNow)
        # print(f"Now: {iTimeStampNow}, {dtNow}")
        # dtExpire = datetime.fromtimestamp(iTimeStampExpire)
        # print(f"Expire: {iTimeStampExpire}, {dtExpire}")

        if _bRemoveIfValid is True:
            del dicPublicLinks[_sLink]
            anycfg.Save(pathUserFile, dicUserData, sDTI=self._sDTI)
        # endif

        if iTimeStampExpire <= iTimeStampNow:
            return EAuthResult.EXPIRED
        # endif

        return EAuthResult.VALID

    # enddef

    ####################################################################
    def HashPassword(self, _sPassword: str, _sSalt: Optional[str] = None) -> tuple[str, str]:
        if _sSalt is None:
            bySalt = os.urandom(32)
        else:
            bySalt = base64.b64decode(_sSalt.encode("ascii"))
        # endif

        byKey = hashlib.pbkdf2_hmac(
            "sha256", _sPassword.encode("utf-8"), bySalt, self._iIterations, dklen=self._iKeyLen
        )
        sSalt = base64.b64encode(bySalt).decode("ascii")
        sKey = base64.b64encode(byKey).decode("ascii")
        return sKey, sSalt

    # enddef

    ####################################################################
    def TestUsernamePassword(self, _sUsername: str, _sPassword: str) -> EAuthResult:
        dicUserData: dict = None
        pathUserFile = self.pathUserFile
        if not pathUserFile.exists():
            return EAuthResult.NO_FILE
        # endif

        dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        dicUsers: dict = dicUserData.get("mUser")
        if not isinstance(dicUsers, dict):
            return EAuthResult.CORRUPT_DB
        # endif

        dicUser: dict = dicUsers.get(_sUsername)
        if not isinstance(dicUser, dict):
            return EAuthResult.INVALID_ID
        # endif

        sUserSalt = dicUser.get("sSalt")
        sUserKey = dicUser.get("sKey")
        if sUserSalt is None or sUserKey is None:
            return EAuthResult.CORRUPT_DB
        # endif

        sKey, sSalt = self.HashPassword(_sPassword, sUserSalt)
        if sUserKey != sKey:
            return EAuthResult.INVALID_USER
        # endif

        iExpire: int = dicUser.get("iExpire")
        if isinstance(iExpire, int) and iExpire > 0:
            if iExpire <= self.iTimestampNow:
                return EAuthResult.EXPIRED
            # endif
        # endif

        return EAuthResult.VALID

    # enddef

    ####################################################################
    def GetUserRights(self, _sUsername: str) -> list[str]:
        dicUserData: dict = None
        pathUserFile = self.pathUserFile
        if not pathUserFile.exists():
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.NO_FILE))
        # endif

        dicUserData = anycfg.Load(pathUserFile, sDTI=self._sDTI)
        dicUsers: dict = dicUserData.get("mUser")
        if not isinstance(dicUsers, dict):
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.CORRUPT_DB))
        # endif

        dicUser: dict = dicUsers.get(_sUsername)
        if not isinstance(dicUser, dict):
            raise RuntimeError(self.GetAuthResultMessage(EAuthResult.INVALID_ID))
        # endif

        lRights: list[str] = dicUser.get("lRights", [])
        return lRights

    # enddef

    ####################################################################
    def GetAuthResultMessage(self, _eResult: EAuthResult) -> str:
        sMsg: str = None
        if _eResult == EAuthResult.NO_FILE:
            sMsg = "Authentication database missing"
        elif _eResult == EAuthResult.CORRUPT_DB:
            sMsg = "Authentication database corrupted"
        elif _eResult in [EAuthResult.INVALID_ID, EAuthResult.INVALID_LINK]:
            sMsg = "Invalid link"
        elif _eResult == EAuthResult.INVALID_USER:
            sMsg = "Invalid username or password"
        elif _eResult == EAuthResult.EXPIRED:
            sMsg = "Authentication expired"
        else:
            sMsg = "Unknown error"
        # endif
        return sMsg

    # enddef


# endclass
