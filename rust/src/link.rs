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
    #[pyo3(get)]
    pub start: GeoidString,
    #[pyo3(get)]
    pub end: GeoidString,

    #[pyo3(get)]
    pub distance_km: f64,
    #[pyo3(get)]
    pub speed_kmph: f64,
}

#[pymethods]
impl LinkTraversal {
    #[new]
    fn new(
        link_id: String,
        start: GeoidString,
        end: GeoidString,
        distance_km: f64,
        speed_kmph: f64,
    ) -> Self {
        LinkTraversal {
            link_id,
            start,
            end,
            distance_km,
            speed_kmph,
        }
    }
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

    fn update_start(&self, new_start: GeoidString) -> Self {
        LinkTraversal {
            link_id: self.link_id.clone(),
            start: new_start,
            end: self.end.clone(),
            distance_km: self.distance_km,
            speed_kmph: self.speed_kmph,
        }
    }

    fn update_end(&self, new_end: GeoidString) -> Self {
        LinkTraversal {
            link_id: self.link_id.clone(),
            start: self.start.clone(),
            end: new_end,
            distance_km: self.distance_km,
            speed_kmph: self.speed_kmph,
        }
    }
}
