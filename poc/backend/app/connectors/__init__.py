from app.connectors.base import Connector
from app.connectors.international import (
    EGDIConnector,
    GIIConnector,
    HDIConnector,
    OpenAlexConnector,
    WorldBankConnector,
)
from app.connectors.ipvn import IPVietnamConnector
from app.connectors.neac import NEACConnector

REGISTRY: dict[str, Connector] = {
    c.name: c
    for c in (
        GIIConnector(),
        EGDIConnector(),
        HDIConnector(),
        IPVietnamConnector(),
        OpenAlexConnector(),
        WorldBankConnector(),
        NEACConnector(),
    )
}
