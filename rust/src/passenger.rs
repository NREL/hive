use std::sync::Arc;

use pyo3::{
    prelude::*,
    types::{PyDict, PyType},
};

use crate::membership::Membership;
use crate::type_aliases::*;

#[pyclass]
#[derive(Clone)]
pub struct Passenger {
    id: Arc<PassengerId>,
    origin: Arc<GeoidString>,
    destination: Arc<GeoidString>,
    departure_time: Arc<SimTime>,
    membership: Arc<Membership>,
    vehicle_id: Arc<Option<VehicleId>>,
}

impl Passenger {
    pub fn new(
        id: PassengerId,
        origin: GeoidString,
        destination: GeoidString,
        departure_time: SimTime,
        membership: Option<Membership>,
        vehicle_id: Option<VehicleId>,
    ) -> Self {
        Passenger {
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
impl Passenger {
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
        locals.set_item("departure_time", (*self.departure_time).clone())?;
        py.eval("SimTime(departure_time)", None, Some(locals))
    }

    pub fn membership(&self) -> Membership {
        (*self.membership).clone()
    }

    pub fn vehicle_id(&self) -> Option<VehicleId> {
        (*self.vehicle_id).clone()
    }

    #[classmethod]
    pub fn build(
        _cls: &PyType,
        id: PassengerId,
        origin: GeoidString,
        destination: GeoidString,
        departure_time: SimTime,
        membership: Option<Membership>,
        vehicle_id: Option<VehicleId>,
    ) -> Self {
        Passenger::new(
            id,
            origin,
            destination,
            departure_time,
            membership,
            vehicle_id,
        )
    }
}
