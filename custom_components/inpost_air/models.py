from dataclasses import dataclass


class ParcelLocker:
    """ParcelLocker class."""

    def __init__(self, locker_code: str, locker_id: str) -> None:
        """Init class."""
        self.locker_code = locker_code
        self.locker_id = locker_id


@dataclass
class InPostAirPointCoordinates:
    """
    Represents the coordinates of an InPost Air point.

    Attributes:
        a (float): The latitude coordinate.
        o (float): The longitude coordinate.
    """

    a: float
    o: float


@dataclass
class InPostAirPoint:
    n: str
    t: int
    d: str
    m: str
    q: str
    f: str
    c: str
    g: str
    e: str
    r: str
    o: str
    b: str
    h: str
    i: str
    l: InPostAirPointCoordinates  # noqa: E741
    p: int
    s: int
