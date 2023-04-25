use derive_alias::derive_alias;
use derive_more::{Add, Deref, Display, Div, From, Into, Sub};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::newtype_into_py;

derive_alias! {
    derive_pystruct => #[derive(Clone, Deref, Display, From, FromPyObject, Into)]
}

derive_pystruct! { pub struct BaseId(String); }
newtype_into_py!(BaseId);

derive_pystruct! { pub struct ChargerId(String); }
newtype_into_py!(ChargerId);

derive_pystruct! {
    #[derive(Div)]
    pub struct DistanceKm(f64);
}
newtype_into_py!(DistanceKm);

derive_pystruct! { pub struct EntityId(String); }
newtype_into_py!(EntityId);

derive_pystruct! {
    #[derive(PartialEq)]
    pub struct GeoidString(String);
}
newtype_into_py!(GeoidString);

derive_pystruct! {
    #[derive( PartialEq )]
    pub struct LinkId(String);
}
newtype_into_py!(LinkId);

derive_pystruct! { pub struct MechatronicsId(String); }
newtype_into_py!(MechatronicsId);

derive_pystruct! {
    #[derive(Deserialize, Eq, Hash, PartialEq, Serialize)]
    pub struct MembershipId(String);
}
newtype_into_py!(MembershipId);

derive_pystruct! {
    #[derive(Add, PartialEq, PartialOrd, Sub)]
    pub struct NumStalls(usize);
}
newtype_into_py!(NumStalls);

derive_pystruct! { pub struct PassengerId(String); }
newtype_into_py!(PassengerId);

derive_pystruct! { pub struct PowercurveId(String); }
newtype_into_py!(PowercurveId);

derive_pystruct! { pub struct PowertrainId(String); }
newtype_into_py!(PowertrainId);

derive_pystruct! { pub struct RequestId(String); }
newtype_into_py!(RequestId);

derive_pystruct! { pub struct ScheduleId(String); }
newtype_into_py!(ScheduleId);

derive_pystruct! {
    pub struct SpeedKmph(pub f64);
}
newtype_into_py!(SpeedKmph);

derive_pystruct! { pub struct SimTime(usize); }
newtype_into_py!(SimTime);

derive_pystruct! { pub struct StationId(String); }
newtype_into_py!(StationId);

derive_pystruct! { pub struct VehicleId(String); }
newtype_into_py!(VehicleId);

derive_pystruct! { pub struct VehicleTypeId(String); }
newtype_into_py!(VehicleTypeId);
