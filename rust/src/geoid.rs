use h3ron::H3Cell;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct Geoid {
    pub h3_cell: H3Cell,
}

#[pymethods]
impl Geoid {
    pub fn __str__(&self) -> String {
        self.h3_cell.to_string()
    }
    pub fn __repr__(&self) -> String {
        self.h3_cell.to_string()
    }
}
