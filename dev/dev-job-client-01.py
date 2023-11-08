###
# Author: Christian Perwass (CR/AEC5)
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

import sys
import time
import socket


iPort = 50001
sIp = "localhost"
iBufferSize = 1024
sData = " ".join(sys.argv[1:])

for iIdx in range(10):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skClient:
        skClient.connect((sIp, iPort))
        time.sleep(1)
        skClient.sendall(bytes(f"{iIdx}: {sData}", "utf-8"))
    # endfor
    time.sleep(1)
# endwith
