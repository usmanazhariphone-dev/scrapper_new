from typing import List
from .base import BaseAdapter
from .afak import AFAKAdapter
from .bloomchic import BloomChicAdapter
from .boden import BodenAdapter
from .brakeburn import BrakeburnAdapter
from .costco import CostcoAdapter
from .crazyclearance import CrazyClearanceAdapter
from .europa import EuropaAdapter
from .next_adapter import NextAdapter


def get_all_adapters(core=None) -> List[BaseAdapter]:
    adapters = [
        AFAKAdapter(),
        BloomChicAdapter(),
        BodenAdapter(),
        BrakeburnAdapter(),
        CostcoAdapter(),
        CrazyClearanceAdapter(),
        EuropaAdapter(),
        NextAdapter(),
    ]
    for a in adapters:
        a.core = core
    return adapters
