use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::{prelude::*, types::PyType};

use crate::type_aliases::*;
use crate::utils::h3_dist_km;

#[pyclass]
#[derive(Clone)]
pub struct LinkTraversal {
    #[pyo3(get)]
    pub link_id: LinkId,

    pub start: Arc<GeoidString>,
    pub end: Arc<GeoidString>,

    #[pyo3(get)]
    pub distance_km: f64,
    #[pyo3(get)]
    pub speed_kmph: f64,
}

#[pymethods]
impl LinkTraversal {
    #[new]
    pub fn new(
        link_id: LinkId,
        start: GeoidString,
        end: GeoidString,
        distance_km: f64,
        speed_kmph: f64,
    ) -> Self {
        LinkTraversal {
            link_id,
            start: Arc::new(start),
            end: Arc::new(end),
            distance_km,
            speed_kmph,
        }
    }
    #[classmethod]
    fn build(
        _: &PyType,
        link_id: LinkId,
        start: GeoidString,
        end: GeoidString,
        speed_kmph: f64,
        distance_km: Option<f64>,
    ) -> PyResult<Self> {
        let dist = match distance_km {
            Some(d) => d,
            None => match h3_dist_km(&start, &end) {
                Err(e) => return Err(PyValueError::new_err(e.to_string())),
                Ok(d) => d,
            },
        };
        Ok(LinkTraversal::new(link_id, start, end, speed_kmph, dist))
    }

    #[getter]
    fn travel_time_seconds(&self) -> f64 {
        let time_hours = self.distance_km / self.speed_kmph;
        let time_seconds = time_hours * 3600.0;
        time_seconds
    }

    #[getter]
    fn start(&self) -> GeoidString {
        (*self.start).clone()
    }

    fn where_start(&self) {
        println!("{:p}", self.start);
    }

    fn where_end(&self) {
        println!("{:p}", self.end);
    }

    #[getter]
    fn end(&self) -> GeoidString {
        (*self.end).clone()
    }

    fn update_start(&self, start: GeoidString) -> LinkTraversal {
        let mut new_self = self.clone();
        let new_start = Arc::make_mut(&mut new_self.start);
        *new_start = start;
        new_self
    }

    fn update_end(&self, end: GeoidString) -> LinkTraversal {
        let mut new_self = self.clone();
        let new_end = Arc::make_mut(&mut new_self.end);
        *new_end = end;
        new_self
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use assert_approx_eq::assert_approx_eq;

    fn mock_link() -> LinkTraversal {
        LinkTraversal::new(
            "mock_link".to_string().into(),
            "8f26dc934cccc69".to_string().into(),
            "8f26dc934cc4cdb".to_string().into(),
            0.14,
            40.0,
        )
    }

    #[test]
    fn test_link_travel_time_seconds() {
        let link = mock_link();
        assert_approx_eq!(link.travel_time_seconds(), 12.6);
    }
}
