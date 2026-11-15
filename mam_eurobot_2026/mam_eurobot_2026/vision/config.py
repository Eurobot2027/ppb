"""Camera-frame selection shared by the inherited ROS vision nodes."""


def lookup_camera_config(cfg, image_topic):
    for camera in cfg.get("cameras", []):
        if camera.get("image_topic") == image_topic:
            return camera
    source = cfg.get("image_sources", {}).get(image_topic)
    if source and source.get("frame_id"):
        return {"image_topic": image_topic, **source}
    raise ValueError(f"No camera/frame configured for image topic {image_topic!r}")
