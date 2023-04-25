use std::collections::HashMap;

use pyo3::{class::basic::CompareOp, prelude::*, types::PyDict};

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

    fn __richcmp__(&self, other: &Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => (self == other).into_py(py),
            CompareOp::Ne => (self != other).into_py(py),
            _ => py.NotImplemented(),
        }
    }

    // the following methods are needed to support hive reporting

    fn _asdict(&self) -> HashMap<String, String> {
        let mut dict: HashMap<String, String> = HashMap::new();
        dict.insert("link_id".to_string(), self.link_id.to_owned().into());
        dict.insert("geoid".to_string(), self.geoid.to_owned().into());
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
