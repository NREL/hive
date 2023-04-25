use std::{collections::HashMap, sync::Arc};

use geo_types::coord;
use h3ron::H3Cell;
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyType},
};

use crate::type_aliases::*;
use crate::{
    entity_position::EntityPosition, membership::Membership, road_network::HaversineRoadNetwork,
};

#[pyclass]
#[derive(Clone)]
pub struct Base {
    id: Arc<BaseId>,
    position: Arc<EntityPosition>,
    membership: Arc<Membership>,

    total_stalls: Arc<usize>,
    available_stalls: Arc<usize>,

    station_id: Arc<Option<StationId>>,
}

impl Base {
    pub fn new(
        id: BaseId,
        geoid: GeoidString,
        road_network: HaversineRoadNetwork,
        station_id: Option<StationId>,
        stall_count: usize,
        membership: Option<Membership>,
    ) -> Self {
        Base {
            id: Arc::new(id),
            position: Arc::new(road_network.position_from_geoid(geoid)),
            membership: Arc::new(membership.unwrap_or_default()),
            total_stalls: Arc::new(stall_count),
            available_stalls: Arc::new(stall_count),
            station_id: Arc::new(station_id),
        }
    }
}

#[pymethods]
impl Base {
    pub fn copy(&self) -> Self {
        self.clone()
    }
    pub fn __copy__(&self) -> Self {
        self.clone()
    }
    pub fn __deepcopy__(&self, _memo: &PyDict) -> Self {
        self.clone()
    }

    #[getter]
    pub fn id(&self) -> BaseId {
        (*self.id).clone()
    }

    #[getter]
    pub fn position(&self) -> EntityPosition {
        (*self.position).clone()
    }

    #[getter]
    pub fn membership(&self) -> Membership {
        (*self.membership).clone()
    }

    #[getter]
    pub fn station_id(&self) -> Option<StationId> {
        (*self.station_id).clone()
    }

    #[getter]
    pub fn geoid(&self) -> GeoidString {
        (*self.position).geoid.clone()
    }

    #[getter]
    pub fn total_stalls(&self) -> usize {
        *self.total_stalls
    }

    #[getter]
    pub fn available_stalls(&self) -> usize {
        *self.available_stalls
    }

    #[classmethod]
    pub fn build(
        _: &PyType,
        id: BaseId,
        geoid: GeoidString,
        road_network: HaversineRoadNetwork,
        stall_count: usize,
        station_id: Option<StationId>,
        membership: Option<Membership>,
    ) -> Self {
        Base::new(id, geoid, road_network, station_id, stall_count, membership)
    }

    #[classmethod]
    pub fn from_row(
        _: &PyType,
        row: HashMap<String, String>,
        road_network: HaversineRoadNetwork,
    ) -> PyResult<Self> {
        let base_id = row
            .get(&"base_id".to_string())
            .ok_or(PyValueError::new_err(
                "cannot load base without a base_id value",
            ))?;
        let lat_string = row.get(&"lat".to_string()).ok_or(PyValueError::new_err(
            "cannot load base without a lat value",
        ))?;
        let lat = lat_string.parse().map_err(|e| PyValueError::new_err(e))?;

        let lon_string = row.get(&"lon".to_string()).ok_or(PyValueError::new_err(
            "cannot load base without a lon value",
        ))?;
        let lon = lon_string.parse().map_err(|e| PyValueError::new_err(e))?;
        let stall_count_string =
            row.get(&"stall_count".to_string())
                .ok_or(PyValueError::new_err(
                    "cannot load base without a stall count value",
                ))?;

        let stall_count = stall_count_string
            .parse::<usize>()
            .map_err(|e| PyValueError::new_err(e))?;

        let h3cell =
            H3Cell::from_coordinate(coord! {x: lon, y: lat}, road_network.sim_h3_resolution)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;

        let station_id = match row.get("station_id") {
            Some(sid) => sid,
            None => "none",
        }
        .to_string();

        Ok(Base::new(
            base_id.to_owned().into(),
            h3cell.to_string().into(),
            road_network,
            Some(station_id.into()),
            stall_count,
            Some(Membership::default()),
        ))
    }

    pub fn has_available_stall(&self, membership: Membership) -> bool {
        *self.available_stalls > 0 && self.membership.grant_access_to_membership(&membership)
    }

    pub fn checkout_stall(&self) -> Option<Base> {
        if *self.available_stalls == 0 {
            return None;
        } else {
            let mut new_self = self.clone();
            let new_stalls = Arc::make_mut(&mut new_self.available_stalls);
            *new_stalls = *new_stalls - 1;
            Some(new_self)
        }
    }

    pub fn return_stall(&self) -> (Option<PyErr>, Option<Base>) {
        if (*self.available_stalls + 1) > *self.total_stalls {
            let err = PyValueError::new_err("base already has max stalls");
            (Some(err), None)
        } else {
            let mut new_self = self.clone();
            let new_stalls = Arc::make_mut(&mut new_self.available_stalls);
            *new_stalls = *new_stalls + 1;
            (None, Some(new_self))
        }
    }

    pub fn set_membership(&self, member_ids: Vec<MembershipId>) -> PyResult<Base> {
        let mut new_self = self.clone();
        let new_membership = Arc::make_mut(&mut new_self.membership);
        *new_membership = Membership::_from_tuple(member_ids).map_err(PyValueError::new_err)?;
        Ok(new_self)
    }

    pub fn add_membership(&self, membership_id: MembershipId) -> PyResult<Base> {
        let mut new_self = self.clone();
        let new_membership = Arc::make_mut(&mut new_self.membership);
        *new_membership = new_membership.add_membership(membership_id)?;
        Ok(new_self)
    }
}

#[cfg(test)]
mod tests {
    use geo_types::coord;

    use super::*;

    fn mock_base() -> Base {
        let mock_geoid = H3Cell::from_coordinate(coord! {x: 30.0, y: -100.0}, 15)
            .unwrap()
            .to_string();
        let mock_network = HaversineRoadNetwork {
            sim_h3_resolution: 15,
        };
        Base::new(
            "mock_base".to_string().into(),
            mock_geoid.into(),
            mock_network,
            None,
            5,
            Some(Membership::default()),
        )
    }

    #[test]
    fn test_available_stalls() {
        let mock_base = mock_base();
        assert!(mock_base.has_available_stall(Membership::default()) == true)
    }

    #[test]
    fn test_checkout_stall() {
        let mock_base = mock_base();
        match mock_base.checkout_stall() {
            Some(base_less_stall) => assert!(base_less_stall.available_stalls() == 4),
            None => panic!("base should not be None in this case"),
        }
    }
}
