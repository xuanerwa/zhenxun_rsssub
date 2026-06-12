from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RssImage:
    raw: bytes | None = None
    url: str | None = None
    name: str = "image.png"
    missing_text: str = ""
    bytes_used: int = 0
    failed: bool = False

    @property
    def available(self) -> bool:
        return bool(self.raw or (self.url and not self.failed))


@dataclass(slots=True)
class RssVideo:
    raw: bytes | None = None
    url: str | None = None
    name: str = "video.mp4"
    missing_text: str = ""
    bytes_used: int = 0
    failed: bool = False
    mimetype: str = "video/mp4"

    @property
    def available(self) -> bool:
        return bool(self.raw or (self.url and not self.failed))


@dataclass(slots=True)
class RssMessage:
    text: str = ""
    images: list[RssImage] = field(default_factory=list)
    videos: list[RssVideo] = field(default_factory=list)
    link: str = ""
    nodes: list["RssMessage"] = field(default_factory=list)

    def append_text(self, text: str) -> None:
        self.text += text

    def extend_images(self, images: list[RssImage]) -> None:
        self.images.extend(images)

    def extend_videos(self, videos: list[RssVideo]) -> None:
        self.videos.extend(videos)

    def plain_text(self) -> str:
        parts = [self.text] if self.text else []
        if self.link:
            parts.append(self.link)
        for image in self.images:
            if not image.available and image.missing_text:
                parts.append(image.missing_text)
        for video in self.videos:
            if not video.available and video.missing_text:
                parts.append(video.missing_text)
        return "\n".join(part for part in parts if part)

    def is_empty(self) -> bool:
        return (
            not self.text
            and not self.link
            and not self.images
            and not self.videos
            and not self.nodes
        )


def with_title(title: str, message: RssMessage) -> RssMessage:
    prefix = f"{title}\n\n" if title else ""
    return RssMessage(
        text=prefix + message.text,
        images=list(message.images),
        videos=list(message.videos),
        link=message.link,
        nodes=list(message.nodes),
    )
