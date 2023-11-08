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

import socketserver


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.data = self.request.recv(1024).strip().decode("utf-8")
        # print("{} wrote:".format(self.client_address[0]))
        print(self.data)

    # enddef


# endclass

iPort = 50001
sIp = "localhost"
iBufferSize = 30

with socketserver.TCPServer((sIp, iPort), TCPHandler) as server:
    server.serve_forever()
# endwith

# skServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# skServer.bind((sIp, iPort))
# skServer.listen(1)
# skConnect, sAddress = skServer.accept()
# print(f"Connection Address: {sAddress}")
# # while True:
# #     xData = skConnect.recv(iBufferSize)

# #     if xData is None:
# #         break
# # # endwhile

# # print("Received data", xData)

# # skConnect.send(xData)
# skConnect.close()
# skServer.close()
