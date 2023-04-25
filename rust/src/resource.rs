use std::sync::Arc;

use pyo3::{prelude::*, types::PyDict};

use crate::membership::Membership;
use crate::type_aliases::*;

#[pyclass]
#[derive(Clone)]
pub struct Resource {
    id: Arc<PassengerId>,
    origin: Arc<GeoidString>,
    destination: Arc<GeoidString>,
    departure_time: Arc<SimTime>,
    membership: Arc<Membership>,
    vehicle_id: Arc<Option<VehicleId>>,
}

impl Resource {
    pub fn new(
        id: PassengerId,
        origin: GeoidString,
        destination: GeoidString,
        departure_time: SimTime,
        membership: Option<Membership>,
        vehicle_id: Option<VehicleId>,
    ) -> Self {
        Resource {
            id: Arc::new(id),
            origin: Arc::new(origin),
            destination: Arc::new(destination),
            departure_time: Arc::new(departure_time),
            membership: Arc::new(membership.unwrap_or_default()),
            vehicle_id: Arc::new(vehicle_id),
        }
    }
}

#[pymethods]
impl Resource {
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
    pub fn id(&self) -> PassengerId {
        (*self.id).clone()
    }

    #[getter]
    pub fn origin(&self) -> GeoidString {
        (*self.origin).clone()
    }

    #[getter]
    pub fn destination(&self) -> GeoidString {
        (*self.destination).clone()
    }

    #[getter]
    pub fn departure_time<'a>(&'a self, py: Python<'a>) -> PyResult<&PyAny> {
        let locals = PyDict::new(py);
        let sim_time_mod = PyModule::import(py, "nrel.hive.model.sim_time")?;
        locals.set_item("SimTime", sim_time_mod.getattr("SimTime")?)?;
        locals.set_item("departure_time", (*self.departure_time).clone().into_py(py))?;
        py.eval("SimTime(departure_time)", None, Some(locals))
    }

    #[getter]
    pub fn membership(&self) -> Membership {
        (*self.membership).clone()
    }

    #[getter]
    pub fn vehicle_id(&self) -> Option<VehicleId> {
        (*self.vehicle_id).clone()
    }

    #[new]
    fn py_new(
        id: PassengerId,
        origin: GeoidString,
        destination: GeoidString,
        departure_time: SimTime,
        membership: Option<Membership>,
        vehicle_id: Option<VehicleId>,
    ) -> Self {
        Resource::new(
            id,
            origin,
            destination,
            departure_time,
            membership,
            vehicle_id,
        )
    }

    pub fn add_vehicle_id(&self, vehicle_id: VehicleId) -> Self {
        Resource {
            id: self.id.clone(),
            origin: self.origin.clone(),
            destination: self.destination.clone(),
            departure_time: self.departure_time.clone(),
            membership: self.membership.clone(),
            vehicle_id: Arc::new(Some(vehicle_id)),
        }
    }
}
