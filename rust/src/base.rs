use std::{collections::HashMap, sync::Arc};

use geo_types::coord;
use h3ron::H3Cell;
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyType},
};

use crate::{
    entity_position::EntityPosition, geoid::GeoidString, membership::Membership,
    road_network::HaversineRoadNetwork, station::StationId,
};

pub type BaseId = String;

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
        self.position.geoid.clone()
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

    #[classmethod]
    pub fn from_row(
        _: &PyType,
        row: HashMap<String, String>,
        road_network: HaversineRoadNetwork,
    ) -> PyResult<Self> {
        let base_id = match row.get(&"base_id".to_string()) {
            Some(base_id) => base_id,
            None => {
                return Err(PyValueError::new_err(
                    "cannot load base without a base_id value",
                ))
            }
        }
        .to_owned();
        let lat_string = match row.get(&"lat".to_string()) {
            Some(l) => l,
            None => {
                return Err(PyValueError::new_err(
                    "cannot load base without a lat value",
                ))
            }
        };
        let lat = lat_string.parse().map_err(|e| PyValueError::new_err(e))?;

        let lon_string = match row.get(&"lon".to_string()) {
            Some(l) => l,
            None => {
                return Err(PyValueError::new_err(
                    "cannot load base without a lon value",
                ))
            }
        };
        let lon = lon_string.parse().map_err(|e| PyValueError::new_err(e))?;

        let stall_count_string = match row.get(&"stall_count".to_string()) {
            Some(sc) => sc,
            None => {
                return Err(PyValueError::new_err(
                    "cannot load base without a stall_count value",
                ))
            }
        };
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

        Ok(Base {
            id: Arc::new(base_id),
            position: Arc::new(road_network.position_from_geoid(h3cell.to_string())),
            membership: Arc::new(Membership::default()),
            total_stalls: Arc::new(stall_count),
            available_stalls: Arc::new(stall_count),
            station_id: Arc::new(Some(station_id)),
        })
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

    pub fn set_membership(&self, member_ids: Vec<String>) -> PyResult<Base> {
        let mut new_self = self.clone();
        let new_membership = Arc::make_mut(&mut new_self.membership);
        *new_membership = Membership::_from_tuple(member_ids).map_err(PyValueError::new_err)?;
        Ok(new_self)
    }

    pub fn add_membership(&self, membership_id: String) -> PyResult<Base> {
        let mut new_self = self.clone();
        let new_membership = Arc::make_mut(&mut new_self.membership);
        *new_membership = new_membership.add_membership(membership_id)?;
        Ok(new_self)
    }
}
