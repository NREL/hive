use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::geoid::Geoid;

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct EntityPosition {
    #[pyo3(get)]
    link_id: String,
    #[pyo3(get)]
    geoid: Geoid,
}
