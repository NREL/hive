use pyo3::prelude::*;

pub mod base;
pub mod station;
pub mod entity_position;
pub mod geoid;
pub mod link;
pub mod membership;
pub mod road_network;
pub mod utils;

use base::Base;
use entity_position::EntityPosition;
use geoid::Geoid;
use link::LinkTraversal;
use membership::Membership;
use road_network::HaversineRoadNetwork;

/// A Python module implemented in Rust.
#[pymodule]
fn hive_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Membership>()?;
    m.add_class::<HaversineRoadNetwork>()?;
    m.add_class::<Geoid>()?;
    m.add_class::<EntityPosition>()?;
    m.add_class::<LinkTraversal>()?;
    m.add_class::<Base>()?;
    Ok(())
}
