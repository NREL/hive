use pyo3::{prelude::*, types::PyType};

use serde::{Deserialize, Serialize};

use crate::geoid::GeoidString;
use crate::road_network::LinkId;
use crate::utils::h3_dist_km;

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct LinkTraversal {
    #[pyo3(get)]
    pub link_id: LinkId,
    pub start: GeoidString,
    pub end: GeoidString,

    pub distance_km: f64,
    pub speed_kmph: f64,
}

#[pymethods]
impl LinkTraversal {
    #[classmethod]
    fn build(
        _: &PyType,
        link_id: String,
        start: GeoidString,
        end: GeoidString,
        speed_kmph: f64,
        distance_km: Option<f64>,
    ) -> PyResult<Self> {
        let dist = match distance_km {
            Some(d) => d,
            None => h3_dist_km(&start, &end).unwrap(),
        };
        Ok(LinkTraversal {
            link_id: link_id,
            start: start,
            end: end,
            speed_kmph: speed_kmph,
            distance_km: dist,
        })
    }

    #[getter]
    fn travel_time_seconds(&self) -> f64 {
        let time_hours = self.distance_km / self.speed_kmph;
        let time_seconds = time_hours * 3600.0;
        time_seconds
    }
}
