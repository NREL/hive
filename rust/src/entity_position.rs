use std::collections::HashMap;

use pyo3::{prelude::*, types::PyDict};

use crate::type_aliases::*;

#[pyclass]
#[derive(PartialEq, Clone)]
pub struct EntityPosition {
    #[pyo3(get)]
    pub link_id: LinkId,
    #[pyo3(get)]
    pub geoid: GeoidString,
}

#[pymethods]
impl EntityPosition {
    #[new]
    fn new(link_id: LinkId, geoid: GeoidString) -> PyResult<Self> {
        Ok(EntityPosition {
            link_id: link_id,
            geoid: geoid,
        })
    }

    // the following methods are needed to support hive reporting

    fn _asdict(&self) -> HashMap<String, String> {
        let mut dict = HashMap::new();
        dict.insert("link_id".to_string(), self.link_id.to_owned());
        dict.insert("geoid".to_string(), self.geoid.to_owned());
        dict
    }

    pub fn copy(&self) -> Self {
        self.clone()
    }
    pub fn __copy__(&self) -> Self {
        self.clone()
    }
    pub fn __deepcopy__(&self, _memo: &PyDict) -> Self {
        self.clone()
    }
}
