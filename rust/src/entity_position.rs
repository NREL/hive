use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::geoid::Geoid;

#[pyclass]
#[derive(PartialEq, Clone, Serialize, Deserialize)]
pub struct EntityPosition {
    #[pyo3(get)]
    pub link_id: String,
    #[pyo3(get)]
    pub geoid: Geoid,
}
