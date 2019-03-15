#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           test/fbsp.py
# DESCRIPTION:    Unit tests for FBSP implementation
# CREATED:        26.2.2019
#
# The contents of this file are subject to the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright (c) 2019 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"Unit tests for FBSP implementation."

import unittest
import io
from uuid import UUID
from struct import pack
from saturnin.sdk import fbsp, VENDOR_UID, PLATFORM_UID
from saturnin.sdk.base import Origin

class TestMessages(unittest.TestCase):
    """Basic tests for FBSP Message classes"""
    def setUp(self):
        self.out = io.StringIO()
        self._fbsp = fbsp.Protocol()
    def tearDown(self):
        self.out.close()
    def get_token(self, val: int) -> bytes:
        "Return FBSP message token from integer."
        return pack('Q', val)
    def print_msg(self, msg: fbsp.Message) -> None:
        "Print message"
        print(msg.get_printout(), file=self.out)
        print("=" * 10, file=self.out)
        #print(self.out.getvalue())
    def check_msg(self, msg: fbsp.Message, origin: Origin) -> fbsp.Message:
        "Serialize, validate and parse the message."
        zmsg = msg.as_zmsg()
        self._fbsp.validate(zmsg, origin)
        return self._fbsp.parse(zmsg)
    def create_hello(self) -> fbsp.Message:
        "Creates test HELLO message"
        msg = self._fbsp.create_message_for(fbsp.MsgType.HELLO, self.get_token(1))
        msg.peer.uid = UUID('c24bdd24-46be-11e9-8f39-5404a6a1fd6e').bytes
        msg.peer.host = "localhost"
        msg.peer.pid = 100
        msg.peer.identity.uid = UUID('c9cf8bcc-46be-11e9-8f39-5404a6a1fd6e').bytes
        msg.peer.identity.name = "Agent name"
        msg.peer.identity.version = "1.0"
        msg.peer.identity.fbsp.uid = fbsp.PROTOCOL_UID.bytes
        msg.peer.identity.fbsp.version = '1'
        msg.peer.identity.protocol.uid = fbsp.PROTOCOL_UID.bytes
        msg.peer.identity.protocol.version = '1'
        msg.peer.identity.vendor.uid = VENDOR_UID.bytes
        msg.peer.identity.platform.uid = PLATFORM_UID.bytes
        msg.peer.identity.platform.version = "1.0"
        return msg
    def create_request(self) -> fbsp.Message:
        "Creates test REQUEST/SVC_ABILITIES message"
        return self._fbsp.create_request_for(fbsp.RequestCode.SVC_ABILITIES,
                                             self.get_token(4))
    def test_hello(self):
        "HELLO message"
        expect = """Message type: HELLO: 1
Flags: 0
Type data: 0
Token: 1
Peer:
uid: "c24bdd24-46be-11e9-8f39-5404a6a1fd6e"
host: "localhost"
pid: 100
identity {
  uid: "c9cf8bcc-46be-11e9-8f39-5404a6a1fd6e"
  name: "Agent name"
  version: "1.0"
  fbsp {
    uid: "3aeca6ef-c6e1-5acd-a6fe-7ef6849f95c4"
    version: "1"
  }
  protocol {
    uid: "3aeca6ef-c6e1-5acd-a6fe-7ef6849f95c4"
    version: "1"
  }
  vendor {
    uid: "a86ff2d2-73eb-593f-8b14-f2f7af0233d1"
  }
  platform {
    uid: "c26a6600-d579-5ec7-a9d6-5b0a8b214d3f"
    version: "1.0"
  }
}
# data frames: 0
==========
"""
        try:
            msg = self.create_hello()
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_welcome(self):
        "WELCOME message"
        expect = """Message type: WELCOME: 2
Flags: 0
Type data: 0
Token: 1
Peer:
uid: "b69daa46-46c0-11e9-8f39-5404a6a1fd6e"
host: "localhost"
pid: 100
identity {
  uid: "bcaabd34-46c0-11e9-8f39-5404a6a1fd6e"
  name: "Agent name"
  version: "1.0"
  fbsp {
    uid: "3aeca6ef-c6e1-5acd-a6fe-7ef6849f95c4"
    version: "1"
  }
  protocol {
    uid: "3aeca6ef-c6e1-5acd-a6fe-7ef6849f95c4"
    version: "1"
  }
  vendor {
    uid: "a86ff2d2-73eb-593f-8b14-f2f7af0233d1"
  }
  platform {
    uid: "c26a6600-d579-5ec7-a9d6-5b0a8b214d3f"
    version: "1.0"
  }
}
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_welcome_reply(self.create_hello())
            msg.peer.uid = UUID('b69daa46-46c0-11e9-8f39-5404a6a1fd6e').bytes
            msg.peer.host = "localhost"
            msg.peer.pid = 100
            msg.peer.identity.uid = UUID('bcaabd34-46c0-11e9-8f39-5404a6a1fd6e').bytes
            msg.peer.identity.name = "Agent name"
            msg.peer.identity.version = "1.0"
            msg.peer.identity.fbsp.uid = fbsp.PROTOCOL_UID.bytes
            msg.peer.identity.fbsp.version = '1'
            msg.peer.identity.protocol.uid = fbsp.PROTOCOL_UID.bytes
            msg.peer.identity.protocol.version = '1'
            msg.peer.identity.vendor.uid = VENDOR_UID.bytes
            msg.peer.identity.platform.uid = PLATFORM_UID.bytes
            msg.peer.identity.platform.version = "1.0"

            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_noop(self):
        "NOOP message"
        expect = """Message type: NOOP: 3
Flags: ACK_REQ
Type data: 0
Token: 3
# data frames: 0
==========
Message type: NOOP: 3
Flags: ACK_REPLY
Type data: 0
Token: 3
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_message_for(fbsp.MsgType.NOOP, self.get_token(3),
                                                flags=fbsp.Flag.ACK_REQ)
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            # ACK Response
            zmsg = self._fbsp.create_ack_reply(parsed).as_zmsg()
            self._fbsp.validate(zmsg, Origin.SERVICE)
            noop_reply = self._fbsp.parse(zmsg)
            self.print_msg(noop_reply)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_request(self):
        "REQUEST message"
        expect = """Message type: REQUEST: 4
Flags: 0
Type data: 1
Token: 4
Request code: SVC_ABILITIES: 1
# data frames: 0
==========
"""
        try:
            msg = self.create_request()
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_reply(self):
        "REPLY message"
        expect = """Message type: REPLY: 5
Flags: 0
Type data: 1
Token: 4
Abilities:
can_repeat_messages: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_reply_for(self.create_request())
            msg.abilities.can_repeat_messages = 1
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_data(self):
        "DATA message"
        expect = """Message type: DATA: 6
Flags: 0
Type data: 0
Token: 4
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_data_for(self.create_request())
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_cancel(self):
        "CANCEL message"
        expect = """Message type: CANCEL: 7
Flags: 0
Type data: 0
Token: 7
Cancel request:
token: "\\004\\000\\000\\000\\000\\000\\000\\000"
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_message_for(fbsp.MsgType.CANCEL, self.get_token(7))

            msg.cancel_reqest.token = self.get_token(4)
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_state(self):
        "STATE message"
        expect = """Message type: STATE: 8
Flags: 0
Type data: 1
Token: 4
State: RUNNING: 2
Request code: SVC_ABILITIES: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_state_for(self.create_request(), fbsp.pb.RUNNING)
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(parsed.state, fbsp.pb.RUNNING)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_close(self):
        "CLOSE message"
        expect = """Message type: CLOSE: 9
Flags: 0
Type data: 0
Token: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_message_for(fbsp.MsgType.CLOSE, self.get_token(1))
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_error(self):
        "ERROR message"
        expect = """Message type: ERROR: 31
Flags: 0
Type data: 68
Token: 4
Error code: NOT_IMPLEMENTED: 2
Relates to: REQUEST: 4
# Error frames: 1
@1:
code: 1
description: "Additional error description"
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_error_for(self.create_request(),
                                              fbsp.ErrorCode.NOT_IMPLEMENTED)
            err = msg.add_error()
            err.code = 1
            err.description = "Additional error description"
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_rq_con_repeat(self):
        "REQUEST/CON_REPEAT message"
        expect = """Message type: REQUEST: 4
Flags: 0
Type data: 20
Token: 5
Repeat:
last: 5
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_request_for(fbsp.RequestCode.CON_REPEAT,
                                                self.get_token(5))
            msg.repeat.last = 5
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_rep_svc_abilities(self):
        "REPLY/SVC_ABILITIES message"
        expect = """Message type: REPLY: 5
Flags: 0
Type data: 1
Token: 4
Abilities:
service_state {
  uid: "SSTP"
  version: "1"
  level: 1
}
service_config {
  uid: "RSCFG"
  version: "1"
}
service_control {
  uid: "RSCTRL"
  version: "1"
}
abilities {
  key: "myability"
  value {
    service_type: PROVIDER
    data_handler: B_PROVIDER
    protocol {
      uid: "PUID"
      version: "1.1"
    }
  }
}
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_reply_for(self.create_request())
            msg.abilities.service_state.uid = b'SSTP'
            msg.abilities.service_state.version = "1"
            msg.abilities.service_state.level = 1
            msg.abilities.service_config.uid = b'RSCFG'
            msg.abilities.service_config.version = "1"
            msg.abilities.service_control.uid = b'RSCTRL'
            msg.abilities.service_control.version = "1"
            ability = msg.abilities.abilities["myability"]
            ability.service_type = fbsp.pb.PROVIDER
            ability.data_handler.append(fbsp.pb.B_PROVIDER)
            protocol = ability.protocol.add()
            protocol.uid = b'PUID'
            protocol.version = "1.1"
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))

if __name__ == '__main__':
    unittest.main()
