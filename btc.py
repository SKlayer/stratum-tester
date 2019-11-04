import json
import socket
import random

def decodeUNum(n):
    number = 0
    s = bytes.fromhex(n)
    for i in range(1,4):
        number = number + s[i] * (256**(i-1))
    return number


class StratumTest:
    def __init__(self):
        self.url = "stratum+tcp://0.0.0.0:3333"
        self.jobTime = 15
        self.sockets = None
        self.jobID = 0
        self.coinType = "BTC"
        self.asicBoost = 1
        self.username = ["debout", ""]
        self.notifys = []

    def _method_asic_boost(self):
        if self.asicBoost is None:
            return
        _version_rolling_bit = 4
        asic_boost = {
            0: {"id": self._get_id(), "method": "mining.multi_version", "params": [_version_rolling_bit]},
            1: {"id": self._get_id(), "method": "mining.configure",
                "params": [["version-rolling"],
                           {"version-rolling.mask": "ffffffff",
                            "version-rolling.min-bit-count": _version_rolling_bit}]}
        }
        return asic_boost[self.asicBoost]

    def _method_subscribe(self):
        return {"id": self._get_id(), "method": "mining.subscribe", "params": ["PoolTester/1.0.0"]}

    def _method_authorize(self):
        if self.coinType == "BTC":
            return {"id": self._get_id(), "method": "mining.authorize", "params": [self.username[0], self.username[1]]}
        elif self.coinType == "BTM":
            return {"id": self._get_id(), "jsonrpc": "2.0", "method": "login",
                    "params": {"login": self.username[0], "pass": self.username[1], "agent": "PTS"}}

    def _send(self, inputs):
        print("-->%s" % inputs)
        try:
            self.sockets.sendall(json.dumps(inputs).encode("utf-8") + b"\n")
        except socket.timeout:
            return None
        return self._recv()

    def _recv(self):
        recv = b""
        while 1:
            try:
                recv += self.sockets.recv(1024)
            except socket.timeout:
                return
            if recv == b"":
                print("Pool close connection unexpected")
                break
            if int(recv[-1]) == 10:
                break
        for i in recv.decode("utf-8").split("\n"):
            if len(i) != 0:
                print(i)
                self.notifys.append(json.loads(i))
        return recv

    def _get_id(self):
        self.jobID += 1
        return self.jobID

    def connect(self, **kwargs):
        self.url = kwargs["url"]
        self.jobTime = kwargs["jobTime"]
        self.coinType = kwargs["coinType"]
        self._sock()

    def _sock(self):
        if self.sockets is None:
            self.sockets = socket.socket()
            (addr, port) = (self.url.split("://")[-1].split(":")[0], int(self.url.split("://")[-1].split(":")[1]))
            print("Address is %s:%s." % (addr, port))

            self.sockets.connect((addr, port))
            self.sockets.settimeout(3)
        else:
            return

    def test_process(self):
        self._send(self._method_subscribe())
        self.asicBoost = 0
        self._send(self._method_asic_boost())
        self.asicBoost = 1
        self._send(self._method_asic_boost())
        self._send(self._method_authorize())
        self._recv()
        self._recv()
        #self.sockets.close()
        return self.anylayser_pk()

    def notify_decode(self, notify):
        return decodeUNum(notify["params"][2][84:92])

    def anylayser_pk(self):
        report = {
            "status": False,
            "asicboost": False,
            "multiVersion": False,
            "asicboost_mask": 0x00000000,
            "extraNonce2": "00000000",
            "extraNonce2size": 0,
            "defaultDiff": 0,
            "height": 0,
            "prev_blkhash": None,
        }
        try:
            for i in self.notifys:
                if "method" in i:
                    if i["method"] == "mining.set_difficulty":
                        report["defaultDiff"] = i["params"][0]
                    elif i["method"] == "mining.notify":
                        report["prev_blkhash"] = i["params"][1]
                        report["height"] = self.notify_decode(i)
                    elif i["method"] == "mining.multi_version":
                        report["multiVersion"] = True
                elif isinstance(i["result"], dict):
                    report["asicboost"] = i["result"]["version-rolling"]
                    report["asicboost_mask"] = i["result"]["version-rolling.mask"]
                elif isinstance(i["result"], list):
                    report["extraNonce2size"] = i["result"][2]
                    report["extraNonce2"] = i["result"][1]
                #print(i)
            report["status"] = True
        except:
            report["status"] = False
        return report


if __name__ == "__main__":
    a = StratumTest()
    a.connect(url="stratum+tcp://hk.p2pcash.kz:9348", jobTime=15, coinType="BTC")
    print(a.test_process())
