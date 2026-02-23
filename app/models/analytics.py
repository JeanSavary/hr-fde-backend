from pydantic import BaseModel


class NegotiationDepthBucket(BaseModel):
    round: str
    pct: int


class CarrierObjection(BaseModel):
    reason: str
    count: int
    pct: int


class TopLane(BaseModel):
    lane: str
    calls: int
    bookings: int
    avg_rate: str


class EquipmentDemandSupply(BaseModel):
    type: str
    demand: int
    supply: int


class AnalyticsResponse(BaseModel):
    negotiation_depth: list[NegotiationDepthBucket] = []
    carrier_objections: list[CarrierObjection] = []
    top_lanes: list[TopLane] = []
    equipment_demand_supply: list[EquipmentDemandSupply] = []
