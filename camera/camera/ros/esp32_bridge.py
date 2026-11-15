"""ROS observations to the existing TCP observation protocol, with local expiry."""
import json
import time
import uuid

from rclpy.node import Node
from std_msgs.msg import Bool, String

from camera.pi_vision import ObservationClient, encode_observation
from .common import STATUS_QOS, positive, run


class Esp32Bridge(Node):
    def __init__(self, **kwargs):
        super().__init__("esp32_bridge", **kwargs)
        for name, value in dict(host="", port=5000, send_rate_hz=10.0,
                                stale_timeout_sec=1.0, observation_topic="/vision/observations").items():
            self.declare_parameter(name, value)
        value = lambda name: self.get_parameter(name).value
        host, port = value("host"), int(value("port"))
        if not host or not 1 <= port <= 65535:
            raise ValueError("An ESP32/bench-server host and port 1..65535 are required")
        self.timeout = positive(value("stale_timeout_sec"), "stale_timeout_sec")
        self.client = ObservationClient(host, port)
        self.latest = None
        self.received = 0.0
        self.session, self.seq = "bridge-" + uuid.uuid4().hex, 0
        self.status = self.create_publisher(Bool, "/esp32/link_available", STATUS_QOS)
        self.status.publish(Bool(data=False))
        self.create_subscription(String, value("observation_topic"), self.receive, 1)
        self.create_timer(1 / positive(value("send_rate_hz"), "send_rate_hz"), self.send_latest)

    def receive(self, message):
        try:
            data = json.loads(message.data)
            if data["v"] != 1 or data["type"] != "vision" or not isinstance(data["frame_ok"], bool):
                raise ValueError("Unsupported observation schema")
            # Validate framing, size and nonfinite numbers before caching a payload.
            payload = (json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n").encode()
            if len(payload) > 65536:
                raise ValueError("Observation too large")
            self.latest, self.received = payload, time.monotonic()
        except (ValueError, KeyError, TypeError) as exc:
            self.latest = None
            self.get_logger().error(f"Invalid ROS observation: {exc}")

    def invalid_observation(self):
        payload = encode_observation(self.session, self.seq, False, 0, 0, [], False, time.monotonic_ns())
        self.seq += 1
        return payload

    def send_latest(self):
        payload = self.latest
        if payload is None or time.monotonic() - self.received > self.timeout:
            payload = self.invalid_observation()
        self.status.publish(Bool(data=self.client.send(payload)))

    def destroy_node(self):
        self.client.send(self.invalid_observation())
        self.client.close()
        if self.context.ok():
            self.status.publish(Bool(data=False))
        return super().destroy_node()


def main(args=None):
    run(Esp32Bridge, args)
