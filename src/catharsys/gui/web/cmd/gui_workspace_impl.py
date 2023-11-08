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

import signal
import os
from typing import Optional
from pathlib import Path
from importlib import resources as res

from anybase.cls_any_error import CAnyError_Message

import catharsys.gui.web
import catharsys.api as capi

# from taipy import Gui
from anybase.cls_python import CPythonConfig
from anybase.cls_process_handler import CProcessHandler

from catharsys.gui.web.util.cls_authenticate import CAuthenticate
from catharsys.gui.web.util import paths as guipaths

g_bKillProcess = False


####################################################################
def WorkspaceGui(
    *,
    sPathWorkspace: Optional[str] = None,
    sFileBasenameLaunch: Optional[str] = None,
    sTimeout: int = None,
    sAddUser: str = None,
    sAddAdmin: str = None,
    bNoSsl: bool = False,
):
    try:
        pathWS = None
        if sPathWorkspace is not None:
            # A project path has been specified
            pathWS = Path(sPathWorkspace)
            if not pathWS.exists():
                raise CAnyError_Message(sMsg="Project path does not exist: {}".format(pathWS.as_posix()))
            # endif
        # endif

        # try to find workspace, to report on errors before webserver is started.
        wsX = capi.CWorkspace(xWorkspace=pathWS, sFileBasenameLaunch=sFileBasenameLaunch)
    except Exception as xEx:
        xFinalEx = CAnyError_Message(sMsg="Error obtaining info on workspace", xChildEx=xEx)
        raise RuntimeError(xFinalEx.ToString())
    # endtry

    try:
        sExcept = "Error running command"
        if isinstance(sAddUser, str):
            sExcept = "Error adding user"
            AddUser(wsX, sAddUser)
        elif isinstance(sAddAdmin, str):
            sExcept = "Error adding admin"
            AddUser(wsX, sAddAdmin, _bAdmin=True)
        else:
            sExcept = "Error starting GUI"
            StartGui(sPathWorkspace, sFileBasenameLaunch, sTimeout, bNoSsl)
        # endif
    except Exception as xEx:
        xFinalEx = CAnyError_Message(sMsg=sExcept, xChildEx=xEx)
        raise RuntimeError(xFinalEx.ToString())
    # endtry


# enddef


####################################################################
def AddUser(_wsX: capi.CWorkspace, _sUsername: str, *, _bAdmin: bool = False):
    pathAuth = guipaths.GetSettingsPath(_wsX.pathWorkspace)
    xAuth = CAuthenticate(_pathAuth=pathAuth)
    sPw = xAuth.GetPasswordFromConsole(_sUsername)

    lRights: list[str] = ["default"]
    if _bAdmin is True:
        lRights.append("admin")
    # endif

    xAuth.AddUser(_sUsername, sPw, _lRights=lRights)


# enddef


####################################################################
def PollTerminate() -> bool:
    global g_bKillProcess
    return g_bKillProcess


# enddef


####################################################################
def OnSignalInterrupt(xSignal, xFrame):
    global g_bKillProcess
    g_bKillProcess = True


# enddef


####################################################################
def StartGui(_sPathWorkspace: str, _sFileBasenameLaunch: str, _sTimeout: str, _bNoSsl: bool):
    xPy = CPythonConfig(sCondaEnv=os.environ.get("CONDA_DEFAULT_ENV"))
    xProcHandler = CProcessHandler(_funcPollTerminate=PollTerminate)

    signal.signal(signal.SIGINT, OnSignalInterrupt)

    pathWs = Path.cwd()
    if _sPathWorkspace is not None:
        pathWs = Path(_sPathWorkspace)
    # endif

    pathSettings = guipaths.GetSettingsPath(pathWs)
    pathWsLock = pathSettings / "lock_gui_web.txt"
    if pathWsLock.exists():
        print("GUI web server already running for this workspace")
        return
    # endif

    pathWsLock.write_text("running")

    xApp = res.files(catharsys.gui.web).joinpath("apps").joinpath("run-workspace.py")
    with res.as_file(xApp) as pathApp:
        lArgs = [pathApp.as_posix()]
        if _sPathWorkspace is not None:
            lArgs.extend(["--path", _sPathWorkspace])
        # endif
        if _sFileBasenameLaunch is not None:
            lArgs.extend(["--launch", _sFileBasenameLaunch])
        # endif
        if _sTimeout is not None:
            lArgs.extend(["--timeout", _sTimeout])
        # endif
        if _bNoSsl is True:
            lArgs.extend(["--no-ssl"])
        # endif

        print("Starting Workspace GUI web service...")
        # It seems we need to start NiceGUI in a separate python instance,
        # for it to work.
        xPy.ExecPython(lArgs=lArgs, bDoPrint=True, xProcHandler=xProcHandler)
    # endwith

    pathWsLock.unlink()
    print("GUI web server closed down")


# enddef
