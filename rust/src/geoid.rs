use std::str::FromStr;

use anyhow::Result;
use h3ron::H3Cell;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::type_aliases::*;

#[pyclass]
#[derive(PartialEq, Copy, Clone, Serialize, Deserialize)]
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

impl Geoid {
    pub fn from_string(string: GeoidString) -> Result<Self> {
        let h3_cell = H3Cell::from_str(string.as_str())?;
        Ok(Geoid { h3_cell })
    }
}
